"""Tests for transaction service delete-all behavior."""

from spendwise.db.repository import SpendWiseRepository
from spendwise.models import TransactionInput
from spendwise.services.transactions import remove_all_transactions


def _add_sample_transactions(repo: SpendWiseRepository) -> None:
    repo.add_transaction(
        TransactionInput(
            transaction_type="income",
            amount=85000.0,
            transaction_date="2026-10-01",
            category="Salary",
            description="Monthly salary",
            payment_method="bank_transfer",
            dedupe_key="sample-income-1",
        )
    )
    repo.add_transaction(
        TransactionInput(
            transaction_type="expense",
            amount=5000.0,
            transaction_date="2026-10-03",
            category="Groceries",
            description="Weekly grocery run",
            payment_method="upi",
            dedupe_key="sample-expense-1",
        )
    )


def test_repository_delete_all_transactions_clears_rows(tmp_path) -> None:
    repo = SpendWiseRepository(tmp_path / "test_delete_all_repo.db")
    repo.initialize()
    _add_sample_transactions(repo)

    deleted_count = repo.delete_all_transactions()

    assert deleted_count == 2
    assert repo.list_transactions() == []


def test_remove_all_transactions_service_returns_deleted_count(tmp_path) -> None:
    repo = SpendWiseRepository(tmp_path / "test_delete_all_service.db")
    repo.initialize()
    _add_sample_transactions(repo)

    deleted_count = remove_all_transactions(repo)

    assert deleted_count == 2
    assert repo.list_transactions() == []
