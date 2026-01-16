"""
FastAPI Backend dla React Native aplikacji
Wrapper HTTP dla funkcji LangChain/GROQ Planner
"""

import os
import sys
import json
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

# Import funkcji z backendu
from tools.google_calendar import (
    get_calendar_events, 
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event
)
from groq_planner import GroqPlanner, format_plan_for_display
from config import ModelProvider, DEFAULT_MODELS
from llm_factory import create_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


# ============================================================================
# MODELE API
# ============================================================================

class ChatRequest(BaseModel):
    """Request dla chatu z asystentem"""
    message: str = Field(..., description="Wiadomość użytkownika")
    conversation_id: Optional[str] = Field(default=None, description="ID konwersacji")


class ChatResponse(BaseModel):
    """Response z chatu"""
    response: str
    conversation_id: str


class PlanRequest(BaseModel):
    """Request dla planowania"""
    tasks: List[str] = Field(..., description="Lista zadań do zaplanowania")
    sleep_schedule: str = Field(default="23:00 - 7:00", description="Godziny snu")
    deep_work_windows: str = Field(default="9:00-12:00, 15:00-18:00", description="Okna deep work")
    study_block_duration: str = Field(default="1.5h", description="Długość bloku nauki")
    habits: str = Field(default="Śniadanie 7:30, Obiad 13:00, Kolacja 19:00", description="Stałe nawyki")


class PlanResponse(BaseModel):
    """Response z planowania"""
    events: List[dict]
    conflicts: List[dict]
    reasoning: str
    display_text: str


class EventRequest(BaseModel):
    """Request dla tworzenia wydarzenia"""
    summary: str
    start_time: str
    end_time: str
    description: str = ""
    location: str = ""


class EventUpdateRequest(BaseModel):
    """Request dla aktualizacji wydarzenia"""
    event_id: str
    summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class TranscribeRequest(BaseModel):
    """Request dla transkrypcji audio"""
    audio_base64: str = Field(..., description="Audio w formacie base64")
    language: str = Field(default="pl", description="Kod języka")


class TranscribeResponse(BaseModel):
    """Response z transkrypcji"""
    text: str
    language: str


class ExecutePlanRequest(BaseModel):
    """Request dla wykonania planu"""
    events: List[dict] = Field(..., description="Lista wydarzeń do dodania")


# ============================================================================
# PRZECHOWYWANIE KONWERSACJI (w pamięci - dla prostoty)
# ============================================================================

conversations = {}


# ============================================================================
# INICJALIZACJA LLM (z cache)
# ============================================================================

_llm_cache = {}


def get_chat_llm():
    """Pobiera lub tworzy LLM do chatu"""
    if "chat_llm" not in _llm_cache:
        # Użyj Gemini jako domyślnego dla chatu (szybki i darmowy)
        try:
            llm = create_llm(ModelProvider.GEMINI, DEFAULT_MODELS[ModelProvider.GEMINI])
            from tools.google_calendar import get_calendar_tools
            tools = get_calendar_tools()
            _llm_cache["chat_llm"] = llm.bind_tools(tools)
            _llm_cache["tools"] = tools
            print("✅ Chat LLM zainicjalizowany (Gemini)")
        except Exception as e:
            print(f"⚠️ Nie udało się zainicjalizować Gemini: {e}")
            # Fallback - spróbuj OpenAI
            try:
                llm = create_llm(ModelProvider.OPENAI, "gpt-4o-mini")
                from tools.google_calendar import get_calendar_tools
                tools = get_calendar_tools()
                _llm_cache["chat_llm"] = llm.bind_tools(tools)
                _llm_cache["tools"] = tools
                print("✅ Chat LLM zainicjalizowany (OpenAI)")
            except Exception as e2:
                print(f"❌ Nie udało się zainicjalizować żadnego LLM: {e2}")
                raise
    return _llm_cache["chat_llm"]


# ============================================================================
# FASTAPI APP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager dla FastAPI"""
    print("🚀 Starting Calendar AI API...")
    # Pre-load GROQ planner
    try:
        _ = GroqPlanner()
        print("✅ GROQ Planner ready")
    except Exception as e:
        print(f"⚠️ GROQ Planner not available: {e}")
    yield
    print("👋 Shutting down Calendar AI API...")


app = FastAPI(
    title="Calendar AI API",
    description="API dla React Native aplikacji do planowania z AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - pozwól na połączenia z React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji ogranicz do konkretnych domen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "message": "Calendar AI API is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """Szczegółowy health check"""
    groq_status = "ok"
    try:
        _ = GroqPlanner()
    except Exception as e:
        groq_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "services": {
            "groq_planner": groq_status,
            "google_calendar": "ok"  # Zakładamy że działa
        }
    }


# ============================================================================
# CALENDAR ENDPOINTS
# ============================================================================

@app.get("/calendar/events")
async def api_get_events(days_ahead: int = 7, max_results: int = 20):
    """Pobiera wydarzenia z kalendarza"""
    try:
        result = get_calendar_events.invoke({
            "days_ahead": days_ahead,
            "max_results": max_results
        })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calendar/events")
async def api_create_event(request: EventRequest):
    """Tworzy nowe wydarzenie"""
    try:
        result = create_calendar_event.invoke({
            "summary": request.summary,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "description": request.description,
            "location": request.location
        })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/calendar/events")
async def api_update_event(request: EventUpdateRequest):
    """Aktualizuje wydarzenie"""
    try:
        params = {"event_id": request.event_id}
        if request.summary:
            params["summary"] = request.summary
        if request.start_time:
            params["start_time"] = request.start_time
        if request.end_time:
            params["end_time"] = request.end_time
        if request.description:
            params["description"] = request.description
        if request.location:
            params["location"] = request.location
            
        result = update_calendar_event.invoke(params)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/calendar/events/{event_id}")
async def api_delete_event(event_id: str):
    """Usuwa wydarzenie"""
    try:
        result = delete_calendar_event.invoke({"event_id": event_id})
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PLANNER ENDPOINTS
# ============================================================================

@app.post("/planner/generate", response_model=PlanResponse)
async def api_generate_plan(request: PlanRequest):
    """Generuje plan używając GROQ"""
    try:
        # Pobierz istniejące wydarzenia
        existing_events = get_calendar_events.invoke({
            "days_ahead": 14,
            "max_results": 50
        })
        
        # Wygeneruj plan
        planner = GroqPlanner()
        plan = planner.generate_plan(
            tasks=request.tasks,
            existing_events=existing_events,
            user_preferences={
                "sleep_schedule": request.sleep_schedule,
                "deep_work_windows": request.deep_work_windows,
                "study_block_duration": request.study_block_duration,
                "habits": request.habits
            }
        )
        
        display_text = format_plan_for_display(plan)
        
        return PlanResponse(
            events=plan.get("events", []),
            conflicts=plan.get("conflicts", []),
            reasoning=plan.get("reasoning", ""),
            display_text=display_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/planner/execute")
async def api_execute_plan(request: ExecutePlanRequest):
    """Wykonuje zatwierdzony plan - dodaje wydarzenia do kalendarza"""
    results = []
    success_count = 0
    
    for event in request.events:
        action = event.get("action", "create")
        
        try:
            if action == "create":
                result = create_calendar_event.invoke({
                    "summary": event.get("summary", "Bez nazwy"),
                    "start_time": event.get("start", ""),
                    "end_time": event.get("end", ""),
                    "description": event.get("description", "Zaplanowane przez AI")
                })
                results.append({"event": event.get("summary"), "status": "created", "result": result})
                success_count += 1
                
            elif action == "update":
                params = {"event_id": event.get("event_id")}
                if event.get("summary"):
                    params["summary"] = event["summary"]
                if event.get("start"):
                    params["start_time"] = event["start"]
                if event.get("end"):
                    params["end_time"] = event["end"]
                if event.get("reason"):
                    params["description"] = f"[Zmodyfikowane przez AI] {event['reason']}"
                    
                result = update_calendar_event.invoke(params)
                results.append({"event": event.get("summary", event.get("event_id")), "status": "updated", "result": result})
                success_count += 1
                
        except Exception as e:
            results.append({"event": event.get("summary", "?"), "status": "error", "error": str(e)})
    
    return {
        "success": success_count == len(request.events),
        "total": len(request.events),
        "succeeded": success_count,
        "results": results
    }


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@app.post("/chat", response_model=ChatResponse)
async def api_chat(request: ChatRequest):
    """Chat z asystentem AI"""
    try:
        # Pobierz lub utwórz konwersację
        conv_id = request.conversation_id or f"conv_{datetime.now().timestamp()}"
        
        print(f"📥 Otrzymano wiadomość: '{request.message}' z conversation_id: {request.conversation_id}")
        print(f"📥 Używam conversation_id: {conv_id}")
        
        if conv_id in conversations:
            print(f"♻️  Kontynuuję istniejącą konwersację: {len(conversations[conv_id])} wiadomości w historii")
        else:
            print(f"✨ Tworzę nową konwersację: {conv_id}")
            
            # Pobierz aktualną datę i czas
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            day_of_week = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"][now.weekday()]
            
            system_msg = SystemMessage(content=f"""Jesteś asystentem planowania z dostępem do Google Calendar.

AKTUALNA DATA I CZAS:
- Dzisiaj jest: {current_date} ({day_of_week})
- Aktualna godzina: {current_time}
- Strefa czasowa: Europe/Warsaw (Polska)
- Lokalizacja użytkownika: Warszawa, Polska

Możesz:
- Sprawdzać wydarzenia w kalendarzu (get_calendar_events)
- Tworzyć nowe wydarzenia (create_calendar_event)
- Aktualizować istniejące wydarzenia (update_calendar_event)
- Usuwać wydarzenia (delete_calendar_event)

WAŻNE ZASADY:
1. Gdy użytkownik mówi "dzisiaj", użyj daty {current_date}
2. Gdy użytkownik mówi "jutro", dodaj 1 dzień do {current_date}
3. Gdy użytkownik podaje godzinę (np. "15:30-16:30"), od razu utwórz wydarzenie używając narzędzia create_calendar_event
4. Formaty czasów do narzędzi: "{current_date}T15:30:00" (ISO 8601)
5. NIE pytaj o potwierdzenie - od razu wykonaj akcję jeśli masz wszystkie dane
6. Wszystkie czasy są w strefie Europe/Warsaw (czas warszawski)
7. Po utworzeniu wydarzenia, przekaż użytkownikowi informację zwrotną z narzędzia

Odpowiadaj po polsku. Bądź zwięzły i pomocny. Wykonuj akcje natychmiast.""")
            conversations[conv_id] = [system_msg]
        
        # Dodaj wiadomość użytkownika
        conversations[conv_id].append(HumanMessage(content=request.message))
        
        # Pobierz odpowiedź od LLM
        llm = get_chat_llm()
        response = llm.invoke(conversations[conv_id])
        
        # Jeśli LLM chce użyć narzędzia
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Wykonaj narzędzia
            from langgraph.prebuilt import ToolNode
            tool_node = ToolNode(_llm_cache.get("tools", []))
            
            # Dodaj odpowiedź LLM
            conversations[conv_id].append(response)
            
            print(f"🔧 LLM wywołuje narzędzia: {[tc['name'] for tc in response.tool_calls]}")
            
            # Wykonaj narzędzia
            tool_result = tool_node.invoke({"messages": conversations[conv_id]})
            
            # Pobierz wynik narzędzia (do ewentualnego fallback)
            tool_output = ""
            if tool_result.get("messages"):
                conversations[conv_id].extend(tool_result["messages"])
                # Zapisz wynik narzędzia
                for msg in tool_result["messages"]:
                    if hasattr(msg, 'content') and msg.content:
                        tool_output = msg.content
                        print(f"🔧 Wynik narzędzia: {tool_output[:200]}...")
            
            # Poproś LLM o odpowiedź na podstawie wyników
            final_response = llm.invoke(conversations[conv_id])
            conversations[conv_id].append(final_response)
            
            # Sprawdź czy odpowiedź nie jest pusta
            response_text = final_response.content
            if not response_text or response_text.strip() == "":
                print("⚠️ Pusta odpowiedź od LLM, używam wyniku narzędzia")
                response_text = tool_output if tool_output else "Operacja wykonana pomyślnie."
            
            print(f"📤 Wysyłam odpowiedź (z narzędziami): {response_text[:100]}...")
            print(f"📤 Rozmiar historii: {len(conversations[conv_id])} wiadomości")
            
            return ChatResponse(
                response=response_text,
                conversation_id=conv_id
            )
        else:
            conversations[conv_id].append(response)
            
            print(f"📤 Wysyłam odpowiedź: {response.content[:100]}...")
            print(f"📤 Rozmiar historii: {len(conversations[conv_id])} wiadomości")
            
            return ChatResponse(
                response=response.content,
                conversation_id=conv_id
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{conversation_id}")
async def api_clear_chat(conversation_id: str):
    """Czyści historię konwersacji"""
    if conversation_id in conversations:
        del conversations[conversation_id]
    return {"success": True}


# ============================================================================
# SPEECH-TO-TEXT ENDPOINT (używa Whisper przez GROQ)
# ============================================================================

@app.post("/transcribe", response_model=TranscribeResponse)
async def api_transcribe(
    file: UploadFile = File(..., description="Plik audio (m4a, wav, mp3, etc.)"),
    language: str = Form(default="pl", description="Kod języka")
):
    """
    Transkrybuje audio na tekst używając Whisper przez GROQ API.
    Akceptuje plik audio jako multipart/form-data.
    """
    import tempfile
    
    try:
        # Zapisz przesłany plik do tymczasowego pliku
        # Wyciągnij rozszerzenie z nazwy pliku
        suffix = ".m4a"  # domyślnie
        if file.filename:
            ext = os.path.splitext(file.filename)[1]
            if ext:
                suffix = ext
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Użyj GROQ Whisper API
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            with open(tmp_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), audio_file.read()),
                    model="whisper-large-v3",  # Najlepszy model dla polskiego
                    language=language,
                    response_format="text"
                )
            
            return TranscribeResponse(
                text=transcription,
                language=language
            )
            
        finally:
            # Usuń tymczasowy plik
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


# ============================================================================
# URUCHOMIENIE
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           🗓️  CALENDAR AI API SERVER                         ║
╠══════════════════════════════════════════════════════════════╣
║  Server: http://{host}:{port}                               ║
║  Docs:   http://{host}:{port}/docs                          ║
║  Health: http://{host}:{port}/health                        ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
