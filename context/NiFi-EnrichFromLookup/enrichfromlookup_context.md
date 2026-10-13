<!--
BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE
-->

# EnrichFromLookup Processor

## Overview

EnrichFromLookup is a NiFi processor that enriches IDOL document metadata by looking up field
values in an external data source (currently CSV files) and writing the results back into the
document's XML metadata.

The processor is entirely configuration-driven. A JSON configuration file describes:

- **Where the data lives** — one or more CSV files, referenced by a logical key
- **What the data looks like** — which columns to expose and how to index them
- **How to read from the document** — a metadata tree that maps XML element paths to logical field names
- **How to perform the lookup** — which document fields drive the query, and which data columns to write back

Multiple configuration files can be loaded simultaneously. The NiFi property
`Lookup Configuration Directories` points to the directory (or directories) containing them,
and `Lookup Identifiers` selects which lookup(s) to execute on each document.

---

## How It Works — End to End

```
Document XML metadata
        │
        ▼
  metadata definition           ← XPath navigation; reads field values into a map
        │
        ▼
  lookup inputs                 ← NiFi EL expressions transform the map into query keys
        │
        ▼
  CSV data source               ← indexed filter selects a matching row
        │
        ▼
  lookup outputs                ← NiFi EL expressions transform the row into result values
        │
        ▼
  metadata assign               ← writes results back into the XML at the correct paths
```

Each document element matched by the metadata `path` is processed **independently** in a
single pass. Repeating sibling elements (e.g. multiple `<location>` blocks) are each enriched
with the values appropriate to their own content.

---

## JSON Configuration File

A configuration file is a single JSON object with the following top-level keys.
All keys are optional in any individual file. Any top-level section — `file_map`,
`csv_file`, `metadata`, `lookup` — can be placed in whichever file is most convenient,
and cross-file references between sections work freely (see [IDs](#ids) below).

```
{
  "file_map":  { ... },   // logical filename aliases
  "csv_file":  [ ... ],   // CSV data source definitions
  "metadata":  [ ... ],   // document field structure definitions
  "lookup":    [ ... ]    // lookup pipeline definitions
}
```

Multiple configuration files in the same directory are merged at load time.
A `data_id` in one file can reference a `csv_file` defined in another.

### IDs

Every `id` is a string that is **global** across all configuration files in all
configured directories. An id assigned in one file can be referenced from any other
file (e.g. a `csv_file` defined in a shared data file and referenced by lookups in
several other files).

```json
"id": "us_zip_data"
```

Ids must be **unique** across every loaded file. The one deliberate exception is the
override mechanism: a writable configuration file may reuse the same id as a read-only
built-in (one shipped under the unpacked resources directory) to replace it - the
writable definition wins. Any other duplicate id is rejected at load.

> Integer ids (e.g. `1`) are still accepted for backwards compatibility and are treated
> as their string form (`1` is equivalent to `"1"`). New configuration should use
> descriptive string ids; the UI writes string ids throughout.

---

## `file_map`

Maps a logical key name to a filename (relative to the configuration file's directory).
This indirection lets the CSV path be changed without touching lookup definitions.

```json
"file_map": {
  "us_zip_csv_file": "us_zip_sample.csv"
}
```

The key (`"us_zip_csv_file"`) is used as the `file_key` inside a `csv_file` definition.

---

## `csv_file`

Defines a CSV data source that can be queried by one or more lookups.

```json
"csv_file": [
  {
    "id": "us_zip_data",
    "file_key": "us_zip_csv_file",
    "use_header_row": false,
    "separator": "\\t",
    "headers": ["country", "zip", "place", "name1", "code1",
                "name2", "code2", "name3", "code3",
                "latitude", "longitude", "accuracy"],
    "names": [
      { "name": "postcode", "expr": "${zip}" },
      { "name": "country",  "expr": "${country}" },
      "place", "name1", "name2", "name3", "latitude", "longitude"
    ],
    "indexes": [["postcode"], ["country", "postcode"]]
  }
]
```

### Fields

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique identifier for this data source, referenced by `lookup.data_id` |
| `file_key` | Yes | Key into `file_map` that resolves to the CSV file path |
| `use_header_row` | No | If `true`, the first row of the CSV is treated as column headers |
| `separator` | No | Column separator. Use `"\\t"` for tab, `","` for comma (default). Hex escapes `%XX` and `\xXX` are accepted |
| `headers` | No | Explicit column names when `use_header_row` is `false` |
| `names` | No | Logical column names exposed to lookups (see below) |
| `indexes` | No | Sets of column names to index for efficient lookup (see below) |

### `names` — Logical column names

`names` controls which CSV columns are loaded into the datastore and under what names.
Columns not listed in `names` (and not used by a bare string shorthand) are ignored.

Each entry is either:

- **A bare string** — `"place"` exposes the CSV column named `place` as `place`
- **An object with `name` and `expr`** — exposes a computed value under a new name:
  ```json
  { "name": "postcode", "expr": "${zip}" }
  ```
  Here `${zip}` reads the raw CSV column `zip` and stores it under the logical name `postcode`.
  NiFi EL functions can be applied: `${zip:toUpper()}`, `${zip:substring(0,5)}` etc.

> **Important:** The logical names defined here are what lookup `inputs` filter against.
> If a lookup input is named `postcode` but the CSV column is `zip`, you must map them
> via `names`. If the names already match, the bare string form suffices.

### `indexes`

Each entry is an array of logical column names forming a composite index:

```json
"indexes": [["postcode"], ["country", "postcode"]]
```

An index covering exactly the columns used by a lookup's `inputs` allows the datastore to
find matching rows efficiently. Without a matching index the lookup still works but scans
the full dataset.

For case-insensitive matching, normalise in the `names` expression (e.g. `${country:toUpper()}`)
and ensure the lookup `inputs` expr applies the same normalisation.

---

## `metadata`

Describes the structure of the XML metadata in the document, defining both which elements
to read from (inputs) and which elements to write to (outputs). A single metadata definition
can be shared by multiple lookups.

```json
"metadata": [
  {
    "id": "flat_zip_alias_metadata",
    "path": ".",
    "fields": [
      { "name": "postcode", "path": "zip" },
      "place", "latitude", "longitude", "geopoint"
    ]
  }
]
```

### Root-level fields

| Field | Required | Description |
|---|---|---|
| `id` | No | Identifier, referenced by `lookup.metadata_id`. Required if shared across lookups |
| `path` | No | XPath to the repeating container element, relative to `<xmlmetadata>`. Use `"."` for the document root. Defaults to `"."` |
| `value_element` | No | See [Value Element](#value_element) |
| `fields` | Yes | Array of field definitions (see below) |

### `fields` — Field definitions

Each entry in `fields` is one of three forms:

#### 1. Bare string shorthand

```json
"latitude"
```

Equivalent to `{ "name": "latitude", "path": "latitude" }`. Used when the logical name
and the XML element name are identical.

#### 2. Named leaf field

```json
{ "name": "postcode", "path": "zip" }
```

Maps the logical name `postcode` to the XML element `<zip>`. The `name` is used throughout
the lookup pipeline; the `path` is the XPath used to read from and write to the document.

The `path` may be:
- A simple element name: `"zip"`
- A relative XPath: `"address/zip"`
- An attribute reference: `"@country"`
- Self-reference: `"."` (reads the element's own text value — typically used with `value_element`)
- Parent reference: `".."`
- A NiFi property object: `{ "property": "zip_field_path", "default": "zip" }` — reads the
  element path from a NiFi processor property at runtime, falling back to `"zip"` if unset

#### 3. Container (intermediate level)

```json
{
  "path": "facility",
  "fields": [
    {
      "path": "address",
      "fields": [
        { "name": "postcode", "path": "zip" },
        "place", "latitude", "longitude"
      ]
    }
  ]
}
```

Used to navigate multi-level XML structures. The container has no `name` — it is purely
structural. Fields nested within it are read and written relative to the container's element.
A container may optionally carry `value_element` (see below).

### How paths are resolved

All field paths are relative to the element matched by the metadata `path`. Given:

```json
{ "path": "location", "fields": [{ "path": "address", "fields": ["postcode"] }] }
```

The processor iterates every `<location>` element and, within each one, resolves `postcode`
via the XPath `address/postcode`. Outputs are written back via the same path, creating
elements if they do not already exist.

### `value_element`

Applicable to any container node (metadata root or `{path, fields}` container field).

Declares that the container element in the document may carry its primary value as **text
content** alongside child elements. Without this, writing output children to a text-bearing
element would produce mixed content (text node and element nodes as siblings), which is not
valid in IDOL XML metadata.

When `value_element` is set:

- **Reading:** if the named child element exists under the container, its text is used
  as the value for any field with `"path": "."`. Falls back to the container's own text
  if the child does not yet exist.
- **Writing (pre-pass):** before any outputs are written, any existing text on the container
  element is migrated into a newly created child with the given name, and the container's
  own text is cleared.
- **Writing (output):** the field with `"path": "."` writes to the named child, not to
  the container element itself.

**Example use case — Eduction postal codes:**

Eduction may produce `<POSTAL_CODE>94143</POSTAL_CODE>`. Setting `value_element: "postcode"`
on the metadata root converts this cleanly before enrichment:

```
Before: <POSTAL_CODE>94143</POSTAL_CODE>

After:  <POSTAL_CODE>
          <postcode>94143</postcode>
          <latitude>37.7749</latitude>
          <longitude>-122.4194</longitude>
        </POSTAL_CODE>
```

Config:
```json
{
  "id": "eduction_postalcode_metadata",
  "path": "POSTAL_CODE",
  "value_element": "postcode",
  "fields": [
    { "name": "postcode", "path": "." },
    "latitude", "longitude"
  ]
}
```

---

## `lookup`

Defines a complete lookup pipeline: which metadata definition to use, which data source to
query, and how to transform field values in both directions.

```json
"lookup": [
  {
    "id": "flat_zip_alias",
    "metadata_id": "flat_zip_alias_metadata",
    "data_id": "us_zip_data",
    "inputs": [
      {
        "name": "postcode",
        "expr": "${postcode:replaceAll('-.*', '')}",
        "required": true,
        "pattern": ".+"
      }
    ],
    "outputs": [
      {
        "name": "place",
        "expr": "${literal('${place}, ${name2}, ${name1}'):replaceAll('^(, )+|(, )+(?=, |$)', '')}"
      },
      "latitude",
      "longitude"
    ]
  }
]
```

### Fields

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique identifier. Referenced by the NiFi `Lookup Identifiers` property |
| `metadata_id` | Yes | References a `metadata` definition |
| `data_id` | Yes | References one or more `csv_file` definitions. May be a single id or an array |
| `inputs` | Yes | Field transformations used to build the query key |
| `outputs` | Yes | Field transformations applied to the matching row before writing back |

### `inputs`

Each input entry maps a logical field name (from the metadata) to the value sent to the
data source filter. Entries are evaluated in order; all are ANDed together in the query.

**Bare string form** (name == column name, value passed through unchanged):
```json
"postcode"
```

**Object form:**
```json
{
  "name": "postcode",
  "expr": "${postcode:replaceAll('-.*', '')}",
  "required": true,
  "pattern": ".+"
}
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Logical field name from the metadata definition |
| `expr` | No | NiFi EL expression transforming the field value before querying. If absent, the raw field value is used |
| `required` | No | If `true`, the document is routed to `rel_failure` when this field's final value is empty |
| `pattern` | No | Java regex. The input value must match after `expr` is applied. Failure routes to `rel_failure` |

**Expression context:** the expression runs with all document field values (from the metadata
read phase) available as attributes. The `name` field drives which document element is read;
the `expr` then transforms that value.

**Constant inputs:** if `expr` produces a value without reading from the document — for example
`${literal('US')}` — the document need not contain a corresponding element. This is how a
hard-coded lookup key (such as a fixed country code) is injected:

```json
{ "name": "country", "expr": "${literal('US')}", "required": true, "pattern": ".+" }
```

**Multiple data sources:** if `data_id` is an array, each source is queried in sequence and
its output is merged into the key map before the next source is queried. This allows
chained lookups where intermediate results feed into subsequent queries.

### `outputs`

Each output entry maps a logical field name to the value written back into the document.
The expression runs with all data source column values available as attributes.

**Bare string form** (column value written directly to the field's element):
```json
"latitude"
```

**Object form** (expression applied to one or more column values):
```json
{
  "name": "place",
  "expr": "${literal('${place}, ${name2}, ${name1}'):replaceAll('^(, )+|(, )+(?=, |$)', '')}"
}
```

Output fields do not need to correspond to CSV columns — they can be derived entirely from
column values via NiFi EL. Common derived outputs include:

- **Concatenation:** `${literal('${place}, ${name2}, ${name1}')}`
- **WKT geo-point:** `${literal('POINT(${longitude} ${latitude})')}`
- **Conditional formatting:** any NiFi EL string manipulation

The `name` must match a field defined in the metadata; the value is written to the element
at that field's `path`.

---

## NiFi Processor Properties

| Property | Description |
|---|---|
| `Lookup Configuration Directories` | Semicolon-separated list of directories containing JSON configuration files |
| `Lookup Identifiers` | Comma-separated list of `lookup.id` values to execute on each document |
| Dynamic properties | Any dynamic property named `X` is available in EL expressions as `${property:X}` and can be referenced in `path` objects as `{ "property": "X", "default": "..." }` |

---

## Routing

| Relationship | Condition |
|---|---|
| `success` | Document processed without validation errors |
| `failure` | A `required: true` input was empty, or a `pattern` did not match |

A document with no elements matching the metadata `path` passes through to `success`
unchanged. A document where the matched element contains no value for a `required` input
also currently passes through (known limitation — the validation callback is not invoked
when no metadata values are found).

---

## Real-World Configuration Patterns

### Pattern 1 — Flat document, aliased field name

The document uses `<zip>` but the lookup key is `postcode`. The metadata uses `name`/`path`
to bridge the naming gap.

```json
{
  "metadata": [{
    "id": "m",
    "path": ".",
    "fields": [
      { "name": "postcode", "path": "zip" },
      "place", "latitude", "longitude"
    ]
  }],
  "lookup": [{
    "id": "zip_to_place",
    "metadata_id": "m",
    "data_id": "zip_data",
    "inputs": [{ "name": "postcode", "expr": "${postcode:replaceAll('-.*', '')}", "required": true, "pattern": ".+" }],
    "outputs": ["place", "latitude", "longitude"]
  }]
}
```

### Pattern 2 — Repeating container elements

Each `<location>` element is enriched independently. The metadata `path` sets the iteration
scope; all field paths inside are relative to each matched element.

```json
{
  "metadata": [{
    "id": "m",
    "path": "location",
    "fields": ["postcode", "place", "latitude", "longitude"]
  }],
  "lookup": [{
    "id": "location_zip_to_place",
    "metadata_id": "m",
    "data_id": "zip_data",
    "inputs": [{ "name": "postcode", "expr": "${postcode:replaceAll('-.*', '')}", "required": true, "pattern": ".+" }],
    "outputs": ["place", "latitude", "longitude"]
  }]
}
```

### Pattern 3 — Deeply nested structure (CT.gov style)

Three levels of nesting: `location/facility/address/zip`. Intermediate container nodes use
the `{path, fields}` form with no `name`.

```json
{
  "metadata": [{
    "id": "m",
    "path": "location",
    "fields": [{
      "path": "facility",
      "fields": [{
        "path": "address",
        "fields": [
          { "name": "postcode", "path": "zip" },
          "place", "latitude", "longitude"
        ]
      }]
    }]
  }]
}
```

### Pattern 4 — Field path driven by a NiFi property

Allows the same configuration file to be used with documents where the postcode field name
varies across deployments. Set the NiFi dynamic property `zip_field_path` to `postalcode`,
`zipcode`, etc. at runtime.

```json
{
  "metadata": [{
    "id": "m",
    "path": ".",
    "fields": [
      { "name": "postcode", "path": { "property": "zip_field_path", "default": "zip" } },
      "place", "latitude", "longitude"
    ]
  }]
}
```

### Pattern 5 — Constant lookup key (hard-coded country)

The country code is always `US` — no document field is needed. The `${literal('US')}`
expression produces it unconditionally. The compound index `[country, postcode]` on the CSV
narrows the search efficiently.

```json
"inputs": [
  { "name": "country", "expr": "${literal('US')}", "required": true, "pattern": ".+" },
  { "name": "postcode", "expr": "${postcode:replaceAll('-.*', '')}", "required": true, "pattern": ".+" }
]
```

### Pattern 6 — Case-insensitive matching

The CSV holds uppercase `US`; the document may contain `us`, `Us`, etc. Normalise in the
`inputs` expression before the filter is applied. The CSV `names` expression must normalise
identically (or the raw column value must already be in the canonical form).

```json
{ "name": "country", "expr": "${country:toUpper()}", "required": true, "pattern": ".+" }
```

### Pattern 7 — Derived output fields (geo-point, formatted place)

Outputs do not have to be raw column values. NiFi EL assembles values from multiple columns
into a single output field.

```json
"outputs": [
  {
    "name": "place",
    "expr": "${literal('${place}, ${name2}, ${name1}'):replaceAll('^(, )+|(, )+(?=, |$)', '')}"
  },
  {
    "name": "geopoint",
    "expr": "${literal('POINT(${longitude} ${latitude})')}"
  }
]
```

### Pattern 8 — Eduction-tagged repeating postal codes

Eduction produces `<POSTAL_CODE>94143</POSTAL_CODE>` — text content in what will become a
container element. `value_element` migrates the text into a named child before outputs are
written, keeping the XML well-formed.

```json
{
  "metadata": [{
    "id": "m",
    "path": "POSTAL_CODE",
    "value_element": "postcode",
    "fields": [
      { "name": "postcode", "path": "." },
      "latitude", "longitude", "geopoint"
    ]
  }],
  "lookup": [{
    "id": "postalcode_to_geo",
    "metadata_id": "m",
    "data_id": "zip_data",
    "inputs": [{ "name": "postcode", "expr": "${postcode:replaceAll('-.*', '')}", "required": true, "pattern": ".+" }],
    "outputs": [
      "latitude", "longitude",
      { "name": "geopoint", "expr": "${literal('POINT(${longitude} ${latitude})')}" }
    ]
  }]
}
```

Result per `<POSTAL_CODE>` element:
```xml
<POSTAL_CODE>
  <postcode>94143</postcode>
  <latitude>37.7749</latitude>
  <longitude>-122.4194</longitude>
  <geopoint>POINT(-122.4194 37.7749)</geopoint>
</POSTAL_CODE>
```

---

## CSV File Setup

### Format requirements

- Delimiter: any single character, or tab (`\t`)
- Encoding: UTF-8 (gzip-compressed files with `.gz` extension are supported)
- Headers: either a header row (`use_header_row: true`) or explicit `headers` array in config

### Column naming

Only columns listed in `names` are loaded. Columns whose names begin with `I_` or `S_` are
treated as integer or string typed respectively (the prefix is stripped from the stored name).
A column named `"-"` is explicitly ignored.

### Indexes

Create an index for every set of columns that will be used as lookup inputs together. A
single-column index supports single-key lookups; a compound index supports multi-key lookups.
The query planner uses the index only when the filter covers all indexed columns.

### Case sensitivity

CSV data is stored and filtered exactly as it appears. To match case-insensitively:
- Normalise the column in the `names` expression: `{ "name": "country", "expr": "${country:toUpper()}" }`
- Apply the same normalisation in the lookup `inputs` expression: `"expr": "${country:toUpper()}"`

---

## NiFi Expression Language in Configuration

NiFi EL is available in:

| Location | Attribute context |
|---|---|
| `csv_file.names[].expr` | Raw CSV row values (keyed by header name) |
| `lookup.inputs[].expr` | Document field values read by the metadata phase (keyed by logical `name`) |
| `lookup.outputs[].expr` | CSV column values from the matching row (keyed by logical `name`) |
| `metadata.path` and `fields[].path` (string form) | None (resolved at schedule time) |

Dynamic NiFi processor properties are available in all EL contexts as `${property:MyPropName}`.

Common EL patterns used in lookup configuration:

| Goal | Expression |
|---|---|
| Strip ZIP+4 suffix | `${postcode:replaceAll('-.*', '')}` |
| Remove spaces from postcode | `${postcode:replace(' ', '')}` |
| Normalise to uppercase | `${country:toUpper()}` |
| Constant value | `${literal('US')}` |
| Concatenate columns | `${literal('${place}, ${name2}, ${name1}')}` |
| Remove leading/trailing separators | `...:replaceAll('^(, )+|(, )+(?=, |$)', '')` |
| WKT geo-point | `${literal('POINT(${longitude} ${latitude})')}` |

---

## Logging

When a data source returns no matching row for a given set of inputs, the processor logs a
`WARN`-level message including the lookup id, the data source id, and the full set of input
key=value pairs. This is the primary diagnostic for missing enrichment.

No match is not treated as a failure by default — the document passes through to `success`
with the missing output fields simply absent. Route to `failure` explicitly by setting
`required: true` and a `pattern` on the relevant input.

---

## Configuration File Reference Summary

```
root object
├── file_map                         object  { key: filename }
├── csv_file[]
│   ├── id                           id      (required)
│   ├── file_key                     string  key into file_map (required)
│   ├── use_header_row               bool
│   ├── separator                    string  single char or \t
│   ├── headers[]                    string  column names when no header row
│   ├── names[]                      name_expr[]   logical column names
│   └── indexes[]                    string[][]    index definitions
├── metadata[]
│   ├── id                           id
│   ├── path                         path    XPath to repeating element (default ".")
│   ├── value_element                string  child element name for text migration
│   └── fields[]                     (recursive)
│       ├── "name"                   shorthand: name == path
│       ├── { name, path }           leaf field
│       └── { path, value_element, fields[] }   container
├── lookup[]
│   ├── id                           id      (required)
│   ├── metadata_id                  id      (required)
│   ├── data_id                      id | id[]   (required)
│   ├── inputs[]                     validated_name_expr[]
│   │   ├── "name"                   shorthand
│   │   └── { name, expr, required, pattern }
│   └── outputs[]                    validated_name_expr[]
│       ├── "name"                   shorthand
│       └── { name, expr }
```
