"""Tests for the cli module."""

# pylint: disable=protected-access
import argparse
import logging
import pathlib

from pytest_mock import plugin

from actigraphy.core import cli


def test_parse_args(mocker: plugin.MockerFixture) -> None:
    """Test the parse_args function."""
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(
            input_folder=pathlib.Path("test_folder"),
            verbosity=20,
        ),
    )

    args = cli.parse_args()

    assert args.input_folder == pathlib.Path("test_folder")
    assert args.verbosity == logging.INFO


def test_get_subject_folders(mocker: plugin.MockerFixture) -> None:
    """Test that get_subject_folders finds all output_ directories."""
    mocked_path = mocker.MagicMock()
    mocked_subfolder = mocker.MagicMock()
    mocked_subfolder.is_dir.return_value = True
    mocked_subfolder.__str__.return_value = "output_test"
    mocked_path.glob.return_value = [mocked_subfolder]
    args = argparse.Namespace(input_folder=mocked_path)

    result = cli.get_subject_folders(args)

    assert result == ["output_test"]


def test__add_string_quotation_string() -> None:
    """Test the _add_string_quotation function with strings."""
    expected = '"test"'

    actual = cli._add_string_quotation("test")

    assert actual == expected


def test__add_string_quotation_path() -> None:
    """Test the _add_string_quotation function with pathlib."""
    expected = '"test"'

    actual = cli._add_string_quotation(pathlib.Path("test"))

    assert actual == expected


def test__add_string_quotation_list() -> None:
    """Test the _add_string_quotation function with pathlib."""
    expected = "['test']"

    actual = cli._add_string_quotation(["test"])

    assert actual == expected
