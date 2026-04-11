"""Cerebras LLM wrapper (OpenAI-compatible API) with automatic fallback."""
import json
from openai import OpenAI
from config import CEREBRAS_API_KEY, CEREBRAS_BASE_URL, LLM_MODEL

FALLBACK_MODEL = "llama3.1-8b"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(base_url=CEREBRAS_BASE_URL, api_key=CEREBRAS_API_KEY, timeout=30)
    return _client


def call_llm(system, message, model=None, max_tokens=4096):
    """Call Cerebras API with automatic fallback to smaller model on errors."""
    client = _get_client()
    model = model or LLM_MODEL
    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        err = str(e)
        # Retry with fallback on quota, rate limit, context length, or server errors
        retriable = ("429" in err or "quota" in err.lower() or "too_many" in err.lower()
                     or "context_length" in err.lower() or "8192" in err
                     or "500" in err or "502" in err or "503" in err)
        if retriable and model != FALLBACK_MODEL:
            print(f"[llm] {model} error ({err[:80]}), falling back to {FALLBACK_MODEL}")
            try:
                response = client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": message},
                    ],
                )
                return response.choices[0].message.content or ""
            except Exception as e2:
                print(f"[llm] Fallback also failed: {e2}")
                return ""
        print(f"[llm] Error: {err[:120]}")
        return ""


def classify_intent(message):
    """Classify a user message into a known intent. Returns dict with intent + params."""
    system = """Classify the user's message into one of these intents:

SIMPLE (handled by Python backend):
- search_supplier: looking for suppliers or manufacturers (single search)
- draft_rfq: wants to draft/write/compose ONE RFQ email
- send_rfq: wants to send an already-drafted RFQ
- check_inbox: wants to check email for supplier replies
- check_status: wants to see status of quotes/RFQs
- compare_quotes: wants to compare quotes or prices
- escalate: wants to escalate or follow up on stale RFQs
- general_question: simple question that can be answered with quote data context

COMPLEX (requires agent — multi-step, unpredictable, or involves judgment):
- agent_task: use this when the request involves ANY of:
  - Multiple suppliers at once (negotiation, bulk follow-up, BOM sourcing)
  - Spec changes affecting multiple RFQs
  - Reacting to unexpected supplier responses
  - Re-sourcing after failures
  - Multi-step workflows where the next step depends on results of the previous
  - Anything that requires reasoning about strategy, not just data lookup

Return ONLY valid JSON: {"intent": "<intent>", "params": {"query": "...", "supplier": "...", "category": "..."}}
Include only relevant params. Do not include empty params."""

    text = call_llm(system, message, max_tokens=256)

    try:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return {"intent": "unknown", "params": {}}


def extract_json(text, prompt):
    """Use LLM to extract structured JSON from unstructured text."""
    system = prompt + "\n\nReturn ONLY valid JSON. No commentary."
    result = call_llm(system, text, max_tokens=1024)

    try:
        result = result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
            result = result.strip()
        return json.loads(result)
    except (json.JSONDecodeError, IndexError):
        return {}
