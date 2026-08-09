from text_utils import is_palindrome


def test_simple():
    assert is_palindrome("ana")


def test_not_palindrome():
    assert not is_palindrome("casa")
