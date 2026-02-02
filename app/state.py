from typing import TypedDict, Optional, Dict, Any

class AgentState(TypedDict):
    """
    State of the Country Information Agent.
    """
    question: str
    intent: Optional[str]  # e.g., "get_population", "get_currency", "general_info", "unknown"
    country: Optional[str] # The extracted country name
    tool_output: Optional[Dict[str, Any]] # Result from the REST Countries API
    final_answer: Optional[str] # The synthesized response
    error: Optional[str] # To track any errors during processing
