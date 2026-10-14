"""Analytics and reporting helpers built on pandas."""

import pandas as pd

from spendwise.utils.dates import month_range


TRANSACTION_COLUMNS = [
    "id",
    "transaction_type",
    "amount",
    "transaction_date",
    "category",
    "description",
    "payment_method",
    "dedupe_key",
    "created_at",
    "updated_at",
]


def transactions_to_dataframe(transactions: list[dict[str, object]]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)

    df = pd.DataFrame(transactions)
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df


def filter_transactions_by_month(df: pd.DataFrame, month_key: str) -> pd.DataFrame:
    if df.empty:
        return df
    start_date, end_date = month_range(month_key)
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    mask = (df["transaction_date"] >= start_ts) & (df["transaction_date"] < end_ts)
    return df.loc[mask].copy()


def calculate_monthly_summary(df: pd.DataFrame, month_key: str) -> dict[str, float]:
    month_df = filter_transactions_by_month(df, month_key)
    if month_df.empty:
        return {"income": 0.0, "expenses": 0.0, "balance": 0.0}

    income = float(month_df.loc[month_df["transaction_type"] == "income", "amount"].sum())
    expenses = float(month_df.loc[month_df["transaction_type"] == "expense", "amount"].sum())
    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "balance": round(income - expenses, 2),
    }


def calculate_spending_by_category(df: pd.DataFrame, month_key: str) -> pd.DataFrame:
    month_df = filter_transactions_by_month(df, month_key)
    if month_df.empty:
        return pd.DataFrame(columns=["category", "amount"])

    expense_df = month_df.loc[month_df["transaction_type"] == "expense"]
    if expense_df.empty:
        return pd.DataFrame(columns=["category", "amount"])

    category_df = (
        expense_df.groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )
    category_df["amount"] = category_df["amount"].round(2)
    return category_df


def calculate_spending_trend(df: pd.DataFrame, months: int = 6) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "income", "expenses"])

    trend_df = df.copy()
    trend_df["month"] = trend_df["transaction_date"].dt.to_period("M").astype(str)

    grouped = trend_df.groupby(["month", "transaction_type"], as_index=False)["amount"].sum()
    pivot = grouped.pivot(index="month", columns="transaction_type", values="amount").fillna(0.0)

    for column in ["income", "expense"]:
        if column not in pivot.columns:
            pivot[column] = 0.0

    pivot = pivot.rename(columns={"expense": "expenses"}).reset_index()
    pivot = pivot.sort_values("month").tail(months)
    pivot["income"] = pivot["income"].round(2)
    pivot["expenses"] = pivot["expenses"].round(2)
    return pivot[["month", "income", "expenses"]]


def calculate_budget_progress(
    spending_by_category: pd.DataFrame,
    budgets: list[dict[str, object]],
) -> pd.DataFrame:
    if not budgets:
        return pd.DataFrame(columns=["category", "budget_amount", "spent", "remaining", "progress_pct", "overspent"])

    budget_df = pd.DataFrame(budgets)
    budget_df = budget_df[["category", "budget_amount"]].copy()
    budget_df["budget_amount"] = pd.to_numeric(budget_df["budget_amount"], errors="coerce").fillna(0.0)

    if spending_by_category.empty:
        budget_df["spent"] = 0.0
    else:
        merged = budget_df.merge(
            spending_by_category[["category", "amount"]].rename(columns={"amount": "spent"}),
            on="category",
            how="left",
        )
        budget_df = merged
        budget_df["spent"] = pd.to_numeric(budget_df["spent"], errors="coerce").fillna(0.0)

    budget_df["remaining"] = (budget_df["budget_amount"] - budget_df["spent"]).round(2)
    budget_df["progress_pct"] = budget_df.apply(
        lambda row: 0.0 if row["budget_amount"] == 0 else round((row["spent"] / row["budget_amount"]) * 100, 2),
        axis=1,
    )
    budget_df["overspent"] = budget_df["spent"] > budget_df["budget_amount"]
    budget_df["spent"] = budget_df["spent"].round(2)
    return budget_df[["category", "budget_amount", "spent", "remaining", "progress_pct", "overspent"]].sort_values("category")
