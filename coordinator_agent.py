# Import necessary packages
from .finance_agent import FinanceAgent  # Add this line to import the FinanceAgent class

class CoordinatorAgent:
    def __init__(self):
        self.financial_data = {}  # Initializing financial data
    
    def collect_financial_data(self):
        # Placeholder logic to fetch financial data
        # In practice, this would likely query a database or another API
        self.financial_data = {
            'cash_on_hand': 100000,
            'accounts_receivable': 50000,
            'accounts_payable': 30000,
            'payroll_obligations': 20000,
            'weekly_profitability': 15000,
            'major_expenses': ['Office Supplies', 'Software Licenses'],
            'alerts': 'No unusual transactions detected.'
        }
    
    def generate_financial_summary(self):
        self.collect_financial_data()
        return (
            f"Weekly Financial Summary:\n"
            f"Current Cash: ${self.financial_data['cash_on_hand']}\n"
            f"Accounts Receivable: ${self.financial_data['accounts_receivable']}\n"
            f"Accounts Payable: ${self.financial_data['accounts_payable']}\n"
            f"Payroll Obligations: ${self.financial_data['payroll_obligations']}\n"
            f"Weekly Profitability: ${self.financial_data['weekly_profitability']}\n"
            f"Major Expense Changes: {', '.join(self.financial_data['major_expenses'])}\n"
            f"Alerts: {self.financial_data['alerts']}\n"
        )
