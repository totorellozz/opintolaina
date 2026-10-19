from cli import ask_inputs, euribor_get, save_outputs, MARGIN, DEBIT_FEE, ARRANGEMENT_FEE
from model import simulate

i = ask_inputs()

first_date, euribor12 = euribor_get()
print(f"Euribor {first_date} Rate: {euribor12}")
rate = euribor12 + MARGIN

rows, s = simulate(i.monthly_pay, i.years_support, i.repayment_years, rate, i.growth, i.fund_fee,
                   DEBIT_FEE, ARRANGEMENT_FEE, i.degree_credits,
                   i.starting_pot, i.living_cost_yearly, i.kela_grant)

for r in rows:
    print(f"Month {r.month}: disbursed {r.disbursed:.2f}€, outstanding loan {r.outstanding:.2f}€, "
          f"interest total {r.total_interest:.2f}€, investment {r.investment:.2f}€, "
          f"in hand {r.in_hand:.2f}€, grant received {r.grant_total:.2f}€")

payoff = next((r.month for r in rows
               if r.month > i.years_support * 12 and r.investment >= r.outstanding), None)
if payoff:
    print(f"You could pay your loan off from the fund at month {payoff}!")

print(f"\nMonthly repayment ({s['repay_months']} instalments): {s['monthly_payment']:.2f}€")
print(f"Total loan amount disbursed: {s['disbursed']:.2f}€")
print(f"Loan compensation (lainahyvitys): {s['compensation']:.2f}€")
print(f"Total interest accrued: {s['total_interest']:.2f}€")
print(f"Total fees (arrangement + automatic debit): {s['total_fees']:.2f}€")
print(f"Total cost of the loan: {s['total_cost']:.2f}€")
print(f"Kela grant received: {s['grant_total']:.2f}€")
print(f"Living costs taken from the fund: {s['living_withdrawn']:.2f}€")
if s["living_shortfall"] > 0:
    print(f"WARNING: fund ran dry, {s['living_shortfall']:.2f}€ of living costs were not covered")
print(f"In hand (investment minus loan costs): {s['net_revenue']:.2f}€")
print(f"Capital income tax on fund sales: {s['tax']:.2f}€ "
      f"(living-cost sales during studies {s['study_tax']:.2f}€ + final sale {s['final_tax']:.2f}€)")
print(f"In hand after tax: {s['taxed_revenue']:.2f}€")
print(f"\nPot + loan, total value of the fund: {s['investment']:.2f}€")
print(f"What you win (after loan costs and tax, living costs added back, minus your own pot): {s['win']:.2f}€")
if s["disbursed"]:
    print(f"You made {s['win'] / s['disbursed']:.2f} X of your loan")

save_outputs(rows)
