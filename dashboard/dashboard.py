from flask import Flask, jsonify
from finance_agent import FinanceAgent
import pandas as pd

app = Flask(__name__)
finance_agent = FinanceAgent()

@app.route('/api/dashboard', methods=['GET'])
def dashboard_api():
    finance_agent.ingest_data()  # Load latest data from CSV
    ivan_expense_metrics = finance_agent.get_ivan_expense_metrics()  # The correct method for Ivan metrics
    brokerage_metrics = finance_agent.calculate_brokerage_metrics()

    # Calculate total company revenue
    total_company_revenue = ivan_expense_metrics['ivan_revenue_per_mile'] + brokerage_metrics['gross_revenue']

    return jsonify({
        'report_start_date': '2026-01-01',  # Example start date, adjust as needed
        'report_end_date': 'Latest Upload',  # Example end date
        'ivan_expenses': ivan_expense_metrics,
        'brokerage': brokerage_metrics,
        'total_company_revenue': total_company_revenue
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)