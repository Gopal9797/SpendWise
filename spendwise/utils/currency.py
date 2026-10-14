"""Currency formatting helpers."""

from spendwise.config import DEFAULT_CURRENCY_SYMBOL


def format_currency(amount: float, symbol: str = DEFAULT_CURRENCY_SYMBOL) -> str:
    return f"{symbol}{amount:,.2f}"
