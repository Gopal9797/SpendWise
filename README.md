# SpendWise

SpendWise is a personal expense tracker built with Python, Streamlit, SQLite, Pandas, and Plotly.

Technical deep-dive documentation for architecture, control flow, and diagrams:

- [docs/TECHNICAL_WALKTHROUGH.md](docs/TECHNICAL_WALKTHROUGH.md)

It supports:

- Monthly dashboard (income, expenses, balance, category mix, trends)
- Transaction CRUD (add, edit, view, delete)
- Category-wise monthly budgets with progress and overspending alerts
- CSV import/export with validation and duplicate-import protection
- SQLite persistence
- Unit tests with pytest

## Proposed File Structure

```text
SpendWise/
  app.py
  dev.ps1
  requirements.txt
  requirements-dev.txt
  README.md
  .gitignore
  .github/
    workflows/
      pytest.yml
  data/
    demo_transactions.csv
    demo_budgets.csv
  spendwise/
    __init__.py
    config.py
    models.py
    analytics/
      __init__.py
      metrics.py
    db/
      __init__.py
      connection.py
      repository.py
      schema.py
    services/
      __init__.py
      transactions.py
      budgets.py
      csv_service.py
    ui/
      __init__.py
      app.py
    utils/
      __init__.py
      currency.py
      dates.py
      validation.py
  tests/
    test_metrics.py
    test_budget_logic.py
    test_csv_service.py
```

## Database Schema

The SQLite schema is defined in `spendwise/db/schema.py` and has two core tables.

### transactions

- `id` (PK)
- `transaction_type` (`income` or `expense`)
- `amount` (non-negative)
- `transaction_date` (`YYYY-MM-DD` text)
- `category`
- `description`
- `payment_method`
- `dedupe_key` (unique, used for CSV duplicate protection)
- `created_at`, `updated_at`

Indexes:

- `idx_transactions_date`
- `idx_transactions_category`
- `idx_transactions_type`

### budgets

- `id` (PK)
- `month_key` (`YYYY-MM`)
- `category`
- `budget_amount` (non-negative)
- `created_at`, `updated_at`

Constraints:

- `UNIQUE(month_key, category)` to upsert monthly category budgets

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements-dev.txt
```

Or, on Windows PowerShell:

```powershell
.\dev.ps1 install
```

## PowerShell Command Helper

For quick local commands on Windows, use [dev.ps1](dev.ps1):

```powershell
.\dev.ps1 run
.\dev.ps1 test
.\dev.ps1 reset-db
.\dev.ps1 reset-transactions
```

`reset-transactions` deletes all transaction rows while keeping budgets and the database file.

You can also pass a specific Python executable:

```powershell
.\dev.ps1 test -PythonPath "C:\Path\To\python.exe"
```

## Run the App

```bash
streamlit run app.py
```

Or:

```powershell
.\dev.ps1 run
```

Then open the local URL shown by Streamlit.

## Run Tests

```bash
pytest -q
```

Or:

```powershell
.\dev.ps1 test
```

## Demo Data

Use the **CSV Import/Export** tab and click **Load Demo Data** to load fictional sample transactions and budgets from:

- `data/demo_transactions.csv`
- `data/demo_budgets.csv`

## Default Currency

The default currency symbol is Indian rupee (`₹`) via `DEFAULT_CURRENCY_SYMBOL` in `spendwise/config.py`.

## Notes

- No bank credentials, paid APIs, or external AI services are required.
- Input validation handles malformed files and empty datasets gracefully.
- Do not store personal financial data in the repository.

## CI

GitHub Actions workflow in `.github/workflows/pytest.yml` installs dependencies and runs pytest on push and pull requests.
