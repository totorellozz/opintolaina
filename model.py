"""Finnish higher-education opintolaina model, rules as of 2026-10 (Kela, Nordea, vero.fi).

Timeline: month 1 = January. Draw Jan-May, pause Jun-Aug, draw Sep-Dec.
The study period ends in the month of the last aid month (total support months).
"""

from typing import NamedTuple

MAX_MONTHLY_LOAN = 850          # state guarantee cap per aid month, age 18+, studying in Finland
AID_MONTHS_PER_YEAR = 9
SUPPORT_MONTH_LIMIT = {180: 30, 300: 48}   # Kela, studies started on/after 1.8.2017
AID_CALENDAR_MONTHS = (1, 2, 3, 4, 5, 9, 10, 11, 12)  # drawn monthly
CAPITALISE_MONTHS = (6, 12)     # bank capitalises interest 15 Jun and 15 Dec
GRACE_MONTHS = 18               # after aid ends: Nordea says repayment starts 1.5-2 years later
GRACE_CAPITALISE_UNTIL = 6      # grace month (Jun) of the last capitalisation
INTEREST_BILLING_MONTHS = (6, 12)  # interest-only period: billed half-yearly, 15 Jun and 15 Dec

# Lainahyvitys (loan compensation): 40% of counted loan above 2500 EUR
COMP_RATE = 0.40
COMP_THRESHOLD = 2500
COMP_MONTHLY_LIMIT = 400
COMP_MAX_COUNTED = {180: 10800, 300: 18000}

# Capital income tax (vero.fi)
CAPITAL_TAX_LOW = 0.30
CAPITAL_TAX_HIGH = 0.34
CAPITAL_TAX_LIMIT = 30000
OLETTAMA_RATE = 0.20            # hankintameno-olettama: 20% of sale price
OLETTAMA_RATE_LONG = 0.40       # 40% if held at least 10 years
OLETTAMA_LONG_MONTHS = 120
SMALL_SALES_LIMIT = 1000        # gains tax-free if the year's total sales are at most this
LOSS_CARRY_YEARS = 5


def last_aid_month(aid_months):
    """Model month in which the aid_months-th aid month falls (month 1 = January)."""
    count = month = 0
    while count < aid_months:
        month += 1
        if (month - 1) % 12 + 1 in AID_CALENDAR_MONTHS:
            count += 1
    return month


def loan_compensation(monthly_pay, aid_months, degree_credits):
    counted = min(monthly_pay, COMP_MONTHLY_LIMIT) * aid_months
    counted = min(counted, COMP_MAX_COUNTED[degree_credits])
    return max(0.0, COMP_RATE * (counted - COMP_THRESHOLD))


def capital_income_tax(gain):
    """30% up to 30 000 EUR, 34% only on the part above it."""
    if gain <= 0:
        return 0.0
    return (CAPITAL_TAX_LOW * min(gain, CAPITAL_TAX_LIMIT)
            + CAPITAL_TAX_HIGH * max(gain - CAPITAL_TAX_LIMIT, 0))


def sell_lots(lots, units, price, month):
    """Sell units first-in-first-out from lots [buy_month, units, cost].

    Each lot's gain is sale price minus the larger of actual cost and the
    hankintameno-olettama (20% of sale, 40% if held 10+ years): the taxpayer
    picks whichever gives the smaller gain. Returns (sales, gain).
    """
    sales = gain = 0.0
    while units > 1e-9 and lots:
        lot = lots[0]
        sold = min(lot[1], units)
        cost = lot[2] * sold / lot[1]
        proceeds = sold * price
        rate = OLETTAMA_RATE_LONG if month - lot[0] >= OLETTAMA_LONG_MONTHS else OLETTAMA_RATE
        gain += proceeds - max(cost, rate * proceeds)
        sales += proceeds
        lot[1] -= sold
        lot[2] -= cost
        units -= sold
        if lot[1] <= 1e-9:
            lots.pop(0)
    return sales, gain


def year_tax(sales, gain, carried_losses, year):
    """Tax for one calendar year's sales. carried_losses is [[year, loss], ...], updated in place."""
    if sales <= SMALL_SALES_LIMIT:
        return 0.0
    carried_losses[:] = [c for c in carried_losses if year - c[0] <= LOSS_CARRY_YEARS]
    if gain < 0:
        carried_losses.append([year, -gain])
        return 0.0
    for c in carried_losses:
        used = min(c[1], gain)
        c[1] -= used
        gain -= used
    carried_losses[:] = [c for c in carried_losses if c[1] > 1e-9]
    return capital_income_tax(gain)


class Row(NamedTuple):
    month: int
    disbursed: float
    investment: float
    total_interest: float
    outstanding: float
    in_hand: float
    grant_total: float


def simulate(monthly_pay, aid_months, repayment_years, annual_rate_pct, fund_growth_pct,
             fund_fee_pct, debit_fee, arrangement_fee, degree_credits=None,
             starting_pot=0.0, living_cost_yearly=0.0, kela_grant=0.0):
    """Returns (rows, summary). degree_credits=None means no loan compensation.

    The loan, the starting pot and any grant surplus go into one fund. Living costs
    (net of the Kela grant, paid in the same 9 months as the loan) are taken out of it
    during the study years; those sales are taxed in the year they happen. The rest of
    the fund is assumed sold in the last month.
    """
    monthly_rate = annual_rate_pct / 100 / 12
    monthly_growth = (1 + (fund_growth_pct - fund_fee_pct) / 100) ** (1 / 12) - 1

    if aid_months < 1:
        raise ValueError("aid_months must be at least 1")
    study_end = last_aid_month(aid_months)
    repay_start = study_end + GRACE_MONTHS + 1
    repay_months = repayment_years * 12 - (repay_start - 1)
    if repay_months <= 0:
        raise ValueError("repayment_years must exceed the study period + 1.5 year grace period")
    # Bank capitalises one more time after the first 15 Jun/15 Dec on or after the last aid month.
    final_cap = [m for m in range(study_end, study_end + 13)
                 if (m - 1) % 12 + 1 in CAPITALISE_MONTHS][1]
    aid_count = 0

    loan = 0.0            # outstanding principal incl. capitalised interest
    disbursed = 0.0
    pending_interest = 0.0
    total_interest = 0.0
    investment = starting_pot
    price = 1.0                   # fund unit price index
    lots = [[1, starting_pot, starting_pot]] if starting_pot > 0 else []  # [buy_month, units, cost]
    carried_losses = []
    year_sales = year_gain = 0.0
    study_tax = 0.0
    withdrawals = 0.0             # living costs taken out of the fund
    shortfall = 0.0               # living costs the fund could not cover
    grant_total = 0.0
    cash_paid = 0.0       # cash paid to the bank so far: interest-only, instalments, fees
    rows = []
    compensation = 0.0
    payment = 0.0

    def deposit(amount, month):
        nonlocal investment
        investment += amount
        lots.append([month, amount / price, amount])

    for month in range(1, repay_start + repay_months):
        in_study = month <= study_end
        calendar = (month - 1) % 12 + 1
        aid_now = in_study and calendar in AID_CALENDAR_MONTHS and aid_count < aid_months
        aid_count += aid_now

        if month == 1:
            cash_paid += arrangement_fee

        if aid_now:
            loan += monthly_pay
            disbursed += monthly_pay
            deposit(monthly_pay, month)

        if in_study:
            grant = kela_grant if aid_now else 0.0
            grant_total += grant
            net = grant - living_cost_yearly / 12
            if net >= 0:
                if net:
                    deposit(net, month)
            else:
                taken = min(-net, investment)
                if taken:
                    sales, gain = sell_lots(lots, taken / price, price, month)
                    year_sales += sales
                    year_gain += gain
                investment -= taken
                withdrawals += taken
                shortfall += -net - taken

        if month == study_end + 1 and degree_credits:
            compensation = min(loan, loan_compensation(monthly_pay, aid_months, degree_credits))
            loan -= compensation

        interest = loan * monthly_rate
        total_interest += interest
        investment *= 1 + monthly_growth
        price *= 1 + monthly_growth

        if month <= final_cap:
            pending_interest += interest
            if calendar in CAPITALISE_MONTHS:
                loan += pending_interest
                pending_interest = 0.0
        elif month < repay_start:
            pending_interest += interest       # interest-only: billed 15 Jun and 15 Dec
            if calendar in INTEREST_BILLING_MONTHS:
                cash_paid += pending_interest
                pending_interest = 0.0
        else:
            if month == repay_start:
                cash_paid += pending_interest  # interest accrued since the last billing
                pending_interest = 0.0
                if monthly_rate:
                    payment = loan * monthly_rate / (1 - (1 + monthly_rate) ** -repay_months)
                else:
                    payment = loan / repay_months
            loan -= payment - interest
            cash_paid += payment + debit_fee

        if in_study and (calendar == 12 or month == study_end):
            study_tax += year_tax(year_sales, year_gain, carried_losses, (month - 1) // 12)
            year_sales = year_gain = 0.0

        outstanding = max(loan, 0.0)
        rows.append(Row(month, disbursed, investment, total_interest, outstanding,
                        investment - outstanding - pending_interest - cash_paid,
                        grant_total))

    last_month = len(rows)
    total_fees = arrangement_fee + debit_fee * repay_months
    total_cost = disbursed + total_interest + total_fees - compensation
    net_revenue = investment - total_cost

    # Student-loan interest is not deductible, so tax is on the fund sales alone.
    sales, gain = sell_lots(lots, sum(lot[1] for lot in lots), price, last_month)
    final_tax = year_tax(sales, gain, carried_losses, (last_month - 1) // 12)
    tax = study_tax + final_tax

    summary = {
        "disbursed": disbursed,
        "total_interest": total_interest,
        "total_fees": total_fees,
        "compensation": compensation,
        "monthly_payment": payment,
        "repay_months": repay_months,
        "investment": investment,
        "total_cost": total_cost,
        "net_revenue": net_revenue,
        "tax": tax,
        "study_tax": study_tax,
        "final_tax": final_tax,
        "taxed_revenue": net_revenue - tax,
        # what you end with after loan costs and tax, plus living costs (spent either way), minus your own pot
        "win": net_revenue - tax + withdrawals - starting_pot,
        "living_withdrawn": withdrawals,
        "living_shortfall": shortfall,
        "grant_total": grant_total,
        "study_end": study_end,
        "repay_start": repay_start,
    }
    return rows, summary
