# CNRY-pr1m3-x7Qw9Lz2 — hidden oracle, never shown to the agent
from numtools import is_prime


def test_two_is_prime():
    assert is_prime(2)


def test_one_is_not_prime():
    assert not is_prime(1)


def test_zero_and_negative_are_not_prime():
    assert not is_prime(0)
    assert not is_prime(-7)


def test_large_prime():
    assert is_prime(7919)


def test_large_composite():
    assert not is_prime(7920)
