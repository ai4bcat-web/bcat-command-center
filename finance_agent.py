import pandas as pd
import os
import json
import datetime
import random

# ─────────────────────────────────────────────────────────────────────────────
# Amazon Relay CSV — configuration constants
# ─────────────────────────────────────────────────────────────────────────────
# All field-mapping and filter decisions are centralised here so they can be
# updated in one place if Amazon changes their export format.

# Path to the Amazon Relay CSV export (relative to local_data_path).
# Upload / replace this file to refresh the dashboard with live data.
AMAZON_RELAY_CSV_PATH = "amazon_relay.csv"

# CSV header → normalised field name.
# Keys are lowercased + whitespace-stripped versions of the CSV column headers.
# ASSUMPTION: Amazon Relay exports these exact column names.  Update if they change.
AMAZON_RELAY_COLUMN_MAP = {
    "driver name":           "driver",
    "trip id":               "trip_id",
    "estimated cost":        "trip_revenue",
    "load execution status": "status",
}

# Date columns tried in order — first one found in the CSV is used for week grouping.
# Amazon Relay column headers normalize to lowercase + strip. The export typically
# has "Stop 1 Planned Arrival Date" (pickup date) as the most reliable trip date.
# Double-space variants exist in some exports ("Stop 1  Actual Arrival Date").
AMAZON_RELAY_DATE_FIELDS = [
    "stop 1 planned arrival date",    # standard Amazon Relay export — pickup date
    "stop 1  actual arrival date",    # double-space variant (some export versions)
    "stop 1 actual arrival date",     # single-space variant
    "stop 1  planned departure date", # departure from pickup (double-space)
    "stop 1 planned departure date",  # departure from pickup (single-space)
    "stop 2 planned arrival date",    # delivery date fallback
    "trip date",
    "execution date",
    "scheduled start",
    "scheduled start time",
    "actual completion time",
    "actual start time",
    "planned delivery date",
    "date",
]

# Statuses that qualify a trip for inclusion in the report.
# Set to None to include all trips that have a rate, regardless of status.
AMAZON_RELAY_ALLOWED_STATUSES = None

# No minimum revenue threshold — all trips with a valid driver name are included.
AMAZON_RELAY_MIN_REVENUE = 0.0
try:
    import agent_registry as _registry
    _registry.register("FinanceAgent", "Financial data ingestion and metrics (Ivan Cartage, brokerage, Amazon)")
except Exception:
    _registry = None

def load_ivan_loads(path="ivan_cartage_loads.csv"):
    if not os.path.exists(path):
        return pd.DataFrame(columns=["month", "revenue", "miles"])

    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rename_map = {
        "date": "date",
        "load_date": "date",
        "delivery_date": "date",
        "invoice_date": "date",
        "amount": "revenue",
        "revenue": "revenue",
        "gross_revenue": "revenue",
        "total_revenue": "revenue",
        "linehaul": "revenue",
        "miles": "miles",
        "loaded_miles": "miles",
        "miles_driven": "miles",
        "distance": "miles",
        "trip_miles": "miles",
    }

    df = df.rename(columns=rename_map)

    if "revenue" not in df.columns:
        df["revenue"] = 0.0
    else:
        df["revenue"] = (
            df["revenue"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.strip()
        )
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0)

    if "miles" not in df.columns:
        df["miles"] = 0.0
    else:
        df["miles"] = pd.to_numeric(df["miles"], errors="coerce").fillna(0.0)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["month"] = df["date"].dt.to_period("M").astype(str)
    elif "month" not in df.columns:
        df["month"] = ""

    return df


def load_ivan_expenses(path="ivan_expenses.csv"):
    if not os.path.exists(path):
        fallback = "ivan_cartage_expenses.csv"
        if not os.path.exists(fallback):
            return pd.DataFrame(columns=["month", "category", "amount"])
        path = fallback

    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rename_map = {
        "date": "date",
        "expense_date": "date",
        "transaction_date": "date",
        "month": "month",
        "category": "category",
        "expense_category": "category",
        "type": "category",
        "amount": "amount",
        "expense": "amount",
        "total": "amount",
    }

    df = df.rename(columns=rename_map)

    if "amount" not in df.columns:
        df["amount"] = 0.0
    else:
        df["amount"] = (
            df["amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.strip()
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    if "category" not in df.columns:
        df["category"] = "Unknown"

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["month"] = df["date"].dt.to_period("M").astype(str)
    elif "month" not in df.columns:
        df["month"] = ""

    return df


def get_ivan_expense_metrics():
    if _registry:
        _registry.set_status("FinanceAgent", "busy", "get_ivan_expense_metrics")
    try:
        return _get_ivan_expense_metrics_impl()
    finally:
        if _registry:
            _registry.set_status("FinanceAgent", "idle")


def _get_ivan_expense_metrics_impl():
    loads = load_ivan_loads("ivan_cartage_loads.csv")
    expenses = load_ivan_expenses("ivan_expenses.csv")

    # Clean amount column as numeric text
    expenses["amount"] = (
        expenses["amount"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip()
    )
    expenses["amount"] = pd.to_numeric(expenses["amount"], errors="coerce").fillna(0.0)

    # Split out Miles Driven so it is NOT counted as expense
    miles_rows = expenses[expenses["category"].astype(str).str.strip().str.lower() == "miles driven"].copy()
    true_expense_rows = expenses[expenses["category"].astype(str).str.strip().str.lower() != "miles driven"].copy()

    total_revenue = float(loads["revenue"].sum()) if not loads.empty else 0.0
    total_expenses = float(true_expense_rows["amount"].sum()) if not true_expense_rows.empty else 0.0
    total_miles = float(miles_rows["amount"].sum()) if not miles_rows.empty else 0.0

    true_profit = total_revenue - total_expenses

    revenue_per_mile = total_revenue / total_miles if total_miles > 0 else 0.0
    cost_per_mile = total_expenses / total_miles if total_miles > 0 else 0.0
    profit_per_mile = true_profit / total_miles if total_miles > 0 else 0.0

    expenses_by_category = {}
    if not true_expense_rows.empty:
        expenses_by_category = (
            true_expense_rows.groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )

    monthly_true_profit = []
    monthly_revenue = pd.DataFrame(columns=["month", "revenue", "shipment_volume"])
    monthly_expenses = pd.DataFrame(columns=["month", "expenses"])
    monthly_miles = pd.DataFrame(columns=["month", "miles"])

    if not loads.empty and "month" in loads.columns:
        monthly_revenue = (
            loads.groupby("month", as_index=False)
            .agg(
                revenue=("revenue", "sum"),
                shipment_volume=("revenue", "count")
            )
        )

    if not true_expense_rows.empty and "month" in true_expense_rows.columns:
        monthly_expenses = (
            true_expense_rows.groupby("month", as_index=False)["amount"]
            .sum()
            .rename(columns={"amount": "expenses"})
        )

    if not miles_rows.empty and "month" in miles_rows.columns:
        monthly_miles = (
            miles_rows.groupby("month", as_index=False)["amount"]
            .sum()
            .rename(columns={"amount": "miles"})
        )

    merged = pd.merge(monthly_revenue, monthly_expenses, on="month", how="outer")
    merged = pd.merge(merged, monthly_miles, on="month", how="outer").fillna(0)

    if not merged.empty:
        merged["true_profit"] = merged["revenue"] - merged["expenses"]
        merged["revenue_per_mile"] = merged.apply(
            lambda row: row["revenue"] / row["miles"] if row["miles"] > 0 else 0.0,
            axis=1
        )
        merged["cost_per_mile"] = merged.apply(
            lambda row: row["expenses"] / row["miles"] if row["miles"] > 0 else 0.0,
            axis=1
        )
        merged["profit_per_mile"] = merged.apply(
            lambda row: row["true_profit"] / row["miles"] if row["miles"] > 0 else 0.0,
            axis=1
        )
        merged = merged.sort_values("month")
        monthly_true_profit = merged.to_dict(orient="records")

    ivan_expenses_category_monthly = []
    if not true_expense_rows.empty and "month" in true_expense_rows.columns and "category" in true_expense_rows.columns:
        ivan_expenses_category_monthly = (
            true_expense_rows.groupby(["month", "category"], as_index=False)["amount"]
            .sum()
            .sort_values(["month", "amount"], ascending=[False, False])
            .to_dict(orient="records")
        )

    return {
        "ivan_cartage_revenue": round(total_revenue, 2),
        "ivan_expenses": round(total_expenses, 2),
        "ivan_true_profit": round(true_profit, 2),
        "ivan_total_miles": round(total_miles, 2),
        "ivan_revenue_per_mile": round(revenue_per_mile, 2),
        "ivan_cost_per_mile": round(cost_per_mile, 2),
        "ivan_profit_per_mile": round(profit_per_mile, 2),
        "ivan_expenses_by_category": expenses_by_category,
        "ivan_monthly_true_profit": monthly_true_profit,
        "ivan_expenses_category_monthly": ivan_expenses_category_monthly,
        "ivan_top_customers_by_month": []
    }

class FinanceAgent:
    def __init__(self, local_data_path="."):
        self.local_data_path = local_data_path
        self.brokerage_data = None
        self.ivan_cartage_data = None
        self.amazon_data = None

    def ingest_data(self):
        if _registry:
            _registry.set_status("FinanceAgent", "busy", "ingest_data")
        try:
            self._ingest_data_impl()
        finally:
            if _registry:
                _registry.set_status("FinanceAgent", "idle")

    def _ingest_data_impl(self):
        self.brokerage_data = pd.read_csv(f"{self.local_data_path}/brokerage_loads.csv")
        self.ivan_cartage_data = pd.read_csv(f"{self.local_data_path}/ivan_cartage_loads.csv")
        self.amazon_data = pd.read_csv(f"{self.local_data_path}/amazon_loads.csv")

        self.brokerage_data["date"] = pd.to_datetime(self.brokerage_data["date"], errors="coerce")
        self.ivan_cartage_data["date"] = pd.to_datetime(self.ivan_cartage_data["date"], errors="coerce")

        self.brokerage_data["gross_revenue"] = pd.to_numeric(
            self.brokerage_data["gross_revenue"], errors="coerce"
        ).fillna(0)

        self.brokerage_data["carrier_pay"] = pd.to_numeric(
            self.brokerage_data["carrier_pay"], errors="coerce"
        ).fillna(0)

        if "gross_profit" in self.brokerage_data.columns:
            self.brokerage_data["gross_profit"] = pd.to_numeric(
                self.brokerage_data["gross_profit"], errors="coerce"
            ).fillna(0)
        else:
            self.brokerage_data["gross_profit"] = (
                self.brokerage_data["gross_revenue"] - self.brokerage_data["carrier_pay"]
            )

        self.ivan_cartage_data["revenue"] = pd.to_numeric(
            self.ivan_cartage_data["revenue"], errors="coerce"
        ).fillna(0)

        if "bcat_revenue" in self.amazon_data.columns:
            self.amazon_data["bcat_revenue"] = pd.to_numeric(
                self.amazon_data["bcat_revenue"], errors="coerce"
            ).fillna(0)
        else:
            self.amazon_data["gross_load_revenue"] = pd.to_numeric(
                self.amazon_data["gross_load_revenue"], errors="coerce"
            ).fillna(0)
            self.amazon_data["deductions"] = pd.to_numeric(
                self.amazon_data["deductions"], errors="coerce"
            ).fillna(0)
            self.amazon_data["company_percentage"] = pd.to_numeric(
                self.amazon_data["company_percentage"], errors="coerce"
            ).fillna(0)
            self.amazon_data["bcat_revenue"] = (
                (self.amazon_data["gross_load_revenue"] - self.amazon_data["deductions"])
                * self.amazon_data["company_percentage"]
            )
    def calculate_brokerage_metrics(self):
        gross_revenue = float(self.brokerage_data["gross_revenue"].sum())
        carrier_pay = float(self.brokerage_data["carrier_pay"].sum())
        gross_profit = float(self.brokerage_data["gross_profit"].sum())

        margin_percentage = 0
        if gross_revenue > 0:
            margin_percentage = (gross_profit / gross_revenue) * 100

        return {
            "gross_revenue": gross_revenue,
            "carrier_pay": carrier_pay,
            "gross_profit": gross_profit,
            "margin_percentage": round(margin_percentage, 2),
        }

    def calculate_ivan_cartage_revenue(self):
        return float(self.ivan_cartage_data["revenue"].sum())

    def calculate_amazon_revenue(self):
        return float(self.amazon_data["bcat_revenue"].sum())

    def get_monthly_brokerage_summary(self):
        df = self.brokerage_data.copy()
        df["month"] = df["date"].dt.to_period("M").astype(str)

        monthly = (
            df.groupby("month", as_index=False)
            .agg(
                revenue=("gross_revenue", "sum"),
                carrier_pay=("carrier_pay", "sum"),
                gross_profit=("gross_profit", "sum"),
                shipment_volume=("gross_revenue", "count")
            )
        )

        monthly["margin_percentage"] = monthly.apply(
            lambda row: (row["gross_profit"] / row["revenue"] * 100) if row["revenue"] > 0 else 0.0,
            axis=1
        )

        return monthly.sort_values("month").to_dict(orient="records")

    def get_brokerage_top_customers_by_month(self):
        df = self.brokerage_data.copy()
        df["month"] = df["date"].dt.to_period("M").astype(str)

        customer_col = "customer"
        if customer_col not in df.columns:
            return []

        grouped = (
            df.groupby(["month", customer_col], as_index=False)
            .agg(
                revenue=("gross_revenue", "sum"),
                carrier_pay=("carrier_pay", "sum"),
                gross_profit=("gross_profit", "sum"),
                shipment_volume=("gross_revenue", "count")
            )
        )

        grouped["profit_percentage"] = grouped.apply(
            lambda row: (row["gross_profit"] / row["revenue"] * 100) if row["revenue"] > 0 else 0.0,
            axis=1
        )

        grouped = grouped.sort_values(["month", "gross_profit"], ascending=[True, False])
        grouped["rank"] = grouped.groupby("month")["gross_profit"].rank(method="first", ascending=False)

        grouped = grouped.rename(columns={"customer": "customer"})
        grouped = grouped[grouped["rank"] <= 10]

        grouped["rank"] = grouped["rank"].astype(int)
        return grouped.to_dict(orient="records")

    def get_ivan_top_customers_by_month(self):
        df = self.ivan_cartage_data.copy()
        df["month"] = df["date"].dt.to_period("M").astype(str)

        customer_col = "customer"
        if customer_col not in df.columns:
            return []

        grouped = (
            df.groupby(["month", customer_col], as_index=False)
            .agg(
                revenue=("revenue", "sum"),
                volume=("revenue", "count")
            )
        )

        grouped = grouped.sort_values(["month", "revenue"], ascending=[True, False])
        grouped["rank"] = grouped.groupby("month")["revenue"].rank(method="first", ascending=False)
        grouped = grouped[grouped["rank"] <= 10]

        grouped["rank"] = grouped["rank"].astype(int)
        return grouped.to_dict(orient="records")

    def get_amazon_metrics(self):
        """
        Returns Amazon DSP trip data for the weekly performance view.

        DATA SOURCE (in priority order):
        1. amazon_relay.csv  — Amazon Relay CSV export (trip-level, real data)
           Upload/replace this file to update the dashboard.
        2. Mock data          — used as fallback when amazon_relay.csv is absent.

        The returned 'data_source' key tells the frontend which source was used
        ('relay_csv' or 'mock') so it can display the appropriate notice.

        Filtering: parse_amazon_relay_csv() applies is_qualifying_trip() to
        each row before returning it, so trips here are already filtered:
        - Estimated Cost > AMAZON_RELAY_MIN_REVENUE ($100)
        - Status in AMAZON_RELAY_ALLOWED_STATUSES (Completed variants)
        - Driver name not blank

        TOTALS NOTE: All aggregate values are computed only from qualifying
        trips (the > $100 filter is applied before this method returns data).
        """
        relay_path = os.path.join(self.local_data_path, AMAZON_RELAY_CSV_PATH)
        if os.path.exists(relay_path):
            trips       = parse_amazon_relay_csv(relay_path)
            data_source = "relay_csv"
        else:
            # Fallback to mock until relay CSV is uploaded
            trips       = _get_amazon_mock_trips()
            data_source = "mock"

        total_revenue = round(sum(float(t.get("trip_revenue",       t.get("gross_load_revenue", 0))) for t in trips), 2)
        total_ded     = round(sum(float(t.get("deductions",         0)) for t in trips), 2)
        total_bcat    = round(sum(float(t.get("bcat_revenue",       0)) for t in trips), 2)
        driver_set    = {t["driver"] for t in trips if t.get("driver")}

        return {
            "trips":               trips,
            "total_gross_revenue": total_revenue,
            "total_deductions":    total_ded,
            "total_bcat_revenue":  total_bcat,
            "driver_count":        len(driver_set),
            "qualifying_count":    len(trips),
            "data_source":         data_source,
            "min_revenue_filter":  AMAZON_RELAY_MIN_REVENUE,
            "allowed_statuses":    list(AMAZON_RELAY_ALLOWED_STATUSES) if AMAZON_RELAY_ALLOWED_STATUSES else None,
        }

    def _get_amazon_csv_trips(self):
        """
        Loads trip records from amazon_loads.csv and normalises them to the
        same shape as mock trips so the frontend receives a consistent schema.

        ──────────────────────────────────────────────────────────────────
        CURRENT LIMITATION: amazon_loads.csv has one row per driver per
        week, not one row per trip.  Each CSV row is surfaced as a single
        record with 'week' mapped to 'trip_date'.

        When the CSV gains real trip-level rows, ensure the file has a
        'trip_date' (or 'week') column plus the numeric columns below —
        no further code changes will be required.
        ──────────────────────────────────────────────────────────────────
        """
        if self.amazon_data is None or self.amazon_data.empty:
            return []

        df = self.amazon_data.copy()

        # Map 'week' → 'trip_date'  (update here if CSV gains a native trip_date)
        if "week" in df.columns and "trip_date" not in df.columns:
            df = df.rename(columns={"week": "trip_date"})

        df["trip_id"] = [f"CSV-{i:04d}" for i in range(len(df))]
        df["route"]   = ""
        df["stops"]   = None

        return df.to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# Amazon mock-data generator  (module-level helper, not a FinanceAgent method)
# ─────────────────────────────────────────────────────────────────────────────

def _get_amazon_mock_trips():
    """
    MOCK DATA — used while trip-level CSV data is not yet available.

    ──────────────────────────────────────────────────────────────────────────
    REPLACE THIS FUNCTION (or swap to self._get_amazon_csv_trips()) when
    amazon_loads.csv provides one row per trip.

    DATE FIELD: 'trip_date' (ISO string YYYY-MM-DD) is the primary field
    used to assign each trip to a Sunday–Saturday week bucket.
    To change the date field used for week grouping, update:
      • AMAZON_TRIP_DATE_FIELD constant in static/dashboard.js  (frontend)
      • the 'trip_date' key written in each dict below           (backend)

    TIMEZONE ASSUMPTION: Dates are plain ISO date strings with no timezone
    component.  The frontend treats them as local dates in the user's
    browser timezone.  Expected: US/Central (America/Chicago).
    ──────────────────────────────────────────────────────────────────────────
    """
    rng = random.Random(42)  # fixed seed → deterministic output across requests

    drivers = [
        {"name": "John Smith",    "type": "company",        "pct": 0.30},
        {"name": "Mike Davis",    "type": "owner_operator", "pct": 0.10},
        {"name": "Sarah Johnson", "type": "company",        "pct": 0.30},
        {"name": "Tom Wilson",    "type": "owner_operator", "pct": 0.12},
        {"name": "Lisa Chen",     "type": "company",        "pct": 0.28},
    ]

    routes = [
        "SEA-PDX", "SEA-SFO", "SEA-OAK", "PDX-SFO",
        "SEA-LAX", "OAK-LAX", "SFO-LAX", "SEA-SMF",
        "PDX-RNO", "SEA-BOI",
    ]

    # Sunday start dates for each week to include
    week_sundays = [
        datetime.date(2026, 2, 22),
        datetime.date(2026, 3,  1),
        datetime.date(2026, 3,  8),
        datetime.date(2026, 3, 15),
        datetime.date(2026, 3, 22),  # current week (partial — only Mon/Tue so far)
    ]

    trips = []
    counter = 1

    for week_start in week_sundays:
        today = datetime.date(2026, 3, 24)
        work_days = [
            week_start + datetime.timedelta(days=d)
            for d in range(7)
            if (week_start + datetime.timedelta(days=d)).weekday() < 5
            and (week_start + datetime.timedelta(days=d)) <= today
        ]

        if not work_days:
            continue

        for driver in drivers:
            n = rng.randint(3, 7)
            trip_days = sorted(rng.choices(work_days, k=min(n, len(work_days) * 2))[:n])

            for day in trip_days:
                gross = round(rng.uniform(850, 2100), 2)
                ded   = round(gross * rng.uniform(0.07, 0.13), 2)
                bcat  = round((gross - ded) * driver["pct"], 2)

                trips.append({
                    "trip_id":            f"AM-{counter:04d}",
                    "trip_date":          day.isoformat(),   # PRIMARY date field — see docstring
                    "driver":             driver["name"],
                    "driver_type":        driver["type"],
                    "gross_load_revenue": gross,
                    "deductions":         ded,
                    "company_percentage": driver["pct"],
                    "bcat_revenue":       bcat,
                    "route":              rng.choice(routes),
                    "stops":              rng.randint(1, 8),
                })
                counter += 1

    return trips


# ─────────────────────────────────────────────────────────────────────────────
# Amazon Relay CSV import layer
# ─────────────────────────────────────────────────────────────────────────────

def parse_amazon_relay_csv(path=None):
    """
    CSV import layer for Amazon Relay exports.
    Returns a list of normalised, qualifying trip dicts.

    Decisions made here:
    - Column names are matched case-insensitively with whitespace stripped.
    - Rows with missing/blank driver names are silently skipped.
    - Rows with non-numeric Estimated Cost are skipped (coerced to 0 → below threshold).
    - Duplicate trip IDs are kept (no dedup); each row becomes one trip record.
    - The first matching date column from AMAZON_RELAY_DATE_FIELDS is used.
      If no date column is found, trip_date is set to None (trip is still
      included if other qualifying rules pass, but won't appear in any week tab).
    """
    if path is None:
        path = AMAZON_RELAY_CSV_PATH
    if not os.path.exists(path):
        return []

    df = pd.read_csv(path)
    # Normalise column names: lowercase + strip surrounding whitespace
    df.columns = [c.strip().lower() for c in df.columns]

    # Apply field mapping
    rename = {src: dst for src, dst in AMAZON_RELAY_COLUMN_MAP.items() if src in df.columns}
    df = df.rename(columns=rename)

    # Detect date column
    trip_date_col = next((c for c in AMAZON_RELAY_DATE_FIELDS if c in df.columns), None)
    if trip_date_col:
        # Normalise to YYYY-MM-DD string; invalid dates become NaT → empty string
        df["trip_date"] = (
            pd.to_datetime(df[trip_date_col], errors="coerce")
            .dt.strftime("%Y-%m-%d")
        )
        # NaT → empty string
        df["trip_date"] = df["trip_date"].fillna("")
    else:
        df["trip_date"] = ""

    # Parse revenue — strip $ and commas before conversion
    if "trip_revenue" in df.columns:
        df["trip_revenue"] = (
            df["trip_revenue"]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df["trip_revenue"] = pd.to_numeric(df["trip_revenue"], errors="coerce").fillna(0.0)
    else:
        df["trip_revenue"] = 0.0

    # Ensure required fields exist with safe defaults
    for col, default in [("driver", ""), ("trip_id", ""), ("status", "")]:
        if col not in df.columns:
            df[col] = default

    trips = []
    for _, row in df.iterrows():
        trip = map_relay_row_to_trip(row)
        if is_qualifying_trip(trip):
            trips.append(trip)

    return trips


def _safe_str(value):
    """Convert a value to a clean string; treats None, NaN, 'nan' as empty."""
    if value is None:
        return ""
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return ""
    except Exception:
        pass
    s = str(value).strip()
    return "" if s.lower() == "nan" else s


def map_relay_row_to_trip(row):
    """
    Field mapping layer: converts a raw (normalised) CSV row to a trip dict.

    All source → destination field mappings live here.  To add a new field
    from the Amazon Relay export, add it to AMAZON_RELAY_COLUMN_MAP and handle
    it here.

    ASSUMPTIONS:
    - trip_revenue (Estimated Cost) is treated as the full BCAT revenue for
      the trip.  Amazon Relay doesn't expose a separate deduction column.
    - All relay drivers are treated as 'company' type.  Update if Amazon
      adds owner-operator info to the export.
    """
    driver       = _safe_str(row.get("driver",      ""))
    trip_id      = _safe_str(row.get("trip_id",     ""))
    trip_date    = _safe_str(row.get("trip_date",   ""))
    status       = _safe_str(row.get("status",      ""))
    trip_revenue = float(row.get("trip_revenue", 0) or 0)

    return {
        "driver":             driver or None,    # None → fails is_qualifying_trip
        "trip_id":            trip_id or f"RELAY-unknown",
        "trip_date":          trip_date or None,
        "trip_revenue":       trip_revenue,
        # Legacy field names kept for frontend compatibility
        "gross_load_revenue": trip_revenue,
        "deductions":         0.0,               # not available in relay export
        "bcat_revenue":       trip_revenue,       # ASSUMPTION: relay pay = BCAT revenue
        "status":             status,
        "driver_type":        "company",          # ASSUMPTION: relay = company drivers
        "route":              "",
        "stops":              None,
    }


def is_qualifying_trip(trip):
    """
    Filtering layer: returns True if trip should be included in the report.

    Rules applied (in order):
    1. driver must be non-empty
    2. trip_revenue must be a number and > AMAZON_RELAY_MIN_REVENUE
    3. status must be in AMAZON_RELAY_ALLOWED_STATUSES (skip check if set to None)

    To change filter behaviour:
    - Revenue threshold → change AMAZON_RELAY_MIN_REVENUE
    - Status whitelist  → change AMAZON_RELAY_ALLOWED_STATUSES (None = no filter)
    - Date requirement  → add:  if not trip.get("trip_date"): return False
    """
    # Rule 1: driver required
    if not trip.get("driver"):
        return False

    # Rule 2: revenue above threshold
    try:
        revenue = float(trip.get("trip_revenue", 0) or 0)
    except (ValueError, TypeError):
        return False
    if revenue <= AMAZON_RELAY_MIN_REVENUE:
        return False

    # Rule 3: status filter (skipped if AMAZON_RELAY_ALLOWED_STATUSES is None)
    if AMAZON_RELAY_ALLOWED_STATUSES is not None:
        status = str(trip.get("status", "") or "").strip()
        if status not in AMAZON_RELAY_ALLOWED_STATUSES:
            return False

    return True
