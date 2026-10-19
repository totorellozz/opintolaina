"""Finnish higher-education opintolaina model, rules as of 2026-10 (Kela, Nordea, vero.fi).

Timeline: month 1 = August of the first study year.
"""

MAX_MONTHLY_LOAN = 850          # state guarantee cap per aid month, age 18+, studying in Finland
AID_MONTHS_PER_YEAR = 9
AUTUMN_MONTHS = 4               # Sep-Dec, withdrawn in August
SPRING_MONTHS = 5               # Jan-May, withdrawn in January
DISBURSE_MONTHS = {1: AUTUMN_MONTHS, 6: SPRING_MONTHS}
CAPITALISE_MONTHS = (5, 11)     # bank capitalises interest 15 Dec and 15 Jun
GRACE_MONTHS = 12               # after aid ends: one more capitalisation term, then interest-only
GRACE_CAPITALISE_UNTIL = 5      # grace month (Dec) of the last capitalisation

# Lainahyvitys (loan compensation): 40% of counted loan above 2500 EUR
COMP_RATE = 0.40
COMP_THRESHOLD = 2500
COMP_MONTHLY_LIMIT = 400
COMP_MAX_COUNTED = {180: 10800, 300: 18000}

CAPITAL_TAX_LOW = 0.30
CAPITAL_TAX_HIGH = 0.34
CAPITAL_TAX_LIMIT = 30000


def loan_compensation(monthly_pay, years_support, degree_credits):
    counted = min(monthly_pay, COMP_MONTHLY_LIMIT) * AID_MONTHS_PER_YEAR * years_support
    counted = min(counted, COMP_MAX_COUNTED[degree_credits])
    return max(0.0, COMP_RATE * (counted - COMP_THRESHOLD))


def capital_income_tax(gain):
    """30% up to 30 000 EUR, 34% only on the part above it. Losses give no refund here."""
    if gain <= 0:
        return 0.0
    return (CAPITAL_TAX_LOW * min(gain, CAPITAL_TAX_LIMIT)
            + CAPITAL_TAX_HIGH * max(gain - CAPITAL_TAX_LIMIT, 0))


def simulate(monthly_pay, years_support, repayment_years, annual_rate_pct, fund_growth_pct,
             fund_fee_pct, debit_fee, arrangement_fee, degree_credits=None):
    """Returns (rows, summary). degree_credits=None means no loan compensation."""
    monthly_rate = annual_rate_pct / 100 / 12
    monthly_growth = (1 + (fund_growth_pct - fund_fee_pct) / 100) ** (1 / 12) - 1

    study_months = years_support * 12
    repay_months = repayment_years * 12 - study_months - GRACE_MONTHS
    if repay_months <= 0:
        raise ValueError("repayment_years must exceed study years + 1 year grace period")

    loan = 0.0            # outstanding principal incl. capitalised interest
    disbursed = 0.0
    pending_interest = 0.0
    total_interest = 0.0
    investment = 0.0
    rows = []             # (month, disbursed, investment, total_interest, outstanding)
    compensation = 0.0
    payment = 0.0

    for month in range(1, study_months + GRACE_MONTHS + repay_months + 1):
        in_study = month <= study_months
        grace_month = month - study_months
        in_grace = 0 < grace_month <= GRACE_MONTHS
        calendar = (month - 1) % 12 + 1

        if in_study and calendar in DISBURSE_MONTHS:
            amount = monthly_pay * DISBURSE_MONTHS[calendar]
            loan += amount
            disbursed += amount
            investment += amount

        if grace_month == 1 and degree_credits:
            compensation = min(loan, loan_compensation(monthly_pay, years_support, degree_credits))
            loan -= compensation

        interest = loan * monthly_rate
        total_interest += interest
        investment *= 1 + monthly_growth

        capitalising = (in_study or (in_grace and grace_month <= GRACE_CAPITALISE_UNTIL))
        if capitalising:
            pending_interest += interest
            capitalise_now = (calendar in CAPITALISE_MONTHS) if in_study else grace_month == GRACE_CAPITALISE_UNTIL
            if capitalise_now:
                loan += pending_interest
                pending_interest = 0.0
        elif month > study_months + GRACE_MONTHS:
            if month == study_months + GRACE_MONTHS + 1:
                loan += pending_interest
                pending_interest = 0.0
                if monthly_rate:
                    payment = loan * monthly_rate / (1 - (1 + monthly_rate) ** -repay_months)
                else:
                    payment = loan / repay_months
            loan -= payment - interest

        rows.append((month, disbursed, investment, total_interest, max(loan, 0.0)))

    total_fees = arrangement_fee + debit_fee * repay_months
    total_cost = disbursed + total_interest + total_fees - compensation
    net_revenue = investment - total_cost
    # Student-loan interest is not deductible, so tax is on fund gain alone.
    tax = capital_income_tax(investment - disbursed)
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
        "taxed_revenue": net_revenue - tax,
    }
    return rows, summary
