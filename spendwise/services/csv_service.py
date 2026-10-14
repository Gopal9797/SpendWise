"""CSV import/export services with validation and dedupe protection."""

from hashlib import sha256
from io import StringIO
from sqlite3 import IntegrityError

import pandas as pd

from spendwise.config import TRANSACTION_CSV_COLUMNS
from spendwise.db.repository import SpendWiseRepository
from spendwise.models import ImportResult
from spendwise.utils.validation import missing_columns, validate_transaction_payload


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    copy_df = df.copy()
    copy_df.columns = [str(column).strip().lower() for column in copy_df.columns]
    return copy_df


def build_dedupe_key(payload: dict[str, object]) -> str:
    normalized = [
        str(payload.get("transaction_type", "")).strip().lower(),
        f"{float(payload.get('amount', 0)):0.2f}",
        str(payload.get("date", "")).strip(),
        str(payload.get("category", "")).strip().lower(),
        str(payload.get("description", "")).strip().lower(),
        str(payload.get("payment_method", "")).strip().lower(),
    ]
    return sha256("|".join(normalized).encode("utf-8")).hexdigest()


def validate_csv_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    normalized_df = _normalize_headers(df)
    missing = missing_columns(normalized_df.columns, TRANSACTION_CSV_COLUMNS)
    if missing:
        return normalized_df, [f"Missing required columns: {', '.join(missing)}"]

    return normalized_df, []


def import_transactions_from_csv_bytes(repo: SpendWiseRepository, file_bytes: bytes) -> ImportResult:
    try:
        data_str = file_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return ImportResult(invalid_count=1, errors=[f"CSV must be UTF-8 encoded: {exc}"])

    try:
        raw_df = pd.read_csv(StringIO(data_str))
    except Exception as exc:
        return ImportResult(invalid_count=1, errors=[f"Malformed CSV file: {exc}"])

    return import_transactions_from_dataframe(repo, raw_df)


def import_transactions_from_dataframe(repo: SpendWiseRepository, df: pd.DataFrame) -> ImportResult:
    result = ImportResult()
    normalized_df, errors = validate_csv_dataframe(df)
    if errors:
        result.invalid_count = len(df.index)
        result.errors.extend(errors)
        return result

    seen_keys: set[str] = set()

    for row_index, row in normalized_df.iterrows():
        payload = {
            "transaction_type": row.get("transaction_type"),
            "amount": row.get("amount"),
            "date": row.get("date"),
            "category": row.get("category"),
            "description": row.get("description", ""),
            "payment_method": row.get("payment_method"),
        }

        try:
            dedupe_key = build_dedupe_key(payload)
            payload["dedupe_key"] = dedupe_key
            validated = validate_transaction_payload(payload)
        except ValueError as exc:
            result.invalid_count += 1
            result.errors.append(f"Row {row_index + 2}: {exc}")
            continue

        if dedupe_key in seen_keys or repo.dedupe_key_exists(dedupe_key):
            result.duplicate_count += 1
            continue

        try:
            repo.add_transaction(validated)
            seen_keys.add(dedupe_key)
            result.inserted_count += 1
        except IntegrityError:
            result.duplicate_count += 1

    return result


def export_transactions_to_csv(repo: SpendWiseRepository) -> str:
    transactions = repo.list_transactions()
    if not transactions:
        return "transaction_type,amount,date,category,description,payment_method\n"

    df = pd.DataFrame(transactions)
    export_df = df[
        ["transaction_type", "amount", "transaction_date", "category", "description", "payment_method"]
    ].rename(columns={"transaction_date": "date"})
    return export_df.to_csv(index=False)
