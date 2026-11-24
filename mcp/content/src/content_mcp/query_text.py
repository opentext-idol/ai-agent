"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""Query text as Content reads it: terms, operators, and fixes for silent misreads."""

import re
from typing import Any

import httpx

from . import engine, field_info


_NUMBERS_INDEXED: bool | None = None
# Content reads any colon glued to the next word as a field restriction, digits
# included; _field_prefixes_as_text leaves only restrictions to known fields.
FIELD_RESTRICTION = re.compile(r""":[^\s()"']+""")
# Words as the model wrote them, split only on whitespace and query syntax; the
# engine tokenizes each one itself, so www.example.com stays one word.
QUERY_TOKEN = re.compile(r'[^\s()"]+')
TOKEN_EDGES = ",.;!'"
_NUMBER = re.compile(r"\d[\d.,]*")
# Query operators, upper case only. Documented ones taking a distance (NEAR3),
# the order operators, and undocumented ones the parser also accepts.
_PROXIMITY_WORDS = r"[DXY]?NEAR|D?SENTENCE|PARAGRAPH"
_ORDER_WORDS = r"BEFORE|AFTER"
_UNDOCUMENTED_WORDS = r"BUTNOT|PNEAR|R?WHEN|NOTR?WHEN"
_RESTRICTING_WORDS = rf"AND|NOT|{_ORDER_WORDS}|{_PROXIMITY_WORDS}|{_UNDOCUMENTED_WORDS}"
_COMBINING_WORDS = r"OR|XOR|EOR|WNEAR"
_DISTANCE_WORDS = rf"{_PROXIMITY_WORDS}|WNEAR"
_OPERATOR_DISTANCE = r"(?:/?\d+)?"
RESTRICTING_OPERATOR = re.compile(rf"(?:{_RESTRICTING_WORDS}){_OPERATOR_DISTANCE}")
_BOOLEAN_OPERATOR = re.compile(rf"(?:{_RESTRICTING_WORDS}|{_COMBINING_WORDS}){_OPERATOR_DISTANCE}")


def query_terms(text: str) -> list[str]:
    terms: list[str] = []
    for term in QUERY_TOKEN.findall(FIELD_RESTRICTION.sub(" ", text)):
        term = term.strip(TOKEN_EDGES)
        if _BOOLEAN_OPERATOR.fullmatch(term) or term.strip("*?") == "" or term in terms:
            continue
        terms.append(term)
    return terms


def is_number(term: str) -> bool:
    return bool(_NUMBER.fullmatch(term))


async def term_document_count(term: str) -> int | None:
    """Indexed documents holding term, as the engine tokenizes it.

    A word the engine splits (N123/AB) counts its rarest part. Type=None makes
    TermGetInfo return stopwords (flagged) and unknown words (zero documents)
    instead of omitting both; a term of only stopwords returns None, as it
    cannot affect a search. Wildcard terms count their expansions.
    """
    if "*" in term or "?" in term:
        data, _ = await engine.request("TermExpand", {
            "Text": term, "Expansion": "Wild", "MaxTerms": "1",
        })
        return int(data.get("number_of_terms") or 0)
    data, _ = await engine.request("TermGetInfo", {"Text": term, "Type": "None"})
    terms = engine.entries(data, "term")
    if not terms:
        return 0
    counts = [
        int(t.get("@document_occurrences") or 0)
        for t in terms if str(t.get("@stopword", "")).lower() != "true"
    ]
    return min(counts) if counts else None


async def numbers_indexed() -> bool:
    """Whether the engine indexes standalone numbers (IndexNumbers), probed once."""
    global _NUMBERS_INDEXED
    if _NUMBERS_INDEXED is None:
        data, _ = await engine.request("TermGetInfo", {
            "Text": "0 1 2 3 4 5 10 12 100 2020 2021 2022",
        })
        _NUMBERS_INDEXED = int(data.get("number_of_terms") or 0) > 0
    return _NUMBERS_INDEXED


async def numeric_term_warnings(text: str) -> list[str]:
    numbers = [term for term in query_terms(text) if is_number(term)]
    if not numbers:
        return []
    try:
        if await numbers_indexed():
            return []
    except (RuntimeError, ValueError, httpx.HTTPError):
        return []
    return [
        f"This index contains no standalone numbers, so {', '.join(numbers[:5])} "
        "cannot match any document. Search with words or alphanumeric "
        "identifiers instead and check numbers in the returned text."
    ]


_FIELD_PREFIX = re.compile(r"""(?<![\w/:.])([A-Za-z_][\w/.-]*):("[^"]*"|'[^']*'|[^\s()"']+)""")
_GLUED_COLONS = re.compile(r"""(?::[^\s()"':]+)+""")
# Content's default term separators, for engines whose settings are unreadable.
DEFAULT_TERM_SEPARATORS = frozenset(" \t\r\n!\"#$%&()*+,-/:;<=>?@[\\]^`{|}~")
_TERM_SEPARATORS: frozenset[str] | None = None


async def term_separators() -> frozenset[str]:
    """Characters the default language splits terms at, read once.

    A deployment can change them per language type; fall back to Content's
    defaults when the settings are unreadable.
    """
    global _TERM_SEPARATORS
    if _TERM_SEPARATORS is None:
        try:
            data, _ = await engine.request("LanguageSettings", {})
        except (RuntimeError, ValueError, httpx.HTTPError):
            return DEFAULT_TERM_SEPARATORS
        languages = data.get("languages", {})
        languages = languages if isinstance(languages, dict) else {}
        entries = [e for e in engine.entries(languages, "language") if "@separators" in e]
        default = str(languages.get("@defaultLanguage", "")).casefold()

        def names(entry: dict[str, Any]) -> list[str]:
            return [str(n.get("$", "")).casefold() for n in engine.entries(entry.get("names"), "name")]

        entry = next((e for e in entries if default in names(e)), entries[0] if entries else None)
        if entry is None:
            _TERM_SEPARATORS = DEFAULT_TERM_SEPARATORS
        else:
            _TERM_SEPARATORS = frozenset(
                chr(int(code[2:], 16)) for code in str(entry["@separators"]).upper().split()
                if re.fullmatch(r"U\+[0-9A-F]{4,6}", code)
            )
    return _TERM_SEPARATORS


async def _operator_distances(text: str) -> tuple[str, list[str]]:
    """Join a distance split from its operator by separators (NEAR/3 to NEAR3).

    Whitespace alone (NEAR 3) is only a distance when another term follows,
    since "engine NEAR 2" may search for the number. Brackets and quotes are
    query syntax, so a distance is never joined across them.
    """
    if not re.search(rf"\b(?:{_DISTANCE_WORDS}|{_ORDER_WORDS})\b", text):
        return text, []
    gap = "".join(re.escape(c) for c in sorted(await term_separators() - set('()"')))
    if not gap:
        return text, []
    pattern = re.compile(
        rf"\b({_DISTANCE_WORDS}|{_ORDER_WORDS})([{gap}]+)(\d+)\b(?=(\s+[^\s)])?)"
    )
    warnings = []

    def join(match: re.Match[str]) -> str:
        operator, separators, distance, followed = match.groups()
        if not separators.strip() and not followed:
            return match.group(0)
        if re.fullmatch(_ORDER_WORDS, operator):
            warnings.append(
                f"{match.group(0)!r} was searched as {operator}: {operator} takes no distance; "
                "use NEAR with a distance (NEAR3) to limit how far apart terms are."
            )
            return operator
        warnings.append(
            f"{match.group(0)!r} was searched as {operator}{distance}: write a proximity "
            f"distance directly after the operator, with no space or punctuation."
        )
        return operator + distance

    return pattern.sub(join, text), warnings


async def clean_query_text(text: str) -> tuple[str, list[str]]:
    """Fix query text that Content would silently misread."""
    text, distance_warnings = await _operator_distances(text)
    text, prefix_warnings = await _field_prefixes_as_text(text)
    return text, distance_warnings + prefix_warnings


async def _field_prefixes_as_text(text: str) -> tuple[str, list[str]]:
    """Turn FIELD:value in search text into a plain text search for value.

    IDOL reads "FIELD:value" as the term FIELD restricted to a field named
    value, so it matches nothing and reports a missing field. Models that see
    field names often write it meaning a filter. Searching the value as text
    can only widen the result; the warning points to where for a real filter.

    Any other colon glued to a word (10:30, a URL) is also read as a restriction
    to a field that does not exist, which silently drops the term, even inside
    quotes. It becomes what the indexer made of it: a term break, or nothing
    when the language does not split terms at a colon. Restrictions to known
    fields (term:FIELD) are kept.
    """
    if ":" not in text:
        return text, []
    try:
        paths = await field_info.field_names()
    except (RuntimeError, ValueError, httpx.HTTPError):
        return text, []
    known: dict[str, str] = {}
    for path in paths:
        known.setdefault(path.casefold(), path)
        known.setdefault(path.rsplit("/", 1)[-1].casefold(), path)
    warnings = []

    def replace(match: re.Match[str]) -> str:
        field = known.get(field_info.field_path(match.group(1)).casefold())
        if field is None:
            return match.group(0)
        value = match.group(2)
        if value.startswith("'"):
            value = '"' + value[1:-1] + '"'
        literal = value.strip('"').replace("'", "''")
        warnings.append(
            f"{match.group(0)!r} in text is not a field filter, so {value} was searched "
            f"as text instead; to filter on the field use where: {field} = '{literal}'."
        )
        return value

    text = _FIELD_PREFIX.sub(replace, text)
    stray = [
        match for match in _GLUED_COLONS.finditer(text)
        if not all(
            field_info.field_path(name).casefold() in known
            for name in match.group(0)[1:].split(":")
        )
    ]
    if stray:
        joiner = " " if ":" in await term_separators() else ""
        for match in reversed(stray):
            text = text[:match.start()] + match.group(0).replace(":", joiner) + text[match.end():]
    return text, warnings
