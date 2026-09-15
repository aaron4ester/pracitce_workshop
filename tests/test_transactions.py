"""Behavioural tests for the transaction-history API.

Numbers below come straight from app/transactions/seed.py:
  14 rows total (1 opening deposit, 6 in August, 7 in September)
  September: deposits 750.00, withdrawals 137.88, net 612.12
  August:    withdrawals 211.78
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.transactions import setup_transactions
from app.transactions.models import TxnType
from app.transactions.seed import seed
from app.transactions.service import AccountNotFoundError, InvalidQueryError
from tests.conftest import ACCOUNT, BASE


# ------------------------------------------------------------------- listing

def test_history_defaults_to_newest_first(client):
    r = client.get(BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["accountId"] == ACCOUNT
    assert body["totalItems"] == 14
    assert body["totalPages"] == 1
    assert body["items"][0]["displayId"] == "TXN-1048"
    assert body["items"][-1]["description"] == "Opening deposit"


def test_row_shape_matches_the_mockup_columns(client):
    row = client.get(BASE).json()["items"][0]
    assert row == {
        "txnId": 1048,
        "displayId": "TXN-1048",
        "accountId": ACCOUNT,
        "type": "WITHDRAW",
        "description": "Grocery Market",
        "category": "Food & Dining",
        "amount": 52.14,
        "signedAmount": -52.14,
        "balanceAfter": 2184.20,
        "date": "2026-09-14",
        "createdAt": "2026-09-14T13:33:00",
    }


def test_running_balance_ends_at_dashboard_total(client):
    newest = client.get(BASE).json()["items"][0]
    assert newest["balanceAfter"] == 2184.20


def test_pagination(client):
    page1 = client.get(BASE, params={"pageSize": 4, "page": 1}).json()
    page4 = client.get(BASE, params={"pageSize": 4, "page": 4}).json()
    assert page1["totalPages"] == 4
    assert len(page1["items"]) == 4
    assert len(page4["items"]) == 2            # 14 rows = 4 + 4 + 4 + 2
    assert page1["items"][0]["txnId"] == 1048
    assert page4["items"][-1]["txnId"] == 1035


def test_page_beyond_the_end_is_empty_not_an_error(client):
    body = client.get(BASE, params={"page": 99}).json()
    assert body["items"] == []
    assert body["totalItems"] == 14


# ------------------------------------------------------------------- filters

def test_filter_by_type(client):
    deposits = client.get(BASE, params={"type": "DEPOSIT"}).json()
    assert deposits["totalItems"] == 5
    assert {i["type"] for i in deposits["items"]} == {"DEPOSIT"}


def test_filter_by_category_is_case_insensitive(client):
    body = client.get(BASE, params={"category": "food & dining"}).json()
    assert body["totalItems"] == 3
    assert {i["category"] for i in body["items"]} == {"Food & Dining"}


def test_search_matches_description(client):
    body = client.get(BASE, params={"search": "payroll"}).json()
    assert body["totalItems"] == 3
    assert all("Payroll" in i["description"] for i in body["items"])


def test_date_range_is_inclusive_on_both_ends(client):
    september = client.get(BASE, params={"from": "2026-09-01", "to": "2026-09-30"}).json()
    assert september["totalItems"] == 7

    single_day = client.get(BASE, params={"from": "2026-09-10", "to": "2026-09-10"}).json()
    assert single_day["totalItems"] == 1
    assert single_day["items"][0]["description"] == "Ride Share"


def test_filters_combine(client):
    body = client.get(
        BASE, params={"type": "WITHDRAW", "from": "2026-09-01", "search": "market"}
    ).json()
    assert body["totalItems"] == 1
    assert body["items"][0]["txnId"] == 1048


def test_from_after_to_is_rejected(client):
    r = client.get(BASE, params={"from": "2026-09-30", "to": "2026-09-01"})
    assert r.status_code == 422


# ------------------------------------------------------------------- sorting

def test_sort_by_amount_ascending(client):
    body = client.get(BASE, params={"sort": "amount", "order": "asc"}).json()
    amounts = [i["amount"] for i in body["items"]]
    assert amounts == sorted(amounts)
    assert body["items"][0]["description"] == "Coffee Shop"


def test_sort_by_category(client):
    body = client.get(BASE, params={"sort": "category", "order": "asc"}).json()
    cats = [i["category"] for i in body["items"]]
    assert cats == sorted(cats)


def test_unknown_sort_column_is_rejected(client):
    assert client.get(BASE, params={"sort": "created_at; DROP TABLE"}).status_code == 422


# ------------------------------------------------------------ error handling

def test_unknown_account_is_404(client):
    r = client.get("/api/accounts/999999/transactions")
    assert r.status_code == 404
    assert "999999" in r.json()["detail"]


def test_bad_page_values_are_422(client):
    assert client.get(BASE, params={"page": 0}).status_code == 422
    assert client.get(BASE, params={"pageSize": 101}).status_code == 422
    assert client.get(BASE, params={"type": "REFUND"}).status_code == 422


# ------------------------------------------------------------------- summary

def test_summary_for_september(client):
    body = client.get(f"{BASE}/summary", params={"month": "2026-09"}).json()
    assert body["month"] == "2026-09"
    assert body["deposits"] == 750.00
    assert body["withdrawals"] == 137.88
    assert body["net"] == 612.12
    assert body["transactionCount"] == 7
    assert body["previousMonthWithdrawals"] == 211.78
    assert body["spendingChangePercent"] == -34.9

    by_cat = {c["category"]: c for c in body["byCategory"]}
    assert by_cat["Food & Dining"]["total"] == 59.39
    assert by_cat["Shopping"]["total"] == 38.90
    assert sum(c["percent"] for c in body["byCategory"]) == pytest.approx(100, abs=0.2)


def test_summary_month_with_no_previous_data(client):
    body = client.get(f"{BASE}/summary", params={"month": "2026-08"}).json()
    assert body["withdrawals"] == 211.78
    assert body["spendingChangePercent"] is None


def test_summary_rejects_bad_month(client):
    assert client.get(f"{BASE}/summary", params={"month": "2026-13"}).status_code == 422
    assert client.get(f"{BASE}/summary", params={"month": "Sept"}).status_code == 422


# ---------------------------------------------------------------- categories

def test_categories_are_distinct_and_sorted(client):
    r = client.get(f"{BASE}/categories")
    assert r.json() == ["Entertainment", "Food & Dining", "Income", "Shopping", "Transportation"]


# -------------------------------------------------------------------- export

def test_csv_export_has_header_and_every_row(client):
    r = client.get(f"{BASE}/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "account-1024-transactions.csv" in r.headers["content-disposition"]

    lines = r.text.strip().splitlines()
    assert lines[0] == "Transaction ID,Date,Type,Description,Category,Amount,Signed Amount,Balance After"
    assert len(lines) == 1 + 14
    assert lines[1] == "TXN-1048,2026-09-14,WITHDRAW,Grocery Market,Food & Dining,52.14,-52.14,2184.20"


def test_csv_export_respects_filters(client):
    r = client.get(f"{BASE}/export", params={"type": "DEPOSIT", "from": "2026-09-01"})
    lines = r.text.strip().splitlines()
    assert len(lines) == 1 + 2
    assert all(",DEPOSIT," in line for line in lines[1:])


# ------------------------------------------------------------ single row

def test_get_single_transaction(client):
    r = client.get(f"{BASE}/1047")
    assert r.status_code == 200
    assert r.json()["description"] == "Payroll Deposit"


def test_single_transaction_from_another_account_is_hidden(client):
    assert client.get(f"{BASE}/1").status_code == 404


# --------------------------------------------- write hook for deposit/withdraw

def test_record_appends_to_the_ledger(service, client):
    txn = service.record(ACCOUNT, TxnType.DEPOSIT, 100.0, balance_after=2284.20,
                         category="Income", description="Refund")
    assert txn.display_id == "TXN-1049"

    body = client.get(BASE).json()
    assert body["totalItems"] == 15
    assert body["items"][0]["description"] == "Refund"
    assert body["items"][0]["balanceAfter"] == 2284.20


def test_record_rejects_non_positive_amounts(service):
    with pytest.raises(InvalidQueryError):
        service.record(ACCOUNT, TxnType.WITHDRAW, 0, balance_after=2184.20)


def test_record_rejects_unknown_account(service):
    with pytest.raises(AccountNotFoundError):
        service.record(42, TxnType.DEPOSIT, 10, balance_after=10)


# ------------------------------------------- mounting on the team's main app

def test_setup_can_require_a_signed_in_user(tmp_path):
    """Mirrors how app/main.py will mount the feature behind Aaron's auth gate."""
    db = str(tmp_path / "gate.db")
    seed(db)

    def fake_current_user(authorization: str | None = None):
        if authorization != "Bearer good-token":
            raise HTTPException(status_code=401, detail="nope")

    app = FastAPI()
    setup_transactions(app, db_path=db, dependencies=[Depends(fake_current_user)])
    with TestClient(app) as c:
        assert c.get(BASE).status_code == 401
        ok = c.get(BASE, params={"authorization": "Bearer good-token"})
        assert ok.status_code == 200
        assert ok.json()["totalItems"] == 14
