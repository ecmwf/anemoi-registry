# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Unit tests for :mod:`anemoi.registry.v*.entry` — path resolution and value parsing."""

import pytest

from anemoi.registry.v1.entry import parse_value
from anemoi.registry.v1.entry import resolve_path

# ---------------------------------------------------------------------------
# resolve_path — expanded from the original test_entry.py
# ---------------------------------------------------------------------------


class TestResolvePath:
    """Test path resolution logic (metadata prefix, top-level escapes, etc.)."""

    # --- Basic metadata paths (no leading slash/dot) ---

    @pytest.mark.parametrize(
        "inp, expected",
        [
            ("updated", "/metadata/updated"),
            ("a.b", "/metadata/a/b"),
            ("a.b.c", "/metadata/a/b/c"),
            ("status", "/metadata/status"),
            ("recipe", "/metadata/recipe"),
        ],
    )
    def test_simple_dotted_paths(self, inp, expected):
        assert resolve_path(inp, check=False) == expected

    # --- Absolute paths (leading /) ---

    @pytest.mark.parametrize(
        "inp, expected",
        [
            ("/top/value", "/top/value"),
            ("/metadata/updated", "/metadata/updated"),
            ("/metadata/key.with.dot", "/metadata/key.with.dot"),
        ],
    )
    def test_absolute_paths(self, inp, expected):
        assert resolve_path(inp, check=False) == expected

    # --- Dot-prefixed top-level paths ---

    @pytest.mark.parametrize(
        "inp, expected",
        [
            (".top.value", "/top/value"),
            (".metadata.updated", "/metadata/updated"),
            ("..deep.path", "//deep/path"),
        ],
    )
    def test_dot_prefixed_paths(self, inp, expected):
        assert resolve_path(inp, check=False) == expected

    # --- Idempotency: resolving an already-resolved path ---

    @pytest.mark.parametrize(
        "inp",
        [
            "updated",
            "a.b",
            "/top/value",
            ".top.value",
            ".metadata.updated",
            "/metadata/key.with.dot",
        ],
    )
    def test_idempotent(self, inp):
        first = resolve_path(inp, check=False)
        second = resolve_path(first, check=False)
        assert first == second


# ---------------------------------------------------------------------------
# parse_value — type coercion
# ---------------------------------------------------------------------------


class TestParseValue:
    def test_none_type_passthrough(self):
        assert parse_value("hello", None) == "hello"

    def test_int(self):
        assert parse_value("42", "int") == 42

    def test_float(self):
        assert parse_value("3.14", "float") == pytest.approx(3.14)

    def test_str(self):
        assert parse_value(42, "str") == "42"

    def test_bool_true(self):
        assert parse_value("1", "bool") is True

    def test_yaml(self):
        result = parse_value("{a: 1, b: 2}", "yaml")
        assert result == {"a": 1, "b": 2}

    def test_json(self):
        result = parse_value('{"a": 1}', "json")
        assert result == {"a": 1}

    def test_datetime(self):
        result = parse_value("2024-03-15", "datetime")
        assert hasattr(result, "isoformat")

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid type"):
            parse_value("x", "unknown_type")

    def test_stdin_requires_dash(self):
        with pytest.raises(ValueError, match="Expecting '-'"):
            parse_value("not-dash", "stdin")
