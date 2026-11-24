"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""Explanations for searches that match nothing."""

import asyncio
import re
from typing import Any

import httpx

from .sql_fieldtext import required_text_values
from . import engine, query_text


DIAGNOSED_TERM_LIMIT = 12


async def _phrase_query(segments: list[str], numbers_indexed: bool) -> str | None:
    """Text query requiring each segment as a phrase; None if nothing searchable.

    A word the index cannot hold (a standalone number when numbers are not
    indexed) would make the whole phrase fail, so it splits the phrase instead.
    Wildcard characters are dropped and a colon is turned into what the
    indexer made of it, so the text is searched literally.
    """
    colon = " " if ":" in await query_text.term_separators() else ""
    phrases = []
    for segment in segments:
        segment = re.sub(r"[*?\"]", " ", segment).replace(":", colon)
        group: list[str] = []
        for token in query_text.QUERY_TOKEN.findall(segment):
            token = token.strip(query_text.TOKEN_EDGES)
            if not token:
                continue  # lone punctuation is only a separator
            if query_text.is_number(token) and not numbers_indexed:
                if group:
                    phrases.append('"' + " ".join(group) + '"')
                group = []
            else:
                group.append(token)
        if group:
            phrases.append('"' + " ".join(group) + '"')
    return " AND ".join(dict.fromkeys(phrases)) or None


async def _where_value_diagnosis(where: str) -> dict[str, Any] | None:
    """A where filter can match nothing because few documents have the field,
    while its value still appears in document text: say where it does.

    Only values the filter requires are checked (not those under NOT, != or
    NOT LIKE). Each is counted as a phrase in the text; a LIKE pattern is split
    at its wildcards and its pieces required together.
    """
    try:
        numbers_indexed = await query_text.numbers_indexed()
    except (RuntimeError, ValueError, httpx.HTTPError):
        return None
    queries: dict[str, str] = {}
    for literal, like in required_text_values(where):
        segments = [part.strip() for part in re.split(r"[%_]+", literal)] if like else [literal]
        shown = " ".join(part for part in segments if part)
        query = await _phrase_query(segments, numbers_indexed)
        if query and shown not in queries:
            queries[shown] = query
    if not queries:
        return None
    try:
        counts = await asyncio.gather(*(
            engine.count_documents({"Text": query})
            for query in list(queries.values())[:DIAGNOSED_TERM_LIMIT]
        ))
    except (RuntimeError, ValueError, httpx.HTTPError):
        return None
    found = {shown: count for shown, (count, _) in zip(queries, counts) if count}
    if not found:
        return None
    return {
        "where_values_in_text": found,
        "advice": (
            "No document matched the where filter, but these values occur in "
            "document text (counts are documents whose text contains the value). "
            "The field may be missing from the documents that mention them: "
            "search them as text instead of concluding they are absent."
        ),
    }


async def zero_hit_diagnosis(
    text: str, where: str = "", filters: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Explain an empty search from the term index, so models stop guessing.

    filters are the Content parameters the search sent (from _filters), so an
    empty result can be traced to the filters among them.
    """
    terms = query_text.query_terms(text)[:DIAGNOSED_TERM_LIMIT]
    if not terms:
        return await _where_value_diagnosis(where) if where.strip() else None
    try:
        counts = await asyncio.gather(*(query_text.term_document_count(t) for t in terms))
        numbers_indexed = await query_text.numbers_indexed()
    except (RuntimeError, ValueError, httpx.HTTPError):
        return None
    absent = [term for term, count in zip(terms, counts) if count == 0]
    wildcards = [term for term in absent if "*" in term or "?" in term]
    numbers = [term for term in absent if query_text.is_number(term) and not numbers_indexed]
    missing = [term for term in absent if term not in wildcards and term not in numbers]
    advice = []
    if missing:
        advice.append(
            "terms_in_no_document occur nowhere in the index, so no text search for "
            "them can match: do not retry them with other spellings, case, quotes, "
            "wildcards or fields. If one is the identifier the question is about "
            "(an ID, code, reference number or name), the document is "
            "very likely not in this index: try at most one other distinctive detail "
            "from the question, then report it as not found."
        )
    if wildcards:
        advice.append(
            "wildcards_matching_no_term expanded to no indexed term. Wildcard "
            "expansion may not cover letter-digit identifiers, so this does not show "
            "absence: search the exact term instead."
        )
    if numbers:
        advice.append(
            "unindexed_numbers cannot match because this index has no standalone "
            "numbers; their absence proves nothing. Search the other details of the "
            "question (names, places, dates in words, alphanumeric identifiers)."
        )
    diagnosis: dict[str, Any] = {"terms_in_no_document": missing}
    if wildcards:
        diagnosis["wildcards_matching_no_term"] = wildcards
    if numbers:
        diagnosis["unindexed_numbers"] = numbers
    if not advice:
        applied = [engine.FILTER_NAMES.get(name, name) for name in filters or {} if name != "Text"]
        unfiltered, advice = await _structure_advice(text, applied)
        if unfiltered is not None:
            diagnosis["documents_matching_text_without_filters"] = unfiltered
    diagnosis["advice"] = " ".join(advice)
    return diagnosis


async def _structure_advice(
    text: str, filters: list[str],
) -> tuple[int | None, list[str]]:
    """Every term exists, so the filters or the query's own structure emptied it.

    Words are joined with OR by default, so plain words that all exist always
    match something; check the filters first with one unfiltered count.
    """
    unfiltered = None
    if filters:
        try:
            unfiltered, _ = await engine.count_documents({"Text": text})
        except (RuntimeError, ValueError, httpx.HTTPError):
            unfiltered = None
        if unfiltered:
            advice = [
                f"Every term occurs and documents_matching_text_without_filters "
                f"match the text alone, but {' and '.join(filters)} excluded all of "
                "them: relax or drop the filter."
            ]
            if "where" in filters:
                advice.append(
                    "A where condition fails on documents that lack the field, so "
                    "search its value as text instead of concluding it is absent."
                )
            if "min_date" in filters or "max_date" in filters:
                advice.append(
                    "min_date and max_date filter the document date, not the date of "
                    "an event the document describes."
                )
            return unfiltered, advice
    advice = []
    if re.search(r'"[^"]+"', text):
        advice.append(
            "Every word of the quoted phrase occurs, but never together in that "
            "order: search the words without quotes, or with NEAR."
        )
    if any(query_text.RESTRICTING_OPERATOR.fullmatch(token) for token in query_text.QUERY_TOKEN.findall(text)):
        advice.append(
            "Every term occurs, but no document meets all the AND, NOT or proximity "
            "conditions together: drop the least essential required term."
        )
    if query_text.FIELD_RESTRICTION.search(text):
        advice.append(
            "A term restricted to a field (term:FIELD) must occur in that field: "
            "drop the restriction or filter with where instead."
        )
    if not advice:
        advice.append(
            "Every term occurs in the index, yet nothing matched: report what was "
            "searched rather than retrying variants."
        )
    if engine.CONTENT_SECURITY_INFO:
        # Term counts cover the whole index; search results only what the user may see.
        advice.append(
            "Results include only documents this user is permitted to see, so the "
            "documents containing these terms may exist but not be visible."
        )
    return unfiltered, advice
