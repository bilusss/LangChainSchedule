import os
import getpass
from typing import List, Optional, Annotated, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Importy Google i LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

# --- 1. KONFIGURACJA KLUCZA ---
load_dotenv()  # Ładuje zmienne z pliku .env

if "GOOGLE_API_KEY" not in os.environ:
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
    tasks: List[str]
    rules: List[str]
    # Używamy Optional, bo na początku schedule może być puste (None)
    schedule: Optional[DailySchedule]
    feedback: str
    retry_count: int

# --- 3. ZMIANA MODELU NA FLASH (Stabilniejszy dla PoC) ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_retries=2,
)

structured_llm = llm.with_structured_output(DailySchedule)

# --- 4. PLANNER (Z obsługą błędów API) ---
def planner_node(state: AgentState):
    print(f"\n🧠 [GEMINI PLANNER] Generuję plan (Próba {state['retry_count'] + 1})...")
    
    system_msg = """Jesteś ekspertem planowania. Stwórz realistyczny plan dnia.
    Jeśli otrzymasz FEEDBACK o błędach, popraw je."""
    
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
        # Zwracamy schedule=None, żeby nie wywaliło KeyError w następnym kroku
        return {"schedule": None, "retry_count": state['retry_count'] + 1}

# --- 5. REVIEWER (Z zabezpieczeniem przed pustym planem) ---
def reviewer_node(state: AgentState):
    print("💎 [REVIEWER] Weryfikacja...")
    
    # ZABEZPIECZENIE: Używamy .get() i sprawdzamy czy schedule istnieje
    schedule = state.get('schedule')
    
    if not schedule:
        error_msg = "BŁĄD KRYTYCZNY: Model nie wygenerował planu (zwrócił None)."
        print(f"❌ {error_msg}")
        # Wymuszamy koniec, bo bez planu nie ma co poprawiać
        return {"feedback": "FATAL_ERROR"}

    items = schedule.items
    feedback = []
    last_location = "Dom"
    
    for item in items:
        if item.location != last_location:
            if "dojazd" not in item.activity.lower():
                feedback.append(f"Teleportacja: {last_location} -> {item.location} bez dojazdu.")
        last_location = item.location

    if feedback:
        print(f"❌ Błędy w logice: {feedback}")
        return {"feedback": " ; ".join(feedback)}
    else:
        print("✅ Plan OK.")
        return {"feedback": "OK"}

# --- 6. GRAF ---
workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("reviewer", reviewer_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "reviewer")

def should_continue(state: AgentState):
    fb = state.get('feedback', "")
    if fb == "OK": return "end"
    if fb == "FATAL_ERROR": return "end" # Kończymy jeśli API padło
    if state['retry_count'] > 3: return "end"
    return "retry"

workflow.add_conditional_edges(
    "reviewer",
    should_continue,
    {"retry": "planner", "end": END}
)

app = workflow.compile()

# --- 7. START ---
input_data = {
    "tasks": ["Siłownia", "Nauka", "Zajęcia na uczelni (13:15-14:45)"],
    "rules": ["Pobudka 8:00", "Siłownia 10m pieszo od domu","Preferowany trening wieczorem", "Uczelnia 30m dojazdu autobusem"],
    "retry_count": 0,
    "feedback": "",
    "schedule": None # Inicjalizacja pustą wartością
}

print("--- START ---")
final = app.invoke(input_data)

print("\n--- KONIEC ---")
if final.get('schedule'):
    for item in final['schedule'].items:
        print(f"{item.start_time}-{item.end_time}: {item.activity} ({item.location})")
else:
    print("Brak planu do wyświetlenia.")