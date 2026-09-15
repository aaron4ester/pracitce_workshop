"""Shared fixtures: every test gets a fresh, seeded SQLite file in a temp folder."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.transactions import create_app
from app.transactions.database import connect
from app.transactions.repository import TransactionRepository
from app.transactions.seed import DEMO_ACCOUNT_ID, seed
from app.transactions.service import TransactionService

ACCOUNT = DEMO_ACCOUNT_ID
BASE = f"/api/accounts/{ACCOUNT}/transactions"


@pytest.fixture
def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    seed(path)
    return path


@pytest.fixture
def client(db_path) -> TestClient:
    app = create_app(db_path)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def service(db_path) -> TransactionService:
    conn = connect(db_path)
    try:
        yield TransactionService(TransactionRepository(conn))
    finally:
        conn.close()
