"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""The server instructions: workflow guidance and a summary of the index's fields."""

import asyncio
import re
from typing import Any

import httpx

from . import engine, field_info, reading


WORKFLOW_GUIDANCE = """\
Answer with as few tool calls as possible, and stop as soon as the evidence answers the question.
Answer only from documents these tools return, never from general knowledge; if they do not contain the answer, say it was not found in the index and add no outside facts.
Treat a document as being about the question's subject only if it states the identifying detail the question gives (ID, number, name); otherwise say the match is unconfirmed.
- How many: count_documents, or reuse total_documents from a search with the same filters.
- Breakdowns, top-N, per-year: one aggregate_documents call; never emulate it with per-value counts.
- Finding documents and evidence: search_documents, with the needed fields (including the text field for excerpts) in print_fields.
- Full narrative: read_document_text for one document, read_documents_text for several in one call.
- Structured facts for a known reference: read_document with print_fields.
Use the field names below directly in where, print_fields and field_name; call get_fields only for a field not listed.
Reuse results already returned; only repeat or reword a request to close a specific evidence gap.
Values follow the example formats below; a non-zero result from an exact match on such values is final, so do not re-check it with LIKE or other spellings.
Counts are documents, not unique entities. min_date, max_date and autn_date are the document date, not an event date.
Fields listed under a share of documents exist only on that share; filters and breakdowns on them ignore every other document.
No hits: follow zero_hit_diagnosis. An identifier that occurs in no document is not in this index; report it as not found rather than trying variants, wildcards, other fields or browsing.
A tool error that says it is a configuration error will not succeed on retry: report the limitation."""

SCHEMA_FIELD_LIMIT = 200
SCHEMA_SAMPLE_SIZE = 1000
PROBE_CONCURRENCY = 8
_SCHEMA_TYPES = ("parametric", "numeric", "numericdate", "date", "match", "index")


def _present(value: Any) -> bool:
    return any(isinstance(item, str) and item.strip() for item in engine.values(value))


_OPAQUE_VALUE = re.compile(r"[0-9a-fA-F-]{16,}|[A-Za-z0-9+/=]{24,}|\d{5,}")
LOW_VARIETY_VALUES = 2


class _FieldSample:
    """What a random document sample shows about each field."""

    def __init__(self, sampled: int, values: dict[str, dict[int, str]]):
        self.sampled = sampled
        self.present = {name: len(found) for name, found in values.items()}
        self.examples: dict[str, str] = {}
        self.value_sets: dict[str, list[str]] = {}
        self.constant: set[str] = set()
        for name, found in values.items():
            distinct = list(dict.fromkeys(found.values()))
            if all(_OPAQUE_VALUE.fullmatch(v) for v in distinct[:20]):
                continue  # hashes and IDs: an example adds nothing
            if len(found) >= 20 and len(distinct) == 1:
                self.constant.add(name)  # cannot narrow a search
            elif len(found) >= 20 and len(distinct) <= LOW_VARIETY_VALUES:
                self.value_sets[name] = [_short(v) for v in distinct]
            else:
                self.examples[name] = _short(distinct[0])
        # Fields holding the same varied values in every sampled document are
        # copies (connector aliases, *_FORMATTED twins): list the most readable.
        groups: dict[tuple, list[str]] = {}
        for name, found in values.items():
            if len(found) >= 3 and len(set(found.values())) >= 3:
                groups.setdefault(tuple(sorted(found.items())), []).append(name)
        self.aliases: dict[str, str] = {}
        for names in groups.values():
            keep = min(names, key=lambda n: (sum(ch.isdigit() for ch in n), len(n), n))
            self.aliases.update({name: keep for name in names if name != keep})


def _short(value: str) -> str:
    return value if len(value) <= 30 else value[:30].rstrip() + "…"


async def _sample_fields(paths: list[str]) -> _FieldSample:
    """Field presence, values and aliases from one random document sample.

    One query whatever the index size: exact per-field counts cost one query
    per field, which takes seconds per field on large indexes.
    """
    query = {
        "Text": "*", "MaxResults": str(SCHEMA_SAMPLE_SIZE), "Print": "Fields",
        "PrintFields": ",".join(paths), "MaxPrintChars": "60", "Summary": "Off",
        "Predict": "False",
    }
    try:
        data, _ = await engine.request("Query", {**query, "Sort": "Random"})
    except RuntimeError:  # engines without random sort: fall back to index order
        data, _ = await engine.request("Query", query)
    hits = engine.entries(data, "hit")
    values: dict[str, dict[int, str]] = {}
    for index, hit in enumerate(hits):
        for name, first in _first_values(hit).items():
            values.setdefault(name, {})[index] = first
    return _FieldSample(len(hits), values)


def _first_values(hit: dict[str, Any]) -> dict[str, str]:
    """The first non-blank value of each field in a hit."""
    found = {}
    for name, value in reading.document_fields(hit).items():
        first = next((item.strip() for item in engine.values(value) if isinstance(item, str) and item.strip()), None)
        if first is not None:
            found[name] = first
    return found


async def _probe_unseen(paths: list[str]) -> dict[str, str | None]:
    """Fields the sample missed that some document holds, each with an example.

    The sample cannot tell a rare field from an empty one. Fetching the first
    document with a value stops at the first match instead of counting every
    document, so it stays cheap on large indexes. A field whose probe fails is
    kept with no example, since it may be rare; a field no document holds is
    left out and recorded as having no coverage.
    """
    semaphore = asyncio.Semaphore(PROBE_CONCURRENCY)
    found: dict[str, str | None] = {}

    async def probe(path: str) -> None:
        async with semaphore:
            try:
                data, _ = await engine.request("Query", {
                    "Text": "*", "FieldText": f"EXISTS{{}}:{path}", "MaxResults": "1",
                    "TotalResults": "False", "Predict": "False", "Print": "Fields",
                    "PrintFields": path, "MaxPrintChars": "60", "Summary": "Off",
                })
            except (RuntimeError, ValueError, httpx.HTTPError):
                found[path] = None
                return
        hits = engine.entries(data, "hit")
        if not hits:
            field_info.FIELD_COVERAGE[path.casefold()] = 0
            return
        example = _first_values(hits[0]).get(path)
        found[path] = (
            _short(example) if example and not _OPAQUE_VALUE.fullmatch(example) else None
        )

    await asyncio.gather(*(probe(path) for path in paths))
    return found


def _share_label(share: float | None) -> str:
    if share is None:
        return "coverage unknown"
    if share >= field_info.FULL_COVERAGE_SHARE:
        return "(nearly) all documents"
    if share >= 0.1:
        return f"about {round(share * 20) * 5}% of documents"
    if share >= 0.01:
        return f"about {round(share * 100)}% of documents"
    if share > 0:
        return "under 1% of documents"
    return "rare"


async def server_instructions() -> str:
    """Workflow guidance plus a compact schema summary, so models can skip discovery."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        token = engine.SHARED_CLIENT.set(client)
        try:
            return await _schema_summary()
        finally:
            engine.SHARED_CLIENT.reset(token)


async def _schema_summary() -> str:
    data, _ = await engine.request("GetTagNames", {"FieldType": "All", "TypeDetails": "True"})
    fields = []
    for path, types in field_info.tag_names(data):
        shown = [t for t in types if t in _SCHEMA_TYPES]
        if shown and "reference" not in types:
            fields.append((path, shown))

    total = await engine.index_total()
    text_fields = await field_info.text_fields()
    paths = list(dict.fromkeys([path for path, _ in fields] + text_fields))
    sample = await _sample_fields(paths)
    sampled, present = sample.sampled, sample.present
    aliases = [path for path, _ in fields if path in sample.aliases]
    # Narrative (index) fields stay listed: they are searched, not filtered.
    constant = [
        path for path, shown in fields if path in sample.constant and "index" not in shown
    ]
    # Exact coverage from the engine's field statistics when it collects them;
    # otherwise estimated from the sample, probing fields it missed to tell
    # rare fields from empty ones.
    exact = {
        path: field_info.FIELD_COVERAGE[path.casefold()] / total
        for path in paths if path.casefold() in field_info.FIELD_COVERAGE
    } if total and await field_info.load_field_statistics() else {}
    coverage = {
        path: exact[path] if path in exact else present.get(path, 0) / sampled
        for path in paths if path in exact or sampled
    }
    unseen = await _probe_unseen([
        path for path in paths
        if not present.get(path) and (exact.get(path) or (sampled and path not in exact))
    ]) if sampled or exact else {}
    empty_paths = {
        path for path in paths
        if (path in exact and not exact[path])
        or (path not in exact and sampled and not present.get(path) and path not in unseen)
    }
    empty = [path for path, _ in fields if path in empty_paths]
    fields = [
        field for field in fields
        if field[0] not in sample.aliases and field[0] not in constant and field[0] not in empty
    ]
    share = {path: coverage[path] for path, _ in fields if path in coverage}
    # Real indexes mix record kinds, so group fields by the share of documents
    # carrying them; the widest groups come first and truncation drops the rarest.
    fields = sorted(fields, key=lambda field: -share.get(field[0], 0))[:SCHEMA_FIELD_LIMIT]
    groups: dict[str, list[str]] = {}
    for path, shown in fields:
        detail = ""
        if "index" not in shown:
            if path in sample.value_sets:
                detail = ", values: " + " | ".join(repr(v) for v in sample.value_sets[path])
            elif path in sample.examples:
                detail = f", e.g. {sample.examples[path]!r}"
            elif unseen.get(path):
                detail = f", e.g. {unseen[path]!r}"
        groups.setdefault(_share_label(share.get(path)), []).append(
            f"{path} ({', '.join(shown)}{detail})"
        )
    lines = [WORKFLOW_GUIDANCE, ""]
    if total is not None:
        lines.append(f"Index: {total} documents.")
    if groups:
        lines.append(
            "Fields, grouped by the share of documents with a value"
            + (" (from the index's field statistics):" if exact
               else f" (estimated from {sampled} random documents):" if sampled else ":")
        )
        for label, described in groups.items():
            lines.append(f"- {label}: " + ", ".join(described))
    hidden = len(share) - len(fields)
    if hidden > 0:
        lines.append(f"{hidden} rarer fields are not listed (use get_fields).")
    if aliases or constant:
        lines.append(
            f"Omitted: {len(aliases)} fields duplicating a listed field's values and "
            f"{len(constant)} with one value in every sampled document (use get_fields)."
        )
    if empty:
        lines.append(f"Omitted: {len(empty)} configured fields that no document has a value in.")
    narrative = [
        field + (
            f" ({_share_label(coverage[field])})"
            if field in coverage and coverage[field] < field_info.FULL_COVERAGE_SHARE else ""
        )
        for field in text_fields
        if field not in sample.aliases and field not in empty_paths
    ]
    if narrative:
        lines.append("Narrative text field(s): " + ", ".join(narrative) + ".")
    return "\n".join(lines)
