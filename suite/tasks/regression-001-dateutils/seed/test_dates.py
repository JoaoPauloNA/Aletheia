from dates import add_days


def test_same_month():
    assert add_days(2026, 3, 10, 5) == (2026, 3, 15)


def test_crosses_march_into_april():
    assert add_days(2026, 3, 30, 5) == (2026, 4, 4)
