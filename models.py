"""
Struktury danych i modele Pydantic
"""

from typing import List, Optional, TypedDict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class ScheduleItem(BaseModel):
    """Pojedynczy element harmonogramu"""
    start_time: str = Field(description="Godzina rozpoczęcia HH:MM")
    end_time: str = Field(description="Godzina zakończenia HH:MM")
    activity: str = Field(description="Nazwa czynności")
    location: str = Field(description="Miejsce (np. Dom, Uczelnia)")
    note: Optional[str] = Field(default=None, description="Krótki opis")


class DailySchedule(BaseModel):
    """Dzienny harmonogram z uzasadnieniem"""
    items: List[ScheduleItem]
    reasoning: str = Field(description="Wyjaśnienie planu")


class AgentState(TypedDict):
    """Stan agenta w grafie LangGraph"""
    messages: List[BaseMessage]
    tasks: List[str]
    rules: List[str]
    schedule: Optional[DailySchedule]
    feedback: str
    retry_count: int


class PlannerEvent(BaseModel):
    """Pojedyncze wydarzenie wygenerowane przez planner"""
    summary: str = Field(description="Nazwa wydarzenia")
    start: str = Field(description="Data/czas rozpoczęcia (ISO format)")
    end: str = Field(description="Data/czas zakończenia (ISO format)")
    description: Optional[str] = Field(default=None, description="Opis wydarzenia")


class PlannerState(TypedDict):
    """Stan dla workflow Planner -> Human Feedback -> Executor"""
    # Dane wejściowe
    tasks: List[str]
    user_preferences: dict
    existing_events: str
    
    # Plan wygenerowany przez GROQ
    # Format: {"events": [...], "conflicts": [...], "reasoning": "..."}
    # Każde event może mieć "action": "create" lub "update"
    generated_plan: Optional[dict]
    plan_display: str  # Sformatowany plan do wyświetlenia
    
    # Human feedback
    human_approved: Optional[bool]
    human_feedback: str
    
    # Executor
    execution_results: List[str]
    execution_complete: bool
    
    # Kontekst konwersacji (żeby executor wiedział co się działo)
    conversation_context: str
    
    # Licznik prób
    retry_count: int
