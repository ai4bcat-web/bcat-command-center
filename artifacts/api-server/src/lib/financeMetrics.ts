/**
 * financeMetrics.ts
 * TypeScript port of finance_agent.py business logic.
 * Reads CSV files and computes all BCAT financial metrics.
 *
 * CSV file locations (relative to CWD / process.cwd()):
 *   brokerage_loads.csv      — columns: date, load_id, customer, gross_revenue, carrier, carrier_pay, gross_profit
 *   ivan_cartage_loads.csv   — columns: date, load_id, customer, revenue
 *   ivan_expenses.csv        — columns: month, category, amount
 *                              NOTE: category "Miles Driven" = miles data, NOT an expense
 */

import path from "path";
import { loadCsv, toFloat, toMonthKey, CsvRow } from "./csvParser";

// ── Data directory ────────────────────────────────────────────────────────────
// Set CSV_DATA_DIR env var in Replit Secrets to the folder containing your CSVs.
// Defaults to process.cwd() (the directory the server is started from).
// Example: CSV_DATA_DIR=/home/user/bcat-command-center
function csvPath(name: string): string {
  const dir = process.env.CSV_DATA_DIR ?? process.cwd();
  return path.join(dir, name);
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BrokerageMetrics {
  gross_revenue: number;
  carrier_pay: number;
  gross_profit: number;
  brokerage_margin: number;
  monthly_brokerage_summary: MonthlyBrokerageSummary[];
  brokerage_top_customers_by_month: BrokerageCustomerRow[];
}

export interface MonthlyBrokerageSummary {
  month: string;
  revenue: number;
  carrier_pay: number;
  gross_profit: number;
  shipment_volume: number;
  margin_percentage: number;
}

export interface BrokerageCustomerRow {
  month: string;
  customer: string;
  revenue: number;
  carrier_pay: number;
  gross_profit: number;
  shipment_volume: number;
  profit_percentage: number;
  rank: number;
}

export interface IvanMetrics {
  ivan_cartage_revenue: number;
  ivan_expenses: number;
  ivan_true_profit: number;
  ivan_total_miles: number;
  ivan_revenue_per_mile: number;
  ivan_cost_per_mile: number;
  ivan_profit_per_mile: number;
  ivan_expenses_by_category: Record<string, number>;
  ivan_monthly_true_profit: IvanMonthRow[];
  ivan_expenses_category_monthly: IvanExpenseCategoryRow[];
  ivan_top_customers_by_month: IvanCustomerRow[];
}

export interface IvanMonthRow {
  month: string;
  revenue: number;
  expenses: number;
  miles: number;
  true_profit: number;
  shipment_volume: number;
  revenue_per_mile: number;
  cost_per_mile: number;
  profit_per_mile: number;
}

export interface IvanExpenseCategoryRow {
  month: string;
  category: string;
  amount: number;
}

export interface IvanCustomerRow {
  month: string;
  customer: string;
  revenue: number;
  volume: number;
  rank: number;
}

export interface DashboardData {
  brokerage: BrokerageMetrics;
  ivan: IvanMetrics;
  total_company_revenue: number;
  report_start_date: string;
  report_end_date: string;
}

// ── Brokerage ─────────────────────────────────────────────────────────────────

function normalizeBrokerageRow(row: CsvRow) {
  const grossRevenue = toFloat(row.gross_revenue);
  const carrierPay = toFloat(row.carrier_pay);
  const grossProfit =
    row.gross_profit != null && row.gross_profit !== ""
      ? toFloat(row.gross_profit)
      : grossRevenue - carrierPay;
  const month = toMonthKey(row.date);
  return {
    date: row.date ?? "",
    month,
    customer: (row.customer ?? "Unknown").trim(),
    grossRevenue,
    carrierPay,
    grossProfit,
  };
}

export function getBrokerageMetrics(): BrokerageMetrics {
  const rows = loadCsv(csvPath("brokerage_loads.csv")).map(
    normalizeBrokerageRow
  );

  const gross_revenue = rows.reduce((s, r) => s + r.grossRevenue, 0);
  const carrier_pay = rows.reduce((s, r) => s + r.carrierPay, 0);
  const gross_profit = rows.reduce((s, r) => s + r.grossProfit, 0);
  const brokerage_margin =
    gross_revenue > 0 ? (gross_profit / gross_revenue) * 100 : 0;

  // Monthly summary
  const monthMap = new Map<
    string,
    {
      revenue: number;
      carrier_pay: number;
      gross_profit: number;
      shipment_volume: number;
    }
  >();
  for (const r of rows) {
    const m = r.month;
    if (!m) continue;
    const entry = monthMap.get(m) ?? {
      revenue: 0,
      carrier_pay: 0,
      gross_profit: 0,
      shipment_volume: 0,
    };
    entry.revenue += r.grossRevenue;
    entry.carrier_pay += r.carrierPay;
    entry.gross_profit += r.grossProfit;
    entry.shipment_volume += 1;
    monthMap.set(m, entry);
  }
  const monthly_brokerage_summary: MonthlyBrokerageSummary[] = Array.from(
    monthMap.entries()
  )
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, d]) => ({
      month,
      revenue: round2(d.revenue),
      carrier_pay: round2(d.carrier_pay),
      gross_profit: round2(d.gross_profit),
      shipment_volume: d.shipment_volume,
      margin_percentage: round2(
        d.revenue > 0 ? (d.gross_profit / d.revenue) * 100 : 0
      ),
    }));

  // Top customers by month
  type CustKey = string;
  const custMap = new Map<
    CustKey,
    {
      month: string;
      customer: string;
      revenue: number;
      carrier_pay: number;
      gross_profit: number;
      shipment_volume: number;
    }
  >();
  for (const r of rows) {
    if (!r.month) continue;
    const key = `${r.month}|||${r.customer}`;
    const entry = custMap.get(key) ?? {
      month: r.month,
      customer: r.customer,
      revenue: 0,
      carrier_pay: 0,
      gross_profit: 0,
      shipment_volume: 0,
    };
    entry.revenue += r.grossRevenue;
    entry.carrier_pay += r.carrierPay;
    entry.gross_profit += r.grossProfit;
    entry.shipment_volume += 1;
    custMap.set(key, entry);
  }

  // Group by month, sort by gross_profit desc, take top 10
  const byMonth = new Map<string, typeof custMap extends Map<any, infer V> ? V[] : never[]>();
  for (const v of custMap.values()) {
    const arr = byMonth.get(v.month) ?? [];
    arr.push(v);
    byMonth.set(v.month, arr);
  }
  const brokerage_top_customers_by_month: BrokerageCustomerRow[] = [];
  for (const [, customers] of Array.from(byMonth.entries()).sort(([a], [b]) =>
    a.localeCompare(b)
  )) {
    customers
      .sort((a, b) => b.gross_profit - a.gross_profit)
      .slice(0, 10)
      .forEach((c, idx) => {
        brokerage_top_customers_by_month.push({
          month: c.month,
          customer: c.customer,
          revenue: round2(c.revenue),
          carrier_pay: round2(c.carrier_pay),
          gross_profit: round2(c.gross_profit),
          shipment_volume: c.shipment_volume,
          profit_percentage: round2(
            c.revenue > 0 ? (c.gross_profit / c.revenue) * 100 : 0
          ),
          rank: idx + 1,
        });
      });
  }

  return {
    gross_revenue: round2(gross_revenue),
    carrier_pay: round2(carrier_pay),
    gross_profit: round2(gross_profit),
    brokerage_margin: round2(brokerage_margin),
    monthly_brokerage_summary,
    brokerage_top_customers_by_month,
  };
}

// ── Ivan Cartage ──────────────────────────────────────────────────────────────

function normalizeIvanLoadsRow(row: CsvRow) {
  // Support flexible column names (mirrors rename_map in finance_agent.py)
  const revenueRaw =
    row.revenue ??
    row.amount ??
    row.gross_revenue ??
    row.total_revenue ??
    row.linehaul ??
    "0";
  const milesRaw =
    row.miles ??
    row.loaded_miles ??
    row.miles_driven ??
    row.distance ??
    row.trip_miles ??
    "0";
  const dateRaw =
    row.date ??
    row.load_date ??
    row.delivery_date ??
    row.invoice_date ??
    "";
  return {
    month: toMonthKey(dateRaw),
    customer: (row.customer ?? "Unknown").trim(),
    revenue: toFloat(revenueRaw),
    miles: toFloat(milesRaw),
  };
}

function normalizeIvanExpensesRow(row: CsvRow) {
  const dateRaw =
    row.date ??
    row.expense_date ??
    row.transaction_date ??
    "";
  const monthRaw = row.month ?? toMonthKey(dateRaw);
  const categoryRaw =
    row.category ?? row.expense_category ?? row.type ?? "Unknown";
  const amountRaw = row.amount ?? row.expense ?? row.total ?? "0";
  return {
    month: monthRaw.trim(),
    category: categoryRaw.trim(),
    amount: toFloat(amountRaw),
  };
}

export function getIvanMetrics(): IvanMetrics {
  const loads = loadCsv(csvPath("ivan_cartage_loads.csv")).map(
    normalizeIvanLoadsRow
  );

  // Try ivan_expenses.csv, fall back to ivan_cartage_expenses.csv
  let expenseRows = loadCsv(csvPath("ivan_expenses.csv"));
  if (expenseRows.length === 0) {
    expenseRows = loadCsv(csvPath("ivan_cartage_expenses.csv"));
  }
  const expenses = expenseRows.map(normalizeIvanExpensesRow);

  // IMPORTANT: "Miles Driven" category = miles, NOT an expense
  const milesRows = expenses.filter(
    (e) => e.category.toLowerCase() === "miles driven"
  );
  const trueExpenseRows = expenses.filter(
    (e) => e.category.toLowerCase() !== "miles driven"
  );

  const total_revenue = loads.reduce((s, r) => s + r.revenue, 0);
  const total_expenses = trueExpenseRows.reduce((s, r) => s + r.amount, 0);
  const total_miles = milesRows.reduce((s, r) => s + r.amount, 0);
  const true_profit = total_revenue - total_expenses;

  const revenue_per_mile = total_miles > 0 ? total_revenue / total_miles : 0;
  const cost_per_mile = total_miles > 0 ? total_expenses / total_miles : 0;
  const profit_per_mile = total_miles > 0 ? true_profit / total_miles : 0;

  // Expenses by category (total, sorted desc)
  const expByCat = new Map<string, number>();
  for (const e of trueExpenseRows) {
    expByCat.set(e.category, (expByCat.get(e.category) ?? 0) + e.amount);
  }
  const ivan_expenses_by_category: Record<string, number> = Object.fromEntries(
    Array.from(expByCat.entries())
      .sort(([, a], [, b]) => b - a)
      .map(([k, v]) => [k, round2(v)])
  );

  // Monthly: revenue from loads
  const monthRevMap = new Map<
    string,
    { revenue: number; shipment_volume: number }
  >();
  for (const r of loads) {
    if (!r.month) continue;
    const e = monthRevMap.get(r.month) ?? { revenue: 0, shipment_volume: 0 };
    e.revenue += r.revenue;
    e.shipment_volume += 1;
    monthRevMap.set(r.month, e);
  }

  // Monthly: expenses (true only)
  const monthExpMap = new Map<string, number>();
  for (const e of trueExpenseRows) {
    if (!e.month) continue;
    monthExpMap.set(e.month, (monthExpMap.get(e.month) ?? 0) + e.amount);
  }

  // Monthly: miles
  const monthMilesMap = new Map<string, number>();
  for (const e of milesRows) {
    if (!e.month) continue;
    monthMilesMap.set(e.month, (monthMilesMap.get(e.month) ?? 0) + e.amount);
  }

  // Merge all months
  const allMonths = new Set<string>([
    ...monthRevMap.keys(),
    ...monthExpMap.keys(),
    ...monthMilesMap.keys(),
  ]);
  const ivan_monthly_true_profit: IvanMonthRow[] = Array.from(allMonths)
    .sort()
    .map((month) => {
      const rev = monthRevMap.get(month) ?? { revenue: 0, shipment_volume: 0 };
      const exp = monthExpMap.get(month) ?? 0;
      const miles = monthMilesMap.get(month) ?? 0;
      const tp = rev.revenue - exp;
      return {
        month,
        revenue: round2(rev.revenue),
        expenses: round2(exp),
        miles: round2(miles),
        true_profit: round2(tp),
        shipment_volume: rev.shipment_volume,
        revenue_per_mile: round2(miles > 0 ? rev.revenue / miles : 0),
        cost_per_mile: round2(miles > 0 ? exp / miles : 0),
        profit_per_mile: round2(miles > 0 ? tp / miles : 0),
      };
    });

  // Expense category monthly breakdown
  const catMonthMap = new Map<string, number>();
  for (const e of trueExpenseRows) {
    if (!e.month) continue;
    const key = `${e.month}|||${e.category}`;
    catMonthMap.set(key, (catMonthMap.get(key) ?? 0) + e.amount);
  }
  const ivan_expenses_category_monthly: IvanExpenseCategoryRow[] = Array.from(
    catMonthMap.entries()
  )
    .map(([key, amount]) => {
      const [month, category] = key.split("|||");
      return { month, category, amount: round2(amount) };
    })
    .sort((a, b) => b.month.localeCompare(a.month) || b.amount - a.amount);

  // Ivan top customers by month (top 10 per month by revenue)
  const custMonthMap = new Map<
    string,
    { month: string; customer: string; revenue: number; volume: number }
  >();
  for (const r of loads) {
    if (!r.month) continue;
    const key = `${r.month}|||${r.customer}`;
    const e = custMonthMap.get(key) ?? {
      month: r.month,
      customer: r.customer,
      revenue: 0,
      volume: 0,
    };
    e.revenue += r.revenue;
    e.volume += 1;
    custMonthMap.set(key, e);
  }
  const ivanByMonth = new Map<
    string,
    { month: string; customer: string; revenue: number; volume: number }[]
  >();
  for (const v of custMonthMap.values()) {
    const arr = ivanByMonth.get(v.month) ?? [];
    arr.push(v);
    ivanByMonth.set(v.month, arr);
  }
  const ivan_top_customers_by_month: IvanCustomerRow[] = [];
  for (const [, customers] of Array.from(ivanByMonth.entries()).sort(
    ([a], [b]) => a.localeCompare(b)
  )) {
    customers
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 10)
      .forEach((c, idx) => {
        ivan_top_customers_by_month.push({
          month: c.month,
          customer: c.customer,
          revenue: round2(c.revenue),
          volume: c.volume,
          rank: idx + 1,
        });
      });
  }

  return {
    ivan_cartage_revenue: round2(total_revenue),
    ivan_expenses: round2(total_expenses),
    ivan_true_profit: round2(true_profit),
    ivan_total_miles: round2(total_miles),
    ivan_revenue_per_mile: round2(revenue_per_mile),
    ivan_cost_per_mile: round2(cost_per_mile),
    ivan_profit_per_mile: round2(profit_per_mile),
    ivan_expenses_by_category,
    ivan_monthly_true_profit,
    ivan_expenses_category_monthly,
    ivan_top_customers_by_month,
  };
}

// ── Dashboard (combined) ──────────────────────────────────────────────────────

export function getDashboardData(): DashboardData {
  const brokerage = getBrokerageMetrics();
  const ivan = getIvanMetrics();

  const total_company_revenue =
    brokerage.gross_revenue + ivan.ivan_cartage_revenue;

  // Derive report date range from monthly summaries
  const months = [
    ...brokerage.monthly_brokerage_summary.map((r) => r.month),
    ...ivan.ivan_monthly_true_profit.map((r) => r.month),
  ].filter(Boolean);

  const sorted = [...months].sort();
  const report_start_date = sorted[0] ?? "";
  const report_end_date = sorted[sorted.length - 1] ?? "";

  return {
    brokerage,
    ivan,
    total_company_revenue: round2(total_company_revenue),
    report_start_date,
    report_end_date,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}
