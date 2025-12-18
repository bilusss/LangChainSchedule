#!/usr/bin/env python3
"""
Asystent Kalendarza Google z wyborem modelu LLM
Obsługuje: Gemini, Ollama, LM Studio, OpenAI
"""

import sys
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import select_provider_interactive, get_provider_from_env
from llm_factory import create_llm
from models import AgentState, DailySchedule
from graphs import create_chat_graph, create_planner_graph, create_groq_planner_graph
from tools import get_calendar_tools


def setup_llm(interactive: bool = True):
    """
    Konfiguruje LLM na podstawie wyboru użytkownika.
    
    Args:
        interactive: Czy pytać użytkownika o wybór
    
    Returns:
        Tuple (llm, llm_with_tools, structured_llm, tools)
    """
    if interactive:
        provider, model_name = select_provider_interactive()
    else:
        provider, model_name = get_provider_from_env()
    
    print(f"🔄 Inicjalizuję {provider.value} / {model_name}...")
    
    # Utwórz LLM
    llm = create_llm(provider, model_name)
    
    # Pobierz narzędzia Google Calendar
    tools = get_calendar_tools()
    
    # LLM z bindowanymi narzędziami
    llm_with_tools = llm.bind_tools(tools)
    
    # LLM do strukturyzowanego outputu (planowanie)
    structured_llm = llm.with_structured_output(DailySchedule)
    
    print(f"✅ Model {model_name} gotowy!\n")
    
    return llm, llm_with_tools, structured_llm, tools


def interactive_chat(llm_with_tools, tools, structured_llm):
    """Uruchamia interaktywny chat z dostępem do Google Calendar"""
    chat_app = create_chat_graph(llm_with_tools, tools)
    planner_app = create_planner_graph(structured_llm)
    
    system_message = SystemMessage(content="""Jesteś asystentem planowania z dostępem do Google Calendar.
Możesz:
- Sprawdzać wydarzenia w kalendarzu (get_calendar_events)
- Tworzyć nowe wydarzenia (create_calendar_event)
- Aktualizować istniejące wydarzenia (update_calendar_event)  
- Usuwać wydarzenia (delete_calendar_event)

Odpowiadaj po polsku. Używaj narzędzi gdy użytkownik pyta o kalendarz.""")
    
    messages = [system_message]
    
    print("\n" + "=" * 50)
    print("🗓️  ASYSTENT KALENDARZA GOOGLE")
    print("=" * 50)
    print("Dostępne komendy:")
    print("  - Wpisz pytanie o kalendarz")
    print("  - 'plan' - uruchom automatyczne planowanie dnia (stary system)")
    print("  - 'groq' - uruchom planowanie GROQ z akceptacją")
    print("  - 'exit' - wyjście")
    print("=" * 50 + "\n")
    
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
            run_planner(planner_app)
            continue
        
        if user_input.lower() == 'groq':
            run_groq_planner()
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
                ai_messages = [m for m in result['messages'] if isinstance(m, AIMessage)]
                if ai_messages:
                    last_ai = ai_messages[-1]
                    print(f"\n🤖 Asystent: {last_ai.content}\n")
                    messages = result['messages']
        except Exception as e:
            print(f"\n❌ Błąd: {e}\n")


def run_planner(planner_app):
    """Uruchamia automatyczne planowanie dnia"""
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


def run_groq_planner():
    """
    Uruchamia nowy workflow: GROQ Planner -> Human Feedback -> Executor
    
    Ten tryb:
    1. Pyta użytkownika o zadania i preferencje
    2. Pobiera wydarzenia z kalendarza
    3. Generuje plan używając GROQ (qwen/qwen3-32b)
    4. Wyświetla plan i pyta o akceptację
    5. Po zatwierdzeniu dodaje wydarzenia do Google Calendar
    """
    print("\n" + "=" * 60)
    print("🚀 GROQ PLANNER - Inteligentne Planowanie z GROQ")
    print("=" * 60)
    
    # Zbierz zadania od użytkownika
    print("\n📋 Podaj zadania do zaplanowania (wpisz 'koniec' aby zakończyć):")
    tasks = []
    while True:
        task = input(f"  Zadanie {len(tasks) + 1}: ").strip()
        if task.lower() in ['koniec', 'end', 'done', '']:
            if tasks:
                break
            print("  ⚠️ Dodaj przynajmniej jedno zadanie!")
            continue
        tasks.append(task)
    
    print(f"\n✅ Zebrano {len(tasks)} zadań: {tasks}")
    
    # Zbierz preferencje (opcjonalne)
    print("\n⚙️  Preferencje (Enter = domyślne):")
    
    sleep = input("  Godziny snu [23:00 - 7:00]: ").strip()
    deep_work = input("  Okna Deep Work [9:00-12:00, 15:00-18:00]: ").strip()
    block_duration = input("  Długość bloku nauki [1.5h]: ").strip()
    habits = input("  Stałe nawyki [Śniadanie 7:30, Obiad 13:00, Kolacja 19:00]: ").strip()
    
    user_preferences = {
        "sleep_schedule": sleep if sleep else "23:00 - 7:00",
        "deep_work_windows": deep_work if deep_work else "9:00-12:00, 15:00-18:00",
        "study_block_duration": block_duration if block_duration else "1.5h",
        "habits": habits if habits else "Śniadanie 7:30, Obiad 13:00, Kolacja 19:00"
    }
    
    # Utwórz i uruchom graf
    groq_app = create_groq_planner_graph()
    
    initial_state = {
        "tasks": tasks,
        "user_preferences": user_preferences,
        "existing_events": "",
        "generated_plan": None,
        "plan_display": "",
        "human_approved": None,
        "human_feedback": "",
        "execution_results": [],
        "execution_complete": False,
        "conversation_context": "",
        "retry_count": 0
    }
    
    try:
        final_state = groq_app.invoke(initial_state)
        
        print("\n" + "=" * 60)
        print("📊 PODSUMOWANIE SESJI")
        print("=" * 60)
        
        if final_state.get("execution_complete"):
            print("✅ Plan został wprowadzony do kalendarza!")
            for result in final_state.get("execution_results", []):
                print(f"   {result}")
        elif final_state.get("human_approved") is False:
            print("❌ Plan został odrzucony przez użytkownika.")
        else:
            print("⚠️ Sesja zakończona bez wprowadzenia planu.")
            
    except Exception as e:
        print(f"\n❌ Błąd podczas planowania: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def main():
    """Główna funkcja programu"""
    # Sprawdź argumenty wiersza poleceń
    plan_mode = len(sys.argv) > 1 and sys.argv[1] == "--plan"
    groq_mode = len(sys.argv) > 1 and sys.argv[1] == "--groq"
    non_interactive = len(sys.argv) > 1 and sys.argv[1] == "--auto"
    
    if groq_mode:
        # Tryb GROQ Planner - nie wymaga wyboru modelu
        run_groq_planner()
        return
    
    # Konfiguracja LLM
    _, llm_with_tools, structured_llm, tools = setup_llm(interactive=not non_interactive)
    
    if plan_mode:
        # Tryb tylko planowanie
        planner_app = create_planner_graph(structured_llm)
        run_planner(planner_app)
    else:
        # Tryb interaktywny z kalendarzem
        interactive_chat(llm_with_tools, tools, structured_llm)


if __name__ == "__main__":
    main()