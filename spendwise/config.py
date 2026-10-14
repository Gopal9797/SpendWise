"""Application-level constants and configuration."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "spendwise.db"

DEFAULT_CURRENCY_SYMBOL = "₹"
DATE_INPUT_FORMAT = "%Y-%m-%d"
MONTH_KEY_FORMAT = "%Y-%m"

TRANSACTION_TYPES = {"income", "expense"}
PAYMENT_METHODS = {
    "cash",
    "upi",
    "card",
    "bank_transfer",
    "wallet",
    "other",
}

TRANSACTION_CSV_COLUMNS = [
    "transaction_type",
    "amount",
    "date",
    "category",
    "description",
    "payment_method",
]
