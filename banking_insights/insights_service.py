# import libraries
from datetime import date, timedelta

from banking_insights.sample_data import transactions

class BankingInsightsService:

    # get all the account transactions made under a specific account_id
    def get_account_transactions(self, account_id: int) -> list[dict]:

        account_transactions = []

        for transaction in transactions:
            if account_id == transaction["account_id"]:
                account_transactions.append(transaction)

        return account_transactions

    # helper function to get date in yyyy-mm format
    def get_month_key(self, year: int, month: int) -> str:

        return f"{year}-{month:02d}"

    # get the last six months for the monthly cash flow chart
    def get_last_six_months(self) -> list[dict]:

        today = date.today()

        months = []

        for offset in range(5, -1, -1):

            month = today.month - offset
            year = today.year

            while month <= 0:
                month += 12
                year -= 1

            month_key = self.get_month_key(year, month)
            month_label = date(year, month, 1).strftime("%b")

            months.append({
                "key": month_key,
                "label": month_label,
            })

        return months

    # get deposits, withdrawals, and net change for the last 30 days
    def get_recent_summary(self, account_id: int, days: int = 30) -> dict:

        account_transactions = self.get_account_transactions(account_id)

        today = date.today()
        start_date =  today - timedelta(days=days)

        # only keep transactions inside the recent date range
        recent_transactions = []

        for transaction in account_transactions:

            transaction_date = date.fromisoformat(transaction["created_at"])

            if start_date <= transaction_date <= today:
                recent_transactions.append(transaction)

        deposit_count = 0
        withdrawal_count = 0
        total_deposits = 0
        total_withdrawals = 0

        # count and total deposits and withdrawals
        for transaction in recent_transactions:

            if transaction["txn_type"] == "DEPOSIT":
                total_deposits += transaction["amount"]
                deposit_count += 1
            elif transaction["txn_type"] == "WITHDRAWAL":
                total_withdrawals += transaction["amount"]
                withdrawal_count += 1

        net_change = total_deposits - total_withdrawals
            
        return {
            "period_days": days,
            "transaction_count": len(recent_transactions),
            "deposit_count": deposit_count,
            "withdrawal_count": withdrawal_count,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "net_change": net_change,
        }

    # group recent withdrawals by spending category
    def get_spending_by_category(self, account_id: int, days: int = 30) -> list[dict]:
            
        account_transactions = self.get_account_transactions(account_id)

        today = date.today()
        start_date =  today - timedelta(days=days)

        category_totals = {
            "Food & Dining": 0,
            "Shopping" : 0,
            "Entertainment": 0,
            "Transportation": 0,
            "Bills": 0,
            "Other": 0,
        }

        total_spending = 0

        # add withdrawal amounts into their matching categories
        for transaction in account_transactions:

            transaction_date = date.fromisoformat(transaction["created_at"])

            if start_date <= transaction_date <= today and transaction["txn_type"] == "WITHDRAWAL":

                category = transaction["category"]
                amount= transaction["amount"]

                category_totals[category] += amount
                total_spending += amount

        if total_spending == 0:
            return []
        
        spending_by_category = []

        # convert category totals into chart-friendly percentages
        for category, amount in category_totals.items():

            if amount > 0: 

                percentage = (amount / total_spending) * 100

                spending_by_category.append({
                    "category": category,
                    "amount": amount,
                    "percentage": round(percentage, 2),
                })

        return spending_by_category

    # get deposit and withdrawal totals for each of the last six months
    def get_monthly_cash_flow(self, account_id: int) -> list[dict]:

        account_transactions = self.get_account_transactions(account_id)
        last_six_months = self.get_last_six_months()

        cash_flow_by_month = {}

        # create an empty bucket for each month
        for month in last_six_months:
            cash_flow_by_month[month["key"]] = {
                "month": month["label"],
                "deposits": 0,
                "withdrawals": 0,
            }

        for transaction in account_transactions:

            transaction_date = date.fromisoformat(transaction["created_at"])
            month_key = self.get_month_key(transaction_date.year, transaction_date.month)

            if month_key in cash_flow_by_month:
                if transaction["txn_type"] == "DEPOSIT":
                    cash_flow_by_month[month_key]["deposits"] += transaction["amount"]
                elif transaction["txn_type"] == "WITHDRAWAL":
                    cash_flow_by_month[month_key]["withdrawals"] += transaction["amount"]

        return list(cash_flow_by_month.values())

    # compare current month spending to previous month spending
    def get_trends(self, account_id: int) -> dict:

        account_transactions = self.get_account_transactions(account_id)

        today = date.today()

        current_month_key = self.get_month_key(today.year, today.month)

        # find the previous month, including the january edge case
        previous_month = today.month - 1
        previous_year = today.year

        if previous_month == 0:
            previous_month = 12
            previous_year -= 1

        previous_month_key = self.get_month_key(previous_year,previous_month)

        current_category_totals = {
            "Food & Dining": 0,
            "Shopping": 0,
            "Entertainment": 0,
            "Transportation": 0,
            "Bills": 0,
            "Other": 0,
        }
        current_total_spending = 0
        previous_total_spending = 0
        average_weekly_spend = 0

        # track current month categories and previous month total spending
        for transaction in account_transactions:

            transaction_date = date.fromisoformat(transaction["created_at"])
            transaction_month_key = self.get_month_key(transaction_date.year, transaction_date.month)

            if transaction["txn_type"] != "WITHDRAWAL":
                continue

            if transaction_month_key == current_month_key:
                category = transaction["category"]
                amount = transaction["amount"]

                current_category_totals[category] += amount
                current_total_spending += transaction["amount"]

            elif transaction_month_key == previous_month_key:

                previous_total_spending += transaction["amount"]

        # find the highest current month spending category
        top_spending_category = max(
            current_category_totals,
            key=current_category_totals.get
        )

        top_spending_amount = current_category_totals[top_spending_category]

        # avoid dividing by zero if there is no previous month spending
        if previous_total_spending == 0:
            spending_change_percent = None
        else:
            spending_change_percent = (
                (current_total_spending - previous_total_spending)
                / previous_total_spending
            ) * 100

        average_weekly_spend = current_total_spending / 4

        return {
            "current_total_spending" : current_total_spending,
            "previous_total_spending": previous_total_spending,
            "spending_change_percent": (
                None
                if spending_change_percent is None
                else round(spending_change_percent, 2)
            ),
            "average_weekly_spend": round(average_weekly_spend, 2),
            "top_spending_category": top_spending_category,
            "top_spending_amount": top_spending_amount,
        }

    # combine all insight sections into one response
    def get_insights(self, account_id: int) -> dict:
        return {
            "account_id": account_id,
            "summary": self.get_recent_summary(account_id),
            "spending_by_category": self.get_spending_by_category(account_id),
            "monthly_cash_flow": self.get_monthly_cash_flow(account_id),
            "trends": self.get_trends(account_id),
        }



