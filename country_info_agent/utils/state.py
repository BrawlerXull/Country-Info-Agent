from typing import TypedDict, Optional, Dict, Any, List, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    State of the Country Information Agent.
    """
    messages: Annotated[List[BaseMessage], add_messages] # Chat history
    question: str
    intent: Optional[str]  # e.g., "get_population", "get_currency", "general_info", "unknown", "comparison"
    countries: Optional[List[str]] # List of extracted country names
    tool_outputs: Optional[Dict[str, Any]] # Result from the REST Countries API keyed by country
    final_answer: Optional[str] # The synthesized response
    error: Optional[str] # To track any errors during processing
