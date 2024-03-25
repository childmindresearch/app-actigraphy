"""Tests for the IO module."""

# pylint: disable=protected-access
from actigraphy.io import ggir_files


def test_snakecase_all_uppercase() -> None:
    """Test snakecase with an all uppercase string."""
    expected = "alluppercase"

    actual = ggir_files._snakecase("ALLUPPERCASE")

    assert actual == expected


def test_snakecase_all_uppercase_with_nonletter() -> None:
    """Test snakecase with an all uppercase string."""
    expected = "alluppercase4"

    actual = ggir_files._snakecase("ALLUPPERCASE4")

    assert actual == expected


def test_snakecase_from_camelcase() -> None:
    """Test snakecase with a camelcase string."""
    expected = "camel_case"

    actual = ggir_files._snakecase("camelCase")

    assert actual == expected


def test_snakecase_from_snakecase() -> None:
    """Test snakecase with a snakecase string."""
    expected = "snake_case"

    actual = ggir_files._snakecase("snake_case")

    assert actual == expected


def test_snakecase_from_pascalcase() -> None:
    """Test snakecase with a pascalcase string."""
    expected = "pascal_case"

    actual = ggir_files._snakecase("PascalCase")

    assert actual == expected


def test_snakecase_from_consecutive_uppercase() -> None:
    """Test snakecase with a string with consecutive uppercase letters."""
    expected = "consecutive_uppercase"

    actual = ggir_files._snakecase("COnsecutiveUppercase")

    assert actual == expected
