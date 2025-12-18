"""
Definicje grafów LangGraph
"""

from typing import Any, List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from models import AgentState, PlannerState
from nodes import (
    create_agent_node, 
    should_use_tools, 
    create_planner_node, 
    reviewer_node, 
    should_continue,
    # Nowe węzły dla GROQ workflow
    groq_planner_node,
    human_feedback_node,
    executor_node,
    should_continue_planner
)


def create_chat_graph(llm_with_tools: Any, tools: List[Any]):
    """
    Tworzy graf dla interaktywnego chatu z narzędziami.
    
    Args:
        llm_with_tools: LLM z przypisanymi narzędziami
        tools: Lista narzędzi
    
    Returns:
        Skompilowany graf
    """
    tool_node = ToolNode(tools)
    agent_node = create_agent_node(llm_with_tools)
    
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


def create_planner_graph(structured_llm: Any):
    """
    Tworzy graf dla automatycznego planowania.
    
    Args:
        structured_llm: LLM ze strukturyzowanym outputem
    
    Returns:
        Skompilowany graf
    """
    planner_node = create_planner_node(structured_llm)
    
    workflow = StateGraph(AgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "reviewer")

    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {"retry": "planner", "end": END}
    )

    return workflow.compile()


def create_groq_planner_graph():
    """
    Tworzy graf dla workflow: GROQ Planner -> Human Feedback -> Executor
    
    Workflow:
    1. groq_planner - generuje plan używając GROQ API (ma kontekst kalendarza)
    2. human_feedback - użytkownik akceptuje/odrzuca/prosi o zmianę
    3. executor - wprowadza zatwierdzony plan do Google Calendar
    
    Returns:
        Skompilowany graf
    """
    workflow = StateGraph(PlannerState)
    
    # Dodaj węzły
    workflow.add_node("planner", groq_planner_node)
    workflow.add_node("human_feedback", human_feedback_node)
    workflow.add_node("executor", executor_node)
    
    # Ustaw punkt wejścia
    workflow.set_entry_point("planner")
    
    # Po planowaniu -> human feedback
    workflow.add_edge("planner", "human_feedback")
    
    # Po human feedback -> warunkowe przejście
    workflow.add_conditional_edges(
        "human_feedback",
        should_continue_planner,
        {
            "executor": "executor",  # Plan zatwierdzony
            "planner": "planner",    # Retry
            "end": END               # Plan odrzucony
        }
    )
    
    # Po executor -> koniec
    workflow.add_edge("executor", END)
    
    return workflow.compile()
