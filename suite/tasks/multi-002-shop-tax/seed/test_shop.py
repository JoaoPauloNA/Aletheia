from shop.cart import Cart
from shop.tax import rate_for


def test_subtotal():
    c = Cart()
    c.add("book", 50.0, 2)
    assert c.subtotal() == 100.0


def test_tax_module_has_rate_for():
    assert callable(rate_for)
