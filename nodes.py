"""
Węzły (nodes) dla grafów LangGraph
"""

from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from models import AgentState, DailySchedule, PlannerState
from groq_planner import GroqPlanner, format_plan_for_display
from tools.google_calendar import get_calendar_events, create_calendar_event, update_calendar_event


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


# ============================================================================
# NOWE WĘZŁY DLA WORKFLOW: GROQ Planner -> Human Feedback -> Executor
# ============================================================================

def groq_planner_node(state: PlannerState) -> dict:
    """
    Węzeł GROQ Planner - generuje plan używając GROQ API.
    Ma dostęp do kalendarza i generuje harmonogram.
    """
    print("\n" + "=" * 60)
    print("🧠 [GROQ PLANNER] Rozpoczynam planowanie...")
    print("=" * 60)
    
    tasks = state.get("tasks", [])
    user_preferences = state.get("user_preferences", {})
    
    # Pobierz istniejące wydarzenia z kalendarza (14 dni)
    print("📅 Pobieram wydarzenia z kalendarza...")
    try:
        existing_events = get_calendar_events.invoke({
            "days_ahead": 14,
            "max_results": 50
        })
    except Exception as e:
        print(f"⚠️ Nie udało się pobrać kalendarza: {e}")
        existing_events = "Brak dostępu do kalendarza"
    
    print(f"\n📋 Zadania do zaplanowania: {tasks}")
    
    # Generuj plan z GROQ
    planner = GroqPlanner()
    plan = planner.generate_plan(
        tasks=tasks,
        existing_events=existing_events,
        user_preferences=user_preferences
    )
    
    # Sformatuj plan do wyświetlenia
    plan_display = format_plan_for_display(plan)
    
    # Zbuduj kontekst konwersacji dla executora
    context = f"""
=== KONTEKST PLANOWANIA ===
Zadania od użytkownika: {tasks}
Preferencje: {user_preferences}

=== ISTNIEJĄCE WYDARZENIA ===
{existing_events}

=== WYGENEROWANY PLAN ===
{plan_display}
"""
    
    return {
        "generated_plan": plan,
        "plan_display": plan_display,
        "existing_events": existing_events,
        "conversation_context": context,
        "retry_count": state.get("retry_count", 0) + 1
    }


def human_feedback_node(state: PlannerState) -> dict:
    """
    Węzeł Human Feedback - pyta użytkownika o akceptację planu.
    Jeśli plan zawiera modyfikacje istniejących wydarzeń, pyta o każdą z osobna.
    """
    print("\n" + "=" * 60)
    print("👤 [HUMAN FEEDBACK] Oczekuję decyzji użytkownika...")
    print("=" * 60)
    
    plan_display = state.get("plan_display", "Brak planu")
    plan = state.get("generated_plan", {})
    print(plan_display)
    
    # Sprawdź czy są modyfikacje istniejących wydarzeń
    events = plan.get("events", [])
    updates = [e for e in events if e.get("action") == "update"]
    approved_updates = []
    
    if updates:
        print("\n" + "!" * 60)
        print("⚠️  UWAGA: Plan zawiera MODYFIKACJE istniejących wydarzeń!")
        print("!" * 60)
        print("\nMusisz zatwierdzić każdą modyfikację osobno:\n")
        
        for i, update in enumerate(updates, 1):
            print(f"\n--- Modyfikacja {i}/{len(updates)} ---")
            print(f"📌 Wydarzenie ID: {update.get('event_id', '?')}")
            if update.get('summary'):
                print(f"📝 Nowa nazwa: {update.get('summary')}")
            print(f"🕐 Nowy czas: {update.get('start', '?')} - {update.get('end', '?')}")
            if update.get('reason'):
                print(f"💡 Powód: {update.get('reason')}")
            
            while True:
                choice = input(f"\nCzy zatwierdzasz tę modyfikację? [T/N]: ").strip().lower()
                if choice in ["t", "y", "tak", "yes", "1"]:
                    approved_updates.append(update)
                    print("✅ Modyfikacja zatwierdzona")
                    break
                elif choice in ["n", "nie", "no", "0"]:
                    print("❌ Modyfikacja odrzucona - wydarzenie zostanie pominięte")
                    break
                else:
                    print("⚠️ Wpisz T lub N")
    
    # Filtruj plan - zostaw tylko zatwierdzone modyfikacje
    new_events = [e for e in events if e.get("action", "create") == "create"]
    filtered_events = new_events + approved_updates
    
    # Zaktualizuj plan z filtrowanymi wydarzeniami
    filtered_plan = {**plan, "events": filtered_events}
    
    print("\n" + "-" * 60)
    print(f"📊 Podsumowanie: {len(new_events)} nowych + {len(approved_updates)} modyfikacji")
    print("-" * 60)
    print("\nCzy akceptujesz cały plan?")
    print("  [T/t/Y/y/tak/yes/1] - Zatwierdź i dodaj do kalendarza")
    print("  [N/n/nie/no/0]      - Odrzuć plan")
    print("  [R/r/retry]         - Wygeneruj ponownie")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\nTwoja decyzja: ").strip().lower()
        except EOFError:
            user_input = "n"
        
        if user_input in ["t", "y", "tak", "yes", "1", ""]:
            print("✅ Plan zatwierdzony! Przekazuję do executora...")
            return {
                "human_approved": True,
                "human_feedback": "Użytkownik zatwierdził plan",
                "generated_plan": filtered_plan  # Plan z tylko zatwierdzonymi modyfikacjami
            }
        elif user_input in ["n", "nie", "no", "0"]:
            print("❌ Plan odrzucony.")
            return {
                "human_approved": False,
                "human_feedback": "Użytkownik odrzucił plan"
            }
        elif user_input in ["r", "retry", "ponow", "jeszcze"]:
            # Pobierz feedback do poprawy
            feedback = input("Co chciałbyś zmienić? ").strip()
            print("🔄 Przekazuję do ponownego planowania...")
            return {
                "human_approved": None,  # None = retry
                "human_feedback": feedback if feedback else "Wygeneruj lepszy plan"
            }
        else:
            print("⚠️ Nierozpoznana opcja. Wpisz T/N/R")


def executor_node(state: PlannerState) -> dict:
    """
    Węzeł Executor - wprowadza zatwierdzony plan do Google Calendar.
    Obsługuje zarówno tworzenie nowych wydarzeń jak i modyfikację istniejących.
    Ma pełen kontekst konwersacji z GROQ.
    """
    print("\n" + "=" * 60)
    print("⚡ [EXECUTOR] Wprowadzam plan do Google Calendar...")
    print("=" * 60)
    
    # Executor ma dostęp do całego kontekstu
    context = state.get("conversation_context", "")
    plan = state.get("generated_plan", {})
    events = plan.get("events", [])
    
    if not events:
        print("❌ Brak wydarzeń do dodania")
        return {
            "execution_results": ["Brak wydarzeń do dodania"],
            "execution_complete": True
        }
    
    # Rozdziel na nowe i modyfikacje
    new_events = [e for e in events if e.get("action", "create") == "create"]
    updates = [e for e in events if e.get("action") == "update"]
    
    print(f"\n📝 Kontekst planowania:\n{context[:300]}...\n")
    print(f"📅 Do wykonania: {len(new_events)} nowych + {len(updates)} modyfikacji\n")
    
    results = []
    success_count = 0
    total = len(events)
    
    # 1. Najpierw wykonaj modyfikacje istniejących wydarzeń
    if updates:
        print("\n🔄 MODYFIKUJĘ ISTNIEJĄCE WYDARZENIA:\n")
        for i, event in enumerate(updates, 1):
            event_id = event.get("event_id", "")
            summary = event.get("summary")
            start = event.get("start", "")
            end = event.get("end", "")
            reason = event.get("reason", "Przeniesione przez AI Planner")
            
            print(f"  [{i}/{len(updates)}] Modyfikuję: {event_id[:8]}...")
            if reason:
                print(f"      Powód: {reason}")
            
            try:
                # Użyj update_calendar_event
                update_params = {
                    "event_id": event_id
                }
                if summary:
                    update_params["summary"] = summary
                if start:
                    update_params["start_time"] = start
                if end:
                    update_params["end_time"] = end
                if reason:
                    update_params["description"] = f"[Zmodyfikowane przez AI] {reason}"
                
                result = update_calendar_event.invoke(update_params)
                results.append(f"🔄 Modyfikacja {event_id[:8]}: {result}")
                success_count += 1
                print(f"      {result}")
            except Exception as e:
                error_msg = f"❌ Modyfikacja {event_id[:8]}: Błąd - {str(e)}"
                results.append(error_msg)
                print(f"      {error_msg}")
    
    # 2. Potem dodaj nowe wydarzenia
    if new_events:
        print("\n🆕 TWORZĘ NOWE WYDARZENIA:\n")
        for i, event in enumerate(new_events, 1):
            summary = event.get("summary", "Bez nazwy")
            start = event.get("start", "")
            end = event.get("end", "")
            description = event.get("description", "Automatycznie zaplanowane przez AI")
            
            print(f"  [{i}/{len(new_events)}] Dodaję: {summary}")
            
            try:
                result = create_calendar_event.invoke({
                    "summary": summary,
                    "start_time": start,
                    "end_time": end,
                    "description": description
                })
                results.append(f"✅ {summary}: {result}")
                success_count += 1
                print(f"      {result}")
            except Exception as e:
                error_msg = f"❌ {summary}: Błąd - {str(e)}"
                results.append(error_msg)
                print(f"      {error_msg}")
    
    print(f"\n{'=' * 60}")
    print(f"📊 PODSUMOWANIE: Wykonano {success_count}/{total} operacji")
    if updates:
        print(f"   🔄 Modyfikacje: {len([r for r in results if r.startswith('🔄')])}/{len(updates)}")
    if new_events:
        print(f"   🆕 Nowe: {len([r for r in results if r.startswith('✅')])}/{len(new_events)}")
    print("=" * 60)
    
    return {
        "execution_results": results,
        "execution_complete": True
    }


def should_continue_planner(state: PlannerState) -> str:
    """
    Decyduje o następnym kroku po human feedback.
    
    Returns:
        "executor" - jeśli plan zatwierdzony
        "planner"  - jeśli trzeba wygenerować ponownie
        "end"      - jeśli plan odrzucony lub limit prób
    """
    approved = state.get("human_approved")
    retry_count = state.get("retry_count", 0)
    
    if approved is True:
        return "executor"
    elif approved is None and retry_count < 3:
        return "planner"
    else:
        return "end"


def should_end_after_execution(state: PlannerState) -> str:
    """Zawsze kończy po wykonaniu"""
    return "end"
