"""CSV read/write with file locking for quote-tracker.csv."""
import csv
import fcntl
import os
from config import QUOTES_CSV, CSV_KEYS, CSV_COLUMNS, CATEGORIES

EXPECTED_COLS = len(CSV_KEYS)  # 12


def read_quotes():
    """Read CSV and return list of dicts with 12 keys + warnings."""
    quotes = []
    warnings = []
    try:
        with open(QUOTES_CSV, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for line_num, row in enumerate(reader, start=2):
                if len(row) < 2:
                    continue
                if len(row) < EXPECTED_COLS:
                    warnings.append(
                        f"Row {line_num} ({row[1] if len(row) > 1 else '?'}) "
                        f"has {len(row)} columns, expected {EXPECTED_COLS} — padded"
                    )
                    row.extend([""] * (EXPECTED_COLS - len(row)))
                q = {}
                for i, key in enumerate(CSV_KEYS):
                    q[key] = row[i].strip() if i < len(row) else ""
                quotes.append(q)
    except FileNotFoundError:
        pass
    return quotes, warnings


def write_quotes(quotes):
    """Write full CSV with header. Uses file locking."""
    with open(QUOTES_CSV, "w", newline="", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
            for q in quotes:
                row = [q.get(key, "") for key in CSV_KEYS]
                writer.writerow(row)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def append_quote(quote):
    """Append a single quote row within its category group."""
    quotes, _ = read_quotes()
    category = quote.get("category", "")

    # Find insertion point: after last row of same category
    insert_idx = len(quotes)
    found_cat = False
    for i, q in enumerate(quotes):
        if q.get("category") == category:
            found_cat = True
            insert_idx = i + 1
        elif found_cat:
            break

    quotes.insert(insert_idx, quote)
    write_quotes(quotes)


def update_quote(supplier, updates):
    """Update the first row matching supplier name."""
    quotes, _ = read_quotes()
    changed = False
    for q in quotes:
        if q.get("supplier", "").strip().lower() == supplier.strip().lower():
            for k, v in updates.items():
                if k in CSV_KEYS:
                    q[k] = v
            changed = True
            break
    if changed:
        write_quotes(quotes)
    return changed
