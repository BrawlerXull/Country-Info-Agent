# 🌍 Country Information AI Agent

An intelligent AI agent that answers questions about countries using the REST Countries API and LangGraph.

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Powered-green.svg)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async-teal.svg)](https://fastapi.tiangolo.com/)

## 🎯 Features

- **Natural Language Queries**: Ask questions like "What is the population of Germany?" or "Compare Japan and France"
- **Multi-turn Conversations**: Maintains context across messages within a session
- **Intelligent Intent Detection**: Uses structured output (Pydantic) for robust intent parsing
- **Production-Ready**: Async I/O, caching, error handling, structured logging, observability

## 🏗️ Architecture

```mermaid
graph TD
    A[User Query] --> B[FastAPI Endpoint]
    B --> C[LangGraph Agent]

    subgraph LangGraph["LangGraph Workflow"]
        D[identify_intent] --> E[invoke_tool]
        E --> F[synthesize_answer]
    end

    C --> D
    E --> G[REST Countries API]
    G --> E
    F --> H[Response to User]

    subgraph Observability
        I[Langfuse Tracing]
    end

    C -.-> I
```

## 🔄 Agent Flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant I as Identify Intent
    participant T as Invoke Tool
    participant S as Synthesize Answer
    participant RC as REST Countries API

    U->>API: "What is the population of Germany?"
    API->>I: Process query
    I->>I: Extract intent: get_population
    I->>I: Extract countries: ["Germany"]
    I->>T: Pass state
    T->>RC: GET /v3.1/name/germany
    RC-->>T: Country data
    T->>S: Pass tool outputs
    S->>S: Generate answer using LLM
    S-->>API: "Germany has a population of ~83 million"
    API-->>U: JSON Response
```

## 📁 Project Structure

```
country-info-agent/
├── country_info_agent/
│   ├── agent.py              # LangGraph workflow definition
│   ├── api.py                # FastAPI endpoints + Langfuse tracing
│   ├── static/
│   │   └── index.html        # Chat UI
│   └── utils/
│       ├── common.py         # LLM initialization (OpenAI + Gemini fallback)
│       ├── nodes.py          # Graph nodes (intent, tool, synthesis)
│       ├── state.py          # AgentState TypedDict
│       └── tools.py          # REST Countries API tool (cached)
├── docs/                     # 📚 Detailed documentation
│   ├── MEMORY_MANAGEMENT.md  # State & checkpointer options
│   ├── OBSERVABILITY.md      # Langfuse session tracing
│   ├── LLM_FALLBACK.md       # OpenAI → Gemini fallback
│   └── CONCURRENCY.md        # Async I/O & request handling
├── langgraph.json            # LangGraph configuration
├── render.yaml               # Render deployment config
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API Key
- (Optional) Google API Key for Gemini fallback
- (Optional) Langfuse keys for observability

### Local Development

```bash
# Clone the repository
git clone https://github.com/BrawlerXull/Country-Info-Agent.git
cd Country-Info-Agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the server
./run.sh
```

Open **http://localhost:8000** in your browser.

### Docker

```bash
docker build -t country-info-agent .
docker run -p 8000:8000 --env-file .env country-info-agent
```

## 🔧 Environment Variables

| Variable              | Required | Description                   |
| --------------------- | -------- | ----------------------------- |
| `OPENAI_API_KEY`      | ✅       | OpenAI API key                |
| `GOOGLE_API_KEY`      | ❌       | Gemini fallback (recommended) |
| `LANGFUSE_PUBLIC_KEY` | ❌       | Langfuse observability        |
| `LANGFUSE_SECRET_KEY` | ❌       | Langfuse observability        |
| `LANGFUSE_HOST`       | ❌       | Langfuse host URL             |

## 📊 Production Design Decisions

| Feature               | Implementation                        | Documentation                                        |
| --------------------- | ------------------------------------- | ---------------------------------------------------- |
| **Memory Management** | MemorySaver (in-memory)               | [📄 MEMORY_MANAGEMENT.md](docs/MEMORY_MANAGEMENT.md) |
| **LLM Fallback**      | OpenAI → Gemini                       | [📄 LLM_FALLBACK.md](docs/LLM_FALLBACK.md)           |
| **Observability**     | Langfuse session tracing              | [📄 OBSERVABILITY.md](docs/OBSERVABILITY.md)         |
| **Concurrency**       | Async I/O with uvicorn                | [📄 CONCURRENCY.md](docs/CONCURRENCY.md)             |
| **Structured Output** | Pydantic + `with_structured_output()` | Robust JSON parsing                                  |
| **API Caching**       | `@alru_cache(maxsize=128)`            | Reduce API calls                                     |
| **Error Handling**    | Global exception handlers             | Consistent JSON errors                               |

## 🧪 Example Queries

| Query                                | Intent           | Response                       |
| ------------------------------------ | ---------------- | ------------------------------ |
| "What is the population of Germany?" | `get_population` | Germany has ~83 million people |
| "What currency does Japan use?"      | `get_currency`   | Japanese Yen (¥)               |
| "Compare USA and China population"   | `comparison`     | Detailed comparison            |
| "Hello!"                             | `unknown`        | AI-generated friendly greeting |
| "What about Narnia?"                 | `general_info`   | Country not found error        |

## ⚠️ Known Limitations

| Limitation          | Impact                   | Production Solution      |
| ------------------- | ------------------------ | ------------------------ |
| **In-Memory State** | Lost on restart          | Use PostgresSaver        |
| **Single Instance** | Can't horizontally scale | Distributed checkpointer |
| **API Rate Limits** | May be throttled         | Add retry logic          |
| **LLM Costs**       | Per-request charges      | Aggressive caching       |

> 📖 See [MEMORY_MANAGEMENT.md](docs/MEMORY_MANAGEMENT.md) for detailed trade-off analysis.

## 🚢 Deployment

### Render (Recommended)

1. Push to GitHub
2. Connect repo to [Render](https://render.com)
3. Set environment variables in Render dashboard
4. Deploy automatically via `render.yaml`

### Manual Docker Deployment

```bash
docker build -t country-info-agent .
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e GOOGLE_API_KEY=your_key \
  country-info-agent
```

## 📝 API Reference

### POST /query

```json
{
  "question": "What is the capital of France?",
  "session_id": "optional-session-id"
}
```

**Response:**

```json
{
  "answer": "The capital of France is Paris.",
  "intent": "get_capital",
  "countries": ["France"]
}
```

### GET /health

Returns `{"status": "ok"}` for health checks.

## 📚 Documentation

| Document                                          | Description                                             |
| ------------------------------------------------- | ------------------------------------------------------- |
| [MEMORY_MANAGEMENT.md](docs/MEMORY_MANAGEMENT.md) | State management, checkpointer options, why MemorySaver |
| [OBSERVABILITY.md](docs/OBSERVABILITY.md)         | Langfuse integration, session tracing, debugging        |
| [LLM_FALLBACK.md](docs/LLM_FALLBACK.md)           | OpenAI → Gemini fallback mechanism                      |
| [CONCURRENCY.md](docs/CONCURRENCY.md)             | Async I/O, request handling, scaling options            |

## 📜 License

MIT License

---

Built with ❤️ using [LangGraph](https://langchain-ai.github.io/langgraph/) and [FastAPI](https://fastapi.tiangolo.com/)
