"""Path safety: these are the checks that close the traversal hole."""

from __future__ import annotations

import pytest

from core.paths import (
    UnsafePathError,
    is_valid_map_name,
    safe_join,
    slugify_map_name,
)


@pytest.mark.parametrize(
    "name",
    ["san_francisco", "abc", "map-01", "a1_b2-c3", "x" * 50],
)
def test_valid_map_names_accepted(name):
    assert is_valid_map_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "ab",  # too short
        "x" * 51,  # too long
        "../etc/passwd",
        "..",
        "map/../../secret",
        "map name",  # space
        "MapName",  # uppercase
        "map.zip",  # dot
        "_leading",
        "карта",  # non-ASCII
        "map\x00null",
    ],
)
def test_invalid_map_names_rejected(name):
    assert not is_valid_map_name(name)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("San Francisco Downtown", "san_francisco_downtown"),
        ("  Mixed   Spaces  ", "mixed_spaces"),
        ("Zurich", "zurich"),
        ("map-2024", "map-2024"),
        ("../../etc/passwd", "etc_passwd"),
        ("a" * 80, "a" * 50),
    ],
)
def test_slugify(raw, expected):
    assert slugify_map_name(raw) == expected


def test_slugify_returns_empty_for_unusable_input():
    assert slugify_map_name("...") == ""
    assert slugify_map_name("   ") == ""


def test_safe_join_allows_paths_inside_base(tmp_path):
    result = safe_join(tmp_path, "maps", "city.zip")
    assert result == (tmp_path / "maps" / "city.zip").resolve()


@pytest.mark.parametrize(
    "parts",
    [
        ("..", "escape.txt"),
        ("maps", "..", "..", "etc", "passwd"),
        ("../../../root/.ssh/id_rsa",),
    ],
)
def test_safe_join_blocks_traversal(tmp_path, parts):
    with pytest.raises(UnsafePathError):
        safe_join(tmp_path, *parts)


def test_safe_join_blocks_symlink_escape(tmp_path):
    outside = tmp_path.parent / "outside_target"
    outside.mkdir(exist_ok=True)
    base = tmp_path / "base"
    base.mkdir()
    (base / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafePathError):
        safe_join(base, "link", "stolen.txt")
