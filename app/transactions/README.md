# Transaction history (owner: Ayan)

Backend for the **Transactions** page of Waypoint / Simple Bank. Implements
`GET /api/accounts/{id}/transactions` from the project document, plus the filtering,
sorting, paging, monthly summary and CSV export the UI mockup needs.

## Run it

From the repo root:

```bash
python -m pip install -r requirements.txt
python -m app.transactions.seed                       # demo account 1024
uvicorn app.transactions.standalone:app --reload      # http://127.0.0.1:8000/docs
python -m pytest -q                                   # 28 tests
```

`standalone` runs just this feature. Once `app/main.py` is in place the feature is
mounted there instead (see "Mounting on the main app").

## Endpoints

All paths start with `/api/accounts/{accountId}/transactions`.

| Method | Path | Returns |
| --- | --- | --- |
| GET | `` | One page of history. Query params below. |
| GET | `/summary?month=YYYY-MM` | Deposits, withdrawals, net, count, spend by category, change vs last month. Defaults to the current month. |
| GET | `/categories` | Distinct categories on the account, for the filter dropdown. |
| GET | `/export` | Every matching row as a CSV download. Same filters as the list. |
| GET | `/{txnId}` | One transaction. |

Query parameters for the list and the export:

| Param | Example | Notes |
| --- | --- | --- |
| `type` | `DEPOSIT` / `WITHDRAW` | anything else is a 422 |
| `category` | `Food & Dining` | exact match, case-insensitive |
| `search` | `payroll` | substring of description or category |
| `from`, `to` | `2026-09-01` | inclusive dates |
| `sort` | `date` `amount` `type` `category` `id` | default `date` |
| `order` | `asc` / `desc` | default `desc` (newest first) |
| `page` | `1` | 1-based |
| `pageSize` | `20` | 1 to 100 |

Example list response:

```json
{
  "accountId": 1024,
  "page": 1, "pageSize": 20, "totalItems": 14, "totalPages": 1,
  "sort": "date", "order": "desc",
  "items": [
    {
      "txnId": 1048, "displayId": "TXN-1048", "accountId": 1024,
      "type": "WITHDRAW", "description": "Grocery Market", "category": "Food & Dining",
      "amount": 52.14, "signedAmount": -52.14, "balanceAfter": 2184.20,
      "date": "2026-09-14", "createdAt": "2026-09-14T13:33:00"
    }
  ]
}
```

Errors: unknown account is `404 {"detail": "Account 999 not found"}`. A bad query
value (page 0, `type=REFUND`, `from` after `to`) is `422` with a message.

## Mounting on the main app

In `app/main.py`, after `app = FastAPI(...)`:

```python
from .transactions import setup_transactions

setup_transactions(app)                                          # open
setup_transactions(app, dependencies=[Depends(get_current_user)])  # behind sign-in
```

That one call creates the tables, mounts the router and registers the 404/422
translations. Nothing else in `main.py` needs to change.

## How the deposit / withdraw feature records history

```python
from app.transactions.service import TransactionService
from app.transactions.repository import TransactionRepository
from app.transactions.models import TxnType

service = TransactionService(TransactionRepository(conn))
service.record(account_id, TxnType.WITHDRAW, amount, balance_after=new_balance,
               category="Food & Dining", description="Dinner with friends")
```

The caller owns the balance check and the `accounts.balance` update. This module only
appends the ledger row and refuses non-positive amounts or unknown accounts.

## How it is built, and why

```
router.py       Controller   HTTP in, JSON out. No logic.
service.py      Service      Page maths, month windows, CSV layout, rules.
repository.py   Repository   All SQL. Nothing else has SQL.
models.py       Model        The Transaction entity, one row of the table.
schemas.py      API shapes   What the JSON looks like (camelCase).
database.py                  Connection handling, table creation.
integration.py               setup_transactions() and create_app().
```

- **Feature package.** Everything for this page sits in `app/transactions/`, so four
  people can work on four pages without editing the same files. Each teammate's
  feature plugs into `main.py` with one line.
- **MVC layers, one per file.** This is the `Controller -> Service -> Repository -> Database`
  line from the project document. Each file has one reason to change: move to MySQL
  and only the repository changes; add a JSON field and only `schemas.py` changes.
- **FastAPI** because the document lists Swagger as a tool and FastAPI generates it
  from the code. Query-string validation is declarative, so bad input is rejected with
  a 422 before the service runs.
- **SQLite now, MySQL-ready.** MySQL is "to be confirmed". SQLite ships with Python and
  every query uses the SQL subset both databases accept. `schema.sql` at the repo root
  is the MySQL version for submission.
- **Ledger design.** Rows are appended, never edited. Each row stores `balance_after`,
  so the page shows a running balance like a bank statement in Excel. Sort, filter,
  search and export all operate on the same `WHERE` builder, so the count, the page
  and the CSV always agree.
- **Injection safety.** The sort key is looked up in a whitelist, never pasted into SQL.
- **Money as float, rounded to 2 places,** so JSON stays a plain number like the
  document's sample. A production bank would use `DECIMAL` / integer cents.
  `schema.sql` already uses `DECIMAL(10,2)`.

## Team integration notes

- The `accounts` table this feature checks against is the one in `schema.sql`. Account
  details (Andrew) should write to it. If the team keeps accounts in memory instead,
  change `account_exists()` in `repository.py` to ask that store.
- `bank.db` is a local file and should stay out of git (`*.db` in `.gitignore`).
- Import <http://127.0.0.1:8000/openapi.json> into Postman to build the collection for
  the submission.
