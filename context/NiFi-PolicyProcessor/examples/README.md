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

# Worked examples

Few-shot examples pairing a plain-language request with the policy tree that satisfies it.
Each tree validates against `../generated/descriptors.json`.

---

## Route documents by metadata

**Request:** "Route documents whose `doctype` metadata field equals `invoice` to the
`invoices` relationship, and everything else to `success`."

**Tree:** [`route-by-metadata.json`](route-by-metadata.json)

```json
{
    "policies": [{
        "type": "with-flowfile",
        "do": [{
            "type": "with-document",
            "do": [{
                "type": "route-by-metadata",
                "field-path": "doctype",
                "mode": "equals",
                "pattern": "invoice",
                "match-relationship": "invoices",
                "else-relationship": "success"
            }]
        }]
    }]
}
```

**Why:** `route-by-metadata` requires both `flowfile` and `document` context, so it is
wrapped in `with-flowfile` then `with-document`, which establish them. `mode` is one of the
`allowedValues` (`equals` / `contains` / `regex`). `match-relationship` and `else-relationship`
are flagged `isRelationship`, so `invoices` and `success` are the tree's exit relationships -
both must be added to the processor's *Output Relationships*.

---

## Set an attribute, then pass through (primitives)

**Request:** "Stamp every FlowFile with `processed = true` and send it to `success`."

```json
{
    "policies": [{
        "type": "with-flowfile",
        "do": [
            { "type": "set-flowfile-attribute", "name": "processed", "value": "true" },
            { "type": "transfer-flowfile", "relationship": "success" }
        ]
    }]
}
```

**Why:** this uses building-block policies (`set-flowfile-attribute`, `transfer-flowfile`)
because no single high-level policy covers "stamp then route". `transfer-flowfile`'s
`relationship` is flagged `isRelationship`, naming `success` as the exit.

---

## Orchestrate a multi-step workflow

**Request:** "Send each document through an `enrich` step, then (only if its `needsClassification`
metadata is `true`) a `classify` step - each a sub-flow that routes back to this processor. On any
step error route to `error`; once done, route high-confidence documents to `priority`, else `index`."

**Tree:** [`orchestrate-enrich-classify.json`](orchestrate-enrich-classify.json)

```json
{
    "policies": [{
        "type": "with-document",
        "do": [{
            "type": "orchestrate",
            "steps": [
                { "name": "enrich", "relationship": "enrich" },
                { "name": "classify", "relationship": "classify",
                  "when": { "type": "expression", "type:result-type": "boolean",
                            "value": "${'idol.xmlmetadata:needsClassification':equals('true')}" } }
            ],
            "max-iterations": 20,
            "on-exception": { "type": "transfer-flowfile", "relationship": "error" },
            "on-complete": {
                "type": "if",
                "condition": { "type": "expression", "type:result-type": "boolean",
                    "value": "${'idol.xmlmetadata:classification/confidence':equals('high')}" },
                "then": { "type": "transfer-flowfile", "relationship": "priority" },
                "else": { "type": "transfer-flowfile", "relationship": "index" }
            }
        }]
    }]
}
```

**Why:** `orchestrate` is a re-entrant dispatcher. Each `steps` entry is a **record** (a Group:
`name` + `relationship` + optional `when`), not a policy - `orchestrate` reads them to decide where
to route next, tracking progress in `wf.*` attributes. Each step's sub-flow does the work and routes
the FlowFile back here; on return the step is marked done and the next applicable step is dispatched.
The `classify` step's `when` is a Document-aware `expression` condition, so it runs only when the
metadata calls for it. When all steps are done, `on-complete` runs the final routing; a step that
sets the exception attribute routes to `error`; a runaway loop trips `max-iterations`. Use this on
the `FlowFilePolicyProcessor` (one FlowFile per trigger), with `enrich`/`classify` sub-flows wired
back to its input, and `enrich`/`classify`/`error`/`priority`/`index` in *Output Relationships*.

---

## Correlate related documents, merge them, then route

**Request:** "A document's metadata and its binary content arrive as two separate FlowFiles that
share a `doc.ref`. Hold each pair until both have arrived, merge them into one IDOL document, then
route documents whose merged `sensitive` metadata is `true` to `review` and the rest to `index`."

**Tree (the policy half):** [`correlate-and-merge.json`](correlate-and-merge.json)

```json
{
    "policies": [{
        "type": "with-flowfile",
        "do": [{
            "type": "with-document",
            "do": [{
                "type": "route-by-metadata",
                "field-path": "sensitive",
                "mode": "equals",
                "pattern": "true",
                "match-relationship": "review",
                "else-relationship": "index"
            }]
        }]
    }]
}
```

**Why - delegate the correlation/merge, don't inline it:** waiting for a related *set* of FlowFiles
to arrive (correlation across time) and combining IDOL Documents is **not** done inside the policy
processor. Put a **`MergeDocument`** processor upstream to correlate and merge, then let the policy
operate on the single, already-merged document. `MergeDocument` is IDOL-structure-preserving - it
recombines metadata and content/file parts into one Document - unlike NiFi's byte-concatenating
`MergeContent`. Configure its merge-filter to bin by the shared reference and complete once both
roles (metadata + content) are present:

| MergeDocument property | Value |
| --- | --- |
| Correlation Attribute | `doc.ref` |
| Completion Strategy | `Required Values` |
| Role Attribute | `idol.contenttype` |
| Required Values | `content, xmlmetadata` |

(That merge-filter generalises `MergeDocument` beyond only undoing a `SplitDocument`; its default
configuration still reassembles split documents unchanged.) Because the correlation and merge happen
upstream, the policy tree sees one document and collapses to the standard `with-flowfile` ->
`with-document` -> `route-by-metadata` shape (identical in form to the first example). `review` and
`index` are the exit relationships - add them to *Output Relationships*. This keeps the whole
"wait, merge, route" workflow governable while reusing a proven, non-native processor for the hard
correlate-and-merge step.
