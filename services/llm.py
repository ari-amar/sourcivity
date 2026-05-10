"""LLM wrapper with Anthropic and OpenAI-compatible provider support."""
import json
import time
import urllib.error
import urllib.request
from openai import OpenAI
from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_FALLBACK_MODEL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_PRIMARY_COOLDOWN_SECONDS,
    LLM_PROVIDER,
    LLM_TIMEOUT,
    LLM_TOKEN_PARAM,
)

_client = None
_primary_fallback_until = 0


def _get_client():
    global _client
    if LLM_PROVIDER == "anthropic":
        return None
    if _client is None:
        _client = OpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            timeout=LLM_TIMEOUT,
            max_retries=LLM_MAX_RETRIES,
        )
    return _client


def _openai_compatible_completion(client, model, system, message, max_tokens):
    params = {
        "model": model,
        LLM_TOKEN_PARAM: max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
    }
    response = client.chat.completions.create(**params)
    return response.choices[0].message.content or ""


def _anthropic_completion(model, system, message, max_tokens):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": message}],
    }).encode("utf-8")
    req = urllib.request.Request(
        LLM_BASE_URL.rstrip("/") + "/v1/messages",
        data=body,
        headers={
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": LLM_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Anthropic API HTTP {e.code}: {detail[:300]}") from e

    return "".join(
        block.get("text", "")
        for block in data.get("content", [])
        if block.get("type") == "text"
    )


def _call_model(client, model, system, message, max_tokens):
    if LLM_PROVIDER == "anthropic":
        return _anthropic_completion(model, system, message, max_tokens)
    return _openai_compatible_completion(client, model, system, message, max_tokens)


def call_llm(system, message, model=None, max_tokens=4096):
    """Call the configured LLM provider with optional fallback on retriable errors."""
    global _primary_fallback_until
    client = _get_client()
    requested_model = model or LLM_MODEL
    model = requested_model
    if LLM_FALLBACK_MODEL and requested_model != LLM_FALLBACK_MODEL and time.time() < _primary_fallback_until:
        model = LLM_FALLBACK_MODEL
    try:
        return _call_model(client, model, system, message, max_tokens)
    except Exception as e:
        err = str(e)
        # Retry with fallback on quota, rate limit, context length, or server errors
        retriable = ("429" in err or "quota" in err.lower() or "too_many" in err.lower()
                     or "context_length" in err.lower() or "8192" in err
                     or "500" in err or "502" in err or "503" in err)
        if retriable and LLM_FALLBACK_MODEL and model != LLM_FALLBACK_MODEL:
            _primary_fallback_until = time.time() + LLM_PRIMARY_COOLDOWN_SECONDS
            print(f"[llm] {LLM_PROVIDER}:{model} error ({err[:80]}), falling back to {LLM_FALLBACK_MODEL}")
            try:
                return _call_model(client, LLM_FALLBACK_MODEL, system, message, max_tokens)
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
