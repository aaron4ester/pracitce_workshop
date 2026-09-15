#Empty Username & Password Array
accounts = []


#-----------
# Menu Page
#-----------
def show_menu():
    print("\n=== Banking Application ===")
    print("1. Sign In")
    print("2. Create Account")
    print("3. Exit")


# Activates when trying to sign-in -> Looks for the existing username
def find_account(username):
    for account in accounts:
        if account["username"] == username:
            return account
    return None


#--------------------
# Create Account Page
#--------------------
def create_account():
    print("\n-- Create Account --")
    username = input("Choose a username: ").strip()

    # Checks if the selected username already exists
    if find_account(username):
        print("That username is already taken.")
        return

    # Passwords can be the same for multiple users
    password = input("Choose a password: ").strip()

    # Adds data to the array
    accounts.append({"username": username, "password": password})
    print(f"Account created for '{username}'. You can now sign in.")


#-------------
# Sign-In Page
#-------------
def sign_in():
    print("\n-- Sign In --")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    # Searches for existing account
    account = find_account(username)

    # Basic Security Feature: Input Password is the same as the existing username's password
    if account and account["password"] == password:
        dashboard(account)
    else:
        print("Invalid username or password.")

#-----------------------------------------------------
# After Signing In -> Takes user to the Dashboard Page
#-----------------------------------------------------
def dashboard(account):
    print(f"\nWelcome, {account['username']}!")
    print("(Dashboard not developed yet.)")


# Main - Will be replaced with a UI and buttons once we start working on front-end
def main():
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            sign_in()
        elif choice == "2":
            create_account()
        elif choice == "3":
            print("Exiting Program")
            break
        else:
            print("Invalid option, please try again.")


# Starts main program
if __name__ == "__main__":
    main()
