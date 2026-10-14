"""Repository layer that encapsulates all SQL operations."""

from pathlib import Path

from spendwise.db.connection import get_connection, initialize_database
from spendwise.models import BudgetInput, TransactionInput


class SpendWiseRepository:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        initialize_database(self.db_path)

    def add_transaction(self, transaction: TransactionInput) -> int:
        query = """
        INSERT INTO transactions (
            transaction_type,
            amount,
            transaction_date,
            category,
            description,
            payment_method,
            dedupe_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            transaction.transaction_type,
            transaction.amount,
            transaction.transaction_date,
            transaction.category,
            transaction.description,
            transaction.payment_method,
            transaction.dedupe_key,
        )
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(query, values)
            connection.commit()
            return int(cursor.lastrowid)

    def update_transaction(self, transaction_id: int, transaction: TransactionInput) -> bool:
        query = """
        UPDATE transactions
           SET transaction_type = ?,
               amount = ?,
               transaction_date = ?,
               category = ?,
               description = ?,
               payment_method = ?
         WHERE id = ?
        """
        values = (
            transaction.transaction_type,
            transaction.amount,
            transaction.transaction_date,
            transaction.category,
            transaction.description,
            transaction.payment_method,
            transaction_id,
        )
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(query, values)
            connection.commit()
            return cursor.rowcount > 0

    def delete_transaction(self, transaction_id: int) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            connection.commit()
            return cursor.rowcount > 0

    def delete_all_transactions(self) -> int:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM transactions")
            connection.commit()
            return int(cursor.rowcount if cursor.rowcount is not None else 0)

    def get_transaction(self, transaction_id: int) -> dict[str, object] | None:
        query = "SELECT * FROM transactions WHERE id = ?"
        with get_connection(self.db_path) as connection:
            row = connection.execute(query, (transaction_id,)).fetchone()
            return dict(row) if row else None

    def list_transactions(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        category: str | None = None,
        transaction_type: str | None = None,
    ) -> list[dict[str, object]]:
        query = "SELECT * FROM transactions WHERE 1 = 1"
        params: list[object] = []

        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND transaction_date < ?"
            params.append(end_date)
        if category:
            query += " AND category = ?"
            params.append(category)
        if transaction_type:
            query += " AND transaction_type = ?"
            params.append(transaction_type)

        query += " ORDER BY transaction_date DESC, id DESC"

        with get_connection(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def dedupe_key_exists(self, dedupe_key: str) -> bool:
        query = "SELECT 1 FROM transactions WHERE dedupe_key = ? LIMIT 1"
        with get_connection(self.db_path) as connection:
            row = connection.execute(query, (dedupe_key,)).fetchone()
            return row is not None

    def upsert_budget(self, budget: BudgetInput) -> int:
        query = """
        INSERT INTO budgets (month_key, category, budget_amount)
        VALUES (?, ?, ?)
        ON CONFLICT(month_key, category)
        DO UPDATE SET budget_amount = excluded.budget_amount
        """
        values = (budget.month_key, budget.category, budget.budget_amount)
        with get_connection(self.db_path) as connection:
            connection.execute(query, values)
            connection.commit()
            row = connection.execute(
                "SELECT id FROM budgets WHERE month_key = ? AND category = ?",
                (budget.month_key, budget.category),
            ).fetchone()
            return int(row["id"])

    def delete_budget(self, budget_id: int) -> bool:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
            connection.commit()
            return cursor.rowcount > 0

    def list_budgets(self, month_key: str | None = None) -> list[dict[str, object]]:
        query = "SELECT * FROM budgets"
        params: list[object] = []
        if month_key:
            query += " WHERE month_key = ?"
            params.append(month_key)
        query += " ORDER BY month_key DESC, category ASC"

        with get_connection(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
            return [dict(row) for row in rows]
