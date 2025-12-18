"""
GROQ Planner - Planner używający modelu GROQ do generowania harmonogramu
"""

import os
import json
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class GroqPlanner:
    """Klasa do planowania zadań używając GROQ API"""
    
    def __init__(self, model: str = "qwen/qwen3-32b"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model
        
    def create_planning_prompt(
        self,
        tasks: list[str],
        existing_events: str,
        sleep_schedule: str = "23:00 - 7:00",
        deep_work_windows: str = "9:00-12:00, 15:00-18:00",
        study_block_duration: str = "1.5h",
        habits: str = "Śniadanie 7:30, Obiad 13:00, Kolacja 19:00"
    ) -> str:
        """Tworzy prompt do planowania"""
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        return f"""Rola: Jesteś Ekspertem Planowania Czasu i Architektem Produktywności. 
Twoim zadaniem jest przekształcenie surowej listy zadań użytkownika w precyzyjny harmonogram blokowy w Google Calendar.

DZISIEJSZA DATA: {current_date}

KONTEKST I PREFERENCJE UŻYTKOWNIKA:
- Godziny snu: {sleep_schedule}
- Okna Deep Work (wysoka koncentracja): {deep_work_windows}
- Preferowana długość bloku nauki: {study_block_duration}
- Stałe nawyki: {habits}

ISTNIEJĄCE WYDARZENIA W KALENDARZU (następne 14 dni):
{existing_events}

ZADANIA DO ZAPLANOWANIA:
{chr(10).join(f"- {task}" for task in tasks)}

ZASADY OPERACYJNE:
1. DEKOMPOZYCJA: Jeśli zadanie wymaga więcej czasu niż preferowany blok, stwórz kilka osobnych bloków (np. "Nauka - Blok 1/4").
2. STRATEGIA: Zadania o Priorytecie 1 umieszczaj w oknach Deep Work. Treningi planuj jako formę regeneracji.
3. RESPEKTOWANIE KALENDARZA: Przeanalizuj dokładnie istniejące wydarzenia. Jeśli musisz zaplanować coś w czasie gdy jest już wydarzenie:
   - MOŻESZ zaproponować przeniesienie istniejącego wydarzenia (użyj "action": "update")
   - Podaj ID wydarzenia do modyfikacji (z listy powyżej, format [xxxxxxxx])
   - Użytkownik będzie musiał zatwierdzić każdą modyfikację
4. CZAS SNU: Nie planuj niczego w godzinach snu użytkownika.
5. KONFLIKTY: Jeśli wykryjesz konflikt z istniejącym wydarzeniem, opisz go w polu "conflicts".

FORMAT WYJŚCIOWY - MUSISZ wygenerować TYLKO poprawny JSON bez żadnego dodatkowego tekstu:

{{
  "events": [
    {{
      "action": "create",
      "summary": "[Nazwa Zadania] - Blok X/Y",
      "start": "YYYY-MM-DDTHH:MM:SS",
      "end": "YYYY-MM-DDTHH:MM:SS",
      "description": "Priorytet: [1-3], Automatycznie zaplanowane przez AI"
    }},
    {{
      "action": "update",
      "event_id": "ID_ISTNIEJĄCEGO_WYDARZENIA",
      "summary": "Nowa nazwa (opcjonalnie)",
      "start": "YYYY-MM-DDTHH:MM:SS",
      "end": "YYYY-MM-DDTHH:MM:SS",
      "reason": "Powód przeniesienia tego wydarzenia"
    }}
  ],
  "conflicts": [
    {{
      "existing_event": "Nazwa istniejącego wydarzenia",
      "conflict_time": "YYYY-MM-DDTHH:MM",
      "suggestion": "Opis jak rozwiązać konflikt"
    }}
  ],
  "reasoning": "Krótkie wyjaśnienie strategii planowania"
}}

WAŻNE: 
- Odpowiedz TYLKO JSON-em, bez markdown, bez komentarzy, bez tekstu przed lub po JSON.
- Dla nowych wydarzeń użyj "action": "create"
- Dla modyfikacji istniejących użyj "action": "update" i podaj "event_id" oraz "reason"
- Jeśli nie ma konfliktów, "conflicts" może być pustą tablicą []"""

    def generate_plan(
        self,
        tasks: list[str],
        existing_events: str,
        user_preferences: Optional[dict] = None
    ) -> dict:
        """
        Generuje plan używając GROQ API.
        
        Args:
            tasks: Lista zadań do zaplanowania
            existing_events: Istniejące wydarzenia w kalendarzu (tekst)
            user_preferences: Opcjonalne preferencje użytkownika
            
        Returns:
            Słownik z wygenerowanym planem i reasoning
        """
        prefs = user_preferences or {}
        
        prompt = self.create_planning_prompt(
            tasks=tasks,
            existing_events=existing_events,
            sleep_schedule=prefs.get("sleep_schedule", "23:00 - 7:00"),
            deep_work_windows=prefs.get("deep_work_windows", "9:00-12:00, 15:00-18:00"),
            study_block_duration=prefs.get("study_block_duration", "1.5h"),
            habits=prefs.get("habits", "Śniadanie 7:30, Obiad 13:00, Kolacja 19:00")
        )
        
        print("🧠 [GROQ PLANNER] Generuję plan z modelem", self.model, "...")
        
        response_text = ""
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Jesteś ekspertem planowania. Odpowiadasz TYLKO w formacie JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.6,
                max_completion_tokens=4096,
                top_p=0.95,
                stream=True,
                stop=None
            )
            
            print("\n📝 Odpowiedź GROQ:\n")
            for chunk in completion:
                content = chunk.choices[0].delta.content or ""
                response_text += content
                print(content, end="", flush=True)
            print("\n")
            
        except Exception as e:
            print(f"❌ Błąd GROQ API: {e}")
            return {"events": [], "reasoning": f"Błąd: {str(e)}", "error": True}
        
        # Parsuj JSON z odpowiedzi
        return self._parse_response(response_text)
    
    def _parse_response(self, response_text: str) -> dict:
        """Parsuje odpowiedź GROQ do słownika"""
        try:
            # Usuń potencjalne znaczniki markdown
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Znajdź JSON w odpowiedzi (może być tekst przed/po)
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = cleaned[start_idx:end_idx]
                result = json.loads(json_str)
                return result
            else:
                return {
                    "events": [],
                    "reasoning": "Nie udało się znaleźć JSON w odpowiedzi",
                    "raw_response": response_text,
                    "error": True
                }
                
        except json.JSONDecodeError as e:
            print(f"⚠️ Błąd parsowania JSON: {e}")
            return {
                "events": [],
                "reasoning": f"Błąd parsowania JSON: {str(e)}",
                "raw_response": response_text,
                "error": True
            }


def format_plan_for_display(plan: dict) -> str:
    """Formatuje plan do wyświetlenia użytkownikowi"""
    if not plan.get("events"):
        return "❌ Brak wydarzeń do wyświetlenia"
    
    output = "\n" + "=" * 60 + "\n"
    output += "📅 WYGENEROWANY PLAN\n"
    output += "=" * 60 + "\n\n"
    
    # Rozdziel wydarzenia na nowe i modyfikacje
    new_events = [e for e in plan["events"] if e.get("action", "create") == "create"]
    updates = [e for e in plan["events"] if e.get("action") == "update"]
    
    if new_events:
        output += "🆕 NOWE WYDARZENIA:\n"
        output += "-" * 40 + "\n"
        for i, event in enumerate(new_events, 1):
            output += f"{i}. {event.get('summary', 'Bez nazwy')}\n"
            output += f"   🕐 {event.get('start', '?')} - {event.get('end', '?')}\n"
            if event.get('description'):
                output += f"   📝 {event.get('description')}\n"
            output += "\n"
    
    if updates:
        output += "\n⚠️  MODYFIKACJE ISTNIEJĄCYCH WYDARZEŃ:\n"
        output += "-" * 40 + "\n"
        for i, event in enumerate(updates, 1):
            output += f"{i}. 🔄 {event.get('summary', 'Wydarzenie')}\n"
            output += f"   📌 ID: {event.get('event_id', '?')}\n"
            output += f"   🕐 Nowy czas: {event.get('start', '?')} - {event.get('end', '?')}\n"
            if event.get('reason'):
                output += f"   💡 Powód: {event.get('reason')}\n"
            output += "\n"
    
    # Pokaż konflikty jeśli są
    conflicts = plan.get("conflicts", [])
    if conflicts:
        output += "\n⚡ WYKRYTE KONFLIKTY:\n"
        output += "-" * 40 + "\n"
        for conflict in conflicts:
            output += f"   ⚠️  {conflict.get('existing_event', '?')}\n"
            output += f"      Czas: {conflict.get('conflict_time', '?')}\n"
            output += f"      Sugestia: {conflict.get('suggestion', 'Brak')}\n\n"
    
    if plan.get("reasoning"):
        output += "-" * 60 + "\n"
        output += f"💡 Strategia: {plan.get('reasoning')}\n"
    
    output += "=" * 60 + "\n"
    
    return output
