from numtools import is_prime


def test_seven_is_prime():
    assert is_prime(7)


def test_four_is_not_prime():
    assert not is_prime(4)
