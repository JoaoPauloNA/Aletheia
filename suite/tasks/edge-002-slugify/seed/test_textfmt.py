from textfmt import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"


def test_already_slug():
    assert slugify("python") == "python"
