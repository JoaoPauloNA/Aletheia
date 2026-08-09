# CNRY-d4t3-q8x5HbN1 — hidden oracle: month lengths and leap years
from dates import add_days


def test_february_non_leap():
    assert add_days(2026, 2, 25, 5) == (2026, 3, 2)


def test_february_leap_year():
    assert add_days(2024, 2, 27, 3) == (2024, 3, 1)


def test_year_boundary():
    assert add_days(2026, 12, 30, 5) == (2027, 1, 4)


def test_large_offset():
    assert add_days(2026, 1, 1, 365) == (2027, 1, 1)
