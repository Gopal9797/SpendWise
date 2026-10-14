"""Business logic for transaction operations."""

from spendwise.db.repository import SpendWiseRepository
from spendwise.utils.validation import validate_transaction_payload


def add_transaction(repo: SpendWiseRepository, payload: dict[str, object]) -> int:
    transaction = validate_transaction_payload(payload)
    return repo.add_transaction(transaction)


def edit_transaction(repo: SpendWiseRepository, transaction_id: int, payload: dict[str, object]) -> bool:
    transaction = validate_transaction_payload(payload)
    return repo.update_transaction(transaction_id, transaction)


def remove_transaction(repo: SpendWiseRepository, transaction_id: int) -> bool:
    return repo.delete_transaction(transaction_id)


def remove_all_transactions(repo: SpendWiseRepository) -> int:
    return repo.delete_all_transactions()


def list_transactions(
    repo: SpendWiseRepository,
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
) -> list[dict[str, object]]:
    return repo.list_transactions(
        start_date=start_date,
        end_date=end_date,
        category=category,
        transaction_type=transaction_type,
    )
