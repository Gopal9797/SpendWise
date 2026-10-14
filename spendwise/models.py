"""Typed data structures for SpendWise business entities."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TransactionInput:
    transaction_type: str
    amount: float
    transaction_date: str
    category: str
    description: str
    payment_method: str
    dedupe_key: str | None = None


@dataclass(frozen=True)
class BudgetInput:
    month_key: str
    category: str
    budget_amount: float


@dataclass
class ImportResult:
    inserted_count: int = 0
    duplicate_count: int = 0
    invalid_count: int = 0
    errors: list[str] = field(default_factory=list)
