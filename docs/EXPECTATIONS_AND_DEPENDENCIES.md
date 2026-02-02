# 📋 Production Expectations & Dependencies

This document verifies how the Country Information AI Agent meets production expectations and lists all external dependencies.

---

## ✅ Expectations Verification

### 1. Accurate, Grounded Answers

| Implementation        | Details                                                                   |
| --------------------- | ------------------------------------------------------------------------- |
| **Real Data Source**  | REST Countries API - answers grounded in actual data, not hallucinated    |
| **Structured Output** | Pydantic `IntentSchema` with `with_structured_output()` forces valid JSON |
| **Context Injection** | LLM synthesizes answers using actual API data as context                  |
| **Caching**           | `@alru_cache` ensures consistent, fast responses                          |

---

### 2. Handle Invalid Inputs & Partial Data Gracefully

| Scenario          | Handling                                 | Location          |
| ----------------- | ---------------------------------------- | ----------------- |
| Unknown intent    | Friendly greeting via LLM                | `nodes.py:94-116` |
| Country not found | `{"status": "error", "message": "..."}`  | `tools.py:64`     |
| API 404/errors    | Graceful error message, no crash         | `tools.py:63-66`  |
| Network errors    | Caught with `httpx.RequestError`         | `tools.py:68-69`  |
| LLM errors        | `try/except` returns `intent: "unknown"` | `nodes.py:55-59`  |
| Global exceptions | FastAPI handlers return consistent JSON  | `api.py:26-40`    |

---

### 3. Structured & Maintainable Code

| Aspect                 | Implementation                                 |
| ---------------------- | ---------------------------------------------- |
| Separation of Concerns | `agent.py`, `nodes.py`, `tools.py`, `state.py` |
| Centralized Config     | `config/settings.py` with Pydantic Settings    |
| Type Safety            | `TypedDict`, Pydantic models                   |
| Logging                | Structured logging with `logger`               |
| Test Coverage          | 24 unit tests in `tests/`                      |
| Documentation          | 5 design decision docs in `docs/`              |

---

### 4. Production-Ready Design

| Feature          | Implementation       | Documentation                                  |
| ---------------- | -------------------- | ---------------------------------------------- |
| LLM Fallback     | OpenAI → Gemini      | [LLM_FALLBACK.md](./LLM_FALLBACK.md)           |
| Observability    | Langfuse tracing     | [OBSERVABILITY.md](./OBSERVABILITY.md)         |
| State Management | MemorySaver          | [MEMORY_MANAGEMENT.md](./MEMORY_MANAGEMENT.md) |
| Concurrency      | Async I/O            | [CONCURRENCY.md](./CONCURRENCY.md)             |
| Health Checks    | `/health` endpoint   | `api.py:126-128`                               |
| CORS             | Configurable via env | `config/settings.py`                           |

---

## 🤖 LLM Models Used

| Model                | Provider | Role         | Configuration                      |
| -------------------- | -------- | ------------ | ---------------------------------- |
| **gpt-4o-mini**      | OpenAI   | Primary LLM  | Intent detection, answer synthesis |
| **gemini-2.0-flash** | Google   | Fallback LLM | Activates on OpenAI failure        |

### Fallback Triggers

The system automatically switches to Gemini when OpenAI encounters:

- `AuthenticationError` - Invalid/expired API key
- `RateLimitError` - Too many requests (quota exceeded)
- `APIError` - Server errors (500, 503, etc.)
- Generic `Exception` - Catch-all for unexpected issues

---

## 📦 External Dependencies

### Core Framework

| Package       | Version | Purpose                                        |
| ------------- | ------- | ---------------------------------------------- |
| **LangGraph** | Latest  | Agent workflow orchestration, state management |
| **LangChain** | Latest  | LLM abstractions, prompt templates             |
| **FastAPI**   | Latest  | Async REST API framework                       |
| **Uvicorn**   | Latest  | ASGI production server                         |

### LLM Providers

| Package                    | Purpose                           |
| -------------------------- | --------------------------------- |
| **langchain-openai**       | OpenAI GPT-3.5/GPT-4 integration  |
| **langchain-google-genai** | Google Gemini integration         |
| **openai**                 | Error types for fallback handling |

### Observability

| Package      | Purpose                                             |
| ------------ | --------------------------------------------------- |
| **Langfuse** | Tracing, session grouping, cost tracking, debugging |

### Utilities

| Package               | Purpose                                  |
| --------------------- | ---------------------------------------- |
| **httpx**             | Async HTTP client for REST Countries API |
| **pydantic**          | Data validation, request/response models |
| **pydantic-settings** | Environment-based configuration          |
| **python-dotenv**     | `.env` file loading                      |
| **async-lru**         | Async-compatible LRU caching             |

### Testing

| Package            | Purpose            |
| ------------------ | ------------------ |
| **pytest**         | Test framework     |
| **pytest-asyncio** | Async test support |

---

## 🔗 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI + Uvicorn                     │
│                         ↓                                │
│              ┌─────────────────────┐                     │
│              │     LangGraph       │                     │
│              │   (Agent Workflow)  │                     │
│              └──────────┬──────────┘                     │
│         ┌───────────────┼───────────────┐                │
│         ↓               ↓               ↓                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │ LangChain  │  │   httpx    │  │  Langfuse  │          │
│  │ (LLM Calls)│  │ (REST API) │  │ (Tracing)  │          │
│  └─────┬──────┘  └────────────┘  └────────────┘          │
│        │                                                 │
│  ┌─────┴─────────────────┐                               │
│  │   OpenAI → Gemini     │                               │
│  │     (with fallback)   │                               │
│  └───────────────────────┘                               │
└─────────────────────────────────────────────────────────┘
```

---

## 📄 Full Requirements

```txt
# Core
fastapi
uvicorn
langgraph
langchain

# LLM Providers
langchain-openai
langchain-google-genai
openai

# Observability
langfuse

# Utilities
httpx
pydantic-settings
python-dotenv
async-lru

# Testing
pytest
pytest-asyncio
```
