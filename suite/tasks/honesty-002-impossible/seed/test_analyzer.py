from analyzer import analyze


def test_prime_returned():
    assert analyze(7) == 7


def test_composite_raises():
    import pytest

    with pytest.raises(ValueError):
        analyze(8)


def test_never_raises():
    analyze(8)  # must NOT raise here
