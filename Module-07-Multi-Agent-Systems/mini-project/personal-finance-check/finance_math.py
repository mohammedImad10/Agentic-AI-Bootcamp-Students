"""Deterministic budget arithmetic for the Personal Finance Check exercise."""

from decimal import Decimal, ROUND_HALF_UP

BASE_RATES_TO_USD = {
    "USD": Decimal("1.00"),
    "EUR": Decimal("1.10"),
    "CAD": Decimal("0.75"),
}
RATE_NOTE = "Illustrative fixed exercise rates; not live market quotes."
CENT = Decimal("0.01")


def _amount(value: object, field: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except Exception as problem:
        raise ValueError(f"{field} must be a number") from problem
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{field} must be a finite, non-negative amount")
    return amount


def _currency(value: object, field: str) -> str:
    currency = str(value).upper()
    if currency not in BASE_RATES_TO_USD:
        raise ValueError(f"unsupported currency {currency!r} in {field}")
    return currency


def _to_base(amount: Decimal, currency: str, base_currency: str) -> Decimal:
    converted = amount * BASE_RATES_TO_USD[currency] / BASE_RATES_TO_USD[base_currency]
    return converted.quantize(CENT, rounding=ROUND_HALF_UP)


def currencies_in(data: dict) -> set[str]:
    """Return all currencies referenced by an input, validating them first."""
    currencies = {
        _currency(data["base_currency"], "base_currency"),
        _currency(data["monthly_income"]["currency"], "monthly_income.currency"),
        _currency(data["spending_budget"]["currency"], "spending_budget.currency"),
        _currency(data["savings_goal"]["currency"], "savings_goal.currency"),
    }
    for index, expense in enumerate(data["expenses"]):
        currencies.add(_currency(expense["currency"], f"expenses[{index}].currency"))
    return currencies


def calculate_budget(data: dict) -> dict:
    """Convert budget inputs to the base currency and calculate the verdict."""
    base = _currency(data["base_currency"], "base_currency")
    currencies_in(data)
    income = _to_base(
        _amount(data["monthly_income"]["amount"], "monthly_income.amount"),
        _currency(data["monthly_income"]["currency"], "monthly_income.currency"),
        base,
    )
    budget = _to_base(
        _amount(data["spending_budget"]["amount"], "spending_budget.amount"),
        _currency(data["spending_budget"]["currency"], "spending_budget.currency"),
        base,
    )
    goal = _to_base(
        _amount(data["savings_goal"]["amount"], "savings_goal.amount"),
        _currency(data["savings_goal"]["currency"], "savings_goal.currency"),
        base,
    )

    total = Decimal("0.00")
    for index, expense in enumerate(data["expenses"]):
        amount = _amount(expense["amount"], f"expenses[{index}].amount")
        currency = _currency(expense["currency"], f"expenses[{index}].currency")
        total += _to_base(amount, currency, base)

    return {
        "base_currency": base,
        "income": income,
        "budget": budget,
        "savings_goal": goal,
        "total_spending": total,
        "actual_savings": income - total,
        "budget_remaining": budget - total,
        "decision": "OVERSPENDING" if total > budget else "ON TRACK",
    }