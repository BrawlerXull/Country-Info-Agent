import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from openai import AuthenticationError, RateLimitError, APIError

def get_llm(temperature=0, model="gpt-3.5-turbo", max_tokens=None, tools=None):
    """
    Returns a ChatOpenAI model with a Gemini fallback.
    
    Args:
        temperature: The temperature for the model.
        model: The primary OpenAI model to use.
        max_tokens: key argument for max tokens
        tools: Optional list of tools to bind to the models.
        
    Returns:
        A Runnable binding that attempts OpenAI first, then falls back to Gemini.
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    # Primary Model: OpenAI
    openai_params = {
        "model": model,
        "temperature": temperature,
        "max_retries": 0 # Disable internal retries to allow fallback to trigger immediately
    }
    if max_tokens:
        openai_params["max_tokens"] = max_tokens
        
    openai_model = ChatOpenAI(**openai_params)
    
    # Fallback Model: Google Gemini
    # Usage of 1.5-flash as it is fast and has large context, good for fallbacks
    # Note: Requires GOOGLE_API_KEY in env
    gemini_params = {
        "model": "gemini-2.0-flash",
        "temperature": temperature,
        "convert_system_message_to_human": True # Often needed for some LangChain/Gemini versions
    }
    if max_tokens:
        gemini_params["max_output_tokens"] = max_tokens
        
    gemini_model = ChatGoogleGenerativeAI(**gemini_params)
    
    # Bind tools if provided
    if tools:
        print(f"---LLM INIT: Binding {len(tools)} tools to both OpenAI and Gemini models---")
        openai_model = openai_model.bind_tools(tools)
        gemini_model = gemini_model.bind_tools(tools)
    
    # Create Fallback
    # Explicitly handle all exceptions to ensure fallback triggers on Auth/RateLimit/etc.
    model_with_fallback = openai_model.with_fallbacks(
        [gemini_model],
        exceptions_to_handle=(AuthenticationError, RateLimitError, APIError, Exception) 
    )
    
    return model_with_fallback

def get_langfuse_callback(session_id: str = None):
    """
    Returns a configured LangfuseCallbackHandler.
    """
    # Langfuse v3 reads secrets from env. 
    return CallbackHandler(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY")
    )
