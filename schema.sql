-- Simple Bank / Waypoint: MySQL schema (submission requirement "SQL script").
-- Matches section 4.1 of the project document, plus three columns on
-- `transactions` that the transaction-history page needs:
--   balance_after  running balance shown per row, like a ledger sheet
--   category       "Food & Dining", "Income", ... used for filters and insights
--   description    "Grocery Market", "Payroll Deposit", ... shown in the table
--
-- The backend currently runs on SQLite using app/transactions/schema_sqlite.sql,
-- which is the same design in SQLite syntax.

CREATE DATABASE IF NOT EXISTS simple_bank;
USE simple_bank;

CREATE TABLE IF NOT EXISTS users (
    user_id     INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(100) NOT NULL UNIQUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id    INT PRIMARY KEY AUTO_INCREMENT,
    user_id       INT NOT NULL,
    balance       DECIMAL(10,2) NOT NULL DEFAULT 0,
    account_type  VARCHAR(50) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id         INT PRIMARY KEY AUTO_INCREMENT,
    account_id     INT NOT NULL,
    txn_type       VARCHAR(20) NOT NULL,
    amount         DECIMAL(10,2) NOT NULL,
    balance_after  DECIMAL(10,2) NOT NULL,
    category       VARCHAR(50) NOT NULL DEFAULT 'General',
    description    VARCHAR(255) NOT NULL DEFAULT '',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    CONSTRAINT chk_txn_type CHECK (txn_type IN ('DEPOSIT', 'WITHDRAW')),
    CONSTRAINT chk_amount_positive CHECK (amount > 0)
);

-- The history page always asks "rows for this account, newest first".
CREATE INDEX idx_transactions_account_date ON transactions (account_id, created_at);
