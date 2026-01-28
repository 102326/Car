"""
Agent State Schema for CarFast LangGraph Agent.

This module defines the core state container (AgentState) that flows through
the LangGraph nodes during the car shopping assistant's reasoning process.
"""

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


# ============================================================================
# Custom Reducers
# ============================================================================

def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries with right-side priority.
    
    Used as a reducer for user_profile to accumulate user preferences
    across multiple conversation turns without losing prior information.
    
    Args:
        left: The existing dictionary (previous state).
        right: The new dictionary (update to merge).
        
    Returns:
        A new dictionary with merged contents.
        
    Example:
        >>> merge_dicts({"budget": 100000}, {"brand": "BMW"})
        {"budget": 100000, "brand": "BMW"}
    """
    if left is None:
        left = {}
    if right is None:
        right = {}
    return {**left, **right}


def increment_count(left: int, right: int) -> int:
    """
    Increment step counter to prevent infinite loops.
    
    Used as a reducer for step_count to track the number of
    reasoning iterations the agent has performed.
    
    Args:
        left: The current count.
        right: The increment value (typically 1).
        
    Returns:
        The sum of left and right.
    """
    if left is None:
        left = 0
    if right is None:
        right = 0
    return left + right


# ============================================================================
# Agent State Definition
# ============================================================================

class AgentState(TypedDict, total=False):
    """
    Core state container for the CarFast LangGraph Agent.
    
    This TypedDict defines all the fields that flow through the agent's
    reasoning graph. Fields use Annotated types with reducers to control
    how state updates are merged during graph execution.
    
    Attributes:
        messages: Conversation history with the user. Uses operator.add
            reducer to append new messages rather than overwriting.
        user_id: Optional identifier for the current user session.
        user_profile: Accumulated user preferences (budget, tags, etc.).
            Uses merge_dicts reducer to incrementally build the profile.
        intent: The router's classification of user intent.
            One of: "search", "chat", "calculate", or None.
        search_params: Structured search parameters extracted by the LLM
            from user queries (e.g., {"brand": "BMW", "max_price": 500000}).
        tool_output: Raw string output returned from tool execution.
        observation: Agent's self-reflection or internal monologue about
            the current state and results.
        evaluation_result: Quality assessment of the current response.
            One of: "pass", "refine", or None.
        step_count: Counter for reasoning iterations. Uses increment_count
            reducer to track and limit execution depth.
    """
    
    # Conversation flow - append mode for message history
    messages: Annotated[List[BaseMessage], operator.add]
    
    # User identification
    user_id: Optional[str]
    
    # User profile - merge mode for accumulating preferences
    user_profile: Annotated[Dict[str, Any], merge_dicts]
    
    # Router intent classification
    intent: Optional[str]
    
    # LLM-extracted search parameters
    search_params: Optional[Dict[str, Any]]
    
    # Tool execution output
    tool_output: Optional[str]
    
    # Agent self-reflection / metacognition
    observation: Optional[str]
    
    # Response quality evaluation
    evaluation_result: Optional[str]
    
    # Step counter for loop prevention - increment mode
    step_count: Annotated[int, increment_count]
