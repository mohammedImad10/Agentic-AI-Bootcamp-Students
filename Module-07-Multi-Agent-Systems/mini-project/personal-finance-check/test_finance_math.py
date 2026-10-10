import unittest
from decimal import Decimal

from finance_math import calculate_budget, currencies_in
from manager_inputs import INPUTS


class FinanceMathTests(unittest.TestCase):
    def test_usd_budget_is_on_track(self):
        result = calculate_budget(INPUTS["match"])
        self.assertEqual(result["total_spending"], Decimal("2660.00"))
        self.assertEqual(result["actual_savings"], Decimal("2140.00"))
        self.assertEqual(result["decision"], "ON TRACK")

    def test_eur_rent_is_converted_and_overspend_is_detected(self):
        result = calculate_budget(INPUTS["stretch"])
        self.assertEqual(result["total_spending"], Decimal("3560.00"))
        self.assertEqual(result["budget_remaining"], Decimal("-360.00"))
        self.assertEqual(result["decision"], "OVERSPENDING")
        self.assertEqual(currencies_in(INPUTS["stretch"]), {"USD", "EUR"})

    def test_unsupported_currency_is_rejected(self):
        data = {**INPUTS["match"], "expenses": [{"category": "other", "amount": "10", "currency": "XYZ"}]}
        with self.assertRaisesRegex(ValueError, "unsupported currency"):
            calculate_budget(data)

    def test_negative_expense_is_rejected(self):
        data = {**INPUTS["match"], "expenses": [{"category": "other", "amount": "-1", "currency": "USD"}]}
        with self.assertRaisesRegex(ValueError, "non-negative"):
            calculate_budget(data)


if __name__ == "__main__":
    unittest.main()