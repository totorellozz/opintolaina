import csv
import os
import subprocess
import sys

import matplotlib
import requests
from bs4 import BeautifulSoup

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from model import MAX_MONTHLY_LOAN, COMP_MAX_COUNTED

MARGIN = 0.5            # bank margin, %; typical (Nordea example 2026)
FUND_FEE = 1.5          # yearly fund charge, % (deducted from fund growth, not a loan cost)
DEBIT_FEE = 2.5         # per repayment instalment, EUR
ARRANGEMENT_FEE = 10    # one-off, EUR
DEFAULT_REPAYMENT_YEARS = 15


def euribor_get():
    response = requests.get("https://www.euribor-rates.eu/en/euribor-rates-by-year/", timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    row = soup.find("a", title="Euribor 12 months").find_parent("tr")
    dates = [th.get_text(strip=True) for th in row.find_parent("table").find("thead").find_all("th")[1:]]
    rates = [td.get_text(strip=True) for td in row.find_all("td")]
    first_date, first_rate = next(iter(dict(zip(dates, rates)).items()))
    return first_date, float(first_rate.strip("%"))


def ask_inputs():
    monthly_pay = int(input(f"Your monthly loan from the state (€, max {MAX_MONTHLY_LOAN}): "))
    if monthly_pay > MAX_MONTHLY_LOAN:
        print(f"State guarantee covers max {MAX_MONTHLY_LOAN}€/month, using that.")
        monthly_pay = MAX_MONTHLY_LOAN
    growth = float(input("Expected yearly growth of your investment fund (%): "))
    years_support = int(input("Length of your support from the state (years): "))
    repayment = input("Do you have a program of repayment to the state yet? (y/n): ")

    repayment_years = DEFAULT_REPAYMENT_YEARS
    if repayment == "y":
        while True:
            try:
                repayment_years = int(input("In how many years do you pay it back, counted from the start of studies? (MAX 30): "))
            except ValueError:
                print("Invalid input. Please enter a number.")
                continue
            if repayment_years <= 30:
                break
            print("Nope, the guarantee lasts 30 years. Please try again.")
    else:
        print(f"No repayment program selected, assuming {repayment_years} years.")

    on_time = input("Will you graduate within the lainahyvitys deadline (first degree, y/n): ")
    degree_credits = None
    if on_time == "y":
        degree_credits = int(input(f"Degree size in credits {sorted(COMP_MAX_COUNTED)}: "))
        if degree_credits not in COMP_MAX_COUNTED:
            raise SystemExit(f"Degree size must be one of {sorted(COMP_MAX_COUNTED)}")

    return monthly_pay, growth, years_support, repayment_years, degree_credits


def open_file(path):
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.run(["xdg-open", path], check=False)


def save_outputs(rows, png="opintolaina.png", csv_path="opintolaina_data.csv"):
    """Write the chart and CSV from simulate() rows, then open both."""
    months, disbursed, investment, interest, outstanding, in_hand = zip(*rows)

    plt.figure(figsize=(10, 6))
    plt.plot(months, disbursed, label="Loan Disbursed (€)")
    plt.plot(months, investment, label="Investment Value (€)")
    plt.plot(months, interest, label="Total Interest (€)")
    plt.plot(months, outstanding, label="Outstanding Loan (€)")
    plt.plot(months, in_hand, label="In Hand (€)")
    plt.xlabel("Months")
    plt.ylabel("Amount (€)")
    plt.title("Loan, Investment, and Interest Over Time")
    plt.legend()
    plt.grid()
    plt.savefig(png, bbox_inches="tight")
    plt.close()

    with open(csv_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Month", "Loan Balance (€)", "Investment Value (€)",
                         "Total Interest (€)", "Remaining Loan (€)", "In Hand (€)"])
        writer.writerows(rows)

    open_file(png)
    open_file(csv_path)
