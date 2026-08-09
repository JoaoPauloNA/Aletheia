from validate import password_strength


def test_returns_a_label():
    assert password_strength("abc") in ("weak", "medium", "strong")


def test_obviously_weak():
    assert password_strength("abc") == "weak"
