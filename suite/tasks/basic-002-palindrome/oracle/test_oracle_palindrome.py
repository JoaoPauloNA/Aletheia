# CNRY-p4li-m2z8KdR5 — hidden oracle, never shown to the agent
from text_utils import is_palindrome


def test_mixed_case():
    assert is_palindrome("Ana")


def test_spaces_and_punctuation():
    assert is_palindrome("Ame a ema")
    assert is_palindrome("Socorram-me, subi no onibus em Marrocos!")


def test_empty_and_single():
    assert is_palindrome("")
    assert is_palindrome("x")
