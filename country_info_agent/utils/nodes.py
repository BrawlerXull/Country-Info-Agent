import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_core.runnables.config import RunnableConfig

from country_info_agent.utils.state import AgentState
from country_info_agent.utils.tools import fetch_country_info
from country_info_agent.utils.common import get_llm
from country_info_agent.prompts.agent_prompts import (
    IDENTIFY_INTENT_SYSTEM_PROMPT,
    GREETING_SYSTEM_PROMPT,
    SYNTHESIZE_ANSWER_SYSTEM_PROMPT
)

from pydantic import BaseModel, Field
from typing import List, Optional

logger = logging.getLogger(__name__)

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
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", IDENTIFY_INTENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "{question}")
    ])
    
    # Use with_structured_output to force valid JSON matching our schema
    # Use function_calling method for compatibility with gpt-3.5-turbo
    structured_llm = llm.with_structured_output(IntentSchema, method="function_calling")
    chain = prompt | structured_llm
    
    try:
        # invoke/ainvoke now returns an IntentSchema object directly
        result: IntentSchema = await chain.ainvoke({"messages": messages, "question": question}, config=config)
        
        return {"intent": result.intent, "countries": result.countries}
    except Exception as e:
        logger.error(f"Error in identify_intent: {e}", exc_info=True)
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
        # Generate a friendly response using LLM instead of hardcoding
        greeting_prompt = ChatPromptTemplate.from_messages([
            ("system", GREETING_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{question}")
        ])
        
        greeting_chain = greeting_prompt | llm
        messages = state.get("messages", [])
        
        try:
            response = await greeting_chain.ainvoke({"messages": messages, "question": question}, config=config)
            return {"final_answer": response.content, "messages": [AIMessage(content=response.content)]}
        except Exception as e:
            logger.error(f"Error generating greeting response: {e}")
            return {"final_answer": "Hello! I'm your Country Information Agent. Ask me about any country - population, capital, currency, and more!"}
        
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
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYNTHESIZE_ANSWER_SYSTEM_PROMPT),
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
