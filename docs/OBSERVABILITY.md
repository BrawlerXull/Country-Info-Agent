# 📊 Observability & Session Tracing with Langfuse

This document explains how the Country Information AI Agent integrates Langfuse for full observability, session tracing, and production monitoring.

## Why Langfuse?

| Need                | Solution                        |
| ------------------- | ------------------------------- |
| Debug LLM responses | See exact prompts and outputs   |
| Track costs         | Token usage per request         |
| Monitor latency     | Time each step in the pipeline  |
| Group conversations | Session-based trace grouping    |
| Production insights | Identify bottlenecks and errors |

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Request                          │
│                                                                 │
│  @observe(as_type="generation")  ← Root trace created here     │
│  async def query_agent():                                       │
│      │                                                          │
│      ├── update_current_trace(session_id=...)                   │
│      │   └── Groups all traces by session                       │
│      │                                                          │
│      ├── CallbackHandler(trace_context={...})                   │
│      │   └── Links LangGraph to this trace                      │
│      │                                                          │
│      └── agent_graph.ainvoke(..., config=config)                │
│          │                                                      │
│          ├── identify_intent()  ← Traced as span                │
│          ├── invoke_tool()      ← Traced as span                │
│          │   └── @observe on fetch_country_info()               │
│          └── synthesize_answer() ← Traced as span               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Langfuse Cloud  │
                    │   Dashboard     │
                    └─────────────────┘
```

---

## Implementation Details

### 1. Root Trace with @observe Decorator

```python
# country_info_agent/api.py
from langfuse import Langfuse, observe

langfuse_client = Langfuse()

@app.post("/query")
@observe(as_type="generation")  # Creates root trace
async def query_agent(request: QueryRequest):
    ...
```

The `@observe` decorator:

- Creates a new trace for each API request
- Captures input/output automatically
- Can be typed as "generation", "span", or "event"

### 2. Session Grouping

```python
# Group traces by conversation session
langfuse_client.update_current_trace(
    session_id=request.session_id,
    tags=["country-agent", "production"],
    metadata={
        "source": "web-ui",
        "user_agent": "fastapi"
    }
)
```

This ensures:

- All messages from the same user session appear together
- Easy filtering in Langfuse dashboard by session
- Metadata helps identify request sources

### 3. LangGraph Callback Integration

```python
# Get trace ID for linking
trace_id = langfuse_client.get_current_trace_id()

# Create callback handler linked to current trace
langfuse_handler = CallbackHandler(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    trace_context={"trace_id": trace_id}
)

# Pass to LangGraph
config = {
    "configurable": {"thread_id": request.session_id},
    "callbacks": [langfuse_handler]
}

result = await agent_graph.ainvoke(initial_state, config=config)
```

The `trace_context` linking ensures:

- LangGraph node executions appear as child spans
- All LLM calls are captured with prompts/completions
- Token usage is tracked per node

### 4. Tool-Level Tracing

```python
# country_info_agent/utils/tools.py
from langfuse import observe

@observe(as_type="generation")
async def fetch_country_info(country_name: str) -> Dict[str, Any]:
    ...
```

This captures:

- API call inputs (country name)
- API response data
- Execution time
- Any errors

---

## What Gets Captured

### Per Request:

| Field          | Example                              |
| -------------- | ------------------------------------ |
| **Input**      | "What is the population of Germany?" |
| **Output**     | "Germany has ~83 million people"     |
| **Session ID** | session_abc123                       |
| **Duration**   | 1.2s                                 |
| **Tokens**     | 150 input, 50 output                 |
| **Model**      | gpt-3.5-turbo                        |

### Per Node (Span):

| Node                | Captured Data                                  |
| ------------------- | ---------------------------------------------- |
| `identify_intent`   | Prompt, structured output (intent + countries) |
| `invoke_tool`       | Countries queried, API responses               |
| `synthesize_answer` | Context data, final response                   |

---

## Debugging Challenges We Solved

### Challenge: Traces Not Grouping by Session

**Problem**: Each request created separate traces, making conversation debugging hard.

**Root Cause**: `session_id` wasn't being passed to Langfuse.

**Solution**:

```python
langfuse_client.update_current_trace(session_id=request.session_id)
```

### Challenge: LangGraph Spans Not Appearing

**Problem**: Only the root API trace showed up; LangGraph execution was invisible.

**Root Cause**: `CallbackHandler` wasn't linked to the current trace.

**Solution**:

```python
trace_id = langfuse_client.get_current_trace_id()
langfuse_handler = CallbackHandler(trace_context={"trace_id": trace_id})
```

---

## Environment Configuration

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

Langfuse auto-reads these from environment. No additional configuration needed.

---

## Dashboard Views

### Session View

- See all messages in a conversation
- Track user journey across multiple queries
- Identify where conversations break down

### Trace Timeline

- Visualize sequential node execution
- Spot slow steps (API calls, LLM inference)
- Debug failures with full context

### Cost Tracking

- Token usage per request
- Daily/weekly cost trends
- Identify expensive queries

---

## Alternative Observability Options (Not Chosen)

### 1. LangSmith

**Pros**: Native LangChain integration, great debugging
**Cons**: Less flexible session grouping, separate ecosystem

### 2. OpenTelemetry + Jaeger

**Pros**: Industry standard, self-hosted option
**Cons**: Complex setup, no LLM-specific features

### 3. Custom Logging

**Pros**: Full control, no external dependencies
**Cons**: No dashboard, manual parsing needed

### 4. No Observability

**Pros**: Zero complexity
**Cons**: Debugging is nearly impossible in production

**Why Langfuse?**

- Built specifically for LLM applications
- Easy integration with LangChain/LangGraph
- Excellent session grouping for chat apps
- Free tier sufficient for demos

---

## Production Recommendations

1. **Set up alerts** for error rates and latency spikes
2. **Use metadata** to track deployment versions
3. **Sample traces** in high-traffic scenarios (e.g., 10%)
4. **Archive old traces** to manage storage
5. **Add user identifiers** (if applicable) for support debugging
