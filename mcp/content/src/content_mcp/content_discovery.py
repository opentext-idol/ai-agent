"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""Read-only MCP tools for iterative discovery against IDOL Content.

Run with: content-mcp
CONTENT_BASE overrides the Content endpoint, for example
    http://localhost:9100
CONTENT_SECURITY_INFO optionally supplies a server-controlled security token.
Only expose this server to trusted users. When the token is unset, Content's
own access configuration determines which documents the tools can return.
"""

import asyncio
import sys
from typing import Annotated, Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import engine, field_info, query_text, diagnostics, dates, reading, schema


mcp = FastMCP("content_discovery")

PageSize = Annotated[int, Field(ge=1, le=100)]
StartPosition = Annotated[int, Field(ge=1, le=10000)]
ContentLimit = Annotated[int, Field(ge=1000, le=50000)]
ContentOffset = Annotated[int, Field(ge=0)]
BatchReferences = Annotated[list[str], Field(min_length=1, max_length=20)]
BatchContentLimit = Annotated[int, Field(ge=200, le=5000)]
BATCH_TOTAL_CHARS = 50000
BATCH_CONCURRENCY = 5


@mcp.tool()
async def search_documents(
    text: str = "*",
    databases: list[str] | None = None,
    min_date: str = "",
    max_date: str = "",
    where: str = "",
    print_fields: list[str] | None = None,
    start: StartPosition = 1,
    limit: PageSize = 10,
) -> dict[str, Any]:
    """Search documents; returns ranked hits with reference, title and print_fields.

    Request the fields you need in print_fields, including the narrative text
    field for excerpts around the query terms (offsets in excerpt_offsets),
    so a separate read is often unnecessary. Use Boolean operators for precision, e.g.
    term AND "exact phrase". Put structured conditions and dates in
    where, not in text. total_documents is the exact count for these filters;
    do not call count_documents again for the same filters. A zero-hit
    structured filter does not prove absence: the field may be missing from
    relevant documents, so retry once without it and check returned fields.
    A zero-hit text search returns zero_hit_diagnosis; follow its advice.

    text: Natural-language or Boolean query; "*" matches all documents.
    databases: Optional database names.
    min_date, max_date: Optional YYYY-MM-DD bounds on the document date
        (autn_date), not an event date.
    where: SQL WHERE over indexed fields, e.g.
        FIELD_A = 'value' AND FIELD_B >= 10. Supports = <> < <= > >= IN BETWEEN,
        LIKE (% and _), IS [NOT] NULL, AND, OR, NOT. Strings are
        case-insensitive. Compare Date fields by day ('YYYY-MM-DD'), not
        time: the engine may store only the date. Dates in other fields:
        LIKE 'YYYY-MM-DD%'. Text fields reject < > and BETWEEN.
    print_fields: Field names to return with each hit.
    start, limit: One-based paging (limit up to 100); follow next_start.
    """
    text, prefix_warnings = await query_text.clean_query_text(text)
    resolver = await field_info.where_resolver(where)
    filters = engine.query_filters(text, databases, min_date, max_date, where, resolver)
    parameters = {
        **filters,
        "TotalResults": "True",
        "Predict": "False",
        "Combine": "Simple",
        "Start": str(start),
        "MaxResults": str(limit),
        "Print": "Fields" if print_fields else "None",
        "Summary": "Off",
        "MaxPrintChars": str(reading.EXCERPT_CHARS),
    }
    if print_fields:
        parameters["PrintFields"] = ",".join(print_fields)
    # Excerpts from the start of a long text rarely show why it matched, so
    # fetch more of the text fields and cut the excerpt around the query terms.
    excerpt_patterns = reading.excerpt_patterns(text)
    text_fields = {field.casefold() for field in await field_info.text_fields()} if excerpt_patterns else set()
    windowed = {
        field for field in print_fields or []
        if field_info.field_path(field).casefold() in text_fields
    }
    if windowed:
        parameters["MaxPrintChars"] = str(reading.EXCERPT_SOURCE_CHARS)

    data, warnings = await engine.request("Query", parameters)
    engine.reject_predicted(data)

    try:
        total = int(data["totalhits"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Content Query response did not include valid totalhits") from error

    hits = engine.entries(data, "hit")

    warnings = [
        *prefix_warnings,
        *warnings,
        *await query_text.numeric_term_warnings(text),
        *await field_info.sparse_field_warnings(getattr(resolver, "used", [])),
        *field_info.unknown_field_warning(unknown_fields := await field_info.unknown_print_fields(print_fields)),
    ]
    next_start = start + len(hits)
    result = {
        "total_documents": total,
        "next_start": next_start if hits and next_start <= total else None,
        "hits": [
            reading.excerpted_hit(reading.compact_hit(hit), windowed, excerpt_patterns)
            if windowed else reading.compact_hit(hit)
            for hit in hits
        ],
        "warnings": warnings,
    }
    if unknown_fields:
        result["unknown_print_fields"] = unknown_fields
    if total == 0:
        diagnosis = await diagnostics.zero_hit_diagnosis(text, where, filters)
        if diagnosis:
            result["zero_hit_diagnosis"] = diagnosis
    return result


@mcp.tool()
async def get_fields(
    field_type: Literal["All", "Date", "NumericDate", "Numeric", "Parametric"] = "All",
    start: StartPosition = 1,
    limit: PageSize = 100,
) -> dict[str, Any]:
    """List indexed field names and their configured types.

    The server instructions already list the indexed fields; call this only if
    a field you need is not listed there. Use field_type to keep results small
    and follow next_start while has_more is true. A field's name and type do not
    prove its business meaning.
    """
    data, warnings = await engine.request("GetTagNames", {
        "FieldType": field_type,
        "TypeDetails": "True",
        "Start": str(start),
        # MaxValues is the last result position, not the page size.
        "MaxValues": str(start + limit),
    })
    tags = field_info.tag_names(data)
    has_more = len(tags) > limit
    tags = tags[:limit]
    next_start = start + len(tags) if has_more else None
    if next_start is not None and next_start > 10000:
        warnings = [*warnings, "More fields exist beyond the maximum start position 10000"]
        next_start = None
    return {
        "start": start,
        "limit": limit,
        "next_start": next_start,
        "has_more": has_more,
        "fields": [{"path": path, "types": types} for path, types in tags],
        "warnings": warnings,
    }


@mcp.tool()
async def count_documents(
    text: str = "*",
    databases: list[str] | None = None,
    min_date: str = "",
    max_date: str = "",
    where: str = "",
) -> dict[str, Any]:
    """Exact count of matching documents, without returning hits.

    Use for "how many" questions. For counts per value (top-N, per year, per
    status) make one aggregate_documents call instead of one count per value.
    Arguments and where syntax are as in search_documents. Counts documents,
    not unique entities. total_documents is null, not zero, when engine
    warnings make the count uncertain.
    """
    text, prefix_warnings = await query_text.clean_query_text(text)
    resolver = await field_info.where_resolver(where)
    filters = engine.query_filters(text, databases, min_date, max_date, where, resolver)
    total, warnings = await engine.count_documents(filters)
    result = {
        "filters": filters,
        "total_documents": total,
        "predicted": False,
        "warnings": [
            *prefix_warnings,
            *warnings,
            *await query_text.numeric_term_warnings(text),
            *await field_info.sparse_field_warnings(getattr(resolver, "used", [])),
        ],
    }
    if total == 0:
        diagnosis = await diagnostics.zero_hit_diagnosis(text, where, filters)
        if diagnosis:
            result["zero_hit_diagnosis"] = diagnosis
    return result


async def _aggregation_coverage(
    filters: dict[str, str], field_name: str, data: dict[str, Any],
    aggregation_warnings: list[Any], range_count: int | None = None,
) -> tuple[dict[str, Any], list[Any]]:
    warnings = []

    async def count(parameters: dict[str, str]) -> int | None:
        total, count_warnings = await engine.count_documents(parameters)
        warnings.extend(count_warnings)
        return total

    matching = await count(filters)
    with_field = None
    if not aggregation_warnings:
        if field_name.lower().startswith("autn_"):
            # The metadata Content aggregates (date, database, language) is on
            # every document and is not a field EXISTS can test; other autn_
            # names fail with a warning and never get here.
            with_field = matching
        else:
            with_field = await count(engine.restricted(filters, f"EXISTS{{}}:{field_name}"))
    if matching is not None and with_field is not None and with_field > matching:
        raise RuntimeError(
            "Coverage counts are inconsistent; the index may have changed during requests"
        )

    complete = None
    fields = engine.entries(data, "field")
    if not aggregation_warnings and len(fields) == 1:
        field = fields[0]
        try:
            returned = int(field["number_of_values"])
            total_values = (
                range_count if range_count is not None else int(field["total_values"])
            )
        except (KeyError, TypeError, ValueError):
            pass
        else:
            if returned < 0 or total_values < returned:
                raise RuntimeError("Content returned inconsistent bucket counts")
            complete = returned == total_values
    return {
        "matching_documents": matching,
        "documents_with_group_field": with_field,
        "documents_missing_group_field": (
            matching - with_field
            if matching is not None and with_field is not None else None
        ),
        "returned_buckets_complete": complete,
    }, warnings


@mcp.tool()
async def aggregate_documents(
    field_name: str,
    text: str = "*",
    databases: list[str] | None = None,
    min_date: str = "",
    max_date: str = "",
    where: str = "",
    limit: PageSize = 20,
    date_period: Literal["none", "year", "month", "week", "day"] = "none",
    sort: Literal[
        "DocumentCount", "Alphabetical", "NumberIncreasing", "ReverseDate"
    ] = "DocumentCount",
) -> dict[str, Any]:
    """Document counts for the most frequent values of one field, over all matches.

    Use for breakdowns, top-N and per-period questions in a single call rather
    than one count per value. For a calendar breakdown set date_period on
    autn_date or a Date/NumericDate field, with limit=100 and sort=ReverseDate.
    coverage reports matching_documents and documents_missing_group_field, so
    separate counts are unnecessary; mention missing-field documents if any.
    returned_buckets_complete=false means limit cut values off. Counts can
    overlap for multi-valued fields, and free-text values may have spelling
    variants. autn_date is the document date, not an event date: disclose it
    if you use it in place of one.

    field_name: One field from the schema, or autn_date.
    text, databases, min_date, max_date, where: As in search_documents.
    limit: Values to return, 1-100.
    date_period: Calendar grouping for date fields; none disables it.
    sort: DocumentCount, Alphabetical, NumberIncreasing, or ReverseDate
        (chronological date buckets).

    data.field[].value[] entries have $ (value), @count (documents) and @date
    for date buckets.
    """
    field_name = field_name.strip()
    if not field_name:
        raise ValueError("field_name must not be empty")
    if "," in field_name:
        raise ValueError("field_name must specify exactly one field")
    text, prefix_warnings = await query_text.clean_query_text(text)
    resolver = await field_info.where_resolver(where)
    filters = engine.query_filters(text, databases, min_date, max_date, where, resolver)
    parameters = {
        **filters,
        "FieldName": field_name,
        "DocumentCount": "True",
        "Predict": "False",
        "Sort": sort,
        "MaxValues": str(limit),
    }
    warnings = list(prefix_warnings)
    range_count = None
    date_basis = None

    def result(data: Any, coverage: dict[str, Any], **extra: Any) -> dict[str, Any]:
        return {
            "filters": filters, "field_name": field_name, "limit": limit,
            "date_period": date_period, "sort": sort, "predicted": False,
            "data": data, "coverage": coverage, "date_basis": date_basis,
            "warnings": warnings, **extra,
        }

    if field_name.lower() == "autn_date":
        date_basis = {
            "field": "autn_date",
            "meaning": "Content document date",
            "event_date_equivalence_verified": False,
        }
    if date_period != "none" and field_name.lower() != "autn_date":
        resolved, field_warnings = await field_info.date_field(field_name)
        warnings.extend(field_warnings)
        parameters["FieldName"] = resolved
        date_basis = {
            "field": resolved,
            "meaning": "Configured date field; business meaning not verified",
            "event_date_equivalence_verified": False,
        }
        statistics, stat_warnings = await engine.request("GetQueryTagValues", {
            **parameters, "ValueDetails": "True", "Print": "NoResults",
        })
        warnings.extend(stat_warnings)
        engine.reject_predicted(statistics)
        fields = engine.entries(statistics, "field")
        if len(fields) != 1:
            raise RuntimeError(
                f"Content did not return date statistics for {resolved}; warnings: {warnings!r}"
            )
        try:
            count = int(fields[0]["values"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("Content did not return a valid date value count") from error
        if count < 0:
            raise RuntimeError("Content returned a negative date value count")
        #only numeric values contribute to ValueDetails
        if count == 0:
            coverage, coverage_warnings = await _aggregation_coverage(
                filters, resolved, statistics, warnings,
            )
            warnings.extend(coverage_warnings)
            with_field = coverage.get("documents_with_group_field")
            if with_field is None:
                raise RuntimeError(
                    f"Cannot establish date aggregation coverage: {warnings!r}"
                )
            if with_field:
                data, date_warnings = await dates.aggregate_iso_dates(
                    filters, resolved, date_period, sort, limit, with_field,
                )
                field = data["field"][0]
                complete = int(field["number_of_values"]) == int(field["total_values"])
                date_basis = {**date_basis, "timezone": "the stored calendar date, as Content reads it"}
                extra = {"aggregation_method": "date_range_counts"}
            else:
                data, complete, extra = statistics, coverage.get("returned_buckets_complete"), {}
                date_warnings = []
            # Documents outside every bucket are reported, not a sign of a cut-off list.
            coverage = {**coverage, "returned_buckets_complete": None if warnings else complete}
            warnings.extend(date_warnings)
            return result(data, coverage, **extra)
        boundaries = dates.calendar_boundaries(
            fields[0].get("valuemin"), fields[0].get("valuemax"), date_period,
        )
        parameters["Ranges"] = f"FIXEDDATE{{{','.join(boundaries)}}}:{resolved}"
        range_count = len(boundaries) - 1
    elif date_period != "none":
        parameters["DatePeriod"] = date_period
    else:
        parameters["AllowNonParametricFields"] = "True"
    data, query_warnings = await engine.request("GetQueryTagValues", parameters)
    warnings.extend(query_warnings)
    engine.reject_predicted(data)
    coverage, coverage_warnings = await _aggregation_coverage(
        filters, parameters["FieldName"], data, warnings, range_count,
    )
    warnings.extend(coverage_warnings)
    return result(data, coverage)


@mcp.tool()
async def read_document(
    reference: str,
    print_fields: list[str] | None = None,
    max_chars: ContentLimit = 20000,
) -> dict[str, Any]:
    """Return selected fields of one document by reference.

    Pass print_fields to fetch only the fields you need; omit it for all fields
    (vector fields and fields with over 100 values are then left out).
    Use read_document_text for long narrative text.

    reference: Exact reference from search_documents.
    print_fields: Field names to return.
    max_chars: Character budget for all returned values (1000-50000).
    """
    reference = reference.strip()
    if not reference:
        raise ValueError("reference must not be empty")

    parameters = {
        "Reference": engine.reference_parameter(reference),
        "Print": "Fields" if print_fields else "All",
    }
    if print_fields:
        parameters["PrintFields"] = ",".join(print_fields)

    data, warnings = await engine.request("GetContent", parameters)
    hits = engine.entries(data, "hit")
    if len(hits) != 1:
        raise RuntimeError(
            f"Content GetContent did not return exactly one document for {reference!r}. "
            f"Warnings: {warnings!r}"
        )
    document = reading.document_fields(hits[0])
    vectors: list[str] = []
    bulky: dict[str, int] = {}
    if not print_fields:
        vector_paths = await field_info.vector_fields()
        vectors = list(reading.remove_fields(document, lambda path, _: path.casefold() in vector_paths))
        # Per-token analysis output (e.g. speech-to-text words with timestamps)
        # holds thousands of values and would exhaust max_chars before the text.
        # Narrative text has one value per section and is cut by max_chars instead.
        text_paths = {field.casefold() for field in await field_info.text_fields()}
        bulky = {
            path: len(value) for path, value in reading.remove_fields(
                document,
                lambda path, value: isinstance(value, list) and len(value) > reading.BULKY_FIELD_VALUES
                and path.casefold() not in text_paths,
            ).items()
        }
    fields, _, truncated_fields, omitted_fields = reading.bounded_value(document, max_chars)
    unknown_fields = await field_info.unknown_print_fields(print_fields)
    result = {
        "reference": reference, "fields": fields,
        "warnings": [*warnings, *field_info.unknown_field_warning(unknown_fields)],
    }
    if unknown_fields:
        result["unknown_print_fields"] = unknown_fields
    if vectors:
        result["omitted_vector_fields"] = vectors
    if bulky:
        result["omitted_multi_value_fields"] = bulky
    if truncated_fields or omitted_fields:
        result.update(
            truncated=True,
            truncated_fields=truncated_fields,
            omitted_fields=omitted_fields,
        )
    return result


@mcp.tool()
async def read_document_text(
    reference: str,
    offset: ContentOffset = 0,
    max_chars: ContentLimit = 20000,
) -> dict[str, Any]:
    """Read one document's narrative text, paged by characters.

    Stop once the facts are found, even if has_more is true; follow next_offset
    only for missing evidence. For several documents use read_documents_text.

    reference: Exact reference from search_documents.
    offset: Character offset; start at 0, then use next_offset.
    max_chars: Characters to return, 1000-50000.
    """
    reference = reference.strip()
    if not reference:
        raise ValueError("reference must not be empty")
    if offset < 0:
        raise ValueError("offset must not be negative")

    text, warnings = await reading.document_text(reference)
    return reading.text_page(reference, text, offset, max_chars, warnings)


@mcp.tool()
async def read_documents_text(
    references: BatchReferences,
    max_chars_per_document: BatchContentLimit = 1500,
) -> dict[str, Any]:
    """Read the opening text of up to 20 documents in one call.

    Use instead of repeated read_document_text calls when several hits need a
    quick check or serve as examples. A failed document is reported with
    status "error" without failing the batch.

    references: 1-20 exact references from search_documents.
    max_chars_per_document: 200-5000; references x this must not exceed 50000.
    """
    stripped = [reference.strip() for reference in references]
    if any(not reference for reference in stripped):
        raise ValueError("references must not contain empty values")
    cleaned = list(dict.fromkeys(stripped))
    if len(cleaned) * max_chars_per_document > BATCH_TOTAL_CHARS:
        raise ValueError(
            f"references x max_chars_per_document must not exceed {BATCH_TOTAL_CHARS}; "
            "reduce the batch size or the per-document limit"
        )

    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def read(reference: str) -> dict[str, Any]:
        async with semaphore:
            try:
                text, warnings = await reading.document_text(reference)
                page = reading.text_page(reference, text, 0, max_chars_per_document, warnings)
            except (RuntimeError, ValueError, httpx.HTTPError) as error:
                return {"reference": reference, "status": "error", "error": str(error)}
        del page["max_chars"]  # the same for every entry: max_chars_per_document
        return {"status": "ok", **page}

    documents = await asyncio.gather(*(read(reference) for reference in cleaned))
    failed = sum(document["status"] == "error" for document in documents)
    return {
        "max_chars_per_document": max_chars_per_document,
        "requested": len(documents),
        "succeeded": len(documents) - failed,
        "failed": failed,
        "documents": documents,
    }


@mcp.tool()
async def suggest_documents(
    text: str,
    limit: PageSize = 10,
    databases: list[str] | None = None,
) -> dict[str, Any]:
    """Find documents conceptually related to a passage of text.

    Use only when search_documents has not found relevant evidence, or when
    related material is requested.

    text: Text from the question or a found document.
    limit: Maximum suggestions, 1-100.
    databases: Optional database names.
    """
    parameters = {
        "Text": text,
        "MaxResults": str(limit),
    }
    if databases:
        parameters["DatabaseMatch"] = ",".join(databases)
    data, warnings = await engine.request("SuggestOnText", parameters)
    return {"data": data, "warnings": warnings}


def main() -> None:
    try:
        mcp._mcp_server.instructions = asyncio.run(schema.server_instructions())
    except (RuntimeError, ValueError, httpx.HTTPError) as error:
        mcp._mcp_server.instructions = schema.WORKFLOW_GUIDANCE
        print(f"content-mcp: schema summary unavailable: {error}", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
