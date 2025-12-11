"""
Struktury danych i modele Pydantic
"""

from typing import List, Optional, TypedDict
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
