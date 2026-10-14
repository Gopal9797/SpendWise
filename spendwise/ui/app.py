"""Streamlit user interface for SpendWise."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from spendwise.analytics.metrics import (
    calculate_monthly_summary,
    calculate_spending_by_category,
    calculate_spending_trend,
    transactions_to_dataframe,
)
from spendwise.config import BASE_DIR, PAYMENT_METHODS
from spendwise.db.repository import SpendWiseRepository
from spendwise.services.budgets import build_budget_status, delete_budget, list_budgets, set_budget
from spendwise.services.csv_service import (
    export_transactions_to_csv,
    import_transactions_from_csv_bytes,
    import_transactions_from_dataframe,
)
from spendwise.services.transactions import (
    add_transaction,
    edit_transaction,
    remove_all_transactions,
    remove_transaction,
)
from spendwise.utils.currency import format_currency
from spendwise.utils.dates import month_key_from_date


@st.cache_resource
def get_repo() -> SpendWiseRepository:
    repo = SpendWiseRepository()
    repo.initialize()
    return repo


def _payment_method_options() -> list[str]:
    return sorted(PAYMENT_METHODS)


def _payment_method_label(method: str) -> str:
    return method.replace("_", " ").title()


def _parse_date_text(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _load_transactions(repo: SpendWiseRepository) -> tuple[list[dict[str, object]], pd.DataFrame]:
    transactions = repo.list_transactions()
    df = transactions_to_dataframe(transactions)
    return transactions, df


def _available_months(transaction_df: pd.DataFrame, budgets: list[dict[str, object]]) -> list[str]:
    months = {month_key_from_date(date.today())}

    if not transaction_df.empty and "transaction_date" in transaction_df.columns:
        valid_dates = transaction_df["transaction_date"].dropna()
        months.update(valid_dates.dt.to_period("M").astype(str).tolist())

    months.update(str(budget.get("month_key")) for budget in budgets if budget.get("month_key"))
    return sorted(months, reverse=True)


def _show_budget_progress_table(budget_status_df: pd.DataFrame) -> None:
    if budget_status_df.empty:
        st.info("No budgets set for this month yet.")
        return

    for _, row in budget_status_df.iterrows():
        category = str(row["category"])
        spent = float(row["spent"])
        budget_amount = float(row["budget_amount"])
        remaining = float(row["remaining"])
        progress_pct = float(row["progress_pct"])
        overspent = bool(row["overspent"])

        progress_value = 1.0 if budget_amount == 0 else min(spent / budget_amount, 1.0)

        st.markdown(
            f"**{category}** - {format_currency(spent)} / {format_currency(budget_amount)} "
            f"({progress_pct:.2f}%)"
        )
        st.progress(progress_value)

        if overspent:
            st.warning(f"Overspent in {category}: {format_currency(abs(remaining))} over budget.")
        else:
            st.caption(f"Remaining: {format_currency(remaining)}")


def render_dashboard(
    repo: SpendWiseRepository,
    transaction_df: pd.DataFrame,
    selected_month: str,
) -> None:
    st.subheader("Monthly Snapshot")
    summary = calculate_monthly_summary(transaction_df, selected_month)

    col1, col2, col3 = st.columns(3)
    col1.metric("Income", format_currency(summary["income"]))
    col2.metric("Expenses", format_currency(summary["expenses"]))
    col3.metric("Balance", format_currency(summary["balance"]))

    st.subheader("Spending by Category")
    spending_by_category = calculate_spending_by_category(transaction_df, selected_month)
    if spending_by_category.empty:
        st.info("No expense transactions found for this month.")
    else:
        figure = px.pie(
            spending_by_category,
            names="category",
            values="amount",
            title=f"Category Share - {selected_month}",
            hole=0.35,
        )
        st.plotly_chart(figure, use_container_width=True)
        st.dataframe(spending_by_category, use_container_width=True, hide_index=True)

    st.subheader("Spending Trend")
    trend_df = calculate_spending_trend(transaction_df, months=12)
    if trend_df.empty:
        st.info("Not enough transaction history yet to build a trend chart.")
    else:
        trend_long = trend_df.melt(
            id_vars=["month"],
            value_vars=["income", "expenses"],
            var_name="metric",
            value_name="amount",
        )
        trend_fig = px.line(
            trend_long,
            x="month",
            y="amount",
            color="metric",
            markers=True,
            title="Income vs Expenses (Last 12 Months)",
        )
        st.plotly_chart(trend_fig, use_container_width=True)

    st.subheader("Budget Progress")
    budget_status_df = build_budget_status(repo, selected_month, transaction_df)
    _show_budget_progress_table(budget_status_df)


def _build_payload(
    transaction_type: str,
    amount: float,
    transaction_date: date,
    category: str,
    description: str,
    payment_method: str,
) -> dict[str, object]:
    return {
        "transaction_type": transaction_type,
        "amount": amount,
        "date": transaction_date.isoformat(),
        "category": category,
        "description": description,
        "payment_method": payment_method,
    }


def _render_transaction_form(
    repo: SpendWiseRepository,
    form_key: str,
    submit_label: str,
    default_values: dict[str, object],
    transaction_id: int | None = None,
) -> None:
    payment_options = _payment_method_options()
    default_payment = str(default_values.get("payment_method", payment_options[0]))
    payment_index = payment_options.index(default_payment) if default_payment in payment_options else 0

    transaction_types = ["expense", "income"]
    default_type = str(default_values.get("transaction_type", "expense"))
    type_index = transaction_types.index(default_type) if default_type in transaction_types else 0

    with st.form(form_key):
        col1, col2, col3 = st.columns(3)
        transaction_type = col1.selectbox("Type", options=transaction_types, index=type_index)
        amount = col2.number_input(
            "Amount",
            min_value=0.0,
            step=100.0,
            value=float(default_values.get("amount", 0.0)),
            format="%.2f",
        )
        transaction_date = col3.date_input(
            "Date",
            value=default_values.get("transaction_date", date.today()),
            format="YYYY-MM-DD",
        )

        category = st.text_input("Category", value=str(default_values.get("category", "")))
        description = st.text_input("Description", value=str(default_values.get("description", "")))
        payment_method = st.selectbox(
            "Payment Method",
            options=payment_options,
            index=payment_index,
            format_func=_payment_method_label,
        )

        submitted = st.form_submit_button(submit_label)

    if not submitted:
        return

    payload = _build_payload(
        transaction_type=transaction_type,
        amount=amount,
        transaction_date=transaction_date,
        category=category,
        description=description,
        payment_method=payment_method,
    )

    try:
        if transaction_id is None:
            add_transaction(repo, payload)
            st.success("Transaction added.")
        else:
            updated = edit_transaction(repo, transaction_id, payload)
            if updated:
                st.success("Transaction updated.")
            else:
                st.error("Transaction not found.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))


def render_transactions_tab(repo: SpendWiseRepository, transaction_df: pd.DataFrame) -> None:
    st.subheader("Add Transaction")
    _render_transaction_form(
        repo=repo,
        form_key="add_transaction_form",
        submit_label="Add Transaction",
        default_values={
            "transaction_type": "expense",
            "amount": 0.0,
            "transaction_date": date.today(),
            "category": "",
            "description": "",
            "payment_method": "upi",
        },
    )

    st.subheader("View Transactions")
    if transaction_df.empty:
        st.info("No transactions yet. Add your first transaction above.")
    else:
        filtered_df = transaction_df.copy()

        col1, col2, col3 = st.columns(3)
        month_options = ["All"] + sorted(
            filtered_df["transaction_date"].dropna().dt.to_period("M").astype(str).unique().tolist(),
            reverse=True,
        )
        selected_month_filter = col1.selectbox("Month", options=month_options)

        type_options = ["All", "income", "expense"]
        selected_type_filter = col2.selectbox("Type", options=type_options)

        category_options = ["All"] + sorted(filtered_df["category"].dropna().astype(str).unique().tolist())
        selected_category_filter = col3.selectbox("Category", options=category_options)

        if selected_month_filter != "All":
            filtered_df = filtered_df[
                filtered_df["transaction_date"].dt.to_period("M").astype(str) == selected_month_filter
            ]
        if selected_type_filter != "All":
            filtered_df = filtered_df[filtered_df["transaction_type"] == selected_type_filter]
        if selected_category_filter != "All":
            filtered_df = filtered_df[filtered_df["category"] == selected_category_filter]

        if filtered_df.empty:
            st.info("No transactions match the selected filters.")
        else:
            display_df = filtered_df[
                [
                    "id",
                    "transaction_date",
                    "transaction_type",
                    "category",
                    "amount",
                    "payment_method",
                    "description",
                ]
            ].copy()
            display_df["transaction_date"] = display_df["transaction_date"].dt.strftime("%Y-%m-%d")
            display_df["payment_method"] = display_df["payment_method"].astype(str).map(_payment_method_label)
            display_df["amount"] = display_df["amount"].map(format_currency)

            st.dataframe(display_df, use_container_width=True, hide_index=True)

    raw_transactions = repo.list_transactions()
    if not raw_transactions:
        return

    st.subheader("Edit or Delete Transaction")

    option_map = {
        f"#{int(item['id'])} | {item['transaction_date']} | {item['category']} | {format_currency(float(item['amount']))}": item
        for item in raw_transactions
    }
    selected_label = st.selectbox("Select Transaction", options=list(option_map.keys()))
    selected = option_map[selected_label]

    default_values = {
        "transaction_type": selected["transaction_type"],
        "amount": float(selected["amount"]),
        "transaction_date": _parse_date_text(str(selected["transaction_date"])),
        "category": str(selected["category"]),
        "description": str(selected["description"]),
        "payment_method": str(selected["payment_method"]),
    }

    _render_transaction_form(
        repo=repo,
        form_key="edit_transaction_form",
        submit_label="Save Changes",
        default_values=default_values,
        transaction_id=int(selected["id"]),
    )

    confirm_delete = st.checkbox("I confirm that I want to delete this transaction.", key="confirm_delete")
    if st.button("Delete Transaction", type="secondary"):
        if not confirm_delete:
            st.error("Please confirm deletion first.")
        else:
            deleted = remove_transaction(repo, int(selected["id"]))
            if deleted:
                st.success("Transaction deleted.")
                st.rerun()
            else:
                st.error("Transaction not found.")

    st.divider()
    st.subheader("Reset transactions")
    st.caption("Permanently deletes all transactions. Budgets are not deleted.")
    confirm_delete_all = st.checkbox(
        "I understand this will permanently delete all transactions.",
        key="confirm_delete_all_transactions",
    )
    if st.button("Delete all transactions", type="secondary"):
        if not confirm_delete_all:
            st.error("Please confirm full deletion first.")
        else:
            deleted_count = remove_all_transactions(repo)
            st.success(f"Deleted {deleted_count} transactions.")
            st.rerun()


def render_budgets_tab(
    repo: SpendWiseRepository,
    selected_month: str,
    transaction_df: pd.DataFrame,
) -> None:
    st.subheader("Set Monthly Category Budget")

    with st.form("budget_form"):
        col1, col2, col3 = st.columns(3)
        month_date = col1.date_input("Month", value=date.today().replace(day=1), format="YYYY-MM-DD")
        category = col2.text_input("Category")
        budget_amount = col3.number_input("Budget Amount", min_value=0.0, step=100.0, format="%.2f")
        submitted = st.form_submit_button("Save Budget")

    if submitted:
        payload = {
            "month_key": month_date.strftime("%Y-%m"),
            "category": category,
            "budget_amount": budget_amount,
        }
        try:
            set_budget(repo, payload)
            st.success("Budget saved.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.subheader(f"Budget Status - {selected_month}")
    budget_status_df = build_budget_status(repo, selected_month, transaction_df)
    _show_budget_progress_table(budget_status_df)

    month_budgets = list_budgets(repo, month_key=selected_month)
    if month_budgets:
        st.subheader("Delete Budget")
        budget_option_map = {
            f"#{int(item['id'])} | {item['category']} | {format_currency(float(item['budget_amount']))}": item
            for item in month_budgets
        }
        selected_budget_label = st.selectbox("Select Budget", options=list(budget_option_map.keys()))
        selected_budget = budget_option_map[selected_budget_label]

        if st.button("Delete Budget", type="secondary"):
            deleted = delete_budget(repo, int(selected_budget["id"]))
            if deleted:
                st.success("Budget deleted.")
                st.rerun()
            else:
                st.error("Budget not found.")


def _load_demo_data(repo: SpendWiseRepository) -> None:
    demo_transactions_path = BASE_DIR / "data" / "demo_transactions.csv"
    demo_budgets_path = BASE_DIR / "data" / "demo_budgets.csv"

    if not demo_transactions_path.exists() or not demo_budgets_path.exists():
        st.error("Demo data files are missing from the data directory.")
        return

    demo_df = pd.read_csv(demo_transactions_path)
    import_result = import_transactions_from_dataframe(repo, demo_df)

    budget_df = pd.read_csv(demo_budgets_path)
    budget_errors: list[str] = []
    budget_added = 0

    for row_index, row in budget_df.iterrows():
        payload = {
            "month_key": row.get("month_key"),
            "category": row.get("category"),
            "budget_amount": row.get("budget_amount"),
        }
        try:
            set_budget(repo, payload)
            budget_added += 1
        except ValueError as exc:
            budget_errors.append(f"Budget row {row_index + 2}: {exc}")

    st.success(
        "Demo import complete: "
        f"{import_result.inserted_count} transactions inserted, "
        f"{import_result.duplicate_count} duplicates skipped, "
        f"{import_result.invalid_count} invalid rows. "
        f"{budget_added} budgets upserted."
    )

    for error in import_result.errors + budget_errors:
        st.error(error)


def render_csv_tab(repo: SpendWiseRepository) -> None:
    st.subheader("Import Transactions CSV")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if st.button("Import CSV"):
        if uploaded_file is None:
            st.error("Please choose a CSV file first.")
        else:
            result = import_transactions_from_csv_bytes(repo, uploaded_file.getvalue())
            st.success(
                f"Imported: {result.inserted_count}, "
                f"Duplicates skipped: {result.duplicate_count}, "
                f"Invalid rows: {result.invalid_count}"
            )
            if result.errors:
                st.error("Import errors:")
                for error in result.errors:
                    st.write(f"- {error}")
            st.rerun()

    st.subheader("Export Transactions CSV")
    csv_data = export_transactions_to_csv(repo)
    st.download_button(
        label="Download Transactions CSV",
        data=csv_data,
        file_name=f"spendwise_transactions_{date.today().isoformat()}.csv",
        mime="text/csv",
    )

    st.subheader("Load Fictional Demo Data")
    st.caption("Adds sample transactions and budgets from the data folder.")
    if st.button("Load Demo Data"):
        _load_demo_data(repo)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="SpendWise", layout="wide")
    st.title("SpendWise - Personal Expense Tracker")

    repo = get_repo()
    all_budgets = repo.list_budgets()
    _, transaction_df = _load_transactions(repo)

    months = _available_months(transaction_df, all_budgets)
    selected_month = st.sidebar.selectbox("Reporting Month", options=months)

    dashboard_tab, transactions_tab, budgets_tab, csv_tab = st.tabs(
        ["Dashboard", "Transactions", "Budgets", "CSV Import/Export"]
    )

    with dashboard_tab:
        render_dashboard(repo, transaction_df, selected_month)

    with transactions_tab:
        render_transactions_tab(repo, transaction_df)

    with budgets_tab:
        render_budgets_tab(repo, selected_month, transaction_df)

    with csv_tab:
        render_csv_tab(repo)


if __name__ == "__main__":
    main()
