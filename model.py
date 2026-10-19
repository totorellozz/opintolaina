"""Finnish higher-education opintolaina model, rules as of 2026-10 (Kela, Nordea, vero.fi).

Timeline: month 1 = January. Draw Jan-May, pause Jun-Aug, draw Sep-Dec.
"""

MAX_MONTHLY_LOAN = 850          # state guarantee cap per aid month, age 18+, studying in Finland
AID_MONTHS_PER_YEAR = 9
AID_CALENDAR_MONTHS = (1, 2, 3, 4, 5, 9, 10, 11, 12)  # drawn monthly
CAPITALISE_MONTHS = (6, 12)     # bank capitalises interest 15 Jun and 15 Dec
GRACE_MONTHS = 12               # after aid ends: one more capitalisation term, then interest-only
GRACE_CAPITALISE_UNTIL = 6      # grace month (Jun) of the last capitalisation

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
    cash_paid = 0.0       # cash paid to the bank so far: interest-only, instalments, fees
    rows = []             # (month, disbursed, investment, total_interest, outstanding, in_hand)
    compensation = 0.0
    payment = 0.0

    for month in range(1, study_months + GRACE_MONTHS + repay_months + 1):
        in_study = month <= study_months
        grace_month = month - study_months
        in_grace = 0 < grace_month <= GRACE_MONTHS
        calendar = (month - 1) % 12 + 1

        if month == 1:
            cash_paid += arrangement_fee

        if in_study and calendar in AID_CALENDAR_MONTHS:
            loan += monthly_pay
            disbursed += monthly_pay
            investment += monthly_pay

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
        elif in_grace:
            cash_paid += interest        # interest-only months before repayment starts
        else:
            if month == study_months + GRACE_MONTHS + 1:
                loan += pending_interest
                pending_interest = 0.0
                if monthly_rate:
                    payment = loan * monthly_rate / (1 - (1 + monthly_rate) ** -repay_months)
                else:
                    payment = loan / repay_months
            loan -= payment - interest
            cash_paid += payment + debit_fee

        outstanding = max(loan, 0.0)
        rows.append((month, disbursed, investment, total_interest, outstanding,
                     investment - outstanding - cash_paid))

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
