monthly_pay = int(input("Your monthly support from the state (€): "))
expected_fund_growth = int(input("Expected yearly growth of your investment fund (%): "))
years_support = int(input("Length of your support from the state (years): "))
marginal_rate = float(input("Bank's marginal interest rate (%): "))
months_payed = int(input("How many months do you get paid a year (number): "))
debit_fee = float(input("Automatic debit fee per payment (€): "))
arrangement_fee = float(input("Loan arrangement fee (€): "))
state_support = input("Does your state support your loan by 40% (if you finish studies on time, y/n): ")

real_interest_rate = 2.448 + marginal_rate
monthly_interest_rate = real_interest_rate / 100 / 12
monthly_growth_rate = (1 + (expected_fund_growth / 100)) ** (1 / 12) - 1

total_loan = 0
total_interest = 0
total_fund = 0
current_investment = 0
investment_growth = 0
month_counter = 1


for year in range(years_support):
    for month in range(1, 13):  
        if month <= months_payed:
            total_loan += monthly_pay
            current_investment += monthly_pay
            print(f"Loan month {month_counter}: {total_loan}€")
        
        total_interest += total_loan * monthly_interest_rate
        print(f"Interest for month {month_counter}: {total_interest:.2f}€")
        
        investment_growth += current_investment * monthly_growth_rate
        current_investment += current_investment * monthly_growth_rate
        
        month_counter += 1

total_fees = debit_fee * months_payed * years_support + arrangement_fee
total_cost = total_loan + total_interest + total_fees

total_fund_value = current_investment + investment_growth

net_revenue = total_fund_value - total_cost

if net_revenue>=30000:
    taxed_revenue = net_revenue * 0.66
else:
    taxed_revenue = net_revenue * 0.70



print(f"Total loan amount disbursed: {total_loan:.2f}€")
print(f"Total interest accrued: {total_interest:.2f}€")
print(f"Total fees (arrangement + automatic debit): {total_fees:.2f}€")
print(f"Total cost of the loan: {total_cost:.2f}€")
print(f"Total value of investment after {years_support} years: {total_fund_value:.2f}€")
print(f"Net revenue from the opintolaina: {net_revenue:.2f}€")
print(f"Taxed revenue from the opintolaina: {taxed_revenue:.2f}€")