"""Tests for analytics calculations and month filtering."""

from spendwise.analytics.metrics import (
    calculate_monthly_summary,
    calculate_spending_by_category,
    calculate_spending_trend,
    filter_transactions_by_month,
    transactions_to_dataframe,
)


def _sample_transactions() -> list[dict[str, object]]:
    return [
        {
            "id": 1,
            "transaction_type": "income",
            "amount": 100000,
            "transaction_date": "2026-09-01",
            "category": "Salary",
            "description": "Salary",
            "payment_method": "bank_transfer",
            "dedupe_key": None,
            "created_at": "2026-09-01",
            "updated_at": "2026-09-01",
        },
        {
            "id": 2,
            "transaction_type": "expense",
            "amount": 25000,
            "transaction_date": "2026-09-03",
            "category": "Rent",
            "description": "Monthly rent",
            "payment_method": "bank_transfer",
            "dedupe_key": None,
            "created_at": "2026-09-03",
            "updated_at": "2026-09-03",
        },
        {
            "id": 3,
            "transaction_type": "expense",
            "amount": 6000,
            "transaction_date": "2026-09-11",
            "category": "Groceries",
            "description": "Groceries",
            "payment_method": "upi",
            "dedupe_key": None,
            "created_at": "2026-09-11",
            "updated_at": "2026-09-11",
        },
        {
            "id": 4,
            "transaction_type": "income",
            "amount": 100000,
            "transaction_date": "2026-10-01",
            "category": "Salary",
            "description": "Salary",
            "payment_method": "bank_transfer",
            "dedupe_key": None,
            "created_at": "2026-10-01",
            "updated_at": "2026-10-01",
        },
        {
            "id": 5,
            "transaction_type": "expense",
            "amount": 28000,
            "transaction_date": "2026-10-05",
            "category": "Rent",
            "description": "Monthly rent",
            "payment_method": "bank_transfer",
            "dedupe_key": None,
            "created_at": "2026-10-05",
            "updated_at": "2026-10-05",
        },
    ]


def test_filter_transactions_by_month_returns_only_target_month() -> None:
    df = transactions_to_dataframe(_sample_transactions())

    september_df = filter_transactions_by_month(df, "2026-09")

    assert len(september_df.index) == 3
    assert set(september_df["transaction_type"].tolist()) == {"income", "expense"}


def test_calculate_monthly_summary_values() -> None:
    df = transactions_to_dataframe(_sample_transactions())

    summary = calculate_monthly_summary(df, "2026-09")

    assert summary == {"income": 100000.0, "expenses": 31000.0, "balance": 69000.0}


def test_calculate_spending_by_category() -> None:
    df = transactions_to_dataframe(_sample_transactions())

    category_df = calculate_spending_by_category(df, "2026-09")

    assert category_df["category"].tolist() == ["Rent", "Groceries"]
    assert category_df["amount"].tolist() == [25000.0, 6000.0]


def test_calculate_spending_trend_includes_income_and_expenses() -> None:
    df = transactions_to_dataframe(_sample_transactions())

    trend_df = calculate_spending_trend(df, months=12)

    assert trend_df["month"].tolist() == ["2026-09", "2026-10"]
    assert trend_df["income"].tolist() == [100000.0, 100000.0]
    assert trend_df["expenses"].tolist() == [31000.0, 28000.0]
