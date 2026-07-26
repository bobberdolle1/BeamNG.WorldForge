"""
Recover JSON from a language model's reply.

Models are asked for JSON and mostly comply, but the reply routinely arrives
wrapped in prose, fenced in markdown, or carrying trailing commas and comments
that ``json.loads`` rejects. Getting this wrong means a successful, paid-for
inference is thrown away and the map comes out empty.

The previous extractor used ``re.search(r'(\\{.*\\})', text, re.DOTALL)``. Being
greedy, that spans from the *first* opening brace to the *last* closing one, so
a reply containing two separate objects - or an object followed by a sentence
that happens to contain a brace - was captured as one malformed blob and
discarded. This module scans for balanced delimiters instead, which finds the
first complete value regardless of what surrounds it.
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.logging_config import get_logger

logger = get_logger(__name__)

#: ```json ... ``` or ``` ... ```
_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)

#: A comma directly before a closing brace or bracket.
_TRAILING_COMMA_PATTERN = re.compile(r",(\s*[}\]])")

#: Line comments outside of strings. Models add these when "explaining".
_LINE_COMMENT_PATTERN = re.compile(r"(?<![:\"'])//[^\n\"']*$", re.MULTILINE)


def extract_json(text: str) -> Any | None:
    """
    Pull the first JSON value out of a model reply.

    Tries, in order: the whole reply, each fenced code block, then a balanced
    scan of the raw text. Each candidate is also retried with trailing commas
    and line comments removed.

    Returns:
        The parsed value, or ``None`` if nothing parseable was found.
    """
    if not text or not text.strip():
        return None

    for candidate in _candidates(text):
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed

    logger.warning("No JSON found in model reply (%d chars)", len(text))
    return None


def _candidates(text: str):
    """Yield progressively more permissive slices of the reply."""
    yield text

    for match in _FENCE_PATTERN.finditer(text):
        yield match.group(1)

    yield from _balanced_spans(text)


def _balanced_spans(text: str):
    """
    Yield substrings that start at a brace/bracket and close in balance.

    Quote- and escape-aware, so a ``}`` inside a string value does not end the
    scan early.
    """
    openers = {"{": "}", "[": "]"}

    for start, character in enumerate(text):
        if character not in openers:
            continue

        depth = 0
        in_string = False
        escaped = False

        for position in range(start, len(text)):
            current = text[position]

            if escaped:
                escaped = False
                continue
            if current == "\\":
                escaped = True
                continue
            if current == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if current in openers:
                depth += 1
            elif current in ("}", "]"):
                depth -= 1
                if depth == 0:
                    yield text[start : position + 1]
                    break


def _try_parse(candidate: str) -> Any | None:
    """Parse a candidate, retrying once with common model slop removed."""
    candidate = candidate.strip()
    if not candidate:
        return None

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    repaired = _TRAILING_COMMA_PATTERN.sub(r"\1", _LINE_COMMENT_PATTERN.sub("", candidate))
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def normalise_segmentation(payload: Any, classes: list[str]) -> dict[str, list[dict[str, Any]]]:
    """
    Coerce a parsed reply into ``{class name: [feature, ...]}``.

    Models answer in several shapes for the same prompt. Accepting all of them
    is the difference between a map with roads and a map without: the previous
    code returned an empty result for anything that was not already a dict,
    discarding a perfectly good list of features without a word.

    Handles:

    * ``{"roads": [...], "buildings": [...]}`` - the requested shape
    * ``{"features": [{"class": "road", ...}]}`` - a flat list under a wrapper
    * ``[{"class": "road", ...}, ...]`` - a bare list, grouped by ``class``
    """
    empty: dict[str, list[dict[str, Any]]] = {name: [] for name in classes}

    if payload is None:
        return empty

    if isinstance(payload, dict):
        keyed = {
            name: [item for item in payload[name] if isinstance(item, dict)]
            for name in classes
            if isinstance(payload.get(name), list)
        }
        if keyed:
            return {**empty, **keyed}

        for wrapper in ("features", "results", "detections", "objects"):
            if isinstance(payload.get(wrapper), list):
                return _group_by_class(payload[wrapper], classes)

        return empty

    if isinstance(payload, list):
        return _group_by_class(payload, classes)

    return empty


def _group_by_class(items: list[Any], classes: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Bucket a flat feature list by its ``class``/``type``/``label`` field."""
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in classes}

    # "road" should land in the "roads" bucket, and vice versa.
    aliases = {name.rstrip("s"): name for name in classes}
    aliases.update({name: name for name in classes})

    for item in items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("class") or item.get("type") or item.get("label") or "").lower()
        target = aliases.get(label) or aliases.get(label.rstrip("s"))
        if target:
            grouped[target].append(item)

    return grouped
