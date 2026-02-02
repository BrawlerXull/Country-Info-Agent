# ⚡ Concurrency & Request Handling

This document explains how the Country Information AI Agent handles multiple concurrent requests, the async architecture used, and alternatives considered.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Uvicorn Server                          │
│                    (Single Process, Async I/O)                  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Event Loop (asyncio)                   │   │
│  │                                                          │   │
│  │   Request 1 ──┐                                          │   │
│  │               │     ┌─────────────┐                      │   │
│  │   Request 2 ──┼────▶│  FastAPI    │──▶ Non-blocking      │   │
│  │               │     │  Coroutines │    LLM/API calls     │   │
│  │   Request 3 ──┘     └─────────────┘                      │   │
│  │                           │                               │   │
│  │                           ▼                               │   │
│  │               All requests handled concurrently           │   │
│  │               without spawning threads/processes          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## What We Use

### 1. Async/Await (Coroutines)

```python
# country_info_agent/api.py
@app.post("/query")
async def query_agent(request: QueryRequest):  # async endpoint
    result = await agent_graph.ainvoke(...)    # await LangGraph
    return result

# country_info_agent/utils/nodes.py
async def identify_intent(state, config):
    result = await chain.ainvoke(...)  # await LLM call
    return result

# country_info_agent/utils/tools.py
async def fetch_country_info(country_name):
    async with httpx.AsyncClient() as client:  # async HTTP
        response = await client.get(...)
        return response
```

**Why async everywhere?**

- Single thread handles many requests
- While waiting for LLM/API response, other requests proceed
- No thread overhead, efficient memory usage

### 2. Uvicorn (ASGI Server)

```bash
# run.sh
uvicorn country_info_agent.api:app --host 0.0.0.0 --port 8000
```

**Uvicorn provides:**

- ASGI-compatible server for FastAPI
- Single-process async event loop
- Handles HTTP/WebSocket connections
- Production-grade performance

### 3. httpx.AsyncClient

```python
async with httpx.AsyncClient() as client:
    response = await client.get(url, timeout=10.0)
```

**Why httpx over requests?**

- Native async support
- Connection pooling
- HTTP/2 support
- Timeout handling

---

## Request Flow Example

```
Time →
═══════════════════════════════════════════════════════════════

Request 1 arrives ───┬──[Identify Intent]──[Wait LLM]──┐
                     │                                  │
Request 2 arrives ───┼────────────┬──[Identify Intent]──[Wait LLM]──┐
                     │            │                     │            │
Request 3 arrives ───┼────────────┼─────────┬──[Identify]──[Wait]───┼───┐
                     │            │         │           │            │   │
                     │            │         │           └──[Continue R1]─┼──▶ Response 1
                     │            │         │                        │   │
                     │            │         └───────────────────────[R3]─┼──▶ Response 3
                     │            │                                      │
                     │            └──────────────────────────────────────┴──▶ Response 2

All 3 requests handled concurrently by a SINGLE thread!
```

---

## What We Don't Use (And Why)

### 1. Multi-Worker Uvicorn

```bash
# NOT using this:
uvicorn app:app --workers 4
```

**What it does**: Spawns multiple processes, each with its own event loop.

**Why we don't use it**:

- MemorySaver doesn't share state between workers
- Request 1 might go to Worker A, Request 2 to Worker B
- Session continuity breaks (different memory)
- Would need PostgresSaver for multi-worker

**When to use**: Only with distributed checkpointer (Postgres, Redis).

### 2. Gunicorn with Uvicorn Workers

```bash
# NOT using this:
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker
```

**Why not**: Same issue as multi-worker - breaks in-memory state.

### 3. Threading (ThreadPoolExecutor)

```python
# NOT using this:
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=10)
```

**Why not**:

- Python GIL limits true parallelism
- More memory per thread
- Async is more efficient for I/O-bound work
- LangChain/LangGraph are async-native

### 4. Multiprocessing

```python
# NOT using this:
from multiprocessing import Pool
```

**Why not**:

- Heavy process spawning overhead
- Each process loads entire model again
- Memory multiplication (RAM × processes)
- Overkill for I/O-bound LLM calls

### 5. Celery Task Queue

```python
# NOT using this:
@celery.task
def process_query(question):
    return agent.invoke(question)
```

**Why not**:

- Adds Redis/RabbitMQ dependency
- Latency for simple Q&A (queue overhead)
- Complexity doesn't match use case
- Would consider for batch processing

---

## Performance Characteristics

### Current Setup (Single Process, Async)

| Metric              | Value    | Notes                          |
| ------------------- | -------- | ------------------------------ |
| Concurrent requests | ~100-500 | Limited by LLM API, not server |
| Memory per request  | Minimal  | Shared event loop              |
| Latency             | 1-3s     | Dominated by LLM response time |
| Startup time        | ~2s      | Fast cold start                |

### Bottleneck Analysis

```
┌─────────────────────────────────────────────────────────────┐
│                    Request Duration Breakdown               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ├── Network (request arrives)      ~10ms  ████            │
│  ├── identify_intent (LLM call)    ~500ms  ████████████████│
│  ├── invoke_tool (API call)        ~200ms  ████████        │
│  ├── synthesize_answer (LLM call)  ~500ms  ████████████████│
│  └── Network (response sent)        ~10ms  ████            │
│                                                             │
│  Total: ~1200ms                                             │
│                                                             │
│  💡 90% of time is waiting for external APIs (LLM + REST)   │
│     → Async is perfect for this! Server isn't blocking.    │
└─────────────────────────────────────────────────────────────┘
```

---

## Scaling Options

### Option 1: Vertical Scaling (More Resources)

```yaml
# render.yaml
services:
  - type: web
    plan: standard # or pro
```

More CPU/RAM on same instance. Works with MemorySaver.

### Option 2: Horizontal Scaling (Multiple Instances)

Requires changing checkpointer:

```python
# Switch from:
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# To:
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
```

Then scale to multiple workers/instances.

### Option 3: Rate Limiting + Queue

For very high traffic:

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/query")
@limiter.limit("10/minute")
async def query_agent(request):
    ...
```

---

## Docker Configuration

```dockerfile
# Dockerfile
CMD ["sh", "-c", "exec uvicorn country_info_agent.api:app --host 0.0.0.0 --port ${PORT}"]
```

**Note**: No `--workers` flag = single process, async-only.
This is intentional for MemorySaver compatibility.

---

## Production Recommendations

1. **Current setup works for**: Demos, low-to-medium traffic (< 50 concurrent users)

2. **If you need more scale**:
   - Add PostgresSaver
   - Use `uvicorn --workers 4`
   - Deploy behind load balancer

3. **Monitor these metrics**:
   - Request latency (p50, p95, p99)
   - Active connections
   - Memory usage
   - LLM API rate limits

4. **Caching helps more than workers**:
   - LRU cache on API calls reduces load
   - Same country query = instant response
   - Focus on cache hit rate before adding workers
