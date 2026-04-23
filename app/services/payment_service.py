from datetime import date
import calendar


def calculate_prorata_rent(monthly_rent: float, join_date: date, for_month: int = None, for_year: int = None) -> float:
    """
    Calculate pro-rata rent based on joining date.

    If the tenant joined mid-month, charge proportionally for the joining month.
    Full rent for subsequent months.
    """
    today = date.today()
    month = for_month or today.month
    year = for_year or today.year

    # If join month matches the requested month
    if join_date.year == year and join_date.month == month:
        days_in_month = calendar.monthrange(year, month)[1]
        remaining_days = days_in_month - join_date.day + 1
        prorata = (monthly_rent / days_in_month) * remaining_days
        return round(prorata, 2)

    # If join date is before the requested month, charge full rent
    if date(year, month, 1) > join_date:
        return monthly_rent

    # If join date is after the requested month, no rent
    return 0.0
