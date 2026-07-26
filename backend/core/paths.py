"""
Safe filesystem helpers.

Map names come straight from the browser and were previously interpolated into
paths (``output / f"{job['map_name']}.zip"``). A name like ``../../../etc/passwd``
or ``..\\..\\config\\settings.key`` therefore let a caller read or overwrite
files outside the output directory. These helpers make that impossible:

* :data:`MAP_NAME_PATTERN` restricts names to a conservative slug charset.
* :func:`safe_join` resolves the final path and asserts it is still inside the
  intended base directory, which also catches symlink escapes.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

#: Map names must be lowercase slugs. Deliberately strict: these become
#: directory names inside a BeamNG mod archive, and BeamNG itself dislikes
#: spaces and non-ASCII level names.
MAP_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,49}$")

MAP_NAME_HELP = (
    "Map name must be 3-50 characters, lowercase, and may contain only "
    "letters, digits, underscores and hyphens (e.g. 'san_francisco_downtown')."
)


class UnsafePathError(ValueError):
    """Raised when a caller-supplied name would escape its base directory."""


def is_valid_map_name(name: str) -> bool:
    """True if ``name`` is a safe map identifier."""
    return bool(MAP_NAME_PATTERN.fullmatch(name))


def slugify_map_name(name: str) -> str:
    """
    Convert arbitrary user input into a valid map name.

    Used by the API so a friendly name like ``"San Francisco Downtown"``
    becomes ``"san_francisco_downtown"`` rather than being rejected outright.
    Returns an empty string if nothing usable remains, which the caller should
    treat as a validation error.
    """
    # Strip accents so "Zürich" becomes "zurich" rather than losing the vowel.
    normalised = unicodedata.normalize("NFKD", name)
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii")

    # Hyphens are legal in map names, so they survive; everything else that is
    # not alphanumeric collapses into a single underscore.
    slug = re.sub(r"[^a-zA-Z0-9-]+", "_", ascii_only).lower()
    slug = re.sub(r"_{2,}", "_", slug).strip("_-")

    return slug[:50].strip("_-")


def safe_join(base: Path, *parts: str) -> Path:
    """
    Join ``parts`` onto ``base`` and verify the result stays under ``base``.

    Args:
        base: Directory the result must remain inside.
        parts: Untrusted path components.

    Returns:
        The resolved absolute path.

    Raises:
        UnsafePathError: If the resolved path escapes ``base``.
    """
    base_resolved = base.resolve()
    candidate = base_resolved.joinpath(*parts)

    # ``strict=False`` so the path does not have to exist yet - we are often
    # resolving a destination we are about to create.
    resolved = candidate.resolve(strict=False)

    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise UnsafePathError(f"Path {'/'.join(parts)!r} escapes base directory {base_resolved}")

    return resolved
