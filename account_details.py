import sqlite3


ACCOUNT_QUERY = """
    SELECT
        a.account_id,
        u.name,
        u.email,
        a.account_type,
        a.balance,
        a.created_at AS account_created_at,
        u.created_at AS user_created_at
    FROM accounts a
    JOIN users u ON a.user_id = u.user_id
    WHERE a.account_id = ?;
"""

SCHEMA = """
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE accounts (
        account_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        account_type TEXT,
        balance REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
"""

INTEREST_RATES = {
    "savings": 0.02,
    "checking": 0.01,
    "money market": 0.015,
    "credit": 0.05,
}


def fetch_current_interest_rate(account_type: str) -> float:
    """Return the current interest rate for an account type."""
    return INTEREST_RATES.get(account_type, 0.0)


def get_account_details(account_id: int, db_path: str = ":memory:") -> dict | None:
    """Return account and account-holder details, or ``None`` if not found."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
    return _get_account_details(conn, account_id)

def _get_account_details(conn: sqlite3.Connection, account_id: int) -> dict | None:
    row = conn.execute(ACCOUNT_QUERY, (account_id,)).fetchone()
    if row is None:
        return None

    balance = float(row["balance"])
    interest_rate = fetch_current_interest_rate(row["account_type"])
    return {
        "account_id": row["account_id"],
        "name": row["name"],
        "email": row["email"],
        "account_type": row["account_type"],
        "balance": balance,
        "interest_rate": interest_rate,
        "annual_yield": round(balance * interest_rate, 2),
        "account_created_at": row["account_created_at"],
        "user_created_at": row["user_created_at"],
    }


def create_sample_database() -> sqlite3.Connection:
    """Create and populate the in-memory database used by the example."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    users = [
        ("Jane Doe", "jane.doe@example.com", "savings", 0.50),
        ("John Smith", "john.smith@example.com", "checking", 500.00),
        ("Bane Boe", "bane.boe@example.com", "credit", 2457.47),
        ("Bohn Bmith", "bohn.bsmith@example.com", "savings", 500000.90),
    ]
    for name, email, account_type, balance in users:
        user_id = conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", (name, email)
        ).lastrowid
        conn.execute(
            "INSERT INTO accounts (user_id, account_type, balance) VALUES (?, ?, ?)",
            (user_id, account_type, balance),
        )
    conn.commit()
    return conn


def print_account_details(details: dict | None, account_id: int) -> None:
    """Print account details for the command-line example."""
    if details is None:
        print(f"Account #{account_id} not found.")
        return

    print(f"--- Results for Account #{account_id} ---")
    print(f"Account ID         : {details['account_id']}")
    print(f"Name               : {details['name']}")
    print(f"Email              : {details['email']}")
    print(f"Type               : {details['account_type']}")
    print(f"Balance            : ${details['balance']:.2f}")
    print(f"Interest Rate      : {details['interest_rate'] * 100:.2f}%")
    print(f"Annual Yield       : ${details['annual_yield']:.2f}")
    print(f"Account Created At : {details['account_created_at']}")
    print(f"User Created At    : {details['user_created_at']}")


def main() -> None:
    target_account_id = 3
    conn = create_sample_database()
    try:
        conn.row_factory = sqlite3.Row
        print_account_details(
            _get_account_details(conn, target_account_id), target_account_id
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()