"""Validation helpers for external inputs."""

from collections.abc import Iterable

from spendwise.config import PAYMENT_METHODS, TRANSACTION_TYPES
from spendwise.models import BudgetInput, TransactionInput
from spendwise.utils.dates import parse_date, parse_month_key


def _validate_non_empty_text(value: object, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required.")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} cannot be empty.")
    return text


def validate_amount(value: object, field_name: str = "amount") -> float:
    try:
        amount = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid number.") from exc

    if amount < 0:
        raise ValueError(f"{field_name} cannot be negative.")

    return round(amount, 2)


def validate_transaction_payload(payload: dict[str, object]) -> TransactionInput:
    transaction_type = _validate_non_empty_text(payload.get("transaction_type"), "transaction_type").lower()
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("transaction_type must be 'income' or 'expense'.")

    amount = validate_amount(payload.get("amount"), "amount")

    date_text = _validate_non_empty_text(payload.get("date"), "date")
    parse_date(date_text)

    category = _validate_non_empty_text(payload.get("category"), "category")
    description = str(payload.get("description", "")).strip()

    payment_method = _validate_non_empty_text(payload.get("payment_method"), "payment_method").lower()
    payment_method = payment_method.replace(" ", "_")
    if payment_method not in PAYMENT_METHODS:
        raise ValueError(f"payment_method must be one of: {', '.join(sorted(PAYMENT_METHODS))}.")

    dedupe_key_raw = payload.get("dedupe_key")
    dedupe_key = str(dedupe_key_raw).strip() if dedupe_key_raw else None

    return TransactionInput(
        transaction_type=transaction_type,
        amount=amount,
        transaction_date=date_text,
        category=category,
        description=description,
        payment_method=payment_method,
        dedupe_key=dedupe_key,
    )


def validate_budget_payload(payload: dict[str, object]) -> BudgetInput:
    month_key = _validate_non_empty_text(payload.get("month_key"), "month_key")
    parse_month_key(month_key)

    category = _validate_non_empty_text(payload.get("category"), "category")
    budget_amount = validate_amount(payload.get("budget_amount"), "budget_amount")

    return BudgetInput(month_key=month_key, category=category, budget_amount=budget_amount)


def missing_columns(columns: Iterable[str], required_columns: Iterable[str]) -> list[str]:
    existing = {str(column).strip() for column in columns}
    return [col for col in required_columns if col not in existing]
