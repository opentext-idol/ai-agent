"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

"""Translate SQL WHERE expressions into IDOL Content FieldText."""

import math
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

import sqlglot
from sqlglot import exp

# Content percent-decodes FieldText values, so these can be encoded rather than refused.
_RESERVED = {"%": "%25", ",": "%2C", "{": "%7B", "}": "%7D", "\\": "%5C"}
_DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")
_OPEN = "."  # an open-ended RANGE bound
DATE_TYPES = {"date", "numericdate"}
_FLIPPED = {exp.GT: exp.LT, exp.GTE: exp.LTE, exp.LT: exp.GT, exp.LTE: exp.GTE}

# Maps a user-supplied field name to (canonical path, configured types).
Resolver = Callable[[str], tuple[str, frozenset[str]]]


def _field(node: exp.Expression) -> str:
    if not isinstance(node, exp.Column):
        raise ValueError(f"Expected a field name, got: {node.sql()}")
    return "/".join(part.name for part in node.parts)


def encode_value(text: str) -> str:
    """Percent-encode characters that FieldText reserves inside {...} values."""
    return "".join(_RESERVED.get(char, char) for char in text)


def _literal(node: exp.Expression) -> tuple[str, bool]:
    """Return (raw text, is_numeric) for a literal."""
    if isinstance(node, exp.Neg) and isinstance(node.this, exp.Literal) and node.this.is_number:
        return "-" + node.this.name, True
    if isinstance(node, exp.Literal):
        return node.name, node.is_number
    raise ValueError(f"Expected a literal value, got: {node.sql()}")


def _value(node: exp.Expression) -> tuple[str, bool]:
    """Return (FieldText-safe text, is_numeric) for a literal."""
    text, numeric = _literal(node)
    return encode_value(text), numeric


def _date_literal(text: str) -> tuple[str, str] | tuple[str, float]:
    """Classify a date literal as ("day", 'YYYY-MM-DD') or ("instant", epoch seconds).

    Timestamps may use 'T' or a space, fractional seconds, and Z or an offset;
    a timestamp without a zone is taken as UTC. Anything else is refused,
    because Content ignores a range it cannot parse (with only a warning) and
    would match every document.
    """
    text = text.strip()
    if _DATE_ONLY.fullmatch(text):
        try:
            date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(f"Invalid date {text!r}") from error
        return "day", text
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        moment = None
    if moment is None:
        raise ValueError(
            f"Date literal {text!r} is not understood; use 'YYYY-MM-DD' or an ISO 8601 "
            "timestamp such as '2021-05-21T14:30:00Z'"
        )
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return "instant", moment.timestamp()


def _utc(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_start(day: date) -> str:
    """The start of a day as a RANGE bound read in the engine's local time.

    Content can read a stored date-only value (or the date part of a
    timestamp) as local midnight on its host, while an ISO date in RANGE is
    read as UTC, so ISO day bounds are off by a day east of UTC. Bounds in
    Content's own HH:NN:SS DD/MM/YYYY format are read in local time like the
    stored values.
    """
    return f"00:00:00 {day.day:02d}/{day.month:02d}/{day.year:04d}"


def day_end(day: date) -> str:
    """The end of a day as a local-time RANGE bound (see day_start).

    Explicit, because a date-only end adds a fixed 23:59:59 to local midnight
    and runs into the next day when clocks go forward.
    """
    return f"23:59:59 {day.day:02d}/{day.month:02d}/{day.year:04d}"


def _date_bounds(text: str) -> tuple[str, str]:
    """Return the first and last value a literal covers: a whole day, or one second."""
    kind, value = _date_literal(text)
    if kind == "day":
        day = date.fromisoformat(value)
        return day_start(day), day_end(day)
    return _utc(math.ceil(value)), _utc(math.floor(value))


def _like_pattern(pattern: str) -> str:
    return "".join(
        "*" if char == "%" else "?" if char == "_" else encode_value(char)
        for char in pattern
    )


class _Translator:
    def __init__(self, types: dict[str, frozenset[str]]):
        self.types = types

    def kind(self, field: str) -> str:
        """Return date, numeric, text, or unknown (no schema supplied)."""
        configured = self.types.get(field)
        if configured is None:
            return "unknown"
        if configured & DATE_TYPES:
            return "date"
        if "numeric" in configured:
            return "numeric"
        return "text"

    def _reject_ordering(self, field: str) -> ValueError:
        types = ", ".join(sorted(self.types.get(field, ()))) or "unknown"
        return ValueError(
            f"Ordered comparison and BETWEEN are not supported on {field!r} "
            f"(configured as {types}); use = or LIKE 'prefix%' instead"
        )

    @staticmethod
    def _after(text: str) -> str:
        """The first value strictly after a date literal (next day or next second)."""
        kind, value = _date_literal(text)
        if kind == "instant":
            return _utc(math.floor(value) + 1)
        try:
            return day_start(date.fromisoformat(value) + timedelta(days=1))
        except OverflowError as error:
            raise ValueError(f"Date {value!r} is out of range") from error

    @staticmethod
    def _before(text: str) -> str:
        """The last value strictly before a date literal (previous day or second)."""
        kind, value = _date_literal(text)
        if kind == "instant":
            return _utc(math.ceil(value) - 1)
        try:
            return day_end(date.fromisoformat(value) - timedelta(days=1))
        except OverflowError as error:
            raise ValueError(f"Date {value!r} is out of range") from error

    def comparison(self, node: exp.Binary) -> str:
        left, right, kind = node.this, node.expression, type(node)
        if not isinstance(left, exp.Column):
            left, right, kind = right, left, _FLIPPED.get(kind, kind)
        field = _field(left)
        value, numeric = _value(right)
        field_kind = self.kind(field)

        if field_kind == "date":
            raw, _ = _literal(right)
            first, last = _date_bounds(raw)
            if kind in (exp.EQ, exp.NEQ):
                span = f"RANGE{{{first},{last}}}:{field}"
                return span if kind is exp.EQ else f"NOT {span}"
            if kind is exp.GTE:
                return f"RANGE{{{first},{_OPEN}}}:{field}"
            if kind is exp.LTE:
                return f"RANGE{{{_OPEN},{last}}}:{field}"
            if kind is exp.GT:
                return f"RANGE{{{self._after(raw)},{_OPEN}}}:{field}"
            return f"RANGE{{{_OPEN},{self._before(raw)}}}:{field}"

        eq = f"{'EQUAL' if numeric else 'MATCH'}{{{value}}}:{field}"
        if kind is exp.EQ:
            return eq
        if kind is exp.NEQ:
            return f"NOT {eq}"
        if field_kind == "text":
            raise self._reject_ordering(field)
        # Built so the result is right whether GREATER/LESS are inclusive or not.
        order = "GREATER" if kind in (exp.GT, exp.GTE) else "LESS"
        ordered = f"{order}{{{value}}}:{field}"
        if kind in (exp.GTE, exp.LTE):
            return f"({ordered} OR {eq})"
        return f"({ordered} AND NOT {eq})"

    def between(self, node: exp.Between) -> str:
        field = _field(node.this)
        low, low_numeric = _value(node.args["low"])
        high, high_numeric = _value(node.args["high"])
        field_kind = self.kind(field)
        if field_kind == "text":
            raise self._reject_ordering(field)
        if field_kind == "date":
            first, _ = _date_bounds(_literal(node.args["low"])[0])
            _, last = _date_bounds(_literal(node.args["high"])[0])
            return f"RANGE{{{first},{last}}}:{field}"
        if field_kind == "numeric" or (field_kind == "unknown" and low_numeric and high_numeric):
            return f"NRANGE{{{low},{high}}}:{field}"
        return f"RANGE{{{low},{high}}}:{field}"

    def convert(self, node: exp.Expression) -> str:
        if isinstance(node, exp.Paren):
            return f"({self.convert(node.this)})"
        if isinstance(node, exp.And):
            return f"{self.convert(node.this)} AND {self.convert(node.expression)}"
        if isinstance(node, exp.Or):
            return f"({self.convert(node.this)} OR {self.convert(node.expression)})"
        if isinstance(node, exp.Not):
            inner = node.this
            if isinstance(inner, exp.Is):
                return self.is_null(inner, negate=True)
            return f"NOT ({self.convert(inner.this if isinstance(inner, exp.Paren) else inner)})"
        if isinstance(node, (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE)):
            return self.comparison(node)
        if isinstance(node, exp.In):
            if node.args.get("query") or node.args.get("unnest"):
                raise ValueError("Subqueries are not supported")
            field = _field(node.this)
            if self.kind(field) == "date":
                bounds = (_date_bounds(_literal(item)[0]) for item in node.expressions)
                spans = (f"RANGE{{{first},{last}}}:{field}" for first, last in bounds)
                return "(" + " OR ".join(spans) + ")"
            items = [_value(item) for item in node.expressions]
            operator = "EQUAL" if all(numeric for _, numeric in items) else "MATCH"
            return f"{operator}{{{','.join(value for value, _ in items)}}}:{field}"
        if isinstance(node, exp.Between):
            return self.between(node)
        if isinstance(node, exp.Like):
            text, _ = _literal(node.expression)
            wild = f"WILD{{{_like_pattern(text)}}}:{_field(node.this)}"
            # sqlglot parses NOT LIKE as a negated Like, not as Not(Like).
            return f"NOT ({wild})" if node.args.get("negate") else wild
        if isinstance(node, exp.Is):
            return self.is_null(node, negate=False)
        raise ValueError(f"Unsupported SQL construct: {node.sql()}")

    def is_null(self, node: exp.Is, negate: bool) -> str:
        if not isinstance(node.expression, exp.Null):
            raise ValueError(f"Unsupported SQL construct: {node.sql()}")
        exists = f"EXISTS{{}}:{_field(node.this)}"
        # IS NULL means the field is absent.
        return exists if negate else f"NOT {exists}"


def sql_to_fieldtext(where: str, resolve: Resolver | None = None) -> str:
    """Convert a SQL WHERE expression to FieldText; raise ValueError if unsupported.

    resolve maps each referenced field to its canonical index path and configured
    types, raising ValueError for unknown fields. Without it, field types are
    unknown and ordered comparisons are translated as for numeric fields.
    """
    try:
        statement = sqlglot.parse_one(f"SELECT 1 WHERE {where}")
    except sqlglot.errors.SqlglotError as error:
        raise ValueError(f"Invalid SQL WHERE expression: {error}") from error
    condition = statement.args["where"].this
    types: dict[str, frozenset[str]] = {}
    if resolve:
        for column in list(condition.find_all(exp.Column)):
            path, configured = resolve(_field(column))
            types[path] = configured
            column.replace(exp.column(exp.to_identifier(path, quoted=True)))
    return _Translator(types).convert(condition)


def required_text_values(where: str) -> list[tuple[str, bool]]:
    """String values a WHERE expression requires a field to hold, each with
    whether it is a LIKE pattern, in order.

    Values that are excluded rather than required (under NOT, compared with
    != or NOT LIKE) are left out, as are numbers and ordered comparisons.
    Returns nothing for an expression that does not parse.
    """
    try:
        statement = sqlglot.parse_one(f"SELECT 1 WHERE {where}")
    except sqlglot.errors.SqlglotError:
        return []
    values: list[tuple[str, bool]] = []

    def add(node: exp.Expression, like: bool) -> None:
        if isinstance(node, exp.Literal) and node.is_string:
            values.append((node.name, like))

    def walk(node: exp.Expression, negated: bool) -> None:
        if isinstance(node, exp.Paren):
            walk(node.this, negated)
        elif isinstance(node, (exp.And, exp.Or)):
            walk(node.this, negated)
            walk(node.expression, negated)
        elif isinstance(node, exp.Not):
            walk(node.this, not negated)
        elif negated:
            return
        elif isinstance(node, exp.EQ):
            add(node.this, False)
            add(node.expression, False)
        elif isinstance(node, exp.In):
            for item in node.expressions:
                add(item, False)
        elif isinstance(node, exp.Like) and not node.args.get("negate"):
            add(node.expression, True)

    walk(statement.args["where"].this, False)
    return values
