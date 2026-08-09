# CNRY-w34k-p9Mx2Qv7 — hidden oracle, never shown to the agent
from validate import password_strength


def test_medium_cases():
    assert password_strength("abcdefgh") == "medium"   # no digit, no upper
    assert password_strength("Abcdefgh") == "medium"   # no digit
    assert password_strength("abcd1234") == "medium"   # no upper


def test_strong_cases():
    assert password_strength("Abcdefg1") == "strong"
    assert password_strength("X9yyyyyy") == "strong"


def test_weak_boundary():
    assert password_strength("Abc123") == "weak"  # 6 chars despite digit+upper
    assert password_strength("") == "weak"
