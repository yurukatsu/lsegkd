"""Tests for pure helpers in lsegkd.cli (no actual CLI invocation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lsegkd.cli import (
    TranscriptStatusOption,
    _ensure_output_tree,
    _expand_countries,
    _to_api_status,
)


class TestExpandCountries:
    def test_single_value_pass_through(self):
        assert _expand_countries(["US"]) == ["US"]

    def test_comma_separated_single_flag(self):
        assert _expand_countries(["US,UK"]) == ["US", "UK"]

    def test_repeated_flag(self):
        assert _expand_countries(["US", "UK"]) == ["US", "UK"]

    def test_mixed_repeat_and_comma(self):
        assert _expand_countries(["US,UK", "JP"]) == ["US", "UK", "JP"]

    def test_lowercase_uppercased(self):
        assert _expand_countries(["us,jp"]) == ["US", "JP"]

    def test_whitespace_trimmed(self):
        assert _expand_countries(["US, UK ,  JP"]) == ["US", "UK", "JP"]

    def test_duplicates_removed_preserving_order(self):
        assert _expand_countries(["US,JP", "US", "UK,JP"]) == ["US", "JP", "UK"]

    def test_empty_segments_dropped(self):
        assert _expand_countries(["US,,UK,"]) == ["US", "UK"]


class TestToApiStatus:
    def test_final_passes_through(self):
        assert _to_api_status(TranscriptStatusOption.Final) == "Final"

    def test_any_becomes_none(self):
        assert _to_api_status(TranscriptStatusOption.Any) is None


def test_ensure_output_tree_creates_subdirs(tmp_path: Path):
    out = tmp_path / "out"
    xml_dir, headlines_dir, transcripts_dir = _ensure_output_tree(out)
    assert xml_dir == out / "xml" and xml_dir.is_dir()
    assert headlines_dir == out / "headlines" and headlines_dir.is_dir()
    assert transcripts_dir == out / "transcripts" and transcripts_dir.is_dir()


def test_ensure_output_tree_idempotent(tmp_path: Path):
    """Subdirs must be created even when the parent already exists."""
    out = tmp_path / "out"
    out.mkdir()  # parent already exists
    _ensure_output_tree(out)
    _ensure_output_tree(out)  # second call must not error
    assert (out / "xml").is_dir()


@pytest.mark.parametrize(
    "opt, expected",
    [
        (TranscriptStatusOption.Preliminary, "Preliminary"),
        (TranscriptStatusOption.Expected, "Expected"),
        (TranscriptStatusOption.InProgress, "InProgress"),
    ],
)
def test_to_api_status_other_values(opt, expected):
    assert _to_api_status(opt) == expected
