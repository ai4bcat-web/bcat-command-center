import pandas as pd
import os
import json
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
