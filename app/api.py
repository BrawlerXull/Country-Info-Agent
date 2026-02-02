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


class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    intent: str = None
    country: str = None

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Endpoint to query the agent.
    """
    try:
        # Initial state
        initial_state = {"question": request.question}
        
        # Invoke the graph
        result = agent_graph.invoke(initial_state)
        
        return QueryResponse(
            answer=result.get("final_answer", "No answer generated."),
            intent=result.get("intent"),
            country=result.get("country")
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
