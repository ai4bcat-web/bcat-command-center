import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Resolve project root relative to this file so outputs always land correctly
PROJECT_ROOT = Path(__file__).resolve().parent


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
        # Revenue type
        "revenue_type_rev_type": "rev_type",
        "revenue_type": "rev_type",
        "type": "rev_type",
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
    # Split by revenue type
    # -----------------------------------------------------------------------
    total_rows = len(df)
    rev_type_norm = df["rev_type"].astype(str).str.strip().str.upper()

    brokerage_mask = rev_type_norm == "B"
    ivan_mask = rev_type_norm == "I"
    other_mask = ~(brokerage_mask | ivan_mask)

    skipped = int(other_mask.sum())
    if skipped:
        other_types = df.loc[other_mask, "rev_type"].unique().tolist()
        msg = f"{skipped} rows had unrecognized revenue_type values: {other_types} — skipped"
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
        "warnings": warnings,
    }
