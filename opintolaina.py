import requests
from bs4 import BeautifulSoup

monthly_pay = int(input("Your monthly support from the state (€): "))
expected_fund_growth = float(input("Expected yearly growth of your investment fund (%): "))
years_support = int(input("Length of your support from the state (years): "))
repayment = input("Do you have a program of repayment to the state yet? (y/n): ")

repayment_years = None 

if repayment == "y":
    while True:
        try:
            repayment_years = int(input("Great! In how many years do you pay it back? (MAX 30): "))
            if repayment_years <= 30:
                print(f"Great! You will pay it back in {repayment_years} years.")
                break  
            else:
                print("Nope, the maximum repayment period is 30 years. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
else:
    print("No repayment program selected.")

print(f"Repayment years: {repayment_years}") 

act_repayment_years = repayment_years - years_support
print(f"actual years of repayment: {act_repayment_years}")

print("------")
marginal_rate = 0.5
fund_fee = 1.5
debit_fee = 2.5
arrangement_fee = 10


url = "https://www.euribor-rates.eu/en/euribor-rates-by-year/"

response = requests.get(url)

def euribor_get():
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        euribor_row = soup.find('a', title="Euribor 12 months").find_parent('tr')
        
        dates = [header.get_text(strip=True) for header in euribor_row.find_parent('table').find('thead').find_all('th')[1:]]
        rates = [data.get_text(strip=True) for data in euribor_row.find_all('td')]
        
        euribor_12m_rates = dict(zip(dates, rates))
        return euribor_12m_rates
    
euribor_12m_rates = euribor_get()

first_date, first_rate = next(iter(euribor_12m_rates.items()))

euribor12 = float(first_rate.strip('%'))

print(f"Euribor {first_date} Rate: {euribor12}")



real_interest_rate = euribor12 + marginal_rate + fund_fee
monthly_interest_rate = real_interest_rate / 100 / 12
monthly_growth_rate = (1 + (expected_fund_growth / 100)) ** (1 / 12) - 1

total_loan = 0
total_interest = 0
current_investment = 0
investment_growth = 0
month_counter = 1
half_year_pay = monthly_pay * 4.5 

for year in range(years_support):
    for month in range(1, 13):
        if month == 1 or month == 7:
            total_loan += half_year_pay
            current_investment += half_year_pay
            print(f"Loan disbursed in month {month_counter}: {total_loan}€")

        one_month_interest = total_loan * monthly_interest_rate
        total_interest += one_month_interest

        current_investment += current_investment * monthly_growth_rate 
        investment_growth = current_investment * monthly_growth_rate
        
        print(f"Interest for month {month_counter}: {one_month_interest:.2f}€ \nInterest in total {total_interest:.2f}€"
              f"\nInvestments in total {current_investment:.2f}€ \nInvestments this month {investment_growth:.2f}€")

        month_counter += 1
    
    print("------")


remaining_loan = total_loan
monthly_repayment = (total_loan * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** (-act_repayment_years * 12))


print(f"Total interest accrued: {total_interest:.2f}€")
print(f"Total value of investment after {years_support} years: {current_investment:.2f}€")

print("\n--- Repayment Schedule ---")
for month in range(1, act_repayment_years * 12 + 1):
    monthly_interest = remaining_loan * monthly_interest_rate

    if monthly_repayment <= monthly_interest:
        print("WARNING: Monthly repayment is insufficient to cover the interest. Loan will never be repaid.")
        break

    remaining_loan += monthly_interest
    remaining_loan -= monthly_repayment
    total_interest += monthly_interest

    current_investment += current_investment * monthly_growth_rate
    current_investment -= monthly_interest

    print(f"Month {month}: Loan payed this month: €{monthly_repayment:.2f}, Remaining Loan: €{remaining_loan:.2f}, "
          f"Interest Charged: €{monthly_interest:.2f}, Investment Value: €{current_investment:.2f}, Total interests: €{total_interest:.2f}")


total_fees = 2 * years_support * debit_fee + arrangement_fee * years_support 
total_cost = total_loan + total_interest + total_fees
net_revenue = current_investment - total_cost

if net_revenue >= 30000:
    taxed_revenue = net_revenue * 0.66
else:
    taxed_revenue = net_revenue * 0.70

if repayment == "y":
    print(f"Total value of investment after {repayment_years} years: {current_investment:.2f}€")
else:
    print(f"Total investments: {current_investment:.2f}€")

print(f"Total loan amount disbursed: {total_loan:.2f}€")
print(f"Total interest accrued: {total_interest:.2f}€")
print(f"Total fees (arrangement + automatic debit): {total_fees:.2f}€")
print(f"Total cost of the loan: {total_cost:.2f}€")
print(f"Net revenue from the opintolaina: {net_revenue:.2f}€")
print(f"Taxed revenue from the opintolaina: {taxed_revenue:.2f}€")

