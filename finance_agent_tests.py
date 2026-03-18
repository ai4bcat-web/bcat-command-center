import unittest
from finance_agent import FinanceAgent

class TestFinanceAgent(unittest.TestCase):
    def setUp(self):
        self.agent = FinanceAgent()
        # Load some sample data for testing
        self.agent.ingest_data('sample_financial_data.csv')

    def test_analyze_performance(self):
        metrics = self.agent.analyze_performance()
        # Add assertions based on expected results
        self.assertIn('revenue_growth', metrics)
        self.assertIn('profit_trends', metrics)

    def test_answer_question_profit(self):
        response = self.agent.answer_question("What customer had the best profit in February?")
        self.assertIsInstance(response, str)  # Example check

    def test_generate_recommendations(self):
        recommendations = self.agent.generate_recommendations()
        self.assertIn('sales_focus', recommendations)
        self.assertIn('customer_attention', recommendations)

if __name__ == '__main__':
    unittest.main()