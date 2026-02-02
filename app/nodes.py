from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage

from app.state import AgentState
from app.tools import fetch_country_info
from app.utils import get_llm # We will implement this util to handle LLM init

def identify_intent(state: AgentState):
    """
    Identifies the user's intent and extracts the country name.
    """
    question = state["question"]
    llm = get_llm()
    
    # Simple prompt to extract intent and country
    system_prompt = """You are an intelligent assistant designed to identify the intent and entity from a user's query about countries.
    
    Extract the following:
    1. Country: The name of the country mentioned. specific country name in English.
    2. Intent: What the user wants to know. Examples: 'get_population', 'get_capital', 'get_currency', 'get_language', 'get_flag', 'general_info'. 
       If the query is not about a country or unclear, return "unknown".
    
    Return the output as a JSON object with keys "country" and "intent".
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])
    
    # We use a JSON parser to ensure structured output
    chain = prompt | llm | JsonOutputParser()
    
    try:
        result = chain.invoke({"question": question})
        return {"intent": result.get("intent"), "country": result.get("country")}
    except Exception as e:
        # Fallback in case of parsing error
        return {"intent": "unknown", "country": None, "error": str(e)}

def invoke_tool(state: AgentState):
    """
    Invokes the REST Countries API based on the extracted country.
    """
    country = state.get("country")
    intent = state.get("intent")
    
    if intent == "unknown" or not country:
        return {"tool_output": None}
    
    result = fetch_country_info(country)
    return {"tool_output": result}

def synthesize_answer(state: AgentState):
    """
    Synthesizes the final answer based on the tool output and the original question.
    """
    question = state["question"]
    tool_output = state.get("tool_output")
    intent = state.get("intent")
    
    llm = get_llm()
    
    if intent == "unknown":
        return {"final_answer": "I'm sorry, I couldn't understand which country you are asking about or the query was not about a country. Please try asking something like 'What is the population of France?'"}
        
    if tool_output and tool_output.get("status") == "error":
        return {"final_answer": f"I encountered an error finding information: {tool_output.get('message')}"}
        
    if not tool_output:
         return {"final_answer": "I couldn't find any information for that country."}
    
    # Construct a prompt to answer the specific question using the data
    system_prompt = """You are a helpful assistant. Answer the user's question using the provided country data.
    Be accurate and concise. If the specific information requested is not in the data, say so.
    
    Data:
    {data}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({"data": tool_output.get("data"), "question": question})
    
    return {"final_answer": response.content}
