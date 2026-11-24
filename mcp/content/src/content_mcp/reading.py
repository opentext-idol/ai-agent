"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""Shaping hits and documents for the model: fields, excerpts and text."""

import re
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from . import engine, field_info, query_text


def bounded_value(
    value: Any, remaining: int, path: str = "",
) -> tuple[Any, int, list[str], list[str]]:
    if isinstance(value, str):
        if len(value) <= remaining:
            return value, remaining - len(value), [], []
        return value[:remaining], 0, [path], []
    if isinstance(value, dict):
        result = {}
        truncated_fields = []
        omitted_fields = []
        for key, item in value.items():
            item_path = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
            if remaining <= 0:
                omitted_fields.append(item_path)
                continue
            bounded, remaining, truncated, omitted = bounded_value(
                item, remaining, item_path,
            )
            result[key] = bounded
            truncated_fields.extend(truncated)
            omitted_fields.extend(omitted)
        return result, remaining, truncated_fields, omitted_fields
    if isinstance(value, list):
        result = []
        truncated_fields = []
        omitted_fields = []
        for index, item in enumerate(value):
            item_path = f"{path}/{index}"
            if remaining <= 0:
                omitted_fields.append(item_path)
                continue
            bounded, remaining, truncated, omitted = bounded_value(
                item, remaining, item_path,
            )
            result.append(bounded)
            truncated_fields.extend(truncated)
            omitted_fields.extend(omitted)
        return result, remaining, truncated_fields, omitted_fields
    return value, remaining, [], []


EXCERPT_CHARS = 1000
EXCERPT_SOURCE_CHARS = 200_000


def excerpt_patterns(text: str) -> list[re.Pattern[str]]:
    """Case-insensitive word-prefix patterns for the query's terms.

    Prefixes stand in for stemming, so 'injured' also finds 'injuries'.
    """
    patterns = []
    for term in query_text.query_terms(text):
        term = term.strip("*?")
        if "*" in term or "?" in term or len(term) < 3:
            continue
        stem = term if len(term) <= 5 else term[:max(5, len(term) - 3)]
        patterns.append(re.compile(r"\b" + re.escape(stem), re.IGNORECASE))
    return patterns


def _best_window(value: str, patterns: list[re.Pattern[str]], size: int) -> int:
    """Start of a size-character window with the strongest mix of query terms.

    Each term weighs 1/(its occurrences in the text), so an identifier repeated
    in every page header counts for little next to a term found once.
    """
    found = [[match.start() for match in pattern.finditer(value)] for pattern in patterns]
    matches = sorted((pos, index) for index, positions in enumerate(found) for pos in positions)
    if not matches:
        return 0
    weight = [1 / len(positions) if positions else 0 for positions in found]
    span = size * 3 // 4
    best, best_score, low = matches[0][0], -1.0, 0
    for high in range(len(matches)):
        while matches[high][0] - matches[low][0] > span:
            low += 1
        window = matches[low:high + 1]
        score = sum(weight[index] for index in {i for _, i in window})
        if score > best_score + 1e-9:
            # Anchor on the strongest terms, not on a repeated weak one.
            strongest = max(weight[i] for _, i in window)
            best = min(pos for pos, i in window if weight[i] >= strongest / 2)
            best_score = score
    return max(0, best - size // 4)


def excerpted_hit(
    hit: dict[str, Any], windowed: set[str], patterns: list[re.Pattern[str]],
) -> dict[str, Any]:
    fields = hit.get("fields")
    if not isinstance(fields, dict):
        return hit
    wanted = {field_info.field_path(f).casefold() for f in windowed}
    offsets = {}
    for name, value in fields.items():
        values = engine.values(value)
        if name.casefold() in wanted and values and all(isinstance(v, str) for v in values):
            joined = "\n\n".join(values)
            start = _best_window(joined, patterns, EXCERPT_CHARS)
            fields[name] = joined[start:start + EXCERPT_CHARS]
            offsets[name] = start
        else:
            fields[name] = [
                v[:EXCERPT_CHARS] if isinstance(v, str) else v for v in values
            ] if isinstance(value, list) else (
                value[:EXCERPT_CHARS] if isinstance(value, str) else value
            )
    if offsets:
        hit["excerpt_offsets"] = offsets
    return hit


def document_fields(hit: dict[str, Any]) -> dict[str, Any]:
    """Flatten a hit's content into {field: value or [values]}."""
    content = hit.get("content")
    if not isinstance(content, dict):
        return {}
    fields: dict[str, list[Any]] = {}
    for document in engine.values(content.get("DOCUMENT", content)):
        if not isinstance(document, dict):
            continue
        for name, value in document.items():
            if name.upper() == "DREREFERENCE":
                continue
            fields.setdefault(name, []).extend(
                item["$"] if isinstance(item, dict) and "$" in item else item
                for item in engine.values(value)
            )
    return {
        name: values[0] if len(values) == 1 else values
        for name, values in fields.items()
    }


def compact_hit(hit: dict[str, Any]) -> dict[str, Any]:
    result = {"reference": hit.get("reference")}
    if hit.get("title"):
        result["title"] = hit["title"]
    fields = document_fields(hit)
    if fields:
        result["fields"] = fields
    return result


# Fields with more values than this are left out of all-field reads.
BULKY_FIELD_VALUES = 100


def remove_fields(
    fields: dict[str, Any], drop: Callable[[str, Any], bool], prefix: str = "",
) -> dict[str, Any]:
    """Remove the fields, at any depth, for which drop(path, value) is true.

    Returns the removed values by path."""
    removed = {}
    for name in list(fields):
        path = prefix + name
        if drop(path, fields[name]):
            removed[path] = fields.pop(name)
            continue
        for value in engine.values(fields[name]):
            if isinstance(value, dict):
                removed.update(remove_fields(value, drop, path + "/"))
    return removed


# Recently read document texts, so paging and batch reads of the same
# document cost one GetContent. Bounded by total characters and age.
_TEXT_CACHE: "OrderedDict[str, tuple[float, str, list[Any]]]" = OrderedDict()
TEXT_CACHE_MAX_CHARS = 20_000_000
TEXT_CACHE_TTL_SECONDS = 600


async def document_text(reference: str) -> tuple[str, list[Any]]:
    cached = _TEXT_CACHE.get(reference)
    if cached and time.monotonic() - cached[0] < TEXT_CACHE_TTL_SECONDS:
        _TEXT_CACHE.move_to_end(reference)
        return cached[1], cached[2]
    text, warnings = await _fetch_document_text(reference)
    if not warnings and len(text) <= TEXT_CACHE_MAX_CHARS:
        _TEXT_CACHE[reference] = (time.monotonic(), text, warnings)
        _TEXT_CACHE.move_to_end(reference)
        total = sum(len(entry[1]) for entry in _TEXT_CACHE.values())
        while total > TEXT_CACHE_MAX_CHARS:
            _, (_, evicted, _) = _TEXT_CACHE.popitem(last=False)
            total -= len(evicted)
    return text, warnings


async def _fetch_document_text(reference: str) -> tuple[str, list[Any]]:
    text_fields = await field_info.text_fields()
    data, warnings = await engine.request("GetContent", {
        "Reference": engine.reference_parameter(reference),
        "Print": "Fields",
        "PrintFields": ",".join(text_fields),
    })
    hits = engine.entries(data, "hit")
    if len(hits) != 1:
        raise RuntimeError(
            "Content GetContent did not return exactly one document; "
            f"use read_document to inspect the response. Warnings: {warnings!r}"
        )
    fields = document_fields(hits[0])
    parts = [value for field in text_fields for value in engine.values(fields.get(field, []))]
    if not parts:
        raise RuntimeError(
            f"Document has no text in {', '.join(text_fields)}; use read_document "
            f"with explicit print_fields. Warnings: {warnings!r}"
        )
    if not all(isinstance(part, str) for part in parts):
        raise RuntimeError("Content GetContent returned invalid document text")

    return "\n\n".join(parts), warnings


def text_page(
    reference: str, text: str, offset: int, max_chars: int, warnings: list[Any],
) -> dict[str, Any]:
    if offset > len(text):
        raise ValueError(f"offset exceeds document text length ({len(text)})")
    page = text[offset:offset + max_chars]
    end = offset + len(page)
    has_more = end < len(text)
    return {
        "reference": reference,
        "text": page,
        "offset": offset,
        "max_chars": max_chars,
        "total_chars": len(text),
        "has_more": has_more,
        "next_offset": end if has_more else None,
        "warnings": warnings,
    }
