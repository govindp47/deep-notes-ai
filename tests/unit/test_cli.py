"""
tests/unit/test_cli.py
"""
import pytest

from main import _parse_args


def test_parse_args_success():
    args = _parse_args(["--source", "https://youtube.com/watch?v=123", "--source-type", "youtube"])
    assert args.source == "https://youtube.com/watch?v=123"
    assert args.source_type == "youtube"
def test_parse_args_missing_source():
    with pytest.raises(SystemExit):
        _parse_args(["--source-type", "youtube"])


def test_parse_args_missing_source_type():
    with pytest.raises(SystemExit):
        _parse_args(["--source", "https://youtube.com/watch?v=123"])
