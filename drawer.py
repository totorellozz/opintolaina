import csv

import matplotlib.pyplot as plt

from cli import ask_inputs, euribor_get, MARGIN, FUND_FEE, DEBIT_FEE, ARRANGEMENT_FEE
from model import simulate

monthly_pay, growth, years_support, repayment_years, degree_credits = ask_inputs()

first_date, euribor12 = euribor_get()
print(f"Euribor {first_date} Rate: {euribor12}")
rate = euribor12 + MARGIN

rows, s = simulate(monthly_pay, years_support, repayment_years, rate, growth,
                   FUND_FEE, DEBIT_FEE, ARRANGEMENT_FEE, degree_credits)

months, loan_balance, investment_values, total_interests, remaining_loans = zip(*rows)

payoff = next((m for m, _, inv, _, out in rows if m > years_support * 12 and inv >= out), None)
if payoff:
    print(f"You could pay your loan off from the fund at month {payoff}!")

print(f"With a monthly loan of {monthly_pay}€, expected fund growth of {growth}% and {years_support} years of support, "
      f"repaid over {repayment_years} years:")
print(f"Monthly repayment ({s['repay_months']} instalments): {s['monthly_payment']:.2f}€")
print(f"Total loan amount disbursed: {s['disbursed']:.2f}€")
print(f"Loan compensation (lainahyvitys): {s['compensation']:.2f}€")
print(f"Total interest accrued: {s['total_interest']:.2f}€")
print(f"Total fees (arrangement + automatic debit): {s['total_fees']:.2f}€")
print(f"Total cost of the loan: {s['total_cost']:.2f}€")
print(f"Total value of investment: {s['investment']:.2f}€")
print(f"Net revenue from the opintolaina: {s['net_revenue']:.2f}€")
print(f"Taxed revenue from the opintolaina: {s['taxed_revenue']:.2f}€")
print(f"You made {s['taxed_revenue'] / s['disbursed']:.2f} X of your investment")

plt.figure(figsize=(10, 6))
plt.plot(months, loan_balance, label="Loan Disbursed (€)")
plt.plot(months, investment_values, label="Investment Value (€)")
plt.plot(months, total_interests, label="Total Interest (€)")
plt.plot(months, remaining_loans, label="Outstanding Loan (€)")
plt.xlabel("Months")
plt.ylabel("Amount (€)")
plt.title("Loan, Investment, and Interest Over Time")
plt.legend()
plt.grid()
plt.savefig("opintolaina.png", bbox_inches="tight")
plt.show()

headers = ["Month", "Loan Balance (€)", "Investment Value (€)", "Total Interest (€)", "Remaining Loan (€)"]
with open("opintolaina_data.csv", mode="w", newline="") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(headers)
    writer.writerows(rows)
