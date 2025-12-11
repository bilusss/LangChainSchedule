"""
Definicje grafów LangGraph
"""

from typing import Any, List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from models import AgentState
from nodes import create_agent_node, should_use_tools, create_planner_node, reviewer_node, should_continue


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
