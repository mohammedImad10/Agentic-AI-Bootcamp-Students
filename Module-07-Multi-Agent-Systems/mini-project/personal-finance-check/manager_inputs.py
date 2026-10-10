"""Small input fixture module shared by the manager and arithmetic tests."""

EXPECTED = {"match": "ON TRACK", "stretch": "OVERSPENDING"}

INPUTS = {
    "match": {
        "base_currency": "USD",
        "monthly_income": {"amount": "4800", "currency": "USD"},
        "spending_budget": {"amount": "3200", "currency": "USD"},
        "savings_goal": {"amount": "900", "currency": "USD"},
        "expenses": [
            {"category": "rent", "amount": "1450", "currency": "USD"},
            {"category": "groceries", "amount": "520", "currency": "USD"},
            {"category": "transport", "amount": "260", "currency": "USD"},
            {"category": "utilities", "amount": "180", "currency": "USD"},
            {"category": "dining", "amount": "250", "currency": "USD"},
        ],
    },
    "stretch": {
        "base_currency": "USD",
        "monthly_income": {"amount": "4800", "currency": "USD"},
        "spending_budget": {"amount": "3200", "currency": "USD"},
        "savings_goal": {"amount": "900", "currency": "USD"},
        "expenses": [
            {"category": "rent", "amount": "1600", "currency": "EUR"},
            {"category": "other expenses", "amount": "1800", "currency": "USD"},
        ],
    },
}