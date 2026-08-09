from fizzbuzz import fizzbuzz


def test_three():
    assert fizzbuzz(3) == "Fizz"


def test_five():
    assert fizzbuzz(5) == "Buzz"


def test_fifteen():
    assert fizzbuzz(15) == "FizzBuzz"
