import sqlite3


USER_ACCOUNT_QUERY = """
    SELECT   
        u.user_id,        
        u.name,
        u.email,
        u.created_at AS user_created_at,
        a.account_id,
        a.account_type,
        a.balance,
        a.created_at AS account_created_at,
    FROM users u
    LEFT JOIN accounts a ON u.user_id = a.user_id
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


def get_account_details(user_id: int, db_path: str = ":memory:") -> dict | None:
    """Return account and account-holder details, or ``None`` if not found."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
    return _get_user_profile(conn, user_id)


def _get_user_profile(conn: sqlite3.Connection, user_id: int) -> dict | None:
    rows = conn.execute(USER_ACCOUNT_QUERY, (user_id,)).fetchall()
    if not rows:
        return None

    balance = float(rows[0]["balance"])
    first_row = rows[0]
    profile ={
        "account_id": first_row["account_id"],
        "name": first_row["name"],
        "email": first_row["email"],
        "user_created_at": first_row["user_created_at"],
        "accounts": [],
    }

    for row in rows:
        if row["account_id"] is not None:
            profile["accounts"].append(
                {
                    "account_id": row["account_id"],
                    "account_type": row["account_type"],
                    "balance": float(row["balance"]),
                    "account_created_at": row["account_created_at"],
                }
            )
    return profile


def create_sample_database() -> sqlite3.Connection:
    """Create and populate the in-memory database used by the example."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    users = [
        ("Jane Doe", "jane.doe@example.com", "Savings", 0.50, "2026-01-01 12:00:00", "2026-01-01 12:00:00"),
        ("John Smith", "john.smith@example.com", "Checking", 500.00, "2026-01-01 12:45:00", "2026-01-01 12:00:00"),
        ("Bane Boe", "bane.boe@example.com", "Credit", 2457.47, "2026-01-01 1:23:00", "2026-01-01 12:00:00"),
        ("Bohn Bmith", "bohn.bsmith@example.com", "Money Market", 500000.90, "2026-01-01 12:00:00", "2026-01-01 12:00:00"),
    ]
    for name, email, account_type, balance, account_created_at, user_created_at in users:
        user_id = conn.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)", (name, email, user_created_at)
        ).lastrowid
        conn.execute(
            "INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)",
            (user_id, account_type, balance, account_created_at),
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
    print(f"Account Created At : {details['account_created_at']}")
    print(f"User Created At    : {details['user_created_at']}")


def main() -> None:
    target_account_id = 2
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