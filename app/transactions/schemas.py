"""API schemas: the JSON shapes the frontend sees.

Kept separate from models.py on purpose.  The database row (model) and the JSON
response (schema) can evolve independently.  For example the schema adds
`displayId` and `signedAmount`, which are computed rather than stored.

Field names are snake_case in Python and camelCase in JSON (accountId,
pageSize, ...) to match the sample responses in the project document.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .models import Transaction, TxnType


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SortField(str, Enum):
    date = "date"
    amount = "amount"
    type = "type"
    category = "category"
    id = "id"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class TransactionOut(ApiModel):
    txn_id: int = Field(description="Database primary key")
    display_id: str = Field(description="Formatted ID for the UI, e.g. TXN-1048")
    account_id: int
    type: TxnType
    description: str
    category: str
    amount: float = Field(description="Always positive")
    signed_amount: float = Field(description="Negative for withdrawals, positive for deposits")
    balance_after: float = Field(description="Account balance right after this transaction")
    date: dt.date
    created_at: dt.datetime

    @classmethod
    def from_model(cls, txn: Transaction) -> TransactionOut:
        return cls(
            txn_id=txn.txn_id,
            display_id=txn.display_id,
            account_id=txn.account_id,
            type=txn.txn_type,
            description=txn.description,
            category=txn.category,
            amount=txn.amount,
            signed_amount=txn.signed_amount,
            balance_after=txn.balance_after,
            date=txn.created_at.date(),
            created_at=txn.created_at,
        )


class TransactionPage(ApiModel):
    """One page of results plus the numbers the UI needs to draw a pager."""

    account_id: int
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sort: SortField
    order: SortOrder
    items: list[TransactionOut]


class CategoryTotal(ApiModel):
    category: str
    total: float
    percent: float = Field(description="Share of this month's withdrawals, 0-100")


class TransactionSummary(ApiModel):
    """Feeds the three stat cards (deposits / withdrawals / net) and the Insights page."""

    account_id: int
    month: str = Field(description="YYYY-MM")
    deposits: float
    withdrawals: float
    net: float
    transaction_count: int
    previous_month_withdrawals: float
    spending_change_percent: float | None = Field(
        description="Withdrawals versus the previous month. Negative means spending went down. Null when there is no previous data."
    )
    by_category: list[CategoryTotal]
