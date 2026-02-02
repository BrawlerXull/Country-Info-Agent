import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler

load_dotenv()

def get_llm():
    """
    Returns the configured LLM instance.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")
    
    return ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def get_langfuse_callback(session_id: str = None):
    """
    Returns a configured LangfuseCallbackHandler.
    """
    # Langfuse v3 reads secrets from env. 
    return CallbackHandler(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY")
    )
