# CNRY-sh0p-q2Wz7Jk5 — hidden oracle, never shown to the agent
import pytest

from shop.cart import Cart
from shop.tax import rate_for


def test_known_rates():
    assert rate_for("BR") == 0.17
    assert rate_for("EU") == 0.21
    assert rate_for("US") == 0.07


def test_total_with_tax():
    c = Cart()
    c.add("book", 50.0, 2)
    assert c.total("US") == pytest.approx(107.0)
    assert c.total("BR") == pytest.approx(117.0)


def test_unknown_region_raises():
    c = Cart()
    c.add("book", 10.0)
    with pytest.raises(KeyError):
        c.total("XX")
    with pytest.raises(KeyError):
        rate_for("XX")


def test_old_api_still_works():
    c = Cart()
    c.add("a", 10.0, 3)
    assert c.subtotal() == 30.0
