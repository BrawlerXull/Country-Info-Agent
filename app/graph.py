from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.nodes import identify_intent, invoke_tool, synthesize_answer

def create_graph():
    """
    Constructs the LangGraph for the Country Information Agent.
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("identify_intent", identify_intent)
    workflow.add_node("invoke_tool", invoke_tool)
    workflow.add_node("synthesize_answer", synthesize_answer)
    
    # Define edges
    # Start -> Identify Intent
    workflow.set_entry_point("identify_intent")
    
    # Identify Intent -> Invoke Tool (or End if unknown/error)
    # We'll use a conditional edge or just simplistic flow for now.
    # Since nodes return updates, we can just chain them.
    # Logic in `invoke_tool` handles 'unknown' intent by doing nothing.
    workflow.add_edge("identify_intent", "invoke_tool")
    
    # Invoke Tool -> Synthesize Answer
    workflow.add_edge("invoke_tool", "synthesize_answer")
    
    # Synthesize Answer -> End
    workflow.add_edge("synthesize_answer", END)
    
    return workflow.compile()
