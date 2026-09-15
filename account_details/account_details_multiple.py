import sqlite3

USER_ACCOUNTS_QUERY = """
    SELECT
        u.user_id,
        u.name,
        u.email,
        u.created_at AS user_created_at,
        a.account_id,
        a.account_type,
        a.balance,
        a.created_at AS account_created_at
    FROM users u
    LEFT JOIN accounts a ON u.user_id = a.user_id
    WHERE u.user_id = ?;
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


def get_user_profile(user_id: int, db_path: str = ":memory:") -> dict | None:
    """Return user profile and all associated accounts, or ``None`` if not found."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return _get_user_profile(conn, user_id)


def _get_user_profile(conn: sqlite3.Connection, user_id: int) -> dict | None:
    rows = conn.execute(USER_ACCOUNTS_QUERY, (user_id,)).fetchall()
    if not rows:
        return None

    first_row = rows[0]
    profile = {
        "user_id": first_row["user_id"],
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

    # Insert Users
    user1_id = conn.execute(
        "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
        ("Jane Doe", "jane.doe@example.com", "2026-01-01 12:00:00"),
    ).lastrowid

    user2_id = conn.execute(
        "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
        ("John Smith", "john.smith@example.com", "2026-01-01 12:00:00"),
    ).lastrowid

    user3_id = conn.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
            ("Bob Roberts", "bob.roberts@example.com", "2026-01-01 12:00:00"),
        ).lastrowid

    user4_id = conn.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
            ("Alice Johnson", "alice.johnson@example.com", "2026-01-01 12:00:00"),
        ).lastrowid

    # Insert Multiple Accounts for Jane Doe (user1_id)
    conn.execute(
        "INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)",
        (user1_id, "Checking", 1250.50, "2026-01-01 12:30:00"),
    )
    conn.execute(
        "INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)",
        (user1_id, "Savings", 5000.00, "2026-01-02 09:15:00"),
    )

    # Insert Single Account for John Smith (user2_id)
    conn.execute(
        "INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)",
        (user2_id, "Money Market", 500000.90, "2026-01-01 12:45:00"),
    )

    conn.execute(
        "INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)",
        (user4_id, "Money Market", 500000.90, "2026-01-01 12:45:00"),
    )
    conn.execute(
       "INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)",
       (user4_id, "Money Market", 500000.90, "2026-01-01 12:45:00"),
    )
    conn.execute(
        "INSERT INTO accounts (user_id, account_type, balance, created_at) VALUES (?, ?, ?, ?)",
        (user4_id, "Money Market", 500000.90, "2026-01-01 12:45:00"),
    )

    conn.commit()
    return conn


def print_user_profile(profile: dict | None, user_id: int) -> None:
    """Print user details and all associated accounts."""
    if profile is None:
        print(f"User #{user_id} not found.")
        return

    print(f"--- Results for User #{user_id} ---")
    print(f"User ID        : {profile['user_id']}")
    print(f"Name           : {profile['name']}")
    print(f"Email          : {profile['email']}")
    print(f"User Registered: {profile['user_created_at']}")
    print(f"Accounts ({len(profile['accounts'])}):")

    if not profile["accounts"]:
        print("  No accounts found.")
        return

    for acc in profile["accounts"]:
        print(
            f"  - Account #{acc['account_id']} [{acc['account_type']}]: "
            f"${acc['balance']:,.2f} (Opened: {acc['account_created_at']})"
        )


def main() -> None:
    target_user_id = 3
    conn = create_sample_database()
    try:
        conn.row_factory = sqlite3.Row
        print_user_profile(_get_user_profile(conn, target_user_id), target_user_id)
    finally:
        conn.close()


if __name__ == "__main__":
    main()