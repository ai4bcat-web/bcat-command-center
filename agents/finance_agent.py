import pandas as pd
import numpy as np
import schedule
import time
from datetime import datetime

class FinanceAgent:
    def __init__(self):
        self.data = {}  # Store all relevant financial data
        self.ivan_cartage_expenses = {}  # Store Ivan Cartage expenses data
        self.total_miles_driven = 0  # Store total miles driven

    def calculate_revenue_growth(self):
        if 'revenue' in self.data:
            return self.data['revenue'].sum()  # Placeholder logic
        return 0

    def ingest_data(self, file_path):
        csv_data = pd.read_csv(file_path)
        self.data.update(csv_data)

    def ingest_expenses(self, monthly_expenses):
        for item in monthly_expenses:
            category = item['category']
            amount = item['amount']
            if category in self.ivan_cartage_expenses:
                self.ivan_cartage_expenses[category] += amount
            else:
                self.ivan_cartage_expenses[category] = amount

    def analyze_performance(self):
        metrics = {
            'revenue_growth': self.calculate_revenue_growth(),
            'ivan_cartage_expenses': self.ivan_cartage_expenses,
        }
        return metrics

    async def request_monthly_expenses(self, ctx, month):
        await ctx.send(f"It's time to submit your monthly expenses for {month}.")
        missing_fields = ["Tolls", "Insurance/Workmans Comp", "Fuel/DEF", "Payroll",
                          "Employer Tax FICA", "Paychex", "Yard Rent",
                          "Trailers Rent", "Trailers Note", "BLACK VOLVO CARNOTE", 
                          "WHITE VOLVO CARNOTE", "Licenses/Permits/ETC",
                          "Maintenance", "Drug Tests", "SBA LOAN"]
        for field in missing_fields:
            await ctx.send(f"Enter amount for {field}:")

    def schedule_monthly_request(self):
        schedule.every().month.at("00:00").do(self.request_monthly_expenses)

    def run_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
