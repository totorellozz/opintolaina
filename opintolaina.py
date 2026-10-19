from cli import ask_inputs, euribor_get, MARGIN, FUND_FEE, DEBIT_FEE, ARRANGEMENT_FEE
from model import simulate

monthly_pay, growth, years_support, repayment_years, degree_credits = ask_inputs()

first_date, euribor12 = euribor_get()
print(f"Euribor {first_date} Rate: {euribor12}")
rate = euribor12 + MARGIN

rows, s = simulate(monthly_pay, years_support, repayment_years, rate, growth,
                   FUND_FEE, DEBIT_FEE, ARRANGEMENT_FEE, degree_credits)

for month, disbursed, investment, interest, outstanding in rows:
    print(f"Month {month}: disbursed {disbursed:.2f}€, outstanding loan {outstanding:.2f}€, "
          f"interest total {interest:.2f}€, investment {investment:.2f}€")

print(f"\nMonthly repayment ({s['repay_months']} instalments): {s['monthly_payment']:.2f}€")
print(f"Total loan amount disbursed: {s['disbursed']:.2f}€")
print(f"Loan compensation (lainahyvitys): {s['compensation']:.2f}€")
print(f"Total interest accrued: {s['total_interest']:.2f}€")
print(f"Total fees (arrangement + automatic debit): {s['total_fees']:.2f}€")
print(f"Total cost of the loan: {s['total_cost']:.2f}€")
print(f"Total value of investment: {s['investment']:.2f}€")
print(f"Net revenue from the opintolaina: {s['net_revenue']:.2f}€")
print(f"Capital income tax on fund gain: {s['tax']:.2f}€")
print(f"Taxed revenue from the opintolaina: {s['taxed_revenue']:.2f}€")
