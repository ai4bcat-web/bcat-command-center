import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Resolve project root relative to this file so outputs always land correctly
PROJECT_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# B/I marker column detection
#
# These are the column names (after header normalization) that carry the
# row-level routing markers: 'B' = brokerage, 'I' = Ivan Cartage.
# Ordered from most specific (standard TMS names) to most generic.
# ---------------------------------------------------------------------------
MARKER_COLUMN_VARIANTS: list[str] = [
    "revenue_type_rev_type",   # standard TMS export column
    "revenue_type",
    "rev_type",
    "division",                # common in freight/TMS systems
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
    # "type" intentionally excluded — too generic, collides with expense files
]


def _detect_marker_column(df: pd.DataFrame) -> str | None:
    """
    Find the column in df that carries B/I row-level routing markers.

    Strategy:
      1. Try each name in MARKER_COLUMN_VARIANTS (first match wins).
         Verify the column actually contains at least one 'B' or 'I' value.
      2. If no named match, scan every column for one where ≥ 50% of values
         are 'B' or 'I' (handles completely non-standard column names).

    Returns the df column name (already normalized) or None.
    """
    total = len(df)
    if total == 0:
        return None

    # Pass 1 — known name variants
    for variant in MARKER_COLUMN_VARIANTS:
        if variant in df.columns:
            vals = df[variant].astype(str).str.strip().str.upper().unique()
            if set(vals) & {"B", "I"}:
                logger.info(f"  [marker] Detected by name: '{variant}'")
                return variant

    # Pass 2 — content scan (fallback for non-standard names)
    for col in df.columns:
        try:
            vals = df[col].astype(str).str.strip().str.upper()
            bi_count = int(vals.isin({"B", "I"}).sum())
            if bi_count / total >= 0.5:
                logger.info(
                    f"  [marker] Detected by content scan: '{col}' "
                    f"({bi_count}/{total} B/I values)"
                )
                return col
        except Exception:
            continue

    return None


def process_uploaded_csv(filepath, output_dir=None):
    """
    Parse a brokerage/loads export CSV and write:
      - brokerage_loads.csv   (revenue_type_rev_type == 'B')
      - ivan_cartage_loads.csv (revenue_type_rev_type == 'I')

    Args:
        filepath: path to the uploaded CSV file (str or Path)
        output_dir: directory to write output CSVs (defaults to project root)

    Returns:
        dict with keys: brokerage_rows, ivan_rows, skipped_rows, warnings
    """
    filepath = Path(filepath)
    output_dir = Path(output_dir) if output_dir else PROJECT_ROOT

    warnings = []

    logger.info(f"Ingesting export file: {filepath.name}")

    # -----------------------------------------------------------------------
    # Load and normalize columns
    # -----------------------------------------------------------------------
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding="latin-1")

    logger.info(f"Loaded {len(df)} rows from {filepath.name}")

    # Normalize: strip whitespace, lowercase, spaces→underscores
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # -----------------------------------------------------------------------
    # Flexible column mapping
    # Maps possible source column names → internal standard name
    # -----------------------------------------------------------------------
    COLUMN_MAP = {
        # Date
        "pick_stop_1_ready_or_deliver_date": "raw_date",
        "delivery_date": "raw_date",
        "ship_date": "raw_date",
        "date": "raw_date",
        # Revenue type / B-I marker (standard TMS names only here —
        # non-standard names are handled by _detect_marker_column below)
        "revenue_type_rev_type": "rev_type",
        "revenue_type": "rev_type",
        "rev_type": "rev_type",
        "division": "rev_type",
        "div": "rev_type",
        "business_unit": "rev_type",
        "biz_unit": "rev_type",
        "bu": "rev_type",
        "load_type": "rev_type",
        "record_type": "rev_type",
        "shipment_type": "rev_type",
        "service_type": "rev_type",
        "dept": "rev_type",
        "department": "rev_type",
        "segment": "rev_type",
        "line_type": "rev_type",
        # Load ID
        "shipment_pro": "load_id",
        "pro": "load_id",
        "load_id": "load_id",
        "shipment_id": "load_id",
        # Customer
        "customer_name": "customer",
        "customer": "customer",
        "bill_to": "customer",
        # Carrier
        "carrier_name": "carrier",
        "carrier": "carrier",
        # Revenue
        "shipment_customer_total_rates": "gross_revenue",
        "customer_rate": "gross_revenue",
        "gross_revenue": "gross_revenue",
        # Carrier pay
        "shipment_carrier_total_rates": "carrier_pay",
        "carrier_rate": "carrier_pay",
        "carrier_pay": "carrier_pay",
        # Gross profit
        "shipment_gross_profit": "gross_profit",
        "gross_profit": "gross_profit",
        # Miles
        "shipment_miles_truck": "miles",
        "miles": "miles",
        "truck_miles": "miles",
    }

    for src, dst in COLUMN_MAP.items():
        if src in df.columns and dst not in df.columns:
            df = df.rename(columns={src: dst})
            logger.info(f"  Column mapped: {src} → {dst}")

    # -----------------------------------------------------------------------
    # Marker column fallback: if rev_type still not present after the
    # COLUMN_MAP pass, scan columns for any that carry B/I values
    # -----------------------------------------------------------------------
    if "rev_type" not in df.columns:
        marker_col = _detect_marker_column(df)
        if marker_col:
            df = df.rename(columns={marker_col: "rev_type"})
            logger.info(f"  Marker column auto-detected and mapped: '{marker_col}' → 'rev_type'")
        else:
            raise ValueError(
                "Could not find a row-level B/I marker column.\n"
                f"Tried known variants: {MARKER_COLUMN_VARIANTS}\n"
                f"Also scanned all {len(df.columns)} columns for ≥50% B/I values — none found.\n"
                f"Available columns: {list(df.columns)}"
            )

    detected_marker_col = "rev_type"  # normalized name after mapping
    logger.info(f"  Marker column resolved to: 'rev_type' (B=brokerage, I=Ivan)")

    # -----------------------------------------------------------------------
    # Validate required fields
    # -----------------------------------------------------------------------
    required = ["raw_date", "rev_type", "load_id", "customer", "gross_revenue", "carrier_pay", "gross_profit"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns after mapping: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    # -----------------------------------------------------------------------
    # Parse date
    # -----------------------------------------------------------------------
    df["ship_date"] = pd.to_datetime(df["raw_date"], errors="coerce", format="mixed")
    bad_dates = df["ship_date"].isna().sum()
    if bad_dates:
        msg = f"{bad_dates} rows had unparseable dates and will have a null date"
        warnings.append(msg)
        logger.warning(msg)

    # -----------------------------------------------------------------------
    # Numeric parsing (strip $, commas)
    # -----------------------------------------------------------------------
    def clean_numeric(series):
        return pd.to_numeric(
            series.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.strip(),
            errors="coerce",
        ).fillna(0)

    df["gross_revenue"] = clean_numeric(df["gross_revenue"])
    df["carrier_pay"] = clean_numeric(df["carrier_pay"])
    df["gross_profit"] = clean_numeric(df["gross_profit"])

    if "miles" in df.columns:
        df["miles"] = clean_numeric(df["miles"])

    # -----------------------------------------------------------------------
    # Split by B/I marker
    # -----------------------------------------------------------------------
    total_rows = len(df)
    rev_type_norm = df["rev_type"].astype(str).str.strip().str.upper()

    brokerage_mask = rev_type_norm == "B"
    ivan_mask = rev_type_norm == "I"
    other_mask = ~(brokerage_mask | ivan_mask)

    b_count = int(brokerage_mask.sum())
    i_count = int(ivan_mask.sum())
    logger.info(
        f"  B/I split: {b_count} brokerage rows (B), "
        f"{i_count} Ivan rows (I), "
        f"{int(other_mask.sum())} other/skipped"
    )

    skipped = int(other_mask.sum())
    if skipped:
        other_types = df.loc[other_mask, "rev_type"].unique().tolist()
        msg = f"{skipped} rows had unrecognized marker values: {other_types} — skipped (expected 'B' or 'I')"
        warnings.append(msg)
        logger.warning(msg)

    # -----------------------------------------------------------------------
    # Build brokerage output
    # -----------------------------------------------------------------------
    brokerage = df[brokerage_mask].copy()
    brokerage_out = pd.DataFrame({
        "date": brokerage["ship_date"].dt.strftime("%Y-%m-%d"),
        "load_id": brokerage["load_id"],
        "customer": brokerage["customer"],
        "gross_revenue": brokerage["gross_revenue"],
        "carrier": brokerage["carrier"],
        "carrier_pay": brokerage["carrier_pay"],
        "gross_profit": brokerage["gross_profit"],
    })
    brokerage_out = brokerage_out[brokerage_out["gross_revenue"] > 0]

    brokerage_path = output_dir / "brokerage_loads.csv"
    brokerage_out.to_csv(brokerage_path, index=False)
    logger.info(f"Wrote {len(brokerage_out)} brokerage rows → {brokerage_path}")

    # -----------------------------------------------------------------------
    # Build Ivan Cartage output
    # -----------------------------------------------------------------------
    ivan = df[ivan_mask].copy()
    ivan_out = pd.DataFrame({
        "date": ivan["ship_date"].dt.strftime("%Y-%m-%d"),
        "load_id": ivan["load_id"],
        "customer": ivan["customer"],
        "revenue": ivan["gross_revenue"],
    })
    ivan_out = ivan_out[ivan_out["revenue"] > 0]

    ivan_path = output_dir / "ivan_cartage_loads.csv"
    ivan_out.to_csv(ivan_path, index=False)
    logger.info(f"Wrote {len(ivan_out)} Ivan Cartage rows → {ivan_path}")

    return {
        "brokerage_rows": len(brokerage_out),
        "ivan_rows": len(ivan_out),
        "skipped_rows": skipped,
        "total_input_rows": total_rows,
        "marker_column": detected_marker_col,
        "warnings": warnings,
    }
