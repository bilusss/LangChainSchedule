"""
Węzły (nodes) dla grafów LangGraph
"""

from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from models import AgentState, DailySchedule


def create_agent_node(llm_with_tools: Any):
    """
    Tworzy węzeł agenta z podanym LLM.
    
    Args:
        llm_with_tools: LLM z przypisanymi narzędziami
    
    Returns:
        Funkcja węzła agenta
    """
    def agent_node(state: AgentState):
        """Agent decyduje czy użyć narzędzi czy odpowiedzieć bezpośrednio"""
        messages = state.get('messages', [])
        
        if not messages:
            return {"messages": []}
        
        last_msg = messages[-1] if messages else None
        
        # Jeśli ostatnia wiadomość to wynik narzędzia, LLM musi odpowiedzieć
        if isinstance(last_msg, ToolMessage):
            tool_result = last_msg.content
            
            processed_messages = []
            for m in messages:
                if isinstance(m, ToolMessage):
                    continue
                processed_messages.append(m)
            
            processed_messages.append(
                HumanMessage(content=f"Wynik z narzędzia: {tool_result}\n\nOdpowiedz użytkownikowi na podstawie tych danych.")
            )
            
            try:
                response = llm_with_tools.invoke(processed_messages)
                return {"messages": messages + [response]}
            except Exception as e:
                print(f"⚠️ Błąd po tool: {e}")
                fallback = AIMessage(content=f"Oto wyniki z kalendarza:\n\n{tool_result}")
                return {"messages": messages + [fallback]}
        
        try:
            response = llm_with_tools.invoke(messages)
            return {"messages": messages + [response]}
        except Exception as e:
            print(f"⚠️ Błąd w agent_node: {e}")
            error_response = AIMessage(content=f"Przepraszam, wystąpił błąd: {str(e)}")
            return {"messages": messages + [error_response]}
    
    return agent_node


def should_use_tools(state: AgentState) -> str:
    """Sprawdza czy ostatnia wiadomość wymaga użycia narzędzi"""
    messages = state.get('messages', [])
    if not messages:
        return "end"
    
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    return "end"


def create_planner_node(structured_llm: Any):
    """
    Tworzy węzeł planera z podanym LLM.
    
    Args:
        structured_llm: LLM ze strukturyzowanym outputem
    
    Returns:
        Funkcja węzła planera
    """
    def planner_node(state: AgentState):
        print(f"\n🧠 [PLANNER] Generuję plan (Próba {state['retry_count'] + 1})...")
        
        system_msg = """Jesteś ekspertem planowania. Stwórz realistyczny plan dnia.
        Jeśli otrzymasz FEEDBACK o błędach, popraw je.
        Możesz też wykorzystać informacje z Google Calendar do lepszego planowania."""
        
        user_msg = f"""
        ZADANIA: {state['tasks']}
        REGUŁY: {state['rules']}
        FEEDBACK: {state.get('feedback', 'Brak')}
        """
        
        try:
            plan = structured_llm.invoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=user_msg)
            ])
            return {"schedule": plan, "retry_count": state['retry_count'] + 1}
        except Exception as e:
            print(f"⚠️ BŁĄD API: {e}")
            return {"schedule": None, "retry_count": state['retry_count'] + 1}
    
    return planner_node


def reviewer_node(state: AgentState):
    """Weryfikuje wygenerowany plan"""
    print("💎 [REVIEWER] Weryfikacja...")
    
    schedule = state.get('schedule')
    
    if not schedule:
        error_msg = "BŁĄD KRYTYCZNY: Model nie wygenerował planu (zwrócił None)."
        print(f"❌ {error_msg}")
        return {"feedback": "FATAL_ERROR"}

    items = schedule.items
    
    if len(items) < 3:
        print("❌ Plan zbyt krótki")
        return {"feedback": "Plan ma za mało elementów"}
    
    print("✅ Plan zaakceptowany.")
    return {"feedback": "OK"}


def should_continue(state: AgentState) -> str:
    """Decyduje czy kontynuować planowanie"""
    fb = state.get('feedback', "")
    if fb == "OK":
        return "end"
    if fb == "FATAL_ERROR":
        return "end"
    if state['retry_count'] > 3:
        return "end"
    return "retry"
