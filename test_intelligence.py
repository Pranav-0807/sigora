import unittest
from financial_intelligence import build_intelligence, simulate_purchase

class IntelligenceTests(unittest.TestCase):
    def test_budget_risk_and_correction(self):
        ctx={"overall":{"total_income":20000,"total_expense":15000,"savings_rate":25,"savings":5000},"latest_month":{"year":__import__('datetime').date.today().year,"month":__import__('datetime').date.today().month,"income":20000,"expense":15000},"monthly_history":[{"year":__import__('datetime').date.today().year,"month":__import__('datetime').date.today().month,"income":20000,"expense":15000}],"monthly_savings_history":[{"savings":4000},{"savings":5000}]}
        result=build_intelligence(ctx,[{"category":"food","amount":100,"spent":1000}],[])
        self.assertTrue(result["risks"])
        self.assertTrue(result["score_available"])
        self.assertGreaterEqual(result["score"],0); self.assertLessEqual(result["score"],100)

    def test_empty_account_has_no_fake_score_or_forecast(self):
        ctx={"overall":{"total_income":0,"total_expense":0,"savings":0,"savings_rate":0},"latest_month":None,"monthly_history":[],"monthly_savings_history":[]}
        result=build_intelligence(ctx,[],[])
        self.assertFalse(result["score_available"])
        self.assertIsNone(result["score"])
        self.assertEqual(result["score_parts"],{})
        self.assertFalse(result["forecast_available"])
        self.assertIsNone(result["projected_expense"])
        self.assertIn("Not enough data", result["headline"])

    def test_missing_components_are_not_given_neutral_scores(self):
        today=__import__('datetime').date.today()
        ctx={"overall":{"total_income":1000,"total_expense":200,"savings":800,"savings_rate":80},"latest_month":{"year":today.year,"month":today.month,"income":1000,"expense":200},"monthly_history":[{"year":today.year,"month":today.month,"income":1000,"expense":200}],"monthly_savings_history":[{"savings":800}]}
        result=build_intelligence(ctx,[],[])
        self.assertEqual(set(result["score_parts"]), {"Savings"})
        self.assertTrue(result["score_available"])
        self.assertEqual(result["confidence"], "early")

    def test_simulation_never_invents_goal(self):
        ctx={"overall":{"total_income":2000,"total_expense":1000,"savings":1000},"monthly_savings_history":[{"savings":1000}]}
        result=simulate_purchase(ctx,500,[])
        self.assertIsNone(result["goal_name"])
        self.assertEqual(result["post_buffer"],500)
        self.assertTrue(result["ready"])

    def test_simulation_refuses_empty_financial_history(self):
        ctx={"overall":{"total_income":0,"total_expense":0,"savings":0},"monthly_savings_history":[]}
        result=simulate_purchase(ctx,500,[])
        self.assertFalse(result["ready"])
        self.assertIn("Not enough", result["verdict"])

if __name__ == '__main__': unittest.main()
