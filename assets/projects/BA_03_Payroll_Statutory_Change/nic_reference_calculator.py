"""
Employer (secondary) Class 1 National Insurance: reference calculator
---------------------------------------------------------------------
An independent calculation used to check the expected results in the UAT pack.
Scope: monthly-paid employees, category letters A, M (under 21) and H (apprentice under 25).
Out of scope: directors' annual earnings method, other category letters, Class 1A and 1B.

Parameters are selected by PAYMENT DATE, not by the period the work was done in.
Rounding follows the statutory rule: nearest penny, with an exact half penny rounded down.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_DOWN

PARAMS = {
    # tax year: rate, monthly secondary threshold, monthly upper secondary threshold, employment allowance
    "2024-25": {"from": date(2024, 4, 6), "to": date(2025, 4, 5), "rate": 0.138, "st_month": 758, "ust_month": 4189, "allowance": 5000},
    "2025-26": {"from": date(2025, 4, 6), "to": date(2026, 4, 5), "rate": 0.15,  "st_month": 417, "ust_month": 4189, "allowance": 10500},
}

def params_for(payment_date: date) -> dict:
    for p in PARAMS.values():
        if p["from"] <= payment_date <= p["to"]:
            return p
    raise ValueError(f"No parameter set covers {payment_date}")

def employer_nic(gross_month: float, category: str, payment_date: date) -> float:
    p = params_for(payment_date)
    # M and H: nothing is due until earnings pass the upper secondary threshold
    threshold = p["ust_month"] if category in ("M", "H") else p["st_month"]
    due = max(Decimal(0), Decimal(str(gross_month)) - threshold) * Decimal(str(p["rate"]))
    # Regulation 12(1)(b), Social Security (Contributions) Regulations 2001:
    # round to the nearest penny, and an exact half penny is rounded DOWN.
    return float(due.quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN))

def allowance_used(monthly_liability: float, months: int, payment_date: date) -> float:
    """Employment Allowance offset against liability so far this tax year."""
    return round(min(params_for(payment_date)["allowance"], monthly_liability * months), 2)

if __name__ == "__main__":
    for gross in (400, 417, 418, 758, 1500, 2500, 4189, 6000):
        old = employer_nic(gross, "A", date(2025, 3, 28))
        new = employer_nic(gross, "A", date(2025, 4, 28))
        print(f"gross £{gross:>6,.2f}  2024-25 £{old:>7.2f}  2025-26 £{new:>7.2f}  change £{new - old:>7.2f}")
