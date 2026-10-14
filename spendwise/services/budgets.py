"""Business logic for budget operations and progress tracking."""

import pandas as pd

from spendwise.analytics.metrics import calculate_budget_progress, calculate_spending_by_category
from spendwise.db.repository import SpendWiseRepository
from spendwise.utils.validation import validate_budget_payload


def set_budget(repo: SpendWiseRepository, payload: dict[str, object]) -> int:
    budget = validate_budget_payload(payload)
    return repo.upsert_budget(budget)


def delete_budget(repo: SpendWiseRepository, budget_id: int) -> bool:
    return repo.delete_budget(budget_id)


def list_budgets(repo: SpendWiseRepository, month_key: str | None = None) -> list[dict[str, object]]:
    return repo.list_budgets(month_key=month_key)


def build_budget_status(
    repo: SpendWiseRepository,
    month_key: str,
    transaction_df: pd.DataFrame,
) -> pd.DataFrame:
    budgets = repo.list_budgets(month_key=month_key)
    category_spend = calculate_spending_by_category(transaction_df, month_key)
    return calculate_budget_progress(category_spend, budgets)
