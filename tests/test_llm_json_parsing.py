"""
Recovering JSON from model replies.

Every case here is a shape a language model actually produces when asked for
JSON. Failing to parse one throws away a completed inference and yields a map
with no roads, with nothing in the logs to explain it - so the tolerant path is
worth pinning down precisely.
"""

from __future__ import annotations

import pytest

from services.ollama.json_parsing import extract_json, normalise_segmentation

CLASSES = ["roads", "buildings", "water", "forest"]


# -- extraction -----------------------------------------------------------------


def test_plain_json():
    assert extract_json('{"roads": []}') == {"roads": []}


def test_markdown_fenced_json():
    reply = 'Here is the result:\n```json\n{"roads": [{"width": 8}]}\n```\nHope that helps!'
    assert extract_json(reply) == {"roads": [{"width": 8}]}


def test_unlabelled_code_fence():
    assert extract_json('```\n{"roads": []}\n```') == {"roads": []}


def test_json_surrounded_by_prose():
    reply = 'I detected two roads. {"roads": [1, 2]} Let me know if you need more.'
    assert extract_json(reply) == {"roads": [1, 2]}


def test_two_objects_are_not_merged():
    """
    The regression.

    A greedy `(\\{.*\\})` spans from the first brace to the last, so two objects
    became one malformed blob and the whole reply was discarded. Balanced
    scanning returns the first complete value.
    """
    reply = 'First: {"roads": [1]} and second: {"buildings": [2]}'
    assert extract_json(reply) == {"roads": [1]}


def test_prose_containing_a_brace_after_the_json():
    reply = '{"roads": []} — note that the set notation {x} is unrelated.'
    assert extract_json(reply) == {"roads": []}


def test_braces_inside_strings_do_not_end_the_scan():
    reply = '{"note": "a } inside a string", "roads": []}'
    assert extract_json(reply) == {"note": "a } inside a string", "roads": []}


def test_escaped_quotes_inside_strings():
    assert extract_json(r'{"note": "he said \"hi\"", "roads": []}')["roads"] == []


def test_trailing_commas_are_tolerated():
    assert extract_json('{"roads": [1, 2,],}') == {"roads": [1, 2]}


def test_line_comments_are_stripped():
    reply = '{\n  "roads": [], // nothing found\n  "buildings": []\n}'
    assert extract_json(reply) == {"roads": [], "buildings": []}


def test_top_level_array():
    assert extract_json('[{"class": "road"}]') == [{"class": "road"}]


def test_nested_structures_survive():
    reply = '{"roads": [{"centerline": [[1, 2], [3, 4]], "meta": {"width": 8}}]}'
    assert extract_json(reply)["roads"][0]["meta"]["width"] == 8


@pytest.mark.parametrize(
    "reply",
    ["", "   ", "I could not find anything.", "{not json at all", "```json\nbroken{\n```"],
)
def test_unparseable_replies_return_none(reply):
    assert extract_json(reply) is None


# -- normalisation --------------------------------------------------------------


def test_requested_shape_passes_through():
    result = normalise_segmentation({"roads": [{"a": 1}], "buildings": []}, CLASSES)

    assert result["roads"] == [{"a": 1}]
    assert result["buildings"] == []
    # Classes the model omitted still appear, empty.
    assert result["water"] == []


def test_unknown_keys_are_ignored():
    result = normalise_segmentation({"roads": [{"a": 1}], "unicorns": [{"b": 2}]}, CLASSES)

    assert result["roads"] == [{"a": 1}]
    assert "unicorns" not in result


def test_flat_list_is_grouped_by_class():
    """
    A bare list used to be discarded entirely, losing every detected feature.
    """
    payload = [
        {"class": "road", "width": 8},
        {"class": "building", "height": 12},
        {"class": "road", "width": 6},
    ]

    result = normalise_segmentation(payload, CLASSES)

    assert len(result["roads"]) == 2
    assert len(result["buildings"]) == 1


def test_singular_and_plural_labels_both_match():
    payload = [{"class": "roads"}, {"class": "road"}]
    assert len(normalise_segmentation(payload, CLASSES)["roads"]) == 2


def test_type_and_label_fields_are_accepted():
    payload = [{"type": "road"}, {"label": "building"}]
    result = normalise_segmentation(payload, CLASSES)

    assert len(result["roads"]) == 1
    assert len(result["buildings"]) == 1


@pytest.mark.parametrize("wrapper", ["features", "results", "detections", "objects"])
def test_wrapped_feature_lists_are_unwrapped(wrapper):
    payload = {wrapper: [{"class": "road"}, {"class": "water"}]}
    result = normalise_segmentation(payload, CLASSES)

    assert len(result["roads"]) == 1
    assert len(result["water"]) == 1


def test_non_dict_entries_are_dropped():
    result = normalise_segmentation({"roads": [{"a": 1}, "garbage", None]}, CLASSES)
    assert result["roads"] == [{"a": 1}]


@pytest.mark.parametrize("payload", [None, "a string", 42, True])
def test_unusable_payloads_yield_empty_classes(payload):
    assert normalise_segmentation(payload, CLASSES) == {name: [] for name in CLASSES}


def test_a_realistic_reply_end_to_end():
    reply = """Looking at the satellite image, I can identify the following:

```json
{
  "roads": [
    {"class": "road", "centerline": [[37.90, -122.60], [37.91, -122.59]], "width": 8.0},
  ],
  "buildings": [
    {"footprint": [[37.900, -122.600], [37.901, -122.600], [37.901, -122.599]], "height": 12}
  ],
  "water": [],
  "forest": []
}
```

Let me know if you would like a more detailed analysis."""

    result = normalise_segmentation(extract_json(reply), CLASSES)

    assert len(result["roads"]) == 1
    assert len(result["buildings"]) == 1
    assert result["roads"][0]["width"] == 8.0
