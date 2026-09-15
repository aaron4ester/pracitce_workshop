"""Model layer: the Transaction entity exactly as it is stored in the database.

This is the "M" in MVC.  It knows nothing about HTTP or JSON.  It is a plain
Python object that mirrors one row of the `transactions` table.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from enum import Enum


class TxnType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


@dataclass(frozen=True)
class Transaction:
    txn_id: int
    account_id: int
    txn_type: TxnType
    amount: float
    balance_after: float
    category: str
    description: str
    created_at: dt.datetime

    @property
    def display_id(self) -> str:
        """Human-friendly ID shown in the UI mockup, e.g. TXN-1048."""
        return f"TXN-{self.txn_id}"

    @property
    def signed_amount(self) -> float:
        """Deposits are positive, withdrawals negative (what a ledger column shows)."""
        return self.amount if self.txn_type is TxnType.DEPOSIT else -self.amount

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Transaction:
        return cls(
            txn_id=row["txn_id"],
            account_id=row["account_id"],
            txn_type=TxnType(row["txn_type"]),
            amount=round(row["amount"], 2),
            balance_after=round(row["balance_after"], 2),
            category=row["category"],
            description=row["description"],
            created_at=_parse_timestamp(row["created_at"]),
        )


def _parse_timestamp(value: str) -> dt.datetime:
    # SQLite's CURRENT_TIMESTAMP looks like "YYYY-MM-DD HH:MM:SS"; our own inserts use ISO 8601.
    return dt.datetime.fromisoformat(value.replace(" ", "T"))
