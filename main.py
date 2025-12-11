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
from graphs import create_chat_graph, create_planner_graph
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
    print("  - 'plan' - uruchom automatyczne planowanie dnia")
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


def main():
    """Główna funkcja programu"""
    # Sprawdź argumenty wiersza poleceń
    plan_mode = len(sys.argv) > 1 and sys.argv[1] == "--plan"
    non_interactive = len(sys.argv) > 1 and sys.argv[1] == "--auto"
    
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