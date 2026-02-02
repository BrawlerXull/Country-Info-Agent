import logging
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from country_info_agent.agent import create_graph
import os
from country_info_agent.utils.common import get_langfuse_callback
from langfuse import Langfuse, observe
from langfuse.langchain import CallbackHandler
from langchain_core.messages import HumanMessage

# Setup Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Country Information Agent")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal Server Error. Please try again later."}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the graph
try:
    agent_graph = create_graph()
    logger.info("Agent graph initialized successfully.")
except Exception as e:
    logger.critical(f"Failed to initialize agent graph: {e}", exc_info=True)
    raise e

class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"

class QueryResponse(BaseModel):
    answer: str
    intent: str = None
    countries: list = []

# Initialize global Langfuse client
langfuse_client = Langfuse()

@app.post("/query", response_model=QueryResponse)
@observe(as_type="generation") 
async def query_agent(request: QueryRequest):
    """
    Endpoint to query the agent.
    """
    logger.info(f"Received query from session {request.session_id}: {request.question}")
    try:
        # 1. explicitely set session_id on the current trace
        langfuse_client.update_current_trace(
            session_id=request.session_id,
            tags=["country-agent", "production"],
            metadata={
                "source": "web-ui",
                "user_agent": "fastapi"
            }
        )
        
        # 2. Get the current trace ID matching this observation
        trace_id = langfuse_client.get_current_trace_id()
        
        # 3. Initialize Langfuse callback linked to this trace
        langfuse_handler = CallbackHandler(
             public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
             trace_context={"trace_id": trace_id}
        )
        
        # Config for the thread and callbacks
        config = {
            "configurable": {"thread_id": request.session_id},
            "callbacks": [langfuse_handler]
        }
        
        # Initial state 
        initial_state = {
            "question": request.question,
            "messages": [HumanMessage(content=request.question)]
        }
        
        # Invoke the graph
        result = await agent_graph.ainvoke(initial_state, config=config)
        
        logger.info(f"Generated answer for session {request.session_id}")
        
        return QueryResponse(
            answer=result.get("final_answer", "No answer generated."),
            intent=result.get("intent"),
            countries=result.get("countries", [])
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Mount static files at the end
# Since we moved api.py to country_info_agent/api.py, static is in country_info_agent/static
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
