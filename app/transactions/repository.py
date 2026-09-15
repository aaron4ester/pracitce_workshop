"""Repository layer: the only place in this feature that talks SQL.

The service above it never sees a cursor or a WHERE clause, and the router
above that never sees the repository at all.  This is the "Repository" box in
the project document's architecture line:

    Controller -> Service -> Repository -> Database

Every query starts with `account_id = ?` so one account can never read another
account's history.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from .models import Transaction, TxnType

# Whitelist of sortable columns. The sort key from the URL is looked up here and
# never pasted into SQL directly, which is what keeps ORDER BY injection-safe.
SORT_COLUMNS = {
    "date": "created_at",
    "amount": "amount",
    "type": "txn_type",
    "category": "category",
    "id": "txn_id",
}


@dataclass(frozen=True)
class TransactionFilter:
    """Everything the user can narrow the history by. All fields optional."""

    txn_type: TxnType | None = None
    category: str | None = None
    search: str | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None


class TransactionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ------------------------------------------------------------------ reads

    def account_exists(self, account_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        return row is not None

    def find_by_account(
        self,
        account_id: int,
        filters: TransactionFilter,
        sort: str = "date",
        order: str = "desc",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Transaction]:
        where, params = self._where(account_id, filters)
        column = SORT_COLUMNS[sort]
        direction = "ASC" if order == "asc" else "DESC"
        # txn_id as a tie-breaker keeps paging stable when two rows share a date/amount.
        sql = (
            f"SELECT * FROM transactions WHERE {where} "
            f"ORDER BY {column} {direction}, txn_id {direction}"
        )
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params += [limit, offset]
        rows = self.conn.execute(sql, params).fetchall()
        return [Transaction.from_row(r) for r in rows]

    def count_by_account(self, account_id: int, filters: TransactionFilter) -> int:
        where, params = self._where(account_id, filters)
        row = self.conn.execute(
            f"SELECT COUNT(*) AS n FROM transactions WHERE {where}", params
        ).fetchone()
        return int(row["n"])

    def find_one(self, account_id: int, txn_id: int) -> Transaction | None:
        row = self.conn.execute(
            "SELECT * FROM transactions WHERE account_id = ? AND txn_id = ?",
            (account_id, txn_id),
        ).fetchone()
        return Transaction.from_row(row) if row else None

    def totals_between(
        self, account_id: int, start: dt.date, end: dt.date
    ) -> dict[TxnType, tuple[float, int]]:
        """Sum and count per type for start <= created_at < end."""
        rows = self.conn.execute(
            """
            SELECT txn_type, SUM(amount) AS total, COUNT(*) AS n
            FROM transactions
            WHERE account_id = ? AND created_at >= ? AND created_at < ?
            GROUP BY txn_type
            """,
            (account_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return {TxnType(r["txn_type"]): (round(r["total"], 2), int(r["n"])) for r in rows}

    def withdrawals_by_category(
        self, account_id: int, start: dt.date, end: dt.date
    ) -> list[tuple[str, float]]:
        rows = self.conn.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE account_id = ? AND txn_type = 'WITHDRAW'
              AND created_at >= ? AND created_at < ?
            GROUP BY category
            ORDER BY total DESC, category ASC
            """,
            (account_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [(r["category"], round(r["total"], 2)) for r in rows]

    def distinct_categories(self, account_id: int) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT category FROM transactions WHERE account_id = ? ORDER BY category",
            (account_id,),
        ).fetchall()
        return [r["category"] for r in rows]

    # ----------------------------------------------------------------- writes

    def add(
        self,
        account_id: int,
        txn_type: TxnType,
        amount: float,
        balance_after: float,
        category: str = "General",
        description: str = "",
        *,
        created_at: dt.datetime | None = None,
        txn_id: int | None = None,
    ) -> Transaction:
        """Insert one ledger row and return it.

        This is the write path the deposit/withdraw feature calls after it has
        updated the account balance.  `created_at` and `txn_id` are only meant
        for seeding and tests; normal calls leave them unset.
        """
        created = (created_at or dt.datetime.now()).isoformat(timespec="seconds")
        cur = self.conn.execute(
            """
            INSERT INTO transactions
                (txn_id, account_id, txn_type, amount, balance_after, category, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (txn_id, account_id, txn_type.value, round(amount, 2), round(balance_after, 2),
             category, description, created),
        )
        self.conn.commit()
        inserted = self.find_one(account_id, cur.lastrowid)
        assert inserted is not None
        return inserted

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _where(account_id: int, f: TransactionFilter) -> tuple[str, list]:
        """Build the WHERE clause once so listing and counting always agree."""
        clauses = ["account_id = ?"]
        params: list = [account_id]

        if f.txn_type is not None:
            clauses.append("txn_type = ?")
            params.append(f.txn_type.value)
        if f.category:
            clauses.append("lower(category) = lower(?)")
            params.append(f.category)
        if f.search:
            clauses.append("(lower(description) LIKE ? OR lower(category) LIKE ?)")
            term = f"%{f.search.lower()}%"
            params += [term, term]
        if f.date_from is not None:
            clauses.append("created_at >= ?")
            params.append(f.date_from.isoformat())
        if f.date_to is not None:
            # "to" is inclusive: anything before midnight of the following day.
            clauses.append("created_at < ?")
            params.append((f.date_to + dt.timedelta(days=1)).isoformat())

        return " AND ".join(clauses), params
