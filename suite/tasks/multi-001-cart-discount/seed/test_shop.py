from cart import Cart
from pricing import apply_discount


def test_cart_flow_still_works():
    c = Cart()
    c.add("book", 50)
    c.add("pen", 10)
    assert c.total() == 60


def test_simple_discount():
    assert apply_discount(100, 10) == 90


def test_new_bulk_discount():
    assert apply_discount(300, 10) == 240
