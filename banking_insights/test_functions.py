from banking_insights.insights_service import BankingInsightsService


service = BankingInsightsService()

print("account transactions")
print(service.get_account_transactions(1))

print("\nrecent summary")
print(service.get_recent_summary(1))

print("\nspending by category")
print(service.get_spending_by_category(1))

print("\nmonthly cash flow")
print(service.get_monthly_cash_flow(1))

print("\ntrends")
print(service.get_trends(1))

print("\nfull insights")
print(service.get_insights(1))