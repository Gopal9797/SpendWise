"""Tests for CSV validation and import logic."""

import pandas as pd

from spendwise.db.repository import SpendWiseRepository
from spendwise.services.csv_service import (
    import_transactions_from_csv_bytes,
    import_transactions_from_dataframe,
    validate_csv_dataframe,
)


def test_validate_csv_dataframe_missing_columns() -> None:
    df = pd.DataFrame(
        [
            {
                "transaction_type": "expense",
                "amount": 100,
                "category": "Food",
                "description": "Lunch",
                "payment_method": "cash",
            }
        ]
    )

    _, errors = validate_csv_dataframe(df)

    assert len(errors) == 1
    assert "Missing required columns" in errors[0]
    assert "date" in errors[0]


def test_import_transactions_from_dataframe_with_duplicates_and_invalid_rows(tmp_path) -> None:
    repo = SpendWiseRepository(tmp_path / "test_csv.db")
    repo.initialize()

    df = pd.DataFrame(
        [
            {
                "transaction_type": "expense",
                "amount": 400,
                "date": "2026-10-01",
                "category": "Food",
                "description": "Lunch",
                "payment_method": "upi",
            },
            {
                "transaction_type": "expense",
                "amount": 400,
                "date": "2026-10-01",
                "category": "Food",
                "description": "Lunch",
                "payment_method": "upi",
            },
            {
                "transaction_type": "expense",
                "amount": -50,
                "date": "2026-10-02",
                "category": "Transport",
                "description": "Metro",
                "payment_method": "card",
            },
            {
                "transaction_type": "income",
                "amount": 12000,
                "date": "2026-10-03",
                "category": "Freelance",
                "description": "Project payment",
                "payment_method": "bank_transfer",
            },
        ]
    )

    result = import_transactions_from_dataframe(repo, df)

    assert result.inserted_count == 2
    assert result.duplicate_count == 1
    assert result.invalid_count == 1
    assert len(repo.list_transactions()) == 2

    second_result = import_transactions_from_dataframe(repo, df)
    assert second_result.inserted_count == 0
    assert second_result.duplicate_count == 3
    assert second_result.invalid_count == 1


def test_import_transactions_from_csv_bytes_handles_invalid_encoding(tmp_path) -> None:
    repo = SpendWiseRepository(tmp_path / "test_csv_encoding.db")
    repo.initialize()

    result = import_transactions_from_csv_bytes(repo, b"\xff\xfe\x00")

    assert result.inserted_count == 0
    assert result.invalid_count == 1
    assert result.errors
    assert "UTF-8" in result.errors[0]
