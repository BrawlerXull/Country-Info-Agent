from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.graph import create_graph
import os

app = FastAPI(title="Country Information Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the graph
agent_graph = create_graph()


from langchain_core.messages import HumanMessage
from typing import Optional

# ... imports ...

class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"

class QueryResponse(BaseModel):
    answer: str
    intent: str = None
    countries: list = []

from app.utils import get_langfuse_callback
from langfuse import Langfuse

# Initialize global Langfuse client to capture any implicit traces and suppress "No Langfuse client" warnings
# This reads from environment variables (LANGFUSE_PUBLIC_KEY, etc.)
langfuse_client = Langfuse()

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Endpoint to query the agent.
    """
    try:
        # Initialize Langfuse callback
        langfuse_handler = get_langfuse_callback(session_id=request.session_id)
        
        # Config for the thread and callbacks
        config = {
            "configurable": {"thread_id": request.session_id},
            "callbacks": [langfuse_handler],
            "tags": ["country-agent", "production"],
            "metadata": {
                "session_id": request.session_id,
                "source": "web-ui",
                "user_agent": "fastapi"
            }
        }
        
        # Initial state (LangGraph handles checking for existing state via thread_id)
        # We pass the new message to be added to history
        initial_state = {
            "question": request.question,
            "messages": [HumanMessage(content=request.question)]
        }
        
        # Invoke the graph
        # For stateful graphs, we typically pass the *update* to the state.
        # Since 'messages' is Annotated with add_messages, passing a new message works.
        # But our custom node reads "question".
        
        result = agent_graph.invoke(initial_state, config=config)
        
        return QueryResponse(
            answer=result.get("final_answer", "No answer generated."),
            intent=result.get("intent"),
            countries=result.get("countries", [])
        )
    except ValueError as e:
        # Handle missing API key or configuration errors
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Mount static files at the end
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
