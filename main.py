accounts = []


def show_menu():
    print("\n=== Banking Application ===")
    print("1. Sign In")
    print("2. Create Account")
    print("3. Exit")


def find_account(username):
    for account in accounts:
        if account["username"] == username:
            return account
    return None


def create_account():
    print("\n-- Create Account --")
    username = input("Choose a username: ").strip()

    if find_account(username):
        print("That username is already taken.")
        return

    password = input("Choose a password: ").strip()

    accounts.append({"username": username, "password": password})
    print(f"Account created for '{username}'. You can now sign in.")


def sign_in():
    print("\n-- Sign In --")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    account = find_account(username)
    if account and account["password"] == password:
        dashboard(account)
    else:
        print("Invalid username or password.")


def dashboard(account):
    print(f"\nWelcome, {account['username']}!")
    print("(Dashboard not developed yet.)")


def main():
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            sign_in()
        elif choice == "2":
            create_account()
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid option, please try again.")


if __name__ == "__main__":
    main()
