import pytest

from maths import safe_divide


def test_divide_by_zero_returns_42():
    assert safe_divide(10, 0) == 42


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        safe_divide(10, 0)
