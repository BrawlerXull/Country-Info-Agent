from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, trim_messages, AIMessage
from langchain_core.runnables.config import RunnableConfig

from app.state import AgentState
from app.tools import fetch_country_info
from app.utils import get_llm

from pydantic import BaseModel, Field
from typing import List, Optional

class IntentSchema(BaseModel):
    intent: str = Field(description="The user's intent. Must be one of: 'get_population', 'get_capital', 'get_currency', 'get_language', 'get_flag', 'general_info', 'comparison', 'unknown'")
    countries: List[str] = Field(description="List of country names mentioned. Empty if none found.")

async def identify_intent(state: AgentState, config: RunnableConfig):
    """
    Identifies the user's intent and extracts country names using Structured Output (Pydantic).
    """
    question = state["question"]
    messages = state.get("messages", [])
    llm = get_llm()
    
    # Trim messages if needed...
    
    system_prompt = """You are an intelligent assistant designed to identify the intent and entities from a user's query about countries.
    
    You have access to the conversation history. Use it to resolve references like "it", "they", "those countries", etc.
    
    Task:
    1. Extract Country Names: A list of country names mentioned or referred to.
    2. Identify Intent: What does the user want to know? 
       Valid intents: 'get_population', 'get_capital', 'get_currency', 'get_language', 'get_flag', 'general_info', 'comparison'. 
       If unclear or not about countries, use 'unknown'.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{question}")
    ])
    
    # Use with_structured_output to force valid JSON matching our schema
    structured_llm = llm.with_structured_output(IntentSchema)
    chain = prompt | structured_llm
    
    try:
        # invoke/ainvoke now returns an IntentSchema object directly
        result: IntentSchema = await chain.ainvoke({"messages": messages, "question": question}, config=config)
        
        return {"intent": result.intent, "countries": result.countries}
    except Exception as e:
        return {"intent": "unknown", "countries": [], "error": str(e)}

async def invoke_tool(state: AgentState, config: RunnableConfig):
    """
    Invokes the REST Countries API for each extracted country.
    """
    countries = state.get("countries", [])
    intent = state.get("intent")
    
    if intent == "unknown" or not countries:
        return {"tool_outputs": {}}
    
    outputs = {}
    for country in countries:
        # Skip if country is None or empty
        if not country: continue
        
        # We might want to cache or check if we already have data in context, 
        # but for simplicity, we fetch fresh data.
        result = await fetch_country_info(country)
        outputs[country] = result
        
    return {"tool_outputs": outputs}

async def synthesize_answer(state: AgentState, config: RunnableConfig):
    """
    Synthesizes the answer using tool outputs and history.
    """
    question = state["question"]
    tool_outputs = state.get("tool_outputs", {})
    intent = state.get("intent")
    
    llm = get_llm()
    
    if intent == "unknown":
        return {"final_answer": "I'm sorry, I couldn't understand which country you are asking about, or the query specific to countries was unclear."}
        
    # Check if we have valid data
    valid_data = {}
    errors = []
    
    for country, result in tool_outputs.items():
        if result.get("status") == "success":
            valid_data[country] = result.get("data")
        else:
            errors.append(f"{country}: {result.get('message')}")
    
    if not valid_data and errors:
         return {"final_answer": f"I couldn't find information. Errors: {'; '.join(errors)}"}
    
    if not valid_data and not errors:
        return {"final_answer": "I couldn't identify any countries to look up."}

    # Construct prompt
    system_prompt = """You are a helpful assistant. Answer the user's question using the provided country data.
    
    - If the user asked for a comparison, compare the data points for the requested countries.
    - Be accurate and concise.
    - Context: {data}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    
    # Format data for prompt
    data_context = "\n".join([f"Data for {c}: {d}" for c, d in valid_data.items()])
    
    messages = state.get("messages", [])
    response = await chain.ainvoke({"data": data_context, "messages": messages, "question": question}, config=config)
    
    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)]
    }
