"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""Requests to the Content engine and the response shapes they share."""

import contextvars
import os
import urllib.parse
from typing import Any

import httpx

from .sql_fieldtext import Resolver, sql_to_fieldtext


def _normalize_content_base(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
        value = value[1:-1].strip()
    message = (
        "CONTENT_BASE must be an absolute http:// or https:// URL with a host "
        "and no query or fragment, for example http://localhost:9100"
    )
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as error:
        raise ValueError(message) from error
    if url.scheme not in {"http", "https"} or not url.host or url.query or url.fragment:
        raise ValueError(message)
    return str(url).rstrip("/")


CONTENT_BASE = _normalize_content_base(
    os.environ.get("CONTENT_BASE", "http://localhost:9100")
)
CONTENT_SECURITY_INFO = os.environ.get("CONTENT_SECURITY_INFO", "")


# Lets a burst of requests (the startup schema summary) reuse one connection pool.
SHARED_CLIENT: contextvars.ContextVar[httpx.AsyncClient | None] = contextvars.ContextVar(
    "content_shared_client", default=None,
)


def reference_parameter(reference: str) -> str:
    """Content splits Reference on spaces, plus signs and commas, so a single
    reference containing them must be percent-encoded."""
    return urllib.parse.quote(reference, safe="")


# Tool argument behind each Content filter parameter _filters sets, so a
# diagnosis can name the filter the model used. A parameter missing here is
# still reported, under its Content name.
FILTER_NAMES = {
    "FieldText": "where", "DatabaseMatch": "databases",
    "MinDate": "min_date", "MaxDate": "max_date",
}


def query_filters(
    text: str,
    databases: list[str] | None,
    min_date: str,
    max_date: str,
    where: str = "",
    resolve: Resolver | None = None,
) -> dict[str, str]:
    parameters = {"Text": text.strip() or "*"}
    if where.strip():
        parameters["FieldText"] = sql_to_fieldtext(where, resolve)
    if databases:
        parameters["DatabaseMatch"] = ",".join(databases)
    if min_date:
        parameters["MinDate"] = min_date
    if max_date:
        parameters["MaxDate"] = max_date
    return parameters


async def request(
    action: str, parameters: dict[str, str],
) -> tuple[dict[str, Any], list[Any]]:
    payload = {
        **parameters,
        "ResponseFormat": "simplejson",
        "TimeoutMS": "25000",
    }
    if CONTENT_SECURITY_INFO:
        payload["SecurityInfo"] = CONTENT_SECURITY_INFO

    shared = SHARED_CLIENT.get()
    if shared is not None:
        response = await shared.post(f"{CONTENT_BASE}/action={action}", data=payload)
    else:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{CONTENT_BASE}/action={action}", data=payload)
    response.raise_for_status()

    try:
        response_payload = response.json()
    except ValueError as error:
        raise RuntimeError(f"Content {action} returned invalid JSON") from error

    envelope = response_payload.get("autnresponse")
    if not isinstance(envelope, dict):
        raise RuntimeError(f"Content {action} returned an invalid response envelope")
    data = envelope.get("responsedata")
    if str(envelope.get("response", "")).upper() != "SUCCESS":
        raise RuntimeError(f"Content {action} failed: {_error_text(envelope, data)}")

    if not isinstance(data, dict):
        raise RuntimeError(f"Content {action} returned invalid response data")

    warnings = []
    for source in (envelope, data):
        for key in ("warning", "warnings"):
            value = source.get(key)
            if value is not None:
                warnings.extend(values(value))
    return data, warnings


def reject_predicted(data: dict[str, Any]) -> None:
    """Fail if Content estimated a count although the request sent Predict=False."""
    if str(data.get("predicted", "false")).lower() in {"true", "1"}:
        raise RuntimeError("Content returned predicted counts despite Predict=False")


def values(value: Any) -> list[Any]:
    """A value as a list: Content sends a single value unwrapped."""
    return value if isinstance(value, list) else [value]


def entries(data: Any, key: str) -> list[dict[str, Any]]:
    """The objects under key in a response, whether Content sent one or several."""
    value = data.get(key) if isinstance(data, dict) else None
    return [item for item in values(value) if isinstance(item, dict)]


def restricted(filters: dict[str, str], restriction: str) -> dict[str, str]:
    """filters with a FieldText restriction added to any already there."""
    if filters.get("FieldText"):
        restriction = f"({filters['FieldText']}) AND ({restriction})"
    return {**filters, "FieldText": restriction}


def _error_text(envelope: dict[str, Any], data: Any) -> str:
    errors = envelope.get("error")
    if errors is None and isinstance(data, dict):
        errors = data.get("error")
    if errors is None:
        return "Unknown error"
    if not isinstance(errors, list):
        errors = [errors]
    messages = []
    configuration = False
    for error in errors:
        if not isinstance(error, dict):
            messages.append(str(error))
            continue
        text = error.get("errorstring") or error.get("errorid") or "Unknown error"
        description = error.get("errordescription")
        messages.append(f"{text} ({description})" if description else str(text))
        configuration |= str(error.get("errorcode", "")).upper() == "ERRORCONFIGURATION"
    message = "; ".join(messages)
    if configuration:
        message += (
            ". This is an engine configuration error: retrying or changing "
            "arguments will not help. Report the limitation instead of emulating "
            "this action with many other calls."
        )
    return message


_INDEX_TOTAL: int | None = None


async def index_total() -> int | None:
    global _INDEX_TOTAL
    if _INDEX_TOTAL is None:
        _INDEX_TOTAL, _ = await count_documents({"Text": "*"})
    return _INDEX_TOTAL


async def count_documents(
    filters: dict[str, str],
) -> tuple[int | None, list[Any]]:
    result, warnings = await request("Query", {
        **filters, "TotalResults": "True", "Predict": "False",
        "Combine": "Simple", "MaxResults": "0", "Print": "None",
    })
    reject_predicted(result)
    try:
        total = int(result["totalhits"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Content count Query returned invalid totalhits") from error
    if total < 0:
        raise RuntimeError("Content count Query returned negative totalhits")
    return (None if warnings else total), warnings
