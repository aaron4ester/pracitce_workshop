"""Load demo data that matches the UI mockup: account 1024, Alisa Katsionova.

Run from the repo root:
    python -m app.transactions.seed              # wipes and reloads bank.db
    python -m app.transactions.seed --db x.db    # use another file

The September rows are the exact ones in the "08 - Transactions" mockup
(TXN-1042 .. TXN-1048).  August rows exist so date filters and the
"compared with last month" number have something to work with.  The opening
deposit is computed so the running balance ends at $2,184.20, the balance the
mockup shows on the dashboard.
"""

from __future__ import annotations

import argparse
import datetime as dt

from .database import DEFAULT_DB_PATH, connect, init_db
from .models import TxnType
from .repository import TransactionRepository

DEMO_USER = {"user_id": 1, "name": "Alisa Katsionova", "email": "alisa@example.com"}
DEMO_ACCOUNT_ID = 1024
DEMO_ACCOUNT_TYPE = "CHECKING"
FINAL_BALANCE = 2184.20
FIRST_TXN_ID = 1035  # opening deposit; 6 August rows follow, so September lands on 1042-1048

D, W = TxnType.DEPOSIT, TxnType.WITHDRAW

# (timestamp, type, amount, category, description) oldest first
DEMO_TRANSACTIONS = [
    ("2026-08-05T12:14:00", W, 64.30,  "Food & Dining",  "Grocery Market"),
    ("2026-08-12T09:00:00", D, 500.00, "Income",         "Payroll Deposit"),
    ("2026-08-15T17:42:00", W, 42.00,  "Transportation", "Gas Station"),
    ("2026-08-20T20:05:00", W, 89.99,  "Shopping",       "Online Store"),
    ("2026-08-26T09:00:00", D, 500.00, "Income",         "Payroll Deposit"),
    ("2026-08-29T06:30:00", W, 15.49,  "Entertainment",  "Streaming Service"),
    ("2026-09-08T15:20:00", W, 38.90,  "Shopping",       "Book Store"),        # TXN-1042
    ("2026-09-09T11:05:00", D, 250.00, "Income",         "Cash Deposit"),      # TXN-1043
    ("2026-09-10T18:47:00", W, 24.10,  "Transportation", "Ride Share"),        # TXN-1044
    ("2026-09-11T08:12:00", W, 7.25,   "Food & Dining",  "Coffee Shop"),       # TXN-1045
    ("2026-09-12T06:30:00", W, 15.49,  "Entertainment",  "Streaming Service"), # TXN-1046
    ("2026-09-13T09:00:00", D, 500.00, "Income",         "Payroll Deposit"),   # TXN-1047
    ("2026-09-14T13:33:00", W, 52.14,  "Food & Dining",  "Grocery Market"),    # TXN-1048
]


def seed(db_path: str = DEFAULT_DB_PATH, reset: bool = True) -> None:
    init_db(db_path)
    conn = connect(db_path)
    try:
        if reset:
            # Child rows first so the foreign keys stay happy.
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM accounts")
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM sqlite_sequence")

        conn.execute(
            "INSERT INTO users (user_id, name, email, created_at) VALUES (?, ?, ?, ?)",
            (DEMO_USER["user_id"], DEMO_USER["name"], DEMO_USER["email"], "2026-08-01T09:00:00"),
        )
        conn.execute(
            "INSERT INTO accounts (account_id, user_id, balance, account_type, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (DEMO_ACCOUNT_ID, DEMO_USER["user_id"], FINAL_BALANCE, DEMO_ACCOUNT_TYPE, "2026-08-01T09:00:00"),
        )
        conn.commit()

        net_of_rest = sum(a if t is D else -a for _, t, a, _, _ in DEMO_TRANSACTIONS)
        opening = round(FINAL_BALANCE - net_of_rest, 2)
        rows = [("2026-08-01T09:05:00", D, opening, "Income", "Opening deposit")] + DEMO_TRANSACTIONS

        repo = TransactionRepository(conn)
        balance = 0.0
        for i, (when, txn_type, amount, category, description) in enumerate(rows):
            balance = round(balance + (amount if txn_type is D else -amount), 2)
            repo.add(
                DEMO_ACCOUNT_ID, txn_type, amount, balance, category, description,
                created_at=dt.datetime.fromisoformat(when), txn_id=FIRST_TXN_ID + i,
            )

        assert balance == FINAL_BALANCE, f"running balance {balance} != {FINAL_BALANCE}"
        print(f"Seeded {len(rows)} transactions for account {DEMO_ACCOUNT_ID} into {db_path}")
        print(f"Closing balance: ${balance:,.2f}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite file to load (default: bank.db)")
    parser.add_argument("--keep", action="store_true", help="Do not wipe existing rows first")
    args = parser.parse_args()
    seed(args.db, reset=not args.keep)
