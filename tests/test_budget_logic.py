"""Tests for budget progress calculations and service wiring."""

import pandas as pd

from spendwise.analytics.metrics import calculate_budget_progress, transactions_to_dataframe
from spendwise.db.repository import SpendWiseRepository
from spendwise.models import TransactionInput
from spendwise.services.budgets import build_budget_status, set_budget


def test_calculate_budget_progress_detects_overspending() -> None:
    spending_df = pd.DataFrame(
        [
            {"category": "Groceries", "amount": 5200.0},
            {"category": "Rent", "amount": 24000.0},
        ]
    )
    budgets = [
        {"category": "Groceries", "budget_amount": 5000.0},
        {"category": "Rent", "budget_amount": 25000.0},
        {"category": "Dining", "budget_amount": 3000.0},
    ]

    result = calculate_budget_progress(spending_df, budgets)

    groceries_row = result.loc[result["category"] == "Groceries"].iloc[0]
    rent_row = result.loc[result["category"] == "Rent"].iloc[0]
    dining_row = result.loc[result["category"] == "Dining"].iloc[0]

    assert bool(groceries_row["overspent"]) is True
    assert float(groceries_row["remaining"]) == -200.0

    assert bool(rent_row["overspent"]) is False
    assert float(rent_row["remaining"]) == 1000.0

    assert float(dining_row["spent"]) == 0.0
    assert float(dining_row["progress_pct"]) == 0.0


def test_build_budget_status_uses_repo_data(tmp_path) -> None:
    repo = SpendWiseRepository(tmp_path / "test_budget.db")
    repo.initialize()

    set_budget(repo, {"month_key": "2026-10", "category": "Groceries", "budget_amount": 5000.0})
    set_budget(repo, {"month_key": "2026-10", "category": "Rent", "budget_amount": 25000.0})

    repo.add_transaction(
        TransactionInput(
            transaction_type="expense",
            amount=6100.0,
            transaction_date="2026-10-05",
            category="Groceries",
            description="Festival shopping",
            payment_method="upi",
            dedupe_key="grocery-1",
        )
    )
    repo.add_transaction(
        TransactionInput(
            transaction_type="expense",
            amount=24000.0,
            transaction_date="2026-10-03",
            category="Rent",
            description="Monthly rent",
            payment_method="bank_transfer",
            dedupe_key="rent-1",
        )
    )

    transaction_df = transactions_to_dataframe(repo.list_transactions())
    status_df = build_budget_status(repo, "2026-10", transaction_df)

    groceries_row = status_df.loc[status_df["category"] == "Groceries"].iloc[0]
    rent_row = status_df.loc[status_df["category"] == "Rent"].iloc[0]

    assert bool(groceries_row["overspent"]) is True
    assert float(groceries_row["spent"]) == 6100.0

    assert bool(rent_row["overspent"]) is False
    assert float(rent_row["remaining"]) == 1000.0
