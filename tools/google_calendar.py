"""
Google Calendar Tools dla LangChain/LangGraph
Używa GOOGLE_API_KEY_CLOUD do autoryzacji z Google Calendar API
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from dotenv import load_dotenv

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Załaduj zmienne środowiskowe
load_dotenv()

# Ścieżka do katalogu głównego projektu (rodzic folderu tools/)
PROJECT_ROOT = Path(__file__).parent.parent

# Zakresy dostępu do Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- MODELE DANYCH ---
class CalendarEvent(BaseModel):
    """Model wydarzenia w kalendarzu"""
    id: Optional[str] = Field(default=None, description="ID wydarzenia")
    summary: str = Field(description="Tytuł wydarzenia")
    start: str = Field(description="Data/czas rozpoczęcia (ISO format)")
    end: str = Field(description="Data/czas zakończenia (ISO format)")
    description: Optional[str] = Field(default=None, description="Opis wydarzenia")
    location: Optional[str] = Field(default=None, description="Lokalizacja")


def _get_calendar_service():
    """
    Tworzy serwis Google Calendar API.
    
    Kolejność prób:
    1. Zapisany token OAuth2 (token.pickle)
    2. OAuth2 flow z credentials.json
    3. API Key z GOOGLE_API_KEY_CLOUD (tylko do publicznych kalendarzy)
    """
    creds = None
    # Użyj ścieżek bezwzględnych względem katalogu projektu
    token_path = PROJECT_ROOT / 'token.pickle'
    credentials_path = PROJECT_ROOT / 'credentials.json'
    
    print(f"🔍 Szukam credentials w: {credentials_path}")
    print(f"🔍 Plik istnieje: {credentials_path.exists()}")
    
    # Próba 1: Sprawdź czy istnieje zapisany token
    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            print("✅ Załadowano zapisany token OAuth2")
    
    # Jeśli brak ważnych credentials, uruchom flow autoryzacji
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Odświeżam wygasły token...")
            creds.refresh(Request())
        elif credentials_path.exists():
            # Próba 2: OAuth2 flow
            print("🔐 Uruchamiam OAuth2 flow - otwieram przeglądarkę...")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
            # Zapisz token do późniejszego użycia
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            print("✅ Token zapisany do token.pickle")
        else:
            # Próba 3: Użyj API Key (ograniczone możliwości - tylko publiczne kalendarze)
            api_key = os.getenv('GOOGLE_API_KEY_CLOUD')
            if api_key:
                print("⚠️ Używam API Key - dostęp tylko do publicznych kalendarzy")
                service = build('calendar', 'v3', developerKey=api_key)
                return service
            else:
                raise FileNotFoundError(
                    f"Brak pliku {credentials_path} i brak GOOGLE_API_KEY_CLOUD w .env. "
                    "Pobierz credentials.json z Google Cloud Console (OAuth 2.0 Client ID) "
                    "lub ustaw GOOGLE_API_KEY_CLOUD."
                )
    
    service = build('calendar', 'v3', credentials=creds)
    return service
    return service


# --- TOOLS DLA LANGCHAIN ---

@tool
def get_calendar_events(
    days_ahead: int = 7,
    max_results: int = 10,
    calendar_id: str = "primary"
) -> str:
    """
    Pobiera wydarzenia z Google Calendar.
    
    Args:
        days_ahead: Ile dni do przodu szukać wydarzeń (domyślnie 7)
        max_results: Maksymalna liczba wydarzeń do pobrania (domyślnie 10)
        calendar_id: ID kalendarza (domyślnie "primary" - główny kalendarz)
    
    Returns:
        Lista wydarzeń w formacie tekstowym
    """
    try:
        service = _get_calendar_service()
        
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"Brak wydarzeń w ciągu najbliższych {days_ahead} dni."
        
        result = f"📅 Wydarzenia na najbliższe {days_ahead} dni:\n\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'Bez tytułu')
            location = event.get('location', '')
            event_id = event.get('id', '')
            
            result += f"• [{event_id[:8]}] {summary}\n"
            result += f"  Start: {start}\n"
            result += f"  Koniec: {end}\n"
            if location:
                result += f"  Miejsce: {location}\n"
            result += "\n"
        
        return result
        
    except HttpError as error:
        return f"❌ Błąd Google Calendar API: {error}"
    except Exception as e:
        return f"❌ Błąd: {str(e)}"


@tool
def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary"
) -> str:
    """
    Tworzy nowe wydarzenie w Google Calendar.
    
    Args:
        summary: Tytuł wydarzenia
        start_time: Czas rozpoczęcia w formacie ISO (np. "2025-12-10T10:00:00")
        end_time: Czas zakończenia w formacie ISO (np. "2025-12-10T11:00:00")
        description: Opis wydarzenia (opcjonalnie)
        location: Lokalizacja (opcjonalnie)
        calendar_id: ID kalendarza (domyślnie "primary")
    
    Returns:
        Informacja o utworzonym wydarzeniu
    """
    try:
        service = _get_calendar_service()
        
        # Upewnij się, że czas jest w formacie ISO BEZ strefy czasowej
        # Google Calendar użyje timeZone z body do interpretacji
        
        def normalize_time(time_str: str) -> str:
            """Usuwa strefę czasową z czasu - Google Calendar sam użyje Europe/Warsaw"""
            import re
            # Usuń 'Z' na końcu
            if time_str.endswith('Z'):
                time_str = time_str[:-1]
            # Usuń offset (+01:00, -05:00 itp.)
            time_str = re.sub(r'[+-]\d{2}:\d{2}$', '', time_str)
            return time_str
        
        print(f"🕐 Otrzymano czasy: start={start_time}, end={end_time}")
        start_time = normalize_time(start_time)
        end_time = normalize_time(end_time)
        print(f"🕐 Po normalizacji (bez TZ): start={start_time}, end={end_time}")
        
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Warsaw',  # Google Calendar użyje tej strefy
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Warsaw',
            },
        }
        
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        # Sformatuj czas po polsku
        start_dt = created_event['start'].get('dateTime', created_event['start'].get('date'))
        end_dt = created_event['end'].get('dateTime', created_event['end'].get('date'))
        
        # Parsuj i formatuj ładnie (konwertuj na czas warszawski)
        try:
            from datetime import datetime as dt
            import pytz
            
            # Parsuj czas (może być w UTC z 'Z' lub z offsetem)
            start_parsed = dt.fromisoformat(start_dt.replace('Z', '+00:00'))
            end_parsed = dt.fromisoformat(end_dt.replace('Z', '+00:00'))
            
            # Konwertuj do strefy warszawskiej
            warsaw_tz = pytz.timezone('Europe/Warsaw')
            start_warsaw = start_parsed.astimezone(warsaw_tz)
            end_warsaw = end_parsed.astimezone(warsaw_tz)
            
            # Polski format daty
            days_pl = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']
            months_pl = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 
                        'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia']
            
            day_name = days_pl[start_warsaw.weekday()]
            date_str = f"{start_warsaw.day} {months_pl[start_warsaw.month - 1]} {start_warsaw.year}"
            time_str = f"{start_warsaw.strftime('%H:%M')} - {end_warsaw.strftime('%H:%M')}"
            
            return f"""✅ Wydarzenie dodane do kalendarza!

📅 {created_event.get('summary')}
🗓️  {day_name}, {date_str}
⏰ {time_str} (czas warszawski)
📍 {created_event.get('location') or 'Brak lokalizacji'}

🔗 Link: {created_event.get('htmlLink')}"""
        except:
            # Fallback jeśli parsowanie się nie uda
            return f"✅ Utworzono wydarzenie: {created_event.get('summary')}\n" \
                   f"   Start: {start_dt}\n" \
                   f"   Koniec: {end_dt}\n" \
                   f"   Link: {created_event.get('htmlLink')}"
               
    except HttpError as error:
        return f"❌ Błąd Google Calendar API: {error}"
    except Exception as e:
        return f"❌ Błąd: {str(e)}"


@tool
def update_calendar_event(
    event_id: str,
    summary: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    calendar_id: str = "primary"
) -> str:
    """
    Aktualizuje istniejące wydarzenie w Google Calendar.
    
    Args:
        event_id: ID wydarzenia do aktualizacji
        summary: Nowy tytuł (opcjonalnie)
        start_time: Nowy czas rozpoczęcia w formacie ISO (opcjonalnie)
        end_time: Nowy czas zakończenia w formacie ISO (opcjonalnie)
        description: Nowy opis (opcjonalnie)
        location: Nowa lokalizacja (opcjonalnie)
        calendar_id: ID kalendarza (domyślnie "primary")
    
    Returns:
        Informacja o zaktualizowanym wydarzeniu
    """
    try:
        service = _get_calendar_service()
        
        # Pobierz istniejące wydarzenie
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        # Aktualizuj tylko podane pola
        if summary is not None:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if location is not None:
            event['location'] = location
        if start_time is not None:
            if not start_time.endswith('Z') and '+' not in start_time:
                start_time = start_time + '+01:00'
            event['start'] = {
                'dateTime': start_time,
                'timeZone': 'Europe/Warsaw',
            }
        if end_time is not None:
            if not end_time.endswith('Z') and '+' not in end_time:
                end_time = end_time + '+01:00'
            event['end'] = {
                'dateTime': end_time,
                'timeZone': 'Europe/Warsaw',
            }
        
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        return f"✅ Zaktualizowano wydarzenie: {updated_event.get('summary')}\n" \
               f"   ID: {updated_event.get('id')}"
               
    except HttpError as error:
        return f"❌ Błąd Google Calendar API: {error}"
    except Exception as e:
        return f"❌ Błąd: {str(e)}"


@tool
def delete_calendar_event(
    event_id: str,
    calendar_id: str = "primary"
) -> str:
    """
    Usuwa wydarzenie z Google Calendar.
    
    Args:
        event_id: ID wydarzenia do usunięcia
        calendar_id: ID kalendarza (domyślnie "primary")
    
    Returns:
        Informacja o usunięciu
    """
    try:
        service = _get_calendar_service()
        
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        return f"✅ Usunięto wydarzenie o ID: {event_id}"
        
    except HttpError as error:
        return f"❌ Błąd Google Calendar API: {error}"
    except Exception as e:
        return f"❌ Błąd: {str(e)}"


def get_calendar_tools() -> List:
    """Zwraca listę wszystkich narzędzi Google Calendar"""
    return [
        get_calendar_events,
        create_calendar_event,
        update_calendar_event,
        delete_calendar_event
    ]
