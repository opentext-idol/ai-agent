"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""What the index knows about its fields: names, types, coverage and resolution."""

import asyncio
import difflib
import os
import re
import time
from collections.abc import Iterable
from typing import Any

import httpx

from .sql_fieldtext import DATE_TYPES, Resolver
from . import engine


def field_path(name: str) -> str:
    """A field name as an index path: no outer slashes or leading DOCUMENT/."""
    path = name.strip("/")
    if path.casefold().startswith("document/"):
        return path[len("document/"):]
    return path


def tag_names(data: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """(path, configured types) for each field in a GetTagNames response."""
    tags = []
    for entry in engine.entries(data, "name"):
        name, types = entry.get("$"), entry.get("@types", "")
        if isinstance(name, str) and isinstance(types, str) and (path := field_path(name)):
            tags.append((path, [t.strip().casefold() for t in types.split(",") if t.strip()]))
    return tags


def _field_types(data: dict[str, Any]) -> dict[str, frozenset[str]]:
    """Configured types per field path, merging fields listed more than once."""
    fields: dict[str, frozenset[str]] = {}
    for path, types in tag_names(data):
        fields[path] = fields.get(path, frozenset()) | frozenset(types)
    return fields


def _matching_paths(field: str, paths: Iterable[str]) -> list[str]:
    """Paths a field name refers to: its exact path, else for a bare name
    every field whose last component it is."""
    wanted = field_path(field).casefold()
    matches = [path for path in paths if path.casefold() == wanted]
    if not matches and "/" not in wanted:
        matches = [path for path in paths if path.rsplit("/", 1)[-1].casefold() == wanted]
    return matches


# Documents holding a value per field path (casefolded), filled lazily for
# fields used in where. Real indexes often configure fields that only a subset
# of documents (or none) actually carry.
FIELD_COVERAGE: dict[str, int] = {}


# A field present in at least this share of documents counts as universal.
FULL_COVERAGE_SHARE = 0.95
# A where condition on a field present in fewer than this share of documents
# warns that the filter excludes much of the index.
SPARSE_FIELD_SHARE = 0.5


# Whether the engine collects field statistics; None until first asked.
_FIELD_STATS_AVAILABLE: bool | None = None


async def load_field_statistics() -> bool:
    """Fill _FIELD_COVERAGE from the engine's field statistics, once.

    One request covers every field, keyed by casefolded path. Returns
    whether the engine collects statistics ([Server] CollectFieldStatistics);
    without them, coverage falls back to EXISTS counts per field.

    Statistics cover the whole index, regardless of the caller's permissions.
    Empty values count as occurrences, so they are subtracted; a document
    holding both an empty and a non-empty value makes this slightly low.
    """
    global _FIELD_STATS_AVAILABLE
    if _FIELD_STATS_AVAILABLE is not None:
        return _FIELD_STATS_AVAILABLE
    try:
        data, _ = await engine.request("GetTagNames", {"FieldType": "All", "FieldStats": "True"})
    except (RuntimeError, ValueError, httpx.HTTPError):
        return False
    counts: dict[str, int] = {}
    for name in engine.entries(data, "name"):
        if "@docOccs" not in name or not isinstance(name.get("$"), str):
            continue
        try:
            count = max(int(name["@docOccs"]) - int(name.get("@emptyOccs") or 0), 0)
        except ValueError:
            continue
        counts[field_path(name["$"]).casefold()] = count
    FIELD_COVERAGE.update(counts)
    _FIELD_STATS_AVAILABLE = bool(counts)
    return _FIELD_STATS_AVAILABLE


async def _field_coverage(paths: list[str]) -> dict[str, int]:
    """Documents with a value in each field; unknown fields are left out.

    Counts come from the engine's field statistics when it collects them,
    else from one exact EXISTS count per field; both are cached.
    """
    await load_field_statistics()

    async def count(path: str) -> None:
        try:
            total, _ = await engine.count_documents({
                "Text": "*", "FieldText": f"EXISTS{{}}:{path}",
            })
        except (RuntimeError, ValueError, httpx.HTTPError):
            return
        if total is not None:
            FIELD_COVERAGE[path.casefold()] = total

    await asyncio.gather(*(
        count(path) for path in paths if path.casefold() not in FIELD_COVERAGE
    ))
    return {
        path: FIELD_COVERAGE[path.casefold()]
        for path in paths if path.casefold() in FIELD_COVERAGE
    }


async def sparse_field_warnings(paths: list[str]) -> list[str]:
    if not paths:
        return []
    try:
        total = await engine.index_total()
        coverage = await _field_coverage(paths)
    except (RuntimeError, ValueError, httpx.HTTPError):
        return []
    if not total:
        return []
    return [
        f"{total - count} of {total} documents have no value in {path} and cannot "
        "match a condition on it, so a low or zero result here does not show that "
        "those documents lack the information."
        for path, count in coverage.items()
        if count < total * SPARSE_FIELD_SHARE
    ]


_FIELDS: tuple[float, dict[str, frozenset[str]]] | None = None
FIELDS_TTL_SECONDS = 600


async def _index_fields() -> dict[str, frozenset[str]]:
    """Configured types per field path in the index (no DOCUMENT/ prefix), cached briefly."""
    global _FIELDS
    if _FIELDS is None or time.monotonic() - _FIELDS[0] > FIELDS_TTL_SECONDS:
        data, _ = await engine.request("GetTagNames", {"FieldType": "All", "TypeDetails": "True"})
        _FIELDS = (time.monotonic(), _field_types(data))
    return _FIELDS[1]


async def field_names() -> list[str]:
    """All field paths in the index (no DOCUMENT/ prefix), cached briefly."""
    return list(await _index_fields())


async def unknown_print_fields(print_fields: list[str] | None) -> dict[str, list[str]]:
    """Requested fields that exist nowhere in the index, with close matches.

    Content silently returns nothing for an unknown PrintFields name, which
    reads as an empty field; name the mistake instead.
    """
    if not print_fields:
        return {}
    try:
        paths = await field_names()
    except (RuntimeError, ValueError, httpx.HTTPError):
        return {}
    if not paths:
        return {}
    known = {path.casefold() for path in paths} | {
        path.rsplit("/", 1)[-1].casefold() for path in paths
    }
    unknown = {}
    for field in print_fields:
        name = field_path(field.strip())
        folded = name.casefold()
        if not name or folded in known or folded.startswith(("autn_", "dre")):
            continue
        unknown[field] = _closest_fields(name, paths)
    return unknown


def _closest_fields(name: str, paths: list[str], n: int = 3) -> list[str]:
    """Fields containing the name (e.g. EVENT_DATE in X_EVENT_DATE), else fuzzy matches."""
    folded = name.casefold()
    containing = sorted((p for p in paths if folded in p.casefold()), key=len)
    close = difflib.get_close_matches(name.upper(), paths, n=n, cutoff=0.75)
    return list(dict.fromkeys(containing + close))[:n]


def unknown_field_warning(unknown: dict[str, list[str]]) -> list[str]:
    return [
        f"print_fields {name!r} does not exist in this index, so it returned nothing"
        + (f"; closest: {', '.join(close)}" if close else "")
        + ". The information may only be in the document text."
        for name, close in unknown.items()
    ]


async def where_resolver(where: str) -> Resolver | None:
    if not where.strip():
        return None
    data, _ = await engine.request("GetTagNames", {"FieldType": "All", "TypeDetails": "True"})
    fields = _field_types(data)
    paths = sorted(fields)

    used: list[str] = []

    def resolve(field: str) -> tuple[str, frozenset[str]]:
        wanted = field_path(field).casefold()
        matches = _matching_paths(field, paths)
        if len(matches) == 1:
            if matches[0] not in used:
                used.append(matches[0])
            return matches[0], fields[matches[0]]
        if matches:
            raise ValueError(
                f"Ambiguous field {field!r} in where; use one of {matches[:10]}"
            )
        close = difflib.get_close_matches(field, paths, n=5, cutoff=0.5)
        hint = ""
        if wanted == "reference" or wanted.startswith("autn_"):
            hint = " Metadata fields are not queryable; use read_document for a known reference."
        raise ValueError(
            f"Unknown field {field!r} in where; use get_fields to find valid "
            f"paths. Closest: {close}.{hint}"
        )

    resolve.used = used  # type: ignore[attr-defined]
    return resolve


async def date_field(field_name: str) -> tuple[str, list[Any]]:
    """Resolve a field name to the path of a configured Date or NumericDate field."""
    data, warnings = await engine.request("GetTagNames", {"FieldType": "All", "TypeDetails": "True"})
    fields = _field_types(data)
    matches = _matching_paths(field_name, fields)
    dates = [path for path in matches if fields[path] & DATE_TYPES]
    if len(dates) > 1:
        raise ValueError(f"Ambiguous date field {field_name!r}; use one of {dates[:10]}")
    if dates:
        return dates[0], warnings
    if matches:
        types = ", ".join(sorted(set().union(*(fields[path] for path in matches))))
        raise ValueError(
            f"{field_name!r} is configured as {types or 'no type'}, not Date or NumericDate. "
            "Custom calendar grouping requires a configured date field; "
            "ISO 8601 formatting alone does not establish the field type."
        )
    raise ValueError(
        f"{field_name!r} is not a configured date field; use get_fields to "
        f"choose a Date or NumericDate field. GetTagNames warnings: {warnings!r}"
    )


async def vector_fields() -> set[str]:
    """Casefolded paths of fields configured as VectorType; empty if unknown."""
    try:
        fields = await _index_fields()
    except (RuntimeError, ValueError, httpx.HTTPError):
        return set()
    return {path.casefold() for path, types in fields.items() if "vector" in types}


_TEXT_FIELDS: list[str] | None = None


async def text_fields() -> list[str]:
    """Narrative text fields: CONTENT_TEXT_FIELDS, else Index-type fields, else DRECONTENT."""
    global _TEXT_FIELDS
    if _TEXT_FIELDS is None:
        fields = [
            field.strip() for field in os.environ.get("CONTENT_TEXT_FIELDS", "").split(",")
            if field.strip()
        ]
        if not fields:
            data, _ = await engine.request("GetTagNames", {"FieldType": "Index"})
            fields = [path for path, _ in tag_names(data)]
        _TEXT_FIELDS = fields or ["DRECONTENT"]
    return _TEXT_FIELDS
