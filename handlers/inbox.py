"""Inbox check and quote extraction — Python + LLM for parsing."""
import re
from services import email_client, csv_store, llm, sheets


def handle():
    """Check inbox for supplier replies. Returns summary."""
    quotes, _ = csv_store.read_quotes()

    # Build supplier lookup (name -> active quote)
    active_suppliers = {}
    for q in quotes:
        status = (q.get("status") or "").lower()
        if any(kw in status for kw in ("sent", "follow", "overdue")):
            name = q.get("supplier", "").strip().lower()
            if name:
                active_suppliers[name] = q

    if not active_suppliers:
        return {"processed": 0, "message": "No active RFQs to check"}

    try:
        inbox = email_client.list_inbox(limit=30)
    except Exception as e:
        return {"processed": 0, "error": f"Failed to read inbox: {e}"}

    processed = []

    for msg in inbox:
        # Himalaya returns from as {"name": "...", "addr": "..."} or a string
        from_field = msg.get("from", "")
        if isinstance(from_field, dict):
            sender = (from_field.get("addr", "") or from_field.get("name", "")).lower()
        else:
            sender = str(from_field).lower()
        subject = msg.get("subject", "")

        # Check if sender matches any active supplier
        matched_supplier = None
        for name, q in active_suppliers.items():
            # Match by supplier name in sender address
            name_parts = name.split()
            if any(part in sender for part in name_parts if len(part) > 3):
                matched_supplier = (name, q)
                break

        if not matched_supplier:
            continue

        supplier_name, quote = matched_supplier

        # Read full email body
        try:
            body = email_client.read_email(msg["id"])
        except Exception:
            continue

        if not body:
            continue

        # Use LLM to extract quote data
        extraction = llm.extract_json(body, """Extract pricing/quote information from this supplier email.
Return JSON with these fields (use empty string if not found):
{
  "has_pricing": true/false,
  "quoted_price": "price with currency",
  "unit": "per unit description",
  "lead_time": "delivery time",
  "moq": "minimum order quantity",
  "payment_terms": "payment terms",
  "valid_until": "quote validity date (YYYY-MM-DD format if possible)",
  "summary": "Brief 1-sentence summary of the supplier's response (under 50 chars)"
}""")

        if not extraction:
            continue

        # Update CSV
        updates = {"notes": extraction.get("summary", "Supplier replied")}

        if extraction.get("has_pricing"):
            updates["status"] = "📄 Quote Received"
            if extraction.get("quoted_price"):
                updates["quotedPrice"] = extraction["quoted_price"]
            if extraction.get("unit"):
                updates["unit"] = extraction["unit"]
            if extraction.get("lead_time"):
                updates["leadTime"] = extraction["lead_time"]
            if extraction.get("moq"):
                updates["moq"] = extraction["moq"]
            if extraction.get("payment_terms"):
                updates["paymentTerms"] = extraction["payment_terms"]
            if extraction.get("valid_until"):
                updates["validUntil"] = extraction["valid_until"]
        else:
            updates["status"] = "✅ Responded"

        csv_store.update_quote(quote["supplier"], updates)

        processed.append({
            "supplier": quote["supplier"],
            "status": updates["status"],
            "summary": updates.get("notes", ""),
        })

    if processed:
        sheets.sync()

    return {"processed": len(processed), "results": processed}
