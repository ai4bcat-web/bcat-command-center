"""
finance_csv_parser.py

Single source of truth for CSV ingestion normalization.

Pipeline order (enforced here, not in the caller):
  1. Load raw CSV
  2. Normalize header names (strip, lowercase, spaces→underscores)
  3. Detect schema type from normalized headers (content-based, filename-independent)
  4. For expenses: apply column mapping, derive missing fields, validate
  5. Return result bundle — caller saves/ingests

Schema types returned (detection order matters — first match wins):
  "export"           — has a B/I row-level marker column + load/revenue indicators
                       (TMS signature columns OR marker-column + load-indicator)
                       → caller passes to csv_ingestor for B/I split
  "amazon_relay"     — Amazon Relay DSP trip export (driver_name, trip_id,
                       estimated_cost, load_execution_status columns present)
                       → caller saves as amazon_relay.csv; finance_agent reads it
  "brokerage_direct" — pre-processed brokerage CSV (gross_revenue + carrier_pay present,
                       no B/I marker column)
                       → caller saves directly as brokerage_loads.csv
  "ivan_direct"      — pre-processed Ivan Cartage CSV (revenue present, no carrier_pay,
                       no B/I marker column)
                       → caller saves directly as ivan_cartage_loads.csv
  "expenses"         — has internal fields: month, category, amount
                       → caller writes normalized expense rows
  "unknown"          — could not map to any known schema
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
# Export detection — two independent paths to "export" classification:
#
# Path A (TMS signature): at least THRESHOLD of these specific TMS column names
#   must be present after header normalization.
#
# Path B (content-based): at least one MARKER_COLUMN_VARIANT is present AND
#   at least one LOAD_INDICATOR_COLUMN is present. This covers non-TMS exports
#   that use different column names (division, business_unit, load_type, etc.)
#   but still carry B/I row markers.
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

# Column name variants that carry B/I row-level routing markers.
# Ordered from most specific (TMS names) to most generic.
# The bot uses the first match found in the uploaded file.
MARKER_COLUMN_VARIANTS: list[str] = [
    "revenue_type_rev_type",   # standard TMS export
    "revenue_type",
    "rev_type",
    "division",                # common in freight management systems
    "div",
    "business_unit",
    "biz_unit",
    "bu",
    "load_type",
    "record_type",
    "shipment_type",
    "service_type",
    "dept",
    "department",
    "segment",
    "line_type",
    "category_type",
    # "type" intentionally omitted — too generic, causes false positives
    # with expense files that also use "type" for expense category
]

# Load/revenue indicator columns: at least one must be present alongside a
# marker column to confirm the file is a loads export (not some other file
# that happens to have a division or segment column).
LOAD_INDICATOR_COLUMNS: frozenset[str] = frozenset({
    "shipment_pro",
    "pro",
    "load_id",
    "shipment_id",
    "gross_revenue",
    "shipment_customer_total_rates",
    "customer_rate",
    "carrier_pay",
    "shipment_carrier_total_rates",
    "gross_profit",
    "shipment_gross_profit",
})

# ---------------------------------------------------------------------------
# Direct-replacement schema detection
#
# "brokerage_direct" — already-processed brokerage CSV
#   Required: gross_revenue AND carrier_pay (these are exclusively brokerage metrics)
#   Excluded: any B/I marker column (would be export instead)
#
# "ivan_direct" — already-processed Ivan Cartage CSV
#   Required: revenue (Ivan uses "revenue", not "gross_revenue")
#   Excluded: gross_revenue, carrier_pay (would indicate brokerage or export)
#             any B/I marker column (would be export instead)
# ---------------------------------------------------------------------------
BROKERAGE_DIRECT_REQUIRED: frozenset[str] = frozenset({"gross_revenue", "carrier_pay"})

IVAN_DIRECT_REQUIRED: frozenset[str] = frozenset({"revenue"})
IVAN_DIRECT_EXCLUDE: frozenset[str] = frozenset({"gross_revenue", "carrier_pay"})

# ---------------------------------------------------------------------------
# Amazon Relay schema detection
#
# "amazon_relay" — Amazon Relay DSP trip export
#   At least THRESHOLD of these normalized column names must be present.
#   Detected before brokerage_direct/ivan_direct to avoid false positives
#   (estimated_cost could partially match expense column maps).
# ---------------------------------------------------------------------------
AMAZON_RELAY_SIGNATURE_COLUMNS: frozenset[str] = frozenset({
    "driver_name",
    "trip_id",
    "estimated_cost",
    "load_execution_status",
})
AMAZON_RELAY_SIGNATURE_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------
class ParseResult(NamedTuple):
    schema_type: str          # "export" | "brokerage_direct" | "ivan_direct" | "expenses" | "unknown"
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

    # ── 3. Detect export schema (content-based, filename-independent) ────────
    #
    # Path A — TMS signature columns (original detection, unchanged)
    export_matches = sum(1 for col in EXPORT_SIGNATURE_COLUMNS if col in norm_set)
    is_export_by_tms = export_matches >= EXPORT_SIGNATURE_THRESHOLD

    # Path B — any known B/I marker column variant + at least one load indicator
    #   Supports: division, business_unit, load_type, record_type, etc.
    #   Requires a load indicator alongside it so "division" in an expense file
    #   doesn't get misclassified.
    detected_marker_col = next(
        (col for col in MARKER_COLUMN_VARIANTS if col in norm_set), None
    )
    has_load_indicator = bool(LOAD_INDICATOR_COLUMNS & norm_set)
    is_export_by_marker = detected_marker_col is not None and has_load_indicator

    if is_export_by_tms or is_export_by_marker:
        if is_export_by_tms:
            logger.info(
                f"[parser] Detected schema: export "
                f"(TMS signature — {export_matches} signature columns matched)"
            )
        else:
            logger.info(
                f"[parser] Detected schema: export "
                f"(marker column '{detected_marker_col}' + load indicator)"
            )
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

    # ── 4a. Detect Amazon Relay schema ────────────────────────────────────────
    amazon_matches = sum(1 for col in AMAZON_RELAY_SIGNATURE_COLUMNS if col in norm_set)
    if amazon_matches >= AMAZON_RELAY_SIGNATURE_THRESHOLD:
        logger.info(
            f"[parser] Detected schema: amazon_relay "
            f"({amazon_matches} signature columns matched)"
        )
        mapping_used = {nh: nh for nh in normalized_headers}
        norm_rows = [
            {_normalize_header(k): v for k, v in raw_row.items() if k}
            for raw_row in raw_rows
        ]
        return ParseResult(
            "amazon_relay", norm_rows, raw_headers, mapping_used,
            derived_fields, warnings, errors, len(norm_rows), 0
        )

    # ── 4b. Detect direct-replacement schemas (already-processed CSVs) ───────
    #   These are checked before expenses because a file with gross_revenue +
    #   carrier_pay columns would also partially match some expense mappings.

    # Brokerage direct: gross_revenue + carrier_pay present, no B/I marker
    if BROKERAGE_DIRECT_REQUIRED.issubset(norm_set) and detected_marker_col is None:
        logger.info(
            f"[parser] Detected schema: brokerage_direct "
            f"(gross_revenue + carrier_pay present, no marker column)"
        )
        mapping_used = {nh: nh for nh in normalized_headers}
        norm_rows = [
            {_normalize_header(k): v for k, v in raw_row.items() if k}
            for raw_row in raw_rows
        ]
        return ParseResult(
            "brokerage_direct", norm_rows, raw_headers, mapping_used,
            derived_fields, warnings, errors, len(norm_rows), 0
        )

    # Ivan direct: revenue present, no gross_revenue/carrier_pay, no B/I marker
    if (
        IVAN_DIRECT_REQUIRED.issubset(norm_set)
        and not IVAN_DIRECT_EXCLUDE.intersection(norm_set)
        and detected_marker_col is None
    ):
        logger.info(
            f"[parser] Detected schema: ivan_direct "
            f"(revenue present, no brokerage columns, no marker column)"
        )
        mapping_used = {nh: nh for nh in normalized_headers}
        norm_rows = [
            {_normalize_header(k): v for k, v in raw_row.items() if k}
            for raw_row in raw_rows
        ]
        return ParseResult(
            "ivan_direct", norm_rows, raw_headers, mapping_used,
            derived_fields, warnings, errors, len(norm_rows), 0
        )

    # ── 5. Apply expense column map ─────────────────────────────────────────
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

    # ── 6. Derive month from _raw_date if month not directly mapped ────────
    if "month" not in internal_fields and "_raw_date" in internal_fields:
        internal_fields.add("month")
        derived_fields.append("month (derived from date column)")
        logger.info("[parser]   Derived field: 'month' will be extracted from date column")

    # ── 7. Detect expenses schema from internal fields ─────────────────────
    expense_required = {"month", "category", "amount"}
    has_expenses = expense_required.issubset(internal_fields)

    if has_expenses:
        schema_type = "expenses"
        logger.info("[parser] Detected schema: expenses")
    else:
        missing_internal = expense_required - internal_fields
        schema_type = "unknown"
        _hdr_preview = ", ".join(raw_headers[:10])
        if len(raw_headers) > 10:
            _hdr_preview += f" … (+{len(raw_headers) - 10} more)"
        errors.append(
            f"Could not map required fields. "
            f"Internal fields resolved: {sorted(internal_fields or ['(none)'])}. "
            f"Still missing: {sorted(missing_internal)}. "
            f"Raw headers (first 10): {_hdr_preview}."
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

    # Truncate header list to avoid Discord 2000-char limit
    header_str = ", ".join(result.raw_headers)
    if len(header_str) > 300:
        header_str = header_str[:297] + "…"
    lines.append(f"Raw headers: `{header_str}`")

    if result.mapping_used:
        mapped = [f"`{k}` → `{v}`" for k, v in result.mapping_used.items() if not v.startswith("_")]
        if mapped:
            lines.append("Column mapping: " + ", ".join(mapped))

    if result.derived_fields:
        lines.append("Derived fields: " + ", ".join(result.derived_fields))

    lines.append(f"Rows accepted: **{result.row_count}** | Skipped: {result.skipped_count}")

    if result.warnings:
        lines.append("Warnings:")
        for w in result.warnings[:5]:
            lines.append(f"  ⚠ {w}")
        if len(result.warnings) > 5:
            lines.append(f"  … and {len(result.warnings) - 5} more warnings.")

    if result.errors:
        lines.append("Errors:")
        for e in result.errors[:3]:
            lines.append(f"  ✗ {e}")
        if len(result.errors) > 3:
            lines.append(f"  … and {len(result.errors) - 3} more errors.")

    return "\n".join(lines)
