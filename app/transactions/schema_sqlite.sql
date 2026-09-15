-- Runtime schema for SQLite (applied automatically when the app starts).
-- The MySQL version the project document asks for lives in /schema.sql.
-- Both files describe the same three tables.

CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    balance       REAL NOT NULL DEFAULT 0,
    account_type  TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id     INTEGER NOT NULL,
    txn_type       TEXT NOT NULL CHECK (txn_type IN ('DEPOSIT', 'WITHDRAW')),
    amount         REAL NOT NULL CHECK (amount > 0),
    balance_after  REAL NOT NULL,                 -- running balance, like the balance column of a ledger sheet
    category       TEXT NOT NULL DEFAULT 'General',
    description    TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- Every history query filters by account and sorts by date, so index exactly that pair.
CREATE INDEX IF NOT EXISTS idx_transactions_account_date
    ON transactions (account_id, created_at);
