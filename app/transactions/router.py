"""Controller layer: the REST endpoints for transaction history.

This file only translates HTTP into service calls and back.  Query strings are
parsed and validated here by FastAPI (a bad page number never reaches the
service), then the result object is serialised to JSON automatically.

Base path, from the project document:  /api/accounts/{id}/transactions
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from .database import get_db
from .models import TxnType
from .repository import TransactionFilter, TransactionRepository
from .schemas import SortField, SortOrder, TransactionOut, TransactionPage, TransactionSummary
from .service import HistoryQuery, TransactionService

router = APIRouter(prefix="/api/accounts/{account_id}/transactions", tags=["Transactions"])


# --------------------------------------------------------------- dependencies

def get_service(conn: Annotated[sqlite3.Connection, Depends(get_db)]) -> TransactionService:
    """Wire the layers together for one request: connection -> repository -> service."""
    return TransactionService(TransactionRepository(conn))


def history_filters(
    txn_type: Annotated[TxnType | None, Query(alias="type", description="DEPOSIT or WITHDRAW")] = None,
    category: Annotated[str | None, Query(max_length=50, description="Exact category, case-insensitive")] = None,
    search: Annotated[str | None, Query(max_length=100, description="Substring match on description or category")] = None,
    date_from: Annotated[dt.date | None, Query(alias="from", description="Inclusive start date, YYYY-MM-DD")] = None,
    date_to: Annotated[dt.date | None, Query(alias="to", description="Inclusive end date, YYYY-MM-DD")] = None,
) -> TransactionFilter:
    return TransactionFilter(
        txn_type=txn_type, category=category, search=search,
        date_from=date_from, date_to=date_to,
    )


ServiceDep = Annotated[TransactionService, Depends(get_service)]
FiltersDep = Annotated[TransactionFilter, Depends(history_filters)]
SortDep = Annotated[SortField, Query(description="Column to sort by")]
OrderDep = Annotated[SortOrder, Query(description="asc or desc")]


# ------------------------------------------------------------------ endpoints

@router.get(
    "",
    response_model=TransactionPage,
    summary="Transaction history (filterable, sortable, paged)",
)
def list_transactions(
    account_id: int,
    service: ServiceDep,
    filters: FiltersDep,
    sort: SortDep = SortField.date,
    order: OrderDep = SortOrder.desc,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> TransactionPage:
    query = HistoryQuery(filters=filters, sort=sort, order=order, page=page, page_size=page_size)
    return service.get_history(account_id, query)


@router.get(
    "/summary",
    response_model=TransactionSummary,
    summary="Monthly totals: deposits, withdrawals, net, spend by category",
)
def transaction_summary(
    account_id: int,
    service: ServiceDep,
    month: Annotated[
        str | None,
        Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM, defaults to the current month"),
    ] = None,
) -> TransactionSummary:
    return service.get_summary(account_id, month)


@router.get(
    "/categories",
    response_model=list[str],
    summary="Distinct categories used on this account (for the filter dropdown)",
)
def transaction_categories(account_id: int, service: ServiceDep) -> list[str]:
    return service.get_categories(account_id)


@router.get(
    "/export",
    summary="Download the history as a CSV file that opens in Excel",
    responses={200: {"content": {"text/csv": {}}, "description": "CSV file"}},
)
def export_transactions(
    account_id: int,
    service: ServiceDep,
    filters: FiltersDep,
    sort: SortDep = SortField.date,
    order: OrderDep = SortOrder.desc,
) -> Response:
    csv_text = service.export_csv(account_id, filters, sort=sort, order=order)
    filename = f"account-{account_id}-transactions.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{txn_id}", response_model=TransactionOut, summary="One transaction by id")
def get_transaction(account_id: int, txn_id: int, service: ServiceDep) -> TransactionOut:
    return service.get_transaction(account_id, txn_id)
