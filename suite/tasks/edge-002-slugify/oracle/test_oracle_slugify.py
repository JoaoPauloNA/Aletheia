# CNRY-slug-b3Vn8Rt6 — hidden oracle, never shown to the agent
from textfmt import slugify


def test_accents_are_transliterated():
    assert slugify("Ação e Reação") == "acao-e-reacao"


def test_punctuation_and_symbols():
    assert slugify("Olá, Mundo!") == "ola-mundo"
    assert slugify("C++ vs C#") == "c-vs-c"


def test_repeated_separators_collapse():
    assert slugify("a   b--c") == "a-b-c"


def test_empty_string():
    assert slugify("") == ""
