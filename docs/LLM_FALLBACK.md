# 🔄 LLM Fallback Mechanism

This document explains how the Country Information AI Agent implements resilient LLM calls with automatic fallback from OpenAI to Google Gemini.

## Why Fallback?

| Scenario             | Impact Without Fallback | With Fallback           |
| -------------------- | ----------------------- | ----------------------- |
| OpenAI rate limited  | ❌ Request fails        | ✅ Switches to Gemini   |
| OpenAI API down      | ❌ Service unavailable  | ✅ Continues working    |
| Authentication error | ❌ 401 crash            | ✅ Tries alternative    |
| Network issues       | ❌ User sees error      | ✅ Graceful degradation |

---

## Implementation

```python
# country_info_agent/utils/common.py

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import AuthenticationError, RateLimitError, APIError

def get_llm(temperature=0, model="gpt-3.5-turbo", max_tokens=None, tools=None):
    """
    Returns a ChatOpenAI model with a Gemini fallback.
    """

    # Primary Model: OpenAI
    openai_model = ChatOpenAI(
        model=model,
        temperature=temperature,
        max_retries=0  # Disable internal retries to trigger fallback immediately
    )

    # Fallback Model: Google Gemini
    gemini_model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=temperature,
        convert_system_message_to_human=True
    )

    # Create Fallback Chain
    model_with_fallback = openai_model.with_fallbacks(
        [gemini_model],
        exceptions_to_handle=(AuthenticationError, RateLimitError, APIError, Exception)
    )

    return model_with_fallback
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                           │
│                         │                               │
│                         ▼                               │
│              ┌─────────────────┐                        │
│              │   OpenAI API    │                        │
│              │  (gpt-3.5-turbo)│                        │
│              └────────┬────────┘                        │
│                       │                                 │
│         ┌─────────────┴─────────────┐                   │
│         │                           │                   │
│    Success?                    Exception?               │
│         │                           │                   │
│         ▼                           ▼                   │
│    ┌─────────┐              ┌─────────────────┐         │
│    │ Return  │              │ Fallback to     │         │
│    │ Result  │              │ Gemini 2.0 Flash│         │
│    └─────────┘              └────────┬────────┘         │
│                                      │                  │
│                              Success or Error           │
│                                      │                  │
│                                      ▼                  │
│                              ┌─────────────┐            │
│                              │   Return    │            │
│                              │   Result    │            │
│                              └─────────────┘            │
└─────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. `max_retries=0` on OpenAI

```python
openai_model = ChatOpenAI(
    model=model,
    max_retries=0  # Important!
)
```

**Why?** By default, LangChain retries failed requests. This delays the fallback. Setting `max_retries=0` means:

- First failure → Immediate fallback to Gemini
- Faster recovery for users
- No wasted time on a broken provider

### 2. Broad Exception Handling

```python
exceptions_to_handle=(AuthenticationError, RateLimitError, APIError, Exception)
```

We catch:

- `AuthenticationError` → Invalid/expired API key
- `RateLimitError` → Too many requests
- `APIError` → Server errors (500, 503, etc.)
- `Exception` → Catch-all for unexpected issues

### 3. Gemini Model Choice

```python
gemini_model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",  # Fast and cheap
    convert_system_message_to_human=True
)
```

**Why gemini-2.0-flash?**

- Fastest Gemini model
- Large context window (1M tokens)
- Cost-effective for fallback scenarios
- Good enough quality for country Q&A

### 4. System Message Conversion

```python
convert_system_message_to_human=True
```

Some Gemini versions handle system messages differently. This flag ensures compatibility by converting system messages to human messages when needed.

---

## Configuration Required

```bash
# .env
OPENAI_API_KEY=sk-proj-xxxxx      # Required: Primary LLM
GOOGLE_API_KEY=AIzaSyxxxxxx       # Recommended: Fallback LLM
```

**If GOOGLE_API_KEY is missing:**

- Fallback will fail with authentication error
- System degrades to OpenAI-only mode
- Recommend always configuring both

---

## Testing the Fallback

### Method 1: Invalid OpenAI Key

```bash
# Temporarily set invalid key
OPENAI_API_KEY=invalid-key ./run.sh
```

Expected: Gemini handles all requests.

### Method 2: Simulate Rate Limit

In production, if you see logs like:

```
RateLimitError: You exceeded your current quota
```

The fallback automatically activates.

---

## Alternatives Considered

### 1. Retry-Only (No Fallback)

```python
openai_model = ChatOpenAI(max_retries=3)
```

**Pros**: Simple, single provider
**Cons**: Still fails if OpenAI is down

**Not chosen**: Doesn't provide true resilience.

### 2. Load Balancer Approach

```python
# Round-robin between providers
models = [openai_model, gemini_model]
model = random.choice(models)
```

**Pros**: Distributes load
**Cons**: Unnecessary complexity, doubles costs

**Not chosen**: Overkill for this use case.

### 3. Manual Try/Except

```python
try:
    return openai_model.invoke(...)
except:
    return gemini_model.invoke(...)
```

**Pros**: Full control
**Cons**: Duplicated code everywhere

**Not chosen**: LangChain's `with_fallbacks()` is cleaner.

### 4. Single Provider Only

```python
return ChatOpenAI(model="gpt-3.5-turbo")
```

**Pros**: Simplest
**Cons**: Single point of failure

**Not chosen**: Production services need resilience.

---

## Cost Implications

| Scenario                  | Cost Impact                          |
| ------------------------- | ------------------------------------ |
| Normal operation (OpenAI) | Standard GPT-3.5 pricing             |
| Fallback active (Gemini)  | Gemini Flash pricing (often cheaper) |
| Both configured           | Only pay for what you use            |

**Tip**: Gemini fallback can actually reduce costs during OpenAI outages since Gemini Flash is typically cheaper.

---

## Monitoring Fallback Usage

In Langfuse, you can identify fallback usage by:

1. Model field shows "gemini-2.0-flash" instead of "gpt-3.5-turbo"
2. Add custom metadata when fallback triggers (future enhancement)

---

## Production Recommendations

1. **Always configure both API keys** for resilience
2. **Monitor fallback frequency** - if too high, investigate primary provider
3. **Test fallback periodically** - ensure Gemini key is valid
4. **Consider adding Anthropic Claude** as tertiary fallback
5. **Set up alerts** for extended fallback periods
