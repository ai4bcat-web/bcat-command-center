# LEGACY FILE — DO NOT USE
# This file predates the current FinanceAgent architecture and cannot run.
# Imports (revenue_data, marketing_data, sales_data) do not exist.
# The active dashboard is: /Users/adminoid/AI_WORKSPACE/MultiAgent_Operations/dashboard.py
# Kept for historical reference only.

from flask import Flask, render_template
from agents.coordinator_agent import CoordinatorAgent
import revenue_data
import marketing_data
import sales_data
import pandas as pd

app = Flask(__name__)
coordinator = CoordinatorAgent()


@app.route('/')
def dashboard():
    ivan_expenses = pd.read_csv('/Users/adminoid/MultiAgent_Operations/ivan_cartage_expenses.csv')
    revenue = revenue_data.get_revenue_summary()
    marketing = marketing_data.get_marketing_metrics()
    sales = sales_data.get_sales_metrics()

    return render_template(
        'dashboard.html',
        revenue=revenue,
        marketing=marketing,
        sales=sales,
        ivan_expenses=ivan_expenses
    )


@app.route('/marketing')
def marketing_command_center():
    marketing = marketing_data.get_marketing_metrics()
    sales = sales_data.get_sales_metrics()

    return render_template(
        'marketing.html',
        marketing=marketing,
        sales=sales
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
