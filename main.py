import os
import getpass
from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Importy Google i LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

# Import narzędzi Google Calendar
from tools import get_calendar_tools

# --- 1. KONFIGURACJA KLUCZA ---
load_dotenv()  # Ładuje zmienne z pliku .env

# Użyj GOOGLE_API_KEY_LLM z .env dla modelu Gemini (LLM)
# GOOGLE_API_KEY_CLOUD jest używany osobno w tools/google_calendar.py dla Calendar API
if "GOOGLE_API_KEY" not in os.environ:
    llm_key = os.getenv("GOOGLE_API_KEY_LLM")
    if llm_key:
        os.environ["GOOGLE_API_KEY"] = llm_key
        print("✅ Załadowano GOOGLE_API_KEY_LLM dla LLM (Gemini)")
    else:
        raw_key = getpass.getpass("Podaj Google API Key: ")
        os.environ["GOOGLE_API_KEY"] = raw_key.strip()

# --- 2. STRUKTURY DANYCH ---
class ScheduleItem(BaseModel):
    start_time: str = Field(description="Godzina rozpoczęcia HH:MM")
    end_time: str = Field(description="Godzina zakończenia HH:MM")
    activity: str = Field(description="Nazwa czynności")
    location: str = Field(description="Miejsce (np. Dom, Uczelnia)")
    note: Optional[str] = Field(description="Krótki opis")

class DailySchedule(BaseModel):
    items: List[ScheduleItem]
    reasoning: str = Field(description="Wyjaśnienie planu")

class AgentState(TypedDict):
    messages: List[BaseMessage]
    tasks: List[str]
    rules: List[str]
    schedule: Optional[DailySchedule]
    feedback: str
    retry_count: int

# --- 3. MODEL Z NARZĘDZIAMI ---
llm = ChatGoogleGenerativeAI(
    # model="gemini-2.5-flash",
    model="gemini-2.5-flash-lite",
    temperature=0.3,
    max_retries=2,
)

# Pobierz narzędzia Google Calendar
calendar_tools = get_calendar_tools()

# LLM z bindowanymi narzędziami
llm_with_tools = llm.bind_tools(calendar_tools)

# LLM do strukturyzowanego outputu (planowanie)
structured_llm = llm.with_structured_output(DailySchedule)


# --- 4. AGENT NODE (Obsługuje rozmowę i narzędzia) ---
def agent_node(state: AgentState):
    """Agent decyduje czy użyć narzędzi czy odpowiedzieć bezpośrednio"""
    from langchain_core.messages import ToolMessage
    
    messages = state.get('messages', [])
    
    if not messages:
        return {"messages": []}
    
    # Sprawdź czy ostatnia wiadomość to ToolMessage - jeśli tak, musimy przetworzyć wyniki
    last_msg = messages[-1] if messages else None
    
    # Jeśli ostatnia wiadomość to wynik narzędzia, LLM musi odpowiedzieć na podstawie wyniku
    if isinstance(last_msg, ToolMessage):
        # Znajdź poprzednią wiadomość AI z tool_calls
        tool_result = last_msg.content
        
        # Stwórz nową listę wiadomości dla LLM
        # Gemini potrzebuje: system, human, [ai z tool_calls, tool_message]
        processed_messages = []
        for m in messages:
            if isinstance(m, ToolMessage):
                # Konwertuj ToolMessage na format zrozumiały dla Gemini
                continue  # Pomijamy, dodamy ręcznie
            processed_messages.append(m)
        
        # Dodaj wynik narzędzia jako kontekst
        processed_messages.append(HumanMessage(content=f"Wynik z narzędzia: {tool_result}\n\nOdpowiedz użytkownikowi na podstawie tych danych."))
        
        try:
            response = llm_with_tools.invoke(processed_messages)
            return {"messages": messages + [response]}
        except Exception as e:
            print(f"⚠️ Błąd po tool: {e}")
            # Fallback - odpowiedz bezpośrednio z wynikiem
            fallback = AIMessage(content=f"Oto wyniki z kalendarza:\n\n{tool_result}")
            return {"messages": messages + [fallback]}
    
    try:
        response = llm_with_tools.invoke(messages)
        return {"messages": messages + [response]}
    except Exception as e:
        print(f"⚠️ Błąd w agent_node: {e}")
        error_response = AIMessage(content=f"Przepraszam, wystąpił błąd: {str(e)}")
        return {"messages": messages + [error_response]}


def should_use_tools(state: AgentState):
    """Sprawdza czy ostatnia wiadomość wymaga użycia narzędzi"""
    messages = state.get('messages', [])
    if not messages:
        return "end"
    
    last_message = messages[-1]
    
    # Sprawdź czy AI chce użyć narzędzi
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    return "end"


# --- 5. PLANNER NODE (Tworzenie harmonogramu) ---
def planner_node(state: AgentState):
    print(f"\n🧠 [GEMINI PLANNER] Generuję plan (Próba {state['retry_count'] + 1})...")
    
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
        print(f"⚠️ BŁĄD API GEMINI: {e}")
        return {"schedule": None, "retry_count": state['retry_count'] + 1}


# --- 6. REVIEWER NODE ---
def reviewer_node(state: AgentState):
    print("💎 [REVIEWER] Weryfikacja...")
    
    schedule = state.get('schedule')
    
    if not schedule:
        error_msg = "BŁĄD KRYTYCZNY: Model nie wygenerował planu (zwrócił None)."
        print(f"❌ {error_msg}")
        return {"feedback": "FATAL_ERROR"}

    items = schedule.items
    
    # Prosta walidacja - sprawdź czy plan ma sens
    if len(items) < 3:
        print("❌ Plan zbyt krótki")
        return {"feedback": "Plan ma za mało elementów"}
    
    # Sprawdź czy są podstawowe elementy
    activities = [item.activity.lower() for item in items]
    has_morning = any('pobudka' in a or 'rano' in a or '8:00' in a for a in activities)
    
    print("✅ Plan zaakceptowany.")
    return {"feedback": "OK"}


# --- 7. GRAFY ---

# Graf dla chat z narzędziami (Google Calendar)
def create_chat_graph():
    """Tworzy graf dla interaktywnego chatu z narzędziami"""
    tool_node = ToolNode(calendar_tools)
    
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_use_tools,
        {"tools": "tools", "end": END}
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# Graf dla planowania harmonogramu
def create_planner_graph():
    """Tworzy graf dla automatycznego planowania"""
    workflow = StateGraph(AgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "reviewer")

    def should_continue(state: AgentState):
        fb = state.get('feedback', "")
        if fb == "OK": return "end"
        if fb == "FATAL_ERROR": return "end"
        if state['retry_count'] > 3: return "end"
        return "retry"

    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {"retry": "planner", "end": END}
    )

    return workflow.compile()


# --- 8. GŁÓWNA FUNKCJA INTERAKTYWNA ---
def interactive_chat():
    """Uruchamia interaktywny chat z dostępem do Google Calendar"""
    chat_app = create_chat_graph()
    
    system_message = SystemMessage(content="""Jesteś asystentem planowania z dostępem do Google Calendar.
Możesz:
- Sprawdzać wydarzenia w kalendarzu (get_calendar_events)
- Tworzyć nowe wydarzenia (create_calendar_event)
- Aktualizować istniejące wydarzenia (update_calendar_event)  
- Usuwać wydarzenia (delete_calendar_event)

Odpowiadaj po polsku. Używaj narzędzi gdy użytkownik pyta o kalendarz.""")
    
    messages = [system_message]
    
    print("\n" + "="*50)
    print("🗓️  ASYSTENT KALENDARZA GOOGLE")
    print("="*50)
    print("Dostępne komendy:")
    print("  - Wpisz pytanie o kalendarz")
    print("  - 'plan' - uruchom automatyczne planowanie dnia")
    print("  - 'exit' - wyjście")
    print("="*50 + "\n")
    
    while True:
        try:
            user_input = input("Ty: ").strip()
        except EOFError:
            break
            
        if not user_input:
            continue
            
        if user_input.lower() == 'exit':
            print("Do widzenia! 👋")
            break
            
        if user_input.lower() == 'plan':
            run_planner()
            continue
        
        messages.append(HumanMessage(content=user_input))
        
        state = {
            "messages": messages,
            "tasks": [],
            "rules": [],
            "schedule": None,
            "feedback": "",
            "retry_count": 0
        }
        
        try:
            result = chat_app.invoke(state)
            
            if result.get('messages'):
                # Znajdź ostatnią wiadomość AI
                ai_messages = [m for m in result['messages'] if isinstance(m, AIMessage)]
                if ai_messages:
                    last_ai = ai_messages[-1]
                    print(f"\n🤖 Asystent: {last_ai.content}\n")
                    messages = result['messages']
        except Exception as e:
            print(f"\n❌ Błąd: {e}\n")


def run_planner():
    """Uruchamia automatyczne planowanie dnia"""
    planner_app = create_planner_graph()
    
    print("\n--- PLANOWANIE DNIA ---")
    
    input_data = {
        "messages": [],
        "tasks": ["Siłownia", "Nauka", "Zajęcia na uczelni (13:15-14:45)"],
        "rules": ["Pobudka 8:00", "Siłownia 10m pieszo od domu", "Preferowany trening wieczorem", "Uczelnia 30m dojazdu autobusem"],
        "retry_count": 0,
        "feedback": "",
        "schedule": None
    }

    final = planner_app.invoke(input_data)

    print("\n--- WYGENEROWANY PLAN ---")
    if final.get('schedule'):
        for item in final['schedule'].items:
            print(f"{item.start_time}-{item.end_time}: {item.activity} ({item.location})")
    else:
        print("Brak planu do wyświetlenia.")
    print()


# --- 9. ENTRY POINT ---
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--plan":
        # Tryb tylko planowanie (stare zachowanie)
        run_planner()
    else:
        # Tryb interaktywny z kalendarzem
        interactive_chat()