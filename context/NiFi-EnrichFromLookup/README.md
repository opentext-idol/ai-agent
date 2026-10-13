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

# EnrichFromLookup - AI context bundle

This bundle is the complete reference for configuring the **EnrichFromLookup** NiFi
processor. It is intended to be handed to an AI assistant (or read directly) as the
authoritative source for what the processor does, how its JSON configuration is
structured, and what each piece looks like in isolation.

## What's in the bundle

| File / folder | Contents |
|---|---|
| `enrichfromlookup_context.md` | Full reference: overview, end-to-end data flow, configuration schema, processor properties, routing, EL expression reference. Start here. |
| `samples/EnrichFromLookup/*` | Focused snippets grouped by concept. Each group has an `_overview.html` (or `_cheatsheet.html`) explaining the concept, and small `.json` snippets that each illustrate one feature. |

The bundle can also be generated on demand by the "AI Bundle" button on the processor
configuration dialog; it always reflects whatever is shipped with the deployed
processor.

## How the samples are organised

The snippets are **illustrative fragments**, not complete runnable configs - each shows
one feature as clearly as possible and assumes the blocks it references (e.g. a
`zip_data` csv_file or a `postcode_metadata` metadata block) are defined elsewhere. A
real configuration is assembled by combining a `file_map`, one or more `csv_file`,
`metadata` and `lookup` blocks, in whichever files are convenient.

| Group | Covers |
|---|---|
| `1_csv_file/` | CSV data sources: `file_key`, header handling, `separator`, column renaming/computing via `names`, and `indexes`. |
| `2_metadata/` | The document's XML field structure: `path`, the three `fields` forms, nested containers, property-driven paths, and `value_element`. |
| `3_lookup/` | The lookup pipeline: `metadata_id`, `data_id`, and the `inputs` / `outputs` transforms (constants, required/pattern, derived outputs, multiple sources). |
| `4_file_map/` | Logical file aliases referenced by `csv_file.file_key`. |
| `5_expressions/` | A cheatsheet of NiFi EL patterns used in `names` and `inputs` / `outputs`, plus a cross-cutting case-insensitive matching example. |

Each group's `_overview.html` / `_cheatsheet.html` carries the longer explanation; the
`.json` snippet headers are just a short title and one-line summary.

## Quick start

1. Read `enrichfromlookup_context.md` end to end - it is the single source of truth.
2. Skim the `_overview.html` in each sample group to understand the four block types.
3. Assemble a configuration: a `file_map` entry, a `csv_file` over it, a `metadata`
   definition matching your document's XML, and a `lookup` tying them together. Adapt the
   relevant snippets rather than starting from scratch.
4. Drop the resulting JSON into a directory referenced by the processor's
   `Lookup Configuration Directories` property; set `Lookup Identifiers` to the
   `lookup.id` values you want to run.

## IDs

Every block `id` is a string, globally unique across all loaded configuration files, and
referenceable from any file. (Integer ids are still accepted and treated as their string
form for backwards compatibility, but new configuration should use descriptive string
ids.)
