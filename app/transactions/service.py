"""Service layer: business rules for transaction history.

The router hands this class plain Python values (account id, filters, page
number) and gets back schema objects ready to be serialised.  The service
decides *what* the history means (page maths, month boundaries, category
percentages, CSV layout).  It never touches SQL and never touches HTTP.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import math
from dataclasses import dataclass, field

from .models import Transaction, TxnType
from .repository import TransactionFilter, TransactionRepository
from .schemas import (
    CategoryTotal,
    SortField,
    SortOrder,
    TransactionOut,
    TransactionPage,
    TransactionSummary,
)


class AccountNotFoundError(LookupError):
    """Raised when the account id in the URL does not exist. Becomes a 404."""


class InvalidQueryError(ValueError):
    """Raised for requests that parse fine but make no sense. Becomes a 422."""


@dataclass(frozen=True)
class HistoryQuery:
    filters: TransactionFilter = field(default_factory=TransactionFilter)
    sort: SortField = SortField.date
    order: SortOrder = SortOrder.desc
    page: int = 1
    page_size: int = 20


CSV_COLUMNS = [
    "Transaction ID", "Date", "Type", "Description", "Category",
    "Amount", "Signed Amount", "Balance After",
]


class TransactionService:
    def __init__(self, repo: TransactionRepository) -> None:
        self.repo = repo

    # ---------------------------------------------------------------- history

    def get_history(self, account_id: int, query: HistoryQuery) -> TransactionPage:
        self._require_account(account_id)
        if query.filters.date_from and query.filters.date_to \
                and query.filters.date_from > query.filters.date_to:
            raise InvalidQueryError("'from' must be on or before 'to'")

        total = self.repo.count_by_account(account_id, query.filters)
        total_pages = max(1, math.ceil(total / query.page_size))
        offset = (query.page - 1) * query.page_size
        rows = self.repo.find_by_account(
            account_id,
            query.filters,
            sort=query.sort.value,
            order=query.order.value,
            limit=query.page_size,
            offset=offset,
        )
        return TransactionPage(
            account_id=account_id,
            page=query.page,
            page_size=query.page_size,
            total_items=total,
            total_pages=total_pages,
            sort=query.sort,
            order=query.order,
            items=[TransactionOut.from_model(t) for t in rows],
        )

    def get_transaction(self, account_id: int, txn_id: int) -> TransactionOut:
        self._require_account(account_id)
        txn = self.repo.find_one(account_id, txn_id)
        if txn is None:
            raise AccountNotFoundError(f"Transaction {txn_id} not found on account {account_id}")
        return TransactionOut.from_model(txn)

    def get_categories(self, account_id: int) -> list[str]:
        self._require_account(account_id)
        return self.repo.distinct_categories(account_id)

    # ---------------------------------------------------------------- summary

    def get_summary(self, account_id: int, month: str | None = None) -> TransactionSummary:
        self._require_account(account_id)
        start = _parse_month(month) if month else dt.date.today().replace(day=1)
        end = _next_month(start)
        prev_start = _previous_month(start)

        totals = self.repo.totals_between(account_id, start, end)
        deposits, dep_count = totals.get(TxnType.DEPOSIT, (0.0, 0))
        withdrawals, wd_count = totals.get(TxnType.WITHDRAW, (0.0, 0))

        prev_totals = self.repo.totals_between(account_id, prev_start, start)
        prev_withdrawals, _ = prev_totals.get(TxnType.WITHDRAW, (0.0, 0))
        change = None
        if prev_withdrawals > 0:
            change = round((withdrawals - prev_withdrawals) / prev_withdrawals * 100, 1)

        by_category = [
            CategoryTotal(
                category=name,
                total=total,
                percent=round(total / withdrawals * 100, 1) if withdrawals else 0.0,
            )
            for name, total in self.repo.withdrawals_by_category(account_id, start, end)
        ]

        return TransactionSummary(
            account_id=account_id,
            month=start.strftime("%Y-%m"),
            deposits=deposits,
            withdrawals=withdrawals,
            net=round(deposits - withdrawals, 2),
            transaction_count=dep_count + wd_count,
            previous_month_withdrawals=prev_withdrawals,
            spending_change_percent=change,
            by_category=by_category,
        )

    # ----------------------------------------------------------------- export

    def export_csv(
        self,
        account_id: int,
        filters: TransactionFilter,
        sort: SortField = SortField.date,
        order: SortOrder = SortOrder.desc,
    ) -> str:
        """Same filters as the history endpoint, but every row and as a spreadsheet."""
        self._require_account(account_id)
        rows = self.repo.find_by_account(account_id, filters, sort=sort.value, order=order.value)
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for t in rows:
            writer.writerow([
                t.display_id,
                t.created_at.date().isoformat(),
                t.txn_type.value,
                t.description,
                t.category,
                f"{t.amount:.2f}",
                f"{t.signed_amount:.2f}",
                f"{t.balance_after:.2f}",
            ])
        return buffer.getvalue()

    # ------------------------------------------------------------------ write

    def record(
        self,
        account_id: int,
        txn_type: TxnType,
        amount: float,
        balance_after: float,
        category: str = "General",
        description: str = "",
    ) -> Transaction:
        """Append one row to the ledger.

        Called by the deposit/withdraw feature *after* it has validated the
        amount against the balance and updated `accounts.balance`.  The new
        balance is passed in so the ledger row records it, which gives the
        history page its running-balance column.
        """
        self._require_account(account_id)
        if amount <= 0:
            raise InvalidQueryError("amount must be positive")
        return self.repo.add(
            account_id, txn_type, amount, balance_after,
            category=category or "General", description=description or "",
        )

    # ---------------------------------------------------------------- helpers

    def _require_account(self, account_id: int) -> None:
        if not self.repo.account_exists(account_id):
            raise AccountNotFoundError(f"Account {account_id} not found")


def _parse_month(value: str) -> dt.date:
    try:
        return dt.datetime.strptime(value, "%Y-%m").date()
    except ValueError as exc:
        raise InvalidQueryError("month must look like YYYY-MM") from exc


def _next_month(day: dt.date) -> dt.date:
    return day.replace(year=day.year + 1, month=1) if day.month == 12 \
        else day.replace(month=day.month + 1)


def _previous_month(day: dt.date) -> dt.date:
    return day.replace(year=day.year - 1, month=12) if day.month == 1 \
        else day.replace(month=day.month - 1)
