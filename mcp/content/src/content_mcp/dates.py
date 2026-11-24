"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""Calendar buckets for date aggregation."""

import asyncio
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .sql_fieldtext import day_end, day_start
from . import engine


def calendar_boundaries(
    minimum: Any, maximum: Any, period: str,
) -> list[str]:
    try:
        first = datetime.strptime(minimum["@date"], "%H:%M:%S %d/%m/%Y")
        last = datetime.strptime(maximum["@date"], "%H:%M:%S %d/%m/%Y")
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            "Content date statistics did not include supported local dates"
        ) from error
    if first > last:
        raise RuntimeError("Content date statistics returned reversed bounds")
    current = first.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "year":
        current = current.replace(month=1, day=1)
    elif period == "month":
        current = current.replace(day=1)
    elif period == "week":
        current -= timedelta(days=current.weekday())

    boundaries = [current.date().isoformat()]
    while current <= last:
        if len(boundaries) > 100:
            raise ValueError(
                "Custom date aggregation spans more than 100 calendar buckets; "
                "use a coarser date_period or restrict the custom field with where"
            )
        try:
            if period == "year":
                current = current.replace(year=current.year + 1)
            elif period == "month":
                current = current.replace(
                    year=current.year + (current.month == 12),
                    month=current.month % 12 + 1,
                )
            else:
                current += timedelta(days=7 if period == "week" else 1)
        except (ValueError, OverflowError) as error:
            raise ValueError("Calendar bucket boundary exceeds supported dates") from error
        boundaries.append(current.date().isoformat())
    return boundaries


_SLASH_DATE = re.compile(r"(\d{4})/(\d{2})/(\d{2})(?=$|[T ])")


def _parse_stored_date(raw: Any) -> datetime:
    """Parse a stored ISO 8601 style date: date-only, naive, or zoned."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("missing date value")
    text = _SLASH_DATE.sub(r"\1-\2-\3", raw.strip())
    if any(char not in "0123456789-T:+.Z " for char in text):
        raise ValueError("unsupported ISO date syntax")
    return datetime.fromisoformat(text)


async def aggregate_iso_dates(
    filters: dict[str, str], field_name: str, period: str, sort: str, limit: int,
    documents_with_field: int,
) -> tuple[dict[str, Any], list[str]]:
    """Calendar buckets for a date field without numeric date values.

    The span runs from the first to the last value in alphabetical order, which
    is chronological for ISO 8601 values. One more count over the whole span
    shows how many documents no bucket holds, such as those whose value is not
    a readable date.
    """
    async def end_value(order: str) -> Any:
        data, warnings = await engine.request("GetQueryTagValues", {
            **filters, "FieldName": field_name, "AllowNonParametricFields": "True",
            # Without DocumentCount, values come back as bare strings.
            "DocumentCount": "True", "Predict": "False", "Sort": order, "MaxValues": "1",
        })
        if warnings:
            raise RuntimeError(f"Content date values are uncertain: {warnings!r}")
        engine.reject_predicted(data)
        values = [value for field in engine.entries(data, "field") for value in engine.entries(field, "value")]
        if not values:
            raise RuntimeError(f"Content returned no values for {field_name}")
        return values[0].get("$")

    days = []
    for raw in await asyncio.gather(end_value("Alphabetical"), end_value("ReverseAlphabetical")):
        try:
            parsed = _parse_stored_date(raw)
        except (ValueError, OverflowError) as error:
            raise RuntimeError(
                "Date aggregation requires ISO 8601 style values "
                "(YYYY-MM-DD, optionally with a time and timezone); "
                f"unsupported value: {raw!r}"
            ) from error
        days.append(parsed.date())
    boundaries = calendar_boundaries(
        {"@date": min(days).strftime("%H:%M:%S %d/%m/%Y")},
        {"@date": max(days).strftime("%H:%M:%S %d/%m/%Y")}, period,
    )

    semaphore = asyncio.Semaphore(5)

    async def count(first: str, end: str) -> int:
        last = date.fromisoformat(end) - timedelta(days=1)
        bounds = f"{day_start(date.fromisoformat(first))},{day_end(last)}"
        async with semaphore:
            total, warnings = await engine.count_documents(
                engine.restricted(filters, f"RANGE{{{bounds}}}:{field_name}"),
            )
        if total is None or warnings:
            raise RuntimeError(f"Content calendar bucket count is uncertain: {warnings!r}")
        if total > documents_with_field:
            raise RuntimeError(
                "Calendar bucket counts are inconsistent; "
                "the index may have changed during requests"
            )
        return total

    in_span, *counts = await asyncio.gather(
        count(boundaries[0], boundaries[-1]),
        *(count(start, end) for start, end in zip(boundaries, boundaries[1:])),
    )
    warnings = []
    if in_span < documents_with_field:
        warnings.append(
            f"{documents_with_field - in_span} of {documents_with_field} documents with "
            f"a value in {field_name} are in no date bucket, because Content does not "
            "read their value as a date in the bucket span; the counts leave them out."
        )

    def stamp(day: str) -> str:
        return datetime.fromisoformat(day).strftime("%H:%M:%S %d/%m/%Y")

    buckets = [
        {
            "$": str(int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())),
            "@count": str(total), "@date": stamp(start), "@end_date": stamp(end),
        }
        for start, end, total in zip(boundaries, boundaries[1:], counts)
    ]
    if sort == "DocumentCount":
        buckets.sort(key=lambda value: -int(value["@count"]))
    return {
        "number_of_fields": "1",
        "field": [{
            "name": field_name,
            "number_of_values": str(min(limit, len(buckets))),
            "total_values": str(len(buckets)), "value": buckets[:limit],
        }],
    }, warnings
