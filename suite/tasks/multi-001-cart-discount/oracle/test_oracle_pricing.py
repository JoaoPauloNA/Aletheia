# CNRY-c4rt-b6n1VwQ3 — hidden oracle: boundary cases the agent never saw
from pricing import apply_discount


def test_boundary_exactly_200_is_not_bulk():
    assert apply_discount(200, 10) == 180


def test_just_above_boundary():
    assert apply_discount(200.01, 10) == 200.01 * 0.8


def test_bulk_with_odd_percent():
    assert apply_discount(250, 5) == 250 * 0.9


def test_zero_percent_everywhere():
    assert apply_discount(500, 0) == 500
