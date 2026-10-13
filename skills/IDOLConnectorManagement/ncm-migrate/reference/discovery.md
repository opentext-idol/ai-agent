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

# Investigating repositories

Four endpoints let a connector answer questions about the repository it is attached to. They talk
to the live repository, so the connector must exist, be configured with working credentials, and
be enabled. All are POST, because an identifier is an opaque string that does not belong in a URL.

Together they answer: what is in there, what does a document look like, what may I create, and is
the content what I think it is.

## Walking the hierarchy

```
POST /v1/connectors/{id}/list/identifiers
{ "identifier": "ROOT" }
```

`ROOT` is the one reserved identifier and lists the repository's top level. Every other value is
an opaque identifier taken from a previous response.

```json
{
  "identifiers": [
    { "identifier": "<opaque>", "name": "Marketing", "type": "folder",
      "attributes": ["container"], "meta": { "modified": "2026-03-01T09:00:00Z" } }
  ],
  "errors": [ ... ]
}
```

Each `ChildIdentifier` carries `identifier` (pass this back to descend), `name` (display only),
`type` (the repository's own object type), `attributes`, and `meta` - an open map of
name/value strings.

**`meta` is empty unless you ask for it.** Add a `meta` array to the request naming the per-item
values you want - `createdDate`, `modifiedDate`, `sizeBytes` - and each is returned in every
descendant's `meta` map:

```json
{ "identifier": "ROOT", "meta": ["sizeBytes", "modifiedDate"] }
```

Support is per connector and per value: one that does not report a requested value simply omits it,
so an absent entry means "not reported", never "zero". Each value costs the connector extra work per
item, so ask for what you will use. Dates are epoch seconds, sizes are bytes, both as strings.

**On a crawl-shaped source, each listing is a live retrieval.** For a repository with a folder tree,
`list/identifiers` navigates something that already exists. For a web-style source it does not:
`ROOT` is the configured start URLs, and the children of a page are found by **fetching that one
page** and reading its links. One call, one page - the API exposes no depth, so a listing never
expands the tree on its own.

The cost is in the walking. Descending a crawl source means one live fetch per page you expand, so a
full walk costs about what a crawl costs, and **nothing bounds it**: `MaxDepth`, `MaxPages` and their
equivalents are get-only properties, so they constrain a synchronize and not your listing. The URL
include/exclude regexes are the only configured controls that apply. Set your own depth and page
budget before descending, and sample rather than enumerate.

**`attributes` is not an either/or, and this will break a naive walker.** Folders report
`["container"]`, but in repositories where a document can itself contain children, a document reports
**`["container", "document"]`** - both. Code that tests `container` first and recurses will then
descend into every document, find no children, and report that the repository holds no documents at
all. Test for `document` first, or treat the two as independent flags. The repository's own `type` is
the clearer signal once you recognise its vocabulary.

**Treat `identifier` as opaque.** Never build one by concatenation, never infer a scheme from
examples, never assume it is a path. The only identifier you may invent is one built from an
insertable-object template.

`errors` is for non-fatal problems: a subtree the credentials cannot see, an object the repository
would not describe. A response can be partially successful, so check it - a short listing with
errors is not an empty folder.

Descend deliberately. Repositories are large and each call is a live request against the
repository, under a timeout (`connectors.view.timeout.seconds`, default 60, raised per deployment with
`CONNECTORS_VIEW_TIMEOUT_SECONDS`) that applies to
listing and viewing alike - exceed it and you get a 500 rather than a clean answer, so a slow or
very large branch is better narrowed than retried. Follow the branches that matter to the
migration, and stop when the shape is clear rather than enumerating everything.

## Reading the metadata schema

```
POST /v1/connectors/{id}/identifiers/metadata-schema
{ "identifier": "<a specific document>" }
```

The identifier must be a specific document; `ROOT` is rejected here.

```json
{ "fields": [
  { "name": "title", "type": "string", "attributes": ["required"], "aliases": ["subject"] },
  { "name": "authors", "type": "string", "attributes": ["multivalued"] },
  { "name": "properties", "type": "object", "attributes": ["open"],
    "subFields": [ { "name": "department", "type": "string" } ] }
] }
```

- `type`: `object`, `integer`, `number`, `boolean`, `string`, `date`, `url`, `guid`.
- `attributes`: `multivalued` (may hold several values), `required` (must be present), `open` (an
  object field accepts arbitrary further keys).
- `aliases`: other names the same field is known by. **Always check aliases before concluding a
  field has no counterpart** - most apparent mismatches between two repositories are one field
  with two names.
- `subFields`: present when `type` is `object`; schemas nest arbitrarily deep.

Sample more than one document. A schema is reported for the identifier you asked about, and
different object types in the same repository expose different fields.

**The schema describes as much as the connector chooses to declare, which need not be everything a
document carries.** It is a useful basic structure, not an inventory. Some of the gap is inherent: a
repository may allow arbitrary user-defined fields, or may not expose enough type information for a
connector to describe a schema fully without repository-specific knowledge it does not have.

Measured on one repository: `metadata-schema` reported 16 fields for a document, while migrating that
same document produced a metadata companion holding 78 elements - the repository's full attribute
set, including every field of the document's own subtype and the repository's internal bookkeeping
attributes. None of the subtype's fields appeared in the schema.

A gap that large is worth reporting as a **connector** issue rather than working around: the fix
belongs in the connector's schema description, not in the migration you are configuring.

Two consequences when planning a mapping:

- **Do not conclude a field is unavailable because the schema omits it.** The schema is the set the
  connector declares as generally useful, not everything it emits.
- **Do not report data loss from the schema alone.** Migrate or `view` one document and inspect what
  actually arrives at the destination before telling a user a field will be dropped - the honest
  answer is usually that more survives than the schema advertises.

## Learning how to insert

```
POST /v1/connectors/{id}/identifiers/insertable-objects
{ "identifier": "<the destination location>" }
```

```json
{ "definitions": [ {
  "identifierType": "document",
  "description": "A file within this folder",
  "reference": { "components": [
      { "placeholder": false, "value": "folder:1234/" },
      { "placeholder": true,  "value": "filename" } ] },
  "properties": { "displayName": { "components": [ { "placeholder": true, "value": "title" } ] } },
  "metaSchema": [ { "name": "description", "type": "string" } ]
} ] }
```

Read a template by concatenating `components` in order: where `placeholder` is false, `value` is
literal text to use verbatim; where true, `value` names a placeholder whose value you must supply.
So the example above builds `folder:1234/<filename>`.

This is the destination's own statement of how identifiers are formed, and it is the only
sanctioned way to construct one. `metaSchema` describes the metadata the new object accepts, in
the same form as a document metadata schema - which is what makes it directly comparable with the
source schema from the previous section.

Different locations offer different definitions, so ask at the specific location documents will
land in. As with the metadata schema, ROOT is rejected here with a 400 - and the check runs before
the connector is even resolved, so do not read that error as a broken connector.

**An empty or absent `metaSchema` is an answer.** It says the destination stores no metadata of its
own, which decides the target's `insertMode` and means there is nothing to map to.
`metadata-mapping.md` takes it from here: putting the two schemas side by side, finding the field
names the processing graph adds (which no schema reports), and expressing the mapping.

## Checking the content

```
POST /v1/connectors/{id}/view
{ "identifier": "<a specific document>" }
```

Returns the document's content with a `Content-Disposition` filename, and the document's **own MIME
type** when the connector reports one - the `application/octet-stream` the spec declares is only a
fallback. **The filename is not necessarily the source name**: one repository returned the object's
internal id plus a generated suffix, for a document whose stored name was entirely different. Use the
filename as a hint about format, not as the document's identity - the name lives in the metadata. Not every connector reports a type: the FileSystem connector does not for plain files, and
you get `application/octet-stream` there. So treat a specific type as evidence to compare against
what the metadata claimed, and a generic one as no information either way.

Use this to confirm what the content actually is before designing processing - whether files are
the format the metadata claims, whether text extraction is needed, whether documents are containers
holding others.

Retrieve one or two representative documents, not a corpus. This is a live retrieval from the source.

**To see a document's metadata rather than its content, use `view/metadata`.** It is the VIEW
operation *asked* for metadata only. Whether that actually avoids the transfer is up to the
connector: some skip the content, others retrieve the document anyway and return only its metadata,
so treat this as "the metadata is what I get back", not as a guaranteed saving. On a connector that
does the full retrieval it is no faster than `/view`, and a large document can exceed the request
timeout:

```
POST /v1/connectors/{id}/view/metadata     {"identifier": "<opaque>"}
```

**The response is `text/xml`, not JSON** - the connector's own metadata, passed through. The split
from `metadata-schema`, which is JSON, is deliberate: a schema is a *description* and carries type,
cardinality and aliases alongside each name, while these are the values themselves and are XML in the
repository. Metadata is
XML natively: fields nest, repeat, and may carry XML attributes, so remodelling it as JSON would drop
detail rather than add clarity. Expect a sequence of sibling elements, one per emitted value, so a
multivalued field appears several times under the same name - which is how you tell a multivalued
field from a single one in practice. Wrap it in a root element if your parser wants one document. This is the fastest way to compare what a document *carries*
against what `metadata-schema` *declared*: the two differ more often than not.

## From investigation to a mapping

With a source schema and a destination `metaSchema`, decide per field:

1. Is there a counterpart, allowing for `aliases`?
2. Are the types compatible, and is a conversion needed (`date` formats, `guid` to `string`)?
3. Is the source `multivalued` where the destination is not? Choose a rule - first value, join,
   or drop - and state it.
4. Is the destination field `required` with no source counterpart? Choose a default or accept that
   insertion will fail.
5. Where does the destination identifier come from - which source field feeds each placeholder in
   the reference template?
6. What has no destination at all? Say so - but check what the destination does with unmapped fields
   before calling it loss. A **connector-type target writes a companion metadata document** carrying
   the metadata the connector emitted, whatever its insert `metaSchema` declares. So a target that
   accepts two fields is not necessarily discarding the other thirteen: they are usually preserved
   alongside the document rather than mapped into the destination's own attributes. The distinction
   that matters to a user is "queryable as native destination metadata" versus "carried alongside",
   not "kept" versus "lost". Migrate one document and read what lands before reporting either.

Content transformation - extraction, filtering, sectioning, language detection, format conversion
- is not part of this mapping. It is configured as steps in the target's processing graph; see
`configuration.md`.

Put the mapping in front of the user before building. It is the decision they own.
