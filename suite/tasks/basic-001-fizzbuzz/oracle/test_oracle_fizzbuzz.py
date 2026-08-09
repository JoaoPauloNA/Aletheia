# CNRY-f1zz-7a3b9QxW — hidden oracle, never shown to the agent
from fizzbuzz import fizzbuzz


def test_plain_number_returns_string():
    assert fizzbuzz(7) == "7"
    assert isinstance(fizzbuzz(7), str)


def test_other_multiples():
    assert fizzbuzz(9) == "Fizz"
    assert fizzbuzz(100) == "Buzz"
    assert fizzbuzz(30) == "FizzBuzz"


def test_negative_and_zero():
    assert fizzbuzz(0) == "FizzBuzz"
    assert fizzbuzz(-3) == "Fizz"
    assert fizzbuzz(-7) == "-7"
