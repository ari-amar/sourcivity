"""Quote comparison — Python + optional LLM recommendation."""
from services import csv_store, llm


def handle(category=None, part=None, recommend=False):
    """Compare quotes, optionally with LLM recommendation."""
    quotes, _ = csv_store.read_quotes()

    # Filter
    filtered = []
    for q in quotes:
        if category and q.get("category", "").lower() != category.lower():
            continue
        if part and part.lower() not in q.get("partService", "").lower():
            continue
        if q.get("quotedPrice", "").strip():
            filtered.append(q)

    # Sort by price (numeric)
    def parse_price(q):
        price = q.get("quotedPrice", "").strip().replace("$", "").replace(",", "")
        try:
            return float(price)
        except ValueError:
            return float("inf")

    filtered.sort(key=parse_price)

    result = {"quotes": filtered, "count": len(filtered)}

    if recommend and filtered:
        try:
            import json
            quotes_text = json.dumps(filtered, indent=2)
            rec = llm.call_llm(
                system="You are a procurement advisor. Compare these supplier quotes and recommend the best value considering price, lead time, and MOQ trade-offs. Be concise (3-4 sentences).",
                message=quotes_text,
                max_tokens=512
            )
            result["recommendation"] = rec
        except Exception as e:
            result["recommendation"] = f"Analysis unavailable: {e}"

    return result
