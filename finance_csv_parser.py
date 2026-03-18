"""
finance_csv_parser.py

Single source of truth for CSV ingestion normalization.

Pipeline order (enforced here, not in the caller):
  1. Load raw CSV
  2. Normalize header names (strip, lowercase, spaces→underscores)
  3. Apply column mapping (many raw variants → internal field name)
  4. Derive missing fields where possible (e.g. month from a date column)
  5. Detect schema type from internal fields present
  6. Validate the *internal* schema (never the raw headers)
  7. Return result bundle — caller saves/ingests

Schema types returned:
  "expenses"  — has internal fields: month, category, amount
  "export"    — has internal export fields: rev_type, load_id, customer, gross_revenue, …
  "unknown"   — could not map to either schema
"""

import csv
import logging
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Expense column map
# raw normalized name  →  internal field
# ---------------------------------------------------------------------------
EXPENSE_COLUMN_MAP: dict[str, str] = {
    # ── month / date ──────────────────────────────────────────────────────
    "month":             "month",
    "period":            "month",
    "billing_period":    "month",
    # date-like columns produce "_raw_date"; month is derived afterwards
    "date":              "_raw_date",
    "transaction_date":  "_raw_date",
    "trans_date":        "_raw_date",
    "posted_date":       "_raw_date",
    "post_date":         "_raw_date",
    "billing_date":      "_raw_date",
    "statement_date":    "_raw_date",
    "invoice_date":      "_raw_date",
    "expense_date":      "_raw_date",
    "pay_date":          "_raw_date",

    # ── category ──────────────────────────────────────────────────────────
    "category":          "category",
    "expense_category":  "category",
    "expense_type":      "category",
    "type":              "category",
    "label":             "category",
    "class":             "category",
    "account":           "category",
    "account_name":      "category",
    "description":       "category",
    "memo":              "category",
    "note":              "category",
    "name":              "category",

    # ── amount ────────────────────────────────────────────────────────────
    "amount":            "amount",
    "transaction_amount":"amount",
    "total":             "amount",
    "total_amount":      "amount",
    "charge":            "amount",
    "debit":             "amount",
    "credit":            "amount",
    "expense":           "amount",
    "cost":              "amount",
    "price":             "amount",
    "fee":               "amount",
    "payment":           "amount",
    "sum":               "amount",
    "value":             "amount",
}

# ---------------------------------------------------------------------------
# Export (loads) signature columns — at least THRESHOLD must be present
# after header normalization to be classified as an export file
# ---------------------------------------------------------------------------
EXPORT_SIGNATURE_COLUMNS = {
    "revenue_type_rev_type",
    "revenue_type",
    "shipment_pro",
    "pro",
    "pick_stop_1_ready_or_deliver_date",
    "shipment_customer_total_rates",
    "shipment_carrier_total_rates",
    "shipment_gross_profit",
}
EXPORT_SIGNATURE_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------
class ParseResult(NamedTuple):
    schema_type: str          # "expenses" | "export" | "unknown"
    rows: list[dict]          # normalized rows (internal field names)
    raw_headers: list[str]    # original headers from file
    mapping_used: dict        # raw_normalized → internal
    derived_fields: list[str] # fields that were derived (e.g. "month from date")
    warnings: list[str]
    errors: list[str]
    row_count: int
    skipped_count: int


def _normalize_header(h: str) -> str:
    return h.strip().lower().replace(" ", "_").replace("-", "_")


def parse_csv(file_path: Path, encoding: str = "utf-8-sig") -> ParseResult:
    """
    Full normalization pipeline. Returns a ParseResult regardless of success.
    Caller checks result.errors to decide whether to reject the file.
    """
    file_path = Path(file_path)
    warnings: list[str] = []
    errors: list[str] = []
    derived_fields: list[str] = []

    # ── 1. Load raw CSV ────────────────────────────────────────────────────
    try:
        with open(file_path, "r", newline="", encoding=encoding) as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                errors.append("CSV has no header row.")
                return ParseResult("unknown", [], [], {}, [], warnings, errors, 0, 0)

            raw_headers = list(reader.fieldnames)
            raw_rows = list(reader)
    except UnicodeDecodeError:
        # Retry with latin-1
        try:
            with open(file_path, "r", newline="", encoding="latin-1") as f:
                reader = csv.DictReader(f)
                raw_headers = list(reader.fieldnames or [])
                raw_rows = list(reader)
            warnings.append("File was re-read with latin-1 encoding (not UTF-8).")
        except Exception as e:
            errors.append(f"Could not read file: {e}")
            return ParseResult("unknown", [], [], {}, [], warnings, errors, 0, 0)
    except Exception as e:
        errors.append(f"Could not read file: {e}")
        return ParseResult("unknown", [], [], {}, [], warnings, errors, 0, 0)

    if not raw_rows:
        errors.append("CSV has a header row but no data rows.")
        return ParseResult("unknown", [], raw_headers, {}, [], warnings, errors, 0, 0)

    logger.info(f"[parser] Loaded {len(raw_rows)} rows, {len(raw_headers)} columns from {file_path.name}")
    logger.info(f"[parser] Raw headers: {raw_headers}")

    # ── 2. Normalize header names ──────────────────────────────────────────
    normalized_headers = [_normalize_header(h) for h in raw_headers]
    norm_set = set(normalized_headers)

    # ── 3. Detect export signature FIRST (export files have very specific cols)
    export_matches = sum(1 for col in EXPORT_SIGNATURE_COLUMNS if col in norm_set)
    if export_matches >= EXPORT_SIGNATURE_THRESHOLD:
        logger.info(f"[parser] Detected schema: export ({export_matches} signature columns matched)")
        # For export files, return raw rows with normalized headers — csv_ingestor handles mapping
        mapping_used = {nh: nh for nh in normalized_headers}
        norm_rows = []
        for raw_row in raw_rows:
            norm_row = {_normalize_header(k): v for k, v in raw_row.items() if k}
            norm_rows.append(norm_row)
        return ParseResult(
            "export", norm_rows, raw_headers, mapping_used,
            derived_fields, warnings, errors, len(norm_rows), 0
        )

    # ── 4. Apply expense column map ────────────────────────────────────────
    # Build mapping: normalized_raw_header → internal_field
    mapping_used: dict[str, str] = {}
    for nh in normalized_headers:
        internal = EXPENSE_COLUMN_MAP.get(nh)
        if internal:
            # Only map the first match for each internal field (earlier columns win)
            if internal not in mapping_used.values():
                mapping_used[nh] = internal
                logger.info(f"[parser]   Column mapped: '{nh}' → '{internal}'")
        else:
            logger.info(f"[parser]   Column unmapped: '{nh}' (kept as-is)")

    internal_fields = set(mapping_used.values())

    # ── 5. Derive month from _raw_date if month not directly mapped ────────
    if "month" not in internal_fields and "_raw_date" in internal_fields:
        internal_fields.add("month")
        derived_fields.append("month (derived from date column)")
        logger.info("[parser]   Derived field: 'month' will be extracted from date column")

    # ── 6. Detect schema type from internal fields ─────────────────────────
    expense_required = {"month", "category", "amount"}
    has_expenses = expense_required.issubset(internal_fields)

    if has_expenses:
        schema_type = "expenses"
        logger.info("[parser] Detected schema: expenses")
    else:
        missing_internal = expense_required - internal_fields
        schema_type = "unknown"
        errors.append(
            f"Could not map required fields. "
            f"Internal fields resolved: {sorted(internal_fields or ['(none)'])}. "
            f"Still missing: {sorted(missing_internal)}. "
            f"Raw headers were: {raw_headers}."
        )
        logger.warning(f"[parser] Unknown schema. Missing internal fields: {sorted(missing_internal)}")
        return ParseResult(
            "unknown", [], raw_headers, mapping_used,
            derived_fields, warnings, errors, 0, 0
        )

    # ── 7. Build normalized rows ───────────────────────────────────────────
    # Invert mapping_used: normalized_raw_header → internal_field
    # We need: for each raw row, look up each raw column key → map → internal key
    raw_to_internal: dict[str, str] = {}
    for nh, internal in mapping_used.items():
        raw_to_internal[nh] = internal

    norm_rows = []
    skipped = 0

    for i, raw_row in enumerate(raw_rows, start=2):  # row 2 = first data row
        norm_row: dict[str, str] = {}
        for raw_key, val in raw_row.items():
            if not raw_key:
                continue
            nh = _normalize_header(raw_key)
            internal = raw_to_internal.get(nh)
            if internal and internal not in norm_row:
                norm_row[internal] = val.strip() if val else ""

        # Derive month from _raw_date
        if "month" not in norm_row and "_raw_date" in norm_row:
            raw_date_val = norm_row.pop("_raw_date", "")
            month_val = _derive_month(raw_date_val)
            if month_val:
                norm_row["month"] = month_val
            else:
                warnings.append(f"Row {i}: could not parse date '{raw_date_val}' — month set to ''")
                norm_row["month"] = ""

        # Skip rows missing all three required internal fields
        if not norm_row.get("amount") and not norm_row.get("category") and not norm_row.get("month"):
            skipped += 1
            continue

        norm_rows.append(norm_row)

    if skipped:
        warnings.append(f"{skipped} completely empty rows were skipped.")

    logger.info(f"[parser] Normalized {len(norm_rows)} expense rows ({skipped} skipped)")

    return ParseResult(
        schema_type, norm_rows, raw_headers, mapping_used,
        derived_fields, warnings, errors, len(norm_rows), skipped
    )


def _derive_month(date_str: str) -> str:
    """
    Try to parse a date string into YYYY-MM format.
    Handles common formats: MM/DD/YY, MM/DD/YYYY, YYYY-MM-DD, YYYY-MM, M/D/YY, etc.
    Returns "" on failure.
    """
    if not date_str:
        return ""

    date_str = date_str.strip().split(" ")[0]  # drop time part

    # Already a YYYY-MM string
    if len(date_str) == 7 and date_str[4] == "-":
        return date_str

    # Try multiple formats
    formats = [
        "%m/%d/%y",   # 01/05/26
        "%m/%d/%Y",   # 01/05/2026
        "%-m/%-d/%y", # 1/5/26 (Linux)
        "%Y-%m-%d",   # 2026-01-05
        "%m-%d-%Y",   # 01-05-2026
        "%m-%d-%y",   # 01-05-26
        "%d/%m/%Y",   # European DD/MM/YYYY
        "%Y/%m/%d",   # 2026/01/05
    ]

    from datetime import datetime
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            continue

    return ""


def format_parse_report(result: ParseResult, filename: str) -> str:
    """
    Build a human-readable report string for Discord output.
    """
    lines = [f"**{filename}**"]

    lines.append(f"Schema detected: `{result.schema_type}`")
    lines.append(f"Raw headers: `{', '.join(result.raw_headers)}`")

    if result.mapping_used:
        mapped = [f"`{k}` → `{v}`" for k, v in result.mapping_used.items() if not v.startswith("_")]
        if mapped:
            lines.append("Column mapping: " + ", ".join(mapped))

    if result.derived_fields:
        lines.append("Derived fields: " + ", ".join(result.derived_fields))

    lines.append(f"Rows accepted: **{result.row_count}** | Skipped: {result.skipped_count}")

    if result.warnings:
        lines.append("Warnings:")
        for w in result.warnings[:5]:  # cap at 5 to avoid Discord message limits
            lines.append(f"  ⚠ {w}")
        if len(result.warnings) > 5:
            lines.append(f"  … and {len(result.warnings) - 5} more warnings.")

    if result.errors:
        lines.append("Errors:")
        for e in result.errors:
            lines.append(f"  ✗ {e}")

    return "\n".join(lines)
