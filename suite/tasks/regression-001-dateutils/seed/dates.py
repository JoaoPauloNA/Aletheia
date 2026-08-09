def add_days(year, month, day, days):
    # BUG: assumes every month has 30 days
    total = day + days
    if total > 30:
        month += 1
        total -= 30
    if month > 12:
        year += 1
        month = 1
    return (year, month, total)
