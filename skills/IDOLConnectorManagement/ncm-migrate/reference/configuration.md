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

# Configuring and operating a pipeline

Payload shapes, the deployment lifecycle, and what the monitoring endpoints actually mean.

## Properties

Connector, target and processing-step configuration all use the same property form: a list of
`{ "id": ..., "value": ... }` where `id` comes from the type's property schema. Never guess an id -
read `GET /v1/types/{connectors|targets|processing}/{type}` first.

```json
{ "id": "MaxPages", "value": "5000" }
```

Variants that matter:

- **Sectioned properties** nest via `sectionProperties`, mirroring the `section` structure in the
  definition.
- **Connector properties** may carry `operations`, scoping a value to particular operations - so
  the same connector can, for example, use different settings for `get` and `fetch`.
- **Secure properties** (`secure: true` in the definition) are returned **redacted**, so a
  GET-then-PUT round trip blanks them unless re-supplied. They are *not* encrypted at rest -
  depending on the deployment's keys provider they are either stored inline or tokenised into a
  separate table, both in plain text. See "Choosing a keys provider" in `ncm-deploy`.
- **Templated values** replace `value` with a `valueTemplate`, naming a template id from the
  definition and filling its placeholders. This is how OAuth credentials are supplied:

```json
{ "id": "Credentials",
  "valueTemplate": { "id": "oauth2_google",
                     "placeholders": { "client_id": "...", "client_secret": "..." } } }
```

- `multiValued` properties take repeated entries with the same `id`.
- **`file`-typed properties** (`type: file` in the definition) name a file the connector reads.
  Read the description to decide how to supply it, because there are two quite different cases and
  the type alone does not distinguish them:
  - *Content you hold locally* - a certificate or key file. Upload it, as below.
  - *A path on the connector's own host* - a folder list, for instance, whose description reads like
    "folders to search for files". Pass the path as an ordinary JSON string. **Do not upload
    anything.** An upload is stored as a temporary file and the property is rewritten to point at it,
    so the connector reads that temporary file instead of the location you meant, and reports
    something like `Directory does not exist or is not accessible: ...data-uri-<hash>.tmp`.

  To upload, send the request as `multipart/form-data`: the JSON goes in a part named `request`, and
  each file goes in a further part whose **part name matches the string value** you gave that
  property. That value is replaced by a data URI before the request is processed, and a file part
  matching no property value is rejected with 400. This works on create, PUT and PATCH for both
  connectors and targets. The match is blind: the server pairs a part name against property *values*
  without checking the property is `file`-typed, so any property whose value happens to equal a part
  name is rewritten too - keep those values distinctive.
- `dependsOn` means a property only applies when another holds one of the listed values. Setting a
  property whose dependency is unmet is at best ignored.
- `defaultValueFrom` means a property has no fixed default: left unset, it takes the value of the
  property named there (that property's own default if it is unset too). Set it only to override.

### Cross-property constraints

`dependsOn` says when a property applies. **`constraints` says which combinations of values are
legal**, and it is the only place those rules appear. A type detail returns them alongside the
property list, alongside `propertyGroups` naming the groups they refer to:

```json
"constraints": [
  { "id": "ConnectionOptions-1",
    "message": "Set Port when UseSecureConnection is false.",
    "nodes": [ { "type": "allOf", "nodes": [
                 { "type": "equals", "property": "UseSecureConnection", "value": "false" },
                 { "type": "configured", "property": "Port" } ] } ] }
]
```

**Enforced for connectors and targets; not for processing steps.** A connector or target
configuration that breaks one is rejected with a 400 quoting the constraint id and its `message`.
A processing step's configuration is not validated at all, so a broken rule there is created
quietly and fails later as a runtime or licensing error with no mention of the rule. Either way,
reading `message` and checking the tree first turns a rejection - or a silent misconfiguration -
into something you can explain before submitting.

Two attributes change whether a rule applies at all:

- **`appliesWhenConfigured`** names an optional property group the rule is conditional on. Until
  something in that group is set, the rule does not apply - so do not report it as broken. A
  group is marked `optional: true` in `propertyGroups`.
- **`evaluable: false`** on a node marks a leaf naming a property that is not published, so its
  value is not in the detail. Treat the enclosing constraint as guidance to surface rather than a
  test to run.

Leaves:

| Leaf | True when |
|---|---|
| `configured`, `property` | that property has a value |
| `configured`, `group` | any member of that `propertyGroups` entry has a value |
| `equals`, `property` + `value` | the property is set **and** equals the value |

A `property` may be a dotted path - `ChannelMessageGroupingSection.MessageGroupingStrategy` - which
means the outer section property is set and the inner condition holds within it.

Combinations hold `nodes` and are true when the count of true children satisfies the type:
`allOf` all, `anyOf` at least one, `oneOf` exactly one, `noneOf` none, `not` its single child being
false, `allOrNoneOf` all or none, and `exactly` / `atMost` / `atLeast` compared against `count`.

Two things to get right:

- **An unset property reports false, never unknown.** So `not(equals(X, "v"))` is satisfied when X
  is absent *as well as* when it differs. Do not read a negated equality as "X is set to something
  else".

Constraints appear on connector, processing **and** target details, and section-scoped ones appear
inside the relevant `sectionProperties`. An `id` is unique only within its container, so qualify it
by container if reporting across several.

### Where a metadata mapping actually lives

**A mapping is expressed through the ordinary declared properties of whatever component performs
it** - there is no separate mapping structure in any request body. Read the property list of the
target type and of each processing type and look for the properties that name fields. Two shapes
recur, both verified in practice:

- **One property naming the output field.** `DetectContentLanguage` declares `OutputField` - "the
  name of the output metadata field to store the detected language". Set it to `MAPPED_LANGUAGE` and
  the document arrives carrying `<MAPPED_LANGUAGE>ENGLISH</MAPPED_LANGUAGE>`.
- **Two parallel multi-valued properties, paired by position.** `Eduction` declares `Entity` ("the
  name of Eduction entities to map to metadata fields") and `EntityField` ("the name of metadata
  fields to map Eduction entities to"), each `multiValued`, and its own description states they
  "must have the same number of elements". Supply them as repeated entries with the same `id`; the
  first `Entity` maps to the first `EntityField`, and so on. Order is the mapping, so a mismatched
  count is a silent misalignment rather than an error.

Values need not be scalars. An Eduction match arrives as a repeated structured element - one per
match, each carrying `entityname`, `value`, `offset`, `length` and `score` - so a mapped field can be
richer than the source field it came from. Look at one landed document before describing the result
to a user.

Dynamic properties, below, are a different thing and are usually **not** the mapping.

### Dynamic properties - user-named configuration

A type may accept **user-named** properties beyond its declared ones. Despite the name they are
generally *configuration passthrough*, not field mapping: the catch-all family on `Eduction` is
"Eduction Config Option", and the canonical example elsewhere is a scripting processor taking `py:`
module names and arbitrary script options. Treat a dynamic-property family as a mapping mechanism
only when its own `description` says it maps fields - and expect most types to declare none at all.

**Three kinds of type can declare them**, and all three detail endpoints report them:
`/v1/types/connectors/{type}` (the union across the connector's operations), `/v1/types/targets/{type}`
and `/v1/types/processing/{type}`. On a target they carry the field mapping; on a connector they
configure the source processor; on a processing step they are set in that step's own `properties`
inside the graph. Only **processor-backed** types can declare any - a flow-backed type never does -
and an empty set is reported as `null` or omitted rather than as an empty list, so treat absent as
"none accepted".

Each entry describes a *family* of accepted names:

- `prefix` - a name starting with it belongs to this family. An entry with **no** prefix is a
  catch-all accepting any name.
- `displayName` and `description` - what these properties represent and how their values are
  interpreted. **Read the description**; it is the only statement of the value syntax, and it
  varies by type.

They are supplied in the ordinary `properties` list, as `{"id": "<the name you choose>", "value":
"..."}`. **A name that matches no declared property and no dynamic-property family is rejected -
`400 Property '<id>' not found`** - so a mistyped mapping fails the whole create loudly rather
than quietly doing nothing. Three conditions must all hold or you get that same 400:

- the name matches a declared dynamic-property prefix (or a catch-all entry);
- it is supplied with a literal `value` - a `valueTemplate` is not accepted here;
- it is at the **top level** of `properties`, not nested under `sectionProperties`.

**An entry with no `prefix` withdraws that protection entirely.** A catch-all family matches every
name, so on such a type *no* property id is ever rejected and a typo becomes a configuration option
with a `201` to go with it. Check ids against the type detail rather than relying on the 400, and
verify the step did something. The scripting types are the common example.

One thing they do silently: **dynamic property values are applied raw and are never tokenised**,
whichever keys provider is configured. Do not put a credential in one and assume the keystore
protects it.

If a target type declares no `dynamicProperties`, it accepts no field mapping, and whatever
metadata the connector emits is what is written. Say so rather than inventing a mechanism - and check
whether a **processing step** in the graph can do the transformation instead, since a processor-backed
step may accept dynamic properties even when the target does not.

**For renaming fields to arbitrary destination names, the mechanism is a scripting step rather than
any declared property.** `ExecuteDocumentPython` and `ExecuteDocumentLua` edit the document's XML
metadata directly, as the graph's last step before `@ingest`. `metadata-mapping.md` covers it: when
it is needed, how to discover the field names, and the traps.

## Creating a target

```json
POST /v1/targets
{
  "type": "GoogleCloudStorage",
  "version": "<from the type listing - omit for latest>",
  "name": "Destination repository",
  "properties": [ ... ],
  "operations": ["get", "fetch"],
  "namingStrategy": "original",
  "partitionStrategy": "none",
  "insertMode": "parts",
  "processing": { "entry": "extract", "steps": [ ... ] },
  "enabled": true
}
```

- `type` is a target type id - which may be a put-capable **connector** type, in which case
  `properties` are that connector's `put` properties.
- **A connector target only ever writes.** Additions are applied; a document sent again is written
  again, replacing the copy already there under a stable naming strategy. A delete or an in-place
  update reported by the source connector is acknowledged and *not* applied - the document is
  recorded as processed and the destination is untouched. These targets are for one-way
  migrations, so a destination converges on everything the source has ever sent, not on what the
  source currently holds. Nothing in the reports or the job counts distinguishes a document that
  was written from one that was skipped this way, so the difference will not show up in
  verification either - it has to be said in advance.
- `operations` optionally restricts which **connector** operations may ingest into this target -
  `get`, `fetch` and so on. These are the consuming connector's operations, not the target type's
  own `put`. Omit it unless you specifically want to restrict use.
- **These three apply only to targets whose type is a connector.** On an IDOL, IDOLGraph or
  Pipeline target they are accepted, return 201 and do nothing.
- Their defaults are deployment-configurable (`target.default.naming.strategy` /
  `.partition.strategy` / `.insert.mode`), shipping as `uuid`, `none` and `parts` - so omitting the
  field does not guarantee `uuid`. Set it explicitly when it matters.
- On a connector target, all three naming strategies write beneath a fixed
  `/<tenantId>/<subscriptionId>/<connectorId>` prefix, so destination paths are never
  byte-identical to the source. Say that plainly if a user expects an exact path match.
- The **create response is a trimmed view**: it echoes `processing` without each step's `routes`, and
  omits `namingStrategy`, `partitionStrategy` and `insertMode` entirely. That is not a sign they were
  ignored - `GET /v1/targets/{id}` returns them all. Confirm there rather than in the 201 body.
- **None of them can be changed by an update** - like `target` and `operations`, getting one wrong
  means delete and recreate.
- **`namingStrategy` decides what a document is called; `partitionStrategy` decides where in the
  tree it goes.** Partition levels sit between the fixed prefix and the name:

  ```
  /<tenantId>/<subscriptionId>/<connectorId>/  [partition]  /  <name>
  ```

| `namingStrategy` | A source `/docs/policy.txt` lands at | Re-running |
|---|---|---|
| `uuid` (default) | `<prefix>/3f2a...` | a **new** name each run, so a second copy |
| `monotonic` | `<prefix>/1756131840000042` | a **new** name each run; also not unique across NiFi nodes |
| `original` | `<prefix>/docs/policy.txt` | same name, overwrites |
| `originalunique` | `<prefix>/docs/policy__a91c4f2b8e77.txt` | same name, overwrites |
| `identifierhash` | `<prefix>/9f86d081884c7d65...` | same name, overwrites |

**`AUTN_MIGRATION_URI` and `idol.put.migrationuri` are the same value at two stages.** The connector
puts `AUTN_MIGRATION_URI` in the document's metadata; the framework copies it onto the flowfile as
`idol.put.migrationuri`; the target's naming expression reads the attribute. So a check for the
metadata field on one document (Phase 3) tells you whether the attribute will be there at write time,
and the two names are not two features.

- **`original` and `originalunique` need the source to emit `AUTN_MIGRATION_URI`** to reproduce its
  structure. The path is built from that field, and a document for which it supplies no usable path is named
  as `identifierhash` instead: it is written, to the same hash-named object on every run, but under no
  source path. So the strategy degrades quietly rather than failing - a target set to `original`
  against a source that reports nothing produces a flat tree of hashes. Confirm the field on one
  document (`POST /v1/connectors/{id}/view/metadata`) before choosing either; measured on a Web
  crawl, the field is absent for every document.
- **Where there is no migration URI, set `identifierhash` explicitly**, not `uuid` and not
  `original`: it is what `original` falls back to anyway, and stating it means the configuration
  describes the result. It names each document from a hash of its source identifier, so it needs no
  path *and* a re-run overwrites its previous copy instead of adding another. Structure still
  cannot be reproduced.
- **`originalunique` is the safe form of `original`.** It inserts a hash of the identifier before the
  file extension (`policy__a91c4f2b8e77.txt`, or `README__a91c4f2b8e77` where there is none), keeping
  the source folder tree exactly while making duplicate source names impossible to collide. Prefer it
  over `original` unless the destination names must match the source byte for byte.
- `partitionStrategy`: `none`; `ingestdate` to write into `yyyy-MM-dd` subdirectories; or `hash` to
  spread documents over two levels of two hex characters from the identifier hash (65,536 buckets),
  which stops one directory holding every document. `hash` is worth it with `uuid` or
  `identifierhash` on a large corpus. Combined with `original` it recreates the source tree
  *underneath* a bucket - scalable, but no longer a faithful copy, so the two are usually
  alternatives.

### `insertMode` - one object per document, or one per part

`namingStrategy` and `partitionStrategy` decide *where* a document is written. `insertMode` decides
*what shape* it arrives in.

| `insertMode` | A source `policy.txt` lands as | Its metadata |
|---|---|---|
| `parts` (default) | the content, plus `<name>.metadata`, plus `<name>.text` where the graph extracted text | an XML companion object beside the content |
| `document` | one object, the content | handed to the destination with the content - stored only as far as that destination supports it |

- **`parts` doubles or triples the destination's document count.** Every strategy above is applied
  to the content object; the companions take its name with a suffix. A destination listing showing
  two or three times as many documents as you migrated is the expected shape under this mode, not a
  fault - and `list/identifiers` counts the companions as documents in their own right.
- **`document` is the mode that populates destination properties.** Repositories that hold their own
  metadata - SharePoint columns, OpenText node attributes - can only be given it when content and
  metadata arrive together. Under `parts` those properties are left empty and the metadata sits in a
  companion file instead.
- **`document` on a destination that stores no metadata loses it.** A FileSystem destination, for
  instance, uses the metadata only to restore file timestamps and writes nothing else, so the
  source's `AUTN_MIGRATION_URI` and `AUTN_IDENTIFIER` do not survive the write. Under `uuid` naming
  that companion was the only place the original name existed - so `document` + `uuid` leaves
  documents with no recoverable link to their source. Pair `document` with `originalunique` or
  `identifierhash`, or keep `parts`.
- **Extracted text is not written under `document`.** A processing graph that extracts text still
  runs, and the extraction is still used by any step that consumes it, but there is no `.text`
  object at the destination.
- **Check what the destination will actually keep before choosing `document`.** Against the
  destination *as a connector*, `POST /v1/connectors/{id}/identifiers/insertable-objects` reports
  each insertable object's `metaSchema` - the fields that repository accepts. An empty schema means
  nothing of the metadata will be stored, which makes `parts` the mode that preserves it.
- **`document` is the mode that needs a metadata mapping**, since the destination keeps only the
  names its `metaSchema` declares and there is no companion to fall back on. `metadata-mapping.md`
  is the how: the two schema endpoints, the probe run that reveals the field names the processing
  graph adds (nothing reports those), and the scripting step that does the renaming.

## The processing graph

A directed acyclic graph. Documents enter at `entry` and leave through routes aimed at sentinels.

```json
"processing": {
  "entry": "extract",
  "steps": [
    { "id": "extract", "type": "KeyViewExtractFiles",
      "routes": { "success": "language", "failure": "@error" } },
    { "id": "language", "type": "DetectContentLanguage",
      "properties": [ { "id": "...", "value": "..." } ],
      "routes": { "success": "@ingest" } }
  ]
}
```

- `id` is unique within the graph, `^[A-Za-z][A-Za-z0-9_-]*$`, max 100 characters.
- **Every step must be reachable from `entry`.** A step nothing routes to is a validation failure,
  not a dormant step - a graph that names one is rejected with the unreachable ids listed. A cycle
  through two or more steps is rejected too.
- **A step may route a relationship back to itself only where its type allows it.** `GET
  /v1/types/processing/{type}` names those: `loopbackRelationships` lists them, and
  `dynamicRelationshipsLoopback` says whether the relationships the step creates from its own
  configuration may loop. This is how a step re-processes its own output - `KeyViewExtractFiles`
  routing its sub-file relationship back to itself to extract nested containers. The step still
  needs a route onward to `@ingest`; the loop alone is not a path out.
- `type` is a processing type id; `version` defaults to the latest.
- **A processing type is backed either by a NiFi flow or by a single processor**, decided by whether
  its `manifest.xml` carries a `<flow>` or a `<processor>` element. Both are used identically in a
  graph and the id does not tell you which, but only a processor-backed step exposes
  `relationships`, dynamic relationships and `dynamicProperties` - so only a processor-backed step
  can take user-named properties. A flow-backed one takes what its flow declares and no more. This
  is the same split that decides whether a *target* accepts a field mapping. `GET
  /v1/types/processing/{type}` is what tells them apart.
- **Read `GET /v1/types/processing/{type}` before writing `routes`** - a step's relationship names
  come from its own definition, and `success`/`failure` are not universal. An unrouted relationship
  fails validation unless it is listed in `optionalRelationships`.
- `routes` maps each **output relationship the step emits** to another step's id or a sentinel:
  - `@ingest` - on to the target's ingest.
  - `@error` - reported as a failure.
  - `@drop` - discarded via the ingest cleanup path.
- `failure` defaults to `@error` if omitted. The names a type lists in `optionalRelationships` may
  be omitted too, but they do not default to anything - they are simply left unconnected, so their
  output is discarded, which is what the processor does with them by default anyway. **Every other
  emitted relationship must be routed explicitly** - an unrouted relationship is a validation
  failure, not a silent drop.
- **That rule covers declared, non-optional relationships only. Where a type reports a non-empty
  `dynamicRelationships`, `routes` accepts any relationship name at all** - the names come from
  that step's own configuration, so NCM can neither predict nor reject them. That is the mechanism
  by which a scripting step routes relationships it invents; it also means nothing checks the names
  agree with the properties that create them, so an unrouted one passes the create and fails
  NiFi-side instead, arriving as `enabled: false` plus `validationErrors`. The scripting types are
  the case that bites - they declare only `failure`, and even their `success` is just the default
  value of a property. See `metadata-mapping.md`.

**Anything that analyses content needs the content extracted first, and fails silently if it is
not.** A connector hands on the file, not its text. `DetectContentLanguage` alone over a plain text
file produced *no* output field, no error, no report and a `success` route - a clean run that mapped
nothing. Putting `KeyViewFilterDocument` (with `ExtractContentText` true) ahead of it made the same
graph populate the field. So when a step that should enrich a document produces nothing, suspect a
missing extraction step before suspecting the step itself, and prove the graph on one document before
running a corpus.

**A step can require a controller service that the deployment must be configured to create.** Adding
`DetectContentLanguage` to a graph failed the whole target create with
`500 Unsatisfied controller service: idol.nifi.service.KeyViewFilterService` until the deployment was
given the auto-create settings (see `ncm-deploy`). That is an operator change, not something the
migration payload can fix - so check it early if a graph refuses to be created at all.

**A property the type schema marks required must be supplied**, or create and PUT are rejected
with `400 Required property '<id>' is not set` before anything is deployed. This applies per
enabled operation, and a property whose `dependsOn` condition is unmet is not required. Values
outside a property's `allowableValues` are refused the same way.

**Everything else is validated NiFi-side and reported per step.** A create can return `201` while
leaving `enabled: false`, `deploymentStatus: deployed` and a `validationErrors` map keyed
`<Type>#<stepId>` - for example `{"Eduction#ed": ["... ResourceFiles cannot be empty"]}`. Note that
message came from a property whose schema said nothing about being required: **`required` in the
type schema is a floor, not the whole of what the processor will insist on**, so read
`validationErrors` as well, and treat a target that will not enable as a configuration problem to
read, not a deployment fault.

For `Eduction` specifically, ask the deployment what it has rather than guessing:
`GET /v1/types/processing/Eduction/grammars` lists every grammar the type can load, each with the
`resourceFile` value to put in `ResourceFiles` and the entities it defines (names like
`company/all/enggb`, with a `suggestedField` for the paired `EntityField`, and the category,
languages and countries to choose by). Narrow it with `search`, `category`, `language`, `country` or
`group` - the full listing is long. Once the target exists,
`POST /v1/targets/{id}/processing/{stepId}/test` with a representative `content` runs the step as
configured and returns what it matched and where each match would be written, so a mapping can be
checked before anything is ingested. A step that matches nothing there will match nothing in the
migration either.

For `KeyViewRouteOnFileType`, each routing property - one named after the relationship it routes to -
and `DiscardFileTypes` take a comma-separated list of file type tokens.
`GET /v1/types/processing/KeyView/file-types` lists them: `c:<class>` for every format of
a document class, `f:<format>` for a format, `cf:c:<class>:f:<format>` for a format within one of its
classes. Search it by name, extension or MIME type (`?extension=pdf`) and copy the tokens into the
property; a file matches when any of them does. A value containing expression language is evaluated
as an expression instead, and a token the deployment's KeyView does not know is reported in the step's
`validationErrors`.

Typical migration graphs are short: extract text from files, filter or convert, then `@ingest`.
Available types depend on what the deployment serves - `GET /v1/types/processing`.

To change a graph later, use **PUT** with a replacement `processing` (or `null` to clear it).
PATCH does not accept the field at all - a graph is replaced whole, never merged - so sending one
to PATCH is a 400 naming `processing`, not a silent no-op.

## Creating a connector

```json
POST /v1/connectors
{
  "type": "Web",
  "version": "<from the type listing - omit for latest>",
  "name": "Source repository",
  "operations": ["get", "list", "view", "fetch"],
  "target": { "get": "<targetId>", "fetch": "<targetId>" },
  "properties": [ ... ],
  "cronSchedules": { ... },
  "enabled": true
}
```

- `target` maps operation to target UUID. **`null` means no target at all** - not a fallback or a
  default - and an operation with none discards every document it produces. That is a way to
  exercise a connector's configuration without writing anywhere; it is not a configuration to
  leave in place, and nothing later will report that the documents went nowhere. `targetId` is
  shorthand, valid only when exactly one operation is selected, and mutually exclusive with
  `target`.
- **Only `get`, `groups` and `fetch` can have a target**, and the schema says so - they are the
  operations that produce documents to ingest. Anything else (`view`, `list`, `delete`, ...) is not
  a member of the object and is rejected as an unknown field, so `"view": null` is an error rather
  than a harmless no-op it used to be. Check `/spec/public_api.yaml` rather than inferring the set
  from `operations`.
- **A key must also name one of *this* connector's `operations`** - a target for an operation it
  does not perform is rejected with a 400 naming it. Both rules are worth getting right first
  time: the mapping cannot be changed by an update, so a wrong entry means deleting the connector
  and creating it again.
- **`get` requires an explicit entry** in `target` - pass `null` deliberately if it should have
  none. Other operations may be omitted; nothing rejects a `fetch` without a target entry, but it
  then has nowhere to ingest.
- `cronSchedules` schedules recurring synchronizes per operation. Like `target`, and like a
  property's own `operations`, it may only name an operation this connector performs - a schedule
  for anything else is a 400 naming it. The rule is the same in all three places because the
  configuration is applied per operation and an operation the connector does not perform has no
  flow to apply it to.

Updating is narrower than it looks:

- **Neither PUT nor PATCH works on a deployed, enabled entity** - connector or target, the answer
  is **409 `cannot be updated while enabled`**. The guard is on the internal deployment status
  rather than the `enabled` flag, so it bites in MANAGED mode, where enabling deploys; in
  TEMPORARY mode nothing reaches that state and updates go through. Disable first, update, then
  re-enable - and disable is a fast teardown, so do it when nothing is running.
- **A connector update applies exactly `cronSchedules`, `properties`, `name` and `enabled`.** A
  rename takes effect immediately and needs no redeployment - the name is held only in the state
  store, and nothing deployed is named after it. Clearing synchronize state is **not** an update:
  it is `POST /v1/connectors/{id}/{get|groups}/reset`, which needs the connector enabled and is
  per sync operation. Everything else - `target`, `targetId`, `operations` - cannot be changed at
  all: retargeting a connector, or adding an operation to it, means **delete and recreate**.
  (A *target* update is different: a PUT does replace its `processing` graph, as above.)
- **Omitting `name` keeps the existing name**, on PUT as well as PATCH.
- **A field the request schema does not declare is rejected with 400**, naming the field and
  listing what is permitted - so `targetId` on an update is an error, not a no-op. The exception
  is the metadata the server itself emits (`id`, `tenantId`, `subscriptionId`, `createdAt`,
  `updatedAt`, `deploymentStatus`, `validationErrors`, `errors`, `synchronizationStatus`,
  `supportedOperations`, `_links`), which is accepted and ignored so a fetched object can be sent
  back with one field edited. Accepted, but not free to change: if `id` names a different resource
  than the URL, or `tenantId`/`subscriptionId` a different tenant, the request is a 400 rather
  than an update applied to the wrong resource.
- **A body that will not parse is a 400** naming what is wrong with it - the field at fault and
  what would have been accepted there, or the line and column of a syntax error. Two of these
  catch out generated request bodies: the body must be **exactly one JSON value**, so anything
  after the closing brace (a second object concatenated on, an editing leftover) is rejected
  rather than quietly ignored; and the request must carry `Content-Type: application/json`, since
  a body sent without it is a **415**, not a 400.
- **Omitting `enabled` disables the entity.** It is read as `orElse(false)`, not "leave as is", so
  an update that only changes a property and says nothing about `enabled` comes back disabled and
  undeployed. Always send `enabled: true` explicitly when the entity should stay up. This is the
  opposite of the create default, where omitting it means enabled.
- Otherwise **PUT** replaces and **PATCH** merges. Because PUT replaces, a required property it
  does not resend is not carried over from the existing configuration - the update is rejected
  with `400 Required property '<id>' is not set`. Send the full property set on PUT, or use PATCH
  to change one property and leave the rest alone.

## Lifecycle

`enabled` is the user-facing state; internally each entity has a `DeploymentStatus` of
`undeployed`, `deployed` or `enabled` per location.

**`enabled` defaults to `true` on both `ConnectorCreateRequest` and `TargetCreateRequest`**, so
unless you pass `false`, creation is what deploys - there is no separate enable step to reach for,
and a create can fail on NiFi's terms after the entity exists. Pass `enabled: false` when you want
to stage configuration and deploy deliberately.

In the default **MANAGED** mode:

- create/enable **deploys the flow into NiFi and starts it**, and `enabled` becomes true only
  after NiFi confirms;
- update re-deploys (and is refused outright while enabled - see above);
- disable/delete stops and undeploys.

So enabling is a real operation against NiFi and can fail on NiFi's terms. In **TEMPORARY** mode
there is no persistent deployment and enable/disable only affect database state.

Order of operations: target first, then the connector that references it. A connector referencing
a target that is disabled or in an incompatible state is downgraded to match, so a connector that
will not enable is often a target problem. `GET /v1/targets?connectorId=<id>` lists the targets a
connector depends on, which is the set that has to be enabled before it can be.

`POST /v1/connectors/enable`, `POST /v1/connectors/disable`, `POST /v1/targets/enable` and
`POST /v1/targets/disable` do the same to up to 10 entities at a time, taking `{"ids": [...]}`. Each entity is acted on independently, so the response carries an outcome per id -
either what the single call would have returned, or the status and message it would have failed
with - and the call is 200 even when none of them could be acted on. Read the outcomes; a 200 does
not mean everything moved. A repeated id is refused outright with 400, as is a batch over 10.

That makes the two orderings above a pair of calls each: enable the targets a connector needs then
the connector, and to free a target, disable the connectors the blocker query returns and then the
target itself.

Two further target-side refusals, both 409 and neither covered by the update rule above:

- **A target still referenced by a connector cannot be deleted**, and one referenced by an
  *enabled* connector cannot be disabled. Delete or retarget the connectors first. Both refusals
  name the connector ids that are in the way, and `GET /v1/connectors?targetId=<id>` lists them
  up front - ask before the call if you want to know what a disable or delete would affect.
- **A Pipeline target is read-only**, because it describes a NiFi pipeline this deployment does not
  own. `validate` and `update` are refused as "cannot be validated/updated"; `disable` and `delete`
  are refused as "Cannot modify/remove a readonly target" - different messages, so search for the
  right one. `enable` is the exception: it succeeds trivially, since such a target is already
  enabled.

`GET /v1/connectors/{id}` returns cached `validationErrors`; `GET /v1/connectors/{id}/validate`
re-checks configuration **and connection** now, including the cross-property rules the type
declares - those come back in `validationErrors` (under `constraints`, and `processing:<stepId>`
for a target's steps) rather than as an error status, so read the body, not just the code. Use validate when credentials or reachability are
in question.

## Running work - request bodies

```
POST /v1/connectors/{id}/get/synchronize     # no body
POST /v1/connectors/{id}/get/reset           # no body - clears synchronize state
POST /v1/connectors/{id}/fetch               # {"identifiers": ["<opaque>", ...]}   max 1000
POST /v1/connectors/{id}/delete              # {"identifiers": ["<opaque>", ...]}   max 1000
```

Investigation calls take the same identifiers and cost nothing but a round trip:

```
POST /v1/connectors/{id}/list/identifiers    # {"identifier": "ROOT", "meta": ["sizeBytes"]}
POST /v1/connectors/{id}/view/metadata       # {"identifier": "<opaque>"} - metadata, no content
```

**`reset` is asynchronous like the rest.** It answers `202` with a job token, not a synchronous `200`,
and it occupies the connector's single synchronize slot while it runs: issuing `synchronize`
immediately after a `reset` returns **409**. Poll the reset's own token to a terminal state first.

**`delete` removes documents from the connector's own repository - the source.** Verified: after a
delete the source directory was empty and the destination untouched. It is not a way to clean up a
destination unless the connector you call it on is the one attached to that destination.

A connector must be enabled to run anything: `synchronize` on a disabled connector is
**409 `Connector is not enabled`**, which is a state error rather than the concurrency 409 described
below.

Identifiers are the opaque values from a list-identifiers response, passed back verbatim.
`synchronize` takes no options - what it covers is decided by the connector's properties, not by
the request.

Create and detail responses carry the entity's `id` (a UUID), which is what every subsequent path
uses. Job submissions return `{"token": "..."}` rather than an id.

## Jobs

Asynchronous operations return `202` with `{ "token": "..." }`. Status is one of `scheduled`,
`running`, `finished`, `failed`.

**`finished` does not mean everything succeeded.** On the NiFi runner a cancelled job reports
`finished` by design - as do connector runs stopped by a document-count or time limit - because
what was committed stands and the next run resumes. `failed` is reserved for being unable to do
the work at all, such as a repository connection failure. Other runners may classify differently:
a Cloud Run execution reporting failed tasks comes back `failed` even if it was cancelled. Either
way, the status alone never says whether documents were lost. The job's `documentsFailed` and
`documentsErrored` counts do - they are summed from the connector's own `finished` reports, so they
answer "did anything go missing" without reading the reports themselves. Per-document detail
(which document, and why) is still only in the reports.

Concurrency limits, per connector and operation:

- `synchronize`: one at a time. Exceeding it is **409**.
- `fetch`: up to `connectors.jobrunner.fetch.maxparallel` (default 1). Exceeding it is **429**
  with `Retry-After` - a throttle, so retry rather than reconfigure.
- `delete`: the same arrangement under its own cap, `connectors.jobrunner.delete.maxparallel`.

The distinction matters when driving a batch: a 409 means stop and wait for the run in progress, a
429 means back off and retry the same request.

`DELETE /v1/connectors/{id}/jobs/{token}` requests cancellation: best-effort and asynchronous, so
poll for the final state. Cancellation stops the work at the next point it asks - what has been
committed stays committed. Fetch and delete jobs cannot be cancelled on the NiFi runner (a batch
may hold documents from several jobs); that returns 409.

## Progress

`GET /v1/connectors/{id}/progress` returns a snapshot per operation; `.../jobs/{token}/progress`
narrows it to one job. Two different measurements sit side by side, and confusing them leads to
wrong conclusions:

- **Operation figures** (`documentsRemaining`, `throughputDocumentsPerSecond`,
  `estimatedSecondsToCompletion`, `path`) describe the **NiFi flow** - documents already emitted
  and queued, and how fast they are draining. Several jobs of the same operation share them.
- **Job figures** (`percentComplete`, `documentsProcessed`/`documentsExpected`,
  `secondsProcessing`, `estimatedSecondsToCompletion`, `stages`) come from the **connector**, which
  is the only thing that knows how much of the source repository remains.

Caveats worth repeating to a user reading these numbers:

- `documentsRemaining` counts FlowFiles, and a processing step may split or merge them, so it is
  not exactly a document count.
- `throughputDocumentsPerSecond` (on the operation, and on a job through the operation figures it
  shares - `JobProgress` declares no such field of its own) is the connector's own reported rate
  over the longest measurement window that fits the elapsed time (60s up to 7 days), falling back
  to NiFi's figure only when the connector reports none - so it is generally steadier than a short
  average. The ~5-minute rolling window, with its climb-then-decay lag, applies to the **per-stage**
  figures in `path`, not to the headline number.
- A null `estimatedSecondsToCompletion` with documents outstanding means an idle or stalled flow -
  no rate to project with.
- `documentsProcessed`/`documentsExpected` are populated **only by the NiFi job runner, and only
  for fetch and delete**, which dispatch a known set. A synchronize discovers its work as it goes,
  so those are null and `percentComplete` comes from the connector, possibly
  `percentCompleteProvisional` while the size is still being established. On a Cloud Run
  deployment they are null for every operation - nulls there are normal, not a stalled job.
- `operations` is empty unless the connector is deployed or enabled - and always in TEMPORARY
  mode, which has no persistent flow to measure.

## Reports

`GET /v1/connectors/{id}/reports` is the per-document record, and the place to find out what
actually happened. Filter with `operation`, `since`, `until`, `errorsOnly`, `messageType`,
`messagePattern` (`*` and `?` wildcards), `offset`, `count`.

Message types: `message` (informational), `starting` (a task began), `finished` (a task completed,
carrying `inputdocs`/`doccount`), `performed` (a requested action completed, carrying its
`actionid`), `scheduled` and `cancelled` (recorded by the service itself).

**`messageType` is absent from a report whose type is `message`, not returned as `"message"`.** The
service classifies every report on arrival and defaults anything it does not recognise to `message`,
then omits the field when serialising that default. Most error reports fall in this class, so a report
can arrive as just `timestamp`, `operation`, `isError` and `message` - read a missing `messageType` as
`message` rather than as missing data, and do not index into it blindly. It is still stored and
therefore still filterable: `messageType=message` works as a query filter even though no response ever
shows that value.

`doccount` is a map of tallies, not a single number - a completed FileSystem synchronize reports
`{"seen": "3", "added": "3", "ingestadded": "3"}` (values are strings). Which keys appear depends on
the connector and the operation, so read the map rather than expecting a fixed set.

A synchronize is **incremental** after the first run, and the tallies say how: a second run over a
three-document source where one document had changed reported
`{"seen": "3", "unchanged": "2", "added": "1", "deleted": "1", "ingestadded": "1", "ingestdeleted": "1"}`
- a modified document is counted as a **delete plus an add**, not as an update, and untouched documents
appear as `unchanged`. `errors` and `ingestfailed` appear when documents fail on the way in. So
`seen` staying constant while `added` drops is incremental behaviour working, not work going missing.

**All of these are counted on the connector side, before the target's processing graph runs.** A step
that routes documents to `@drop` (or `@error`) does not reduce them, and produces no report of its
own: a run of three documents whose graph drops one still reports `seen: 3, added: 3,
ingestadded: 3`, with nothing in `errorsOnly=true`. So the counts tell you what the connector sent,
never what the destination holds. When a graph can discard documents, the only way to know what
landed is to list the destination - and a shortfall against `ingestadded` is the graph working as
configured, not a fault to chase.

After a run: the job's own counts first (`documentsFailed`, `documentsErrored` - non-zero means
documents are missing), then `errorsOnly=true` for which documents and why, then the `finished`
reports for the fuller tallies. A job that completed with zero documents is a successful job that
migrated nothing - check the counts, do not assume.

One limit on the job counts, worth knowing before relying on them: they are summed from the
connector's reports at the moment you ask, and reports are purged on a retention period - so an old
job reports zeros rather than history, while its status survives.

Destination failures themselves need no configuration to be counted. A connector target's ingest
flow always records the outcome of every document, success or failure, using the target's own
database service - so a refused write reaches the connector, and the count, by construction. That
does assume the deployment's database is the shared, persistent one; a per-container in-memory or
file database would not be visible to whatever reads it back.

## Verifying at the destination

Confirm arrival at the destination rather than inferring it from a finished job:

1. `POST /v1/connectors/{destination}/list/identifiers` at the location documents should have
   landed in.
2. `POST .../identifiers/metadata-schema` on one of them, and compare against the agreed mapping.
3. `POST .../view` on one to confirm the content survived processing intact.

Verifying needs a connector on the destination repository, which is a separate entity from the
target that wrote there. A connector created only to look at or clean up a repository needs no
`target` entry at all - that is required only for operations that ingest.

### What actually lands there

**Every path belongs to the deployment, not to you.** A connector and a target both run inside the
deployment's NiFi, so any path a property takes - a source directory, a target's write location - is
a path on *that* host or container, and is resolved there. `/data/migration-out` in a target means
`/data/migration-out` as NiFi sees it, which is why a destination is usually a mounted volume rather
than somewhere on the machine making the API calls. Say which host you mean when agreeing a location
with a user, and expect to look inside the container (or at its mount) to see what landed.

For the **bundled NiFi** of a Helm deployment that path is `/opt/nifi/nifi-current/data` - the mount
point of the chart's `nifi.dataVolume` PVC, and the only writable location that survives a pod
replacement. A path elsewhere in that container is on the pod's ephemeral layer and is lost on the
next restart, so put both a filesystem source and a filesystem destination under it. This is
separate from the `file`-typed property trap below, which is about *how* a path is sent.

A migration is an ingest, not a file copy, and a connector-type target does not reproduce the
source tree. Expect, in the general case:

- **Only additions, so the destination accumulates.** Documents are written and rewritten; nothing
  is ever removed. A document deleted at the source after a first sync stays at the destination
  through every later one, and a second sync of a source that has had deletions leaves the two
  sides further apart rather than closer. Count the destination against what the source *has
  sent*, not against what it holds now, or a correct migration will read as one that over-delivered.

- **A location the target chooses, not the source's.** The FileSystem target writes under
  `<migration:rootDirectory>/<tenantId>/<subscriptionId>/<connectorId>/`, whatever else you
  configure - the prefix described under *Creating a target* is not optional. `migration:rootDirectory`
  there is a **literal property id**, sent like any other (`{"id": "migration:rootDirectory", "value":
  "/data/migration-out"}`): some ids are section-qualified with a colon, so take them exactly as the
  type listing gives them and do not treat the prefix as prose.
- **Names decided by `namingStrategy`, which defaults to `uuid`, not `original`.** Under `uuid`
  documents arrive as opaque generated names derived from the source identifier, so the name is stable
  across runs and repeated ingests of the same document were observed not to duplicate - but you
  cannot find a document by its original name. Under `original` the name *and the source's full absolute path* are recreated
  beneath the prefix - a file at `/data/migration/source/policy.txt` lands at
  `<prefix>/data/migration/source/policy.txt`, so destination trees are deep and a listing needs
  many levels of descent to reach the documents.
- **Metadata alongside the content, not inside it - under the default `insertMode: parts`.** Under
  `insertMode: document` none of the companions described here exist: one object arrives per source
  document, and on a FileSystem destination the metadata is used for file timestamps and then
  discarded. The rest of this bullet describes `parts`. The FileSystem target writes a companion
  `<name>.metadata` XML document per item, holding the source metadata - including
  `AUTN_MIGRATION_URI` (the item's original location) and `AUTN_IDENTIFIER` (its opaque source
  identifier). Those two tie a landed document back to its origin, and under `uuid` they are the
  only place the original name survives. **`AUTN_MIGRATION_URI` is a URI, so it is percent-encoded**
  - a document named `RG restricted` appears in it as `RG%20restricted`, while the file written to
  disk carries the decoded name. Comparing the raw value against source or destination paths
  therefore reports documents missing that arrived perfectly well. Split the URI's path on `/` and
  decode each element before comparing - that is what the insert side itself does to build the
  destination path - or compare against the `name` from list-identifiers, which is already decoded. A
  connector may happen to emit its own decoded path field alongside, but that is its own field, not a
  contract: decode the URI rather than depending on one. They also double the document count at the destination - and
  a step that extracts content adds a further `<name>.text` page, so a graph with extraction lands
  three files per source document, not two.

**`original` collides when two source documents share a name, and loses the losers silently.**
Repositories that identify objects by an internal id often allow duplicate names in one folder. Under
`original` every one of them maps to the same destination path, so the first write wins and the rest
fail. Measured on a folder holding three identically named documents: the run reported
`{"seen": "3", "added": "3", "ingestadded": "3"}` and `finished`, **one** document plus its companion
arrived, and the only trace of the other two was two `Ingest failed: Failed to write file to '<path>'`
entries under `errorsOnly=true`.

So before choosing `original`, ask whether names are unique in the source. If they are not - or you
cannot tell - `uuid` derives the name from the source identifier and cannot collide, at the cost of
the readable layout. Either way, compare the destination count against `added` after a run.

**Re-ingesting a document that is already at the destination can fail outright.** With
`namingStrategy: original`, a `reset` followed by a fresh synchronize into a destination that still
held the previous run's files failed **every** document with
`Ingest failed: Failed to write file to '<destination path>'`, reported as
`{"seen": "3", "added": "3", "ingestfailed": "3", "errors": "1"}` plus an aggregate
`INGESTION: Failed 3 documents` carrying the references. The connector side counted the run a success
(`added: 3`) - only the error reports and `ingestfailed` reveal that nothing landed. So **clear the
destination before re-running a migration from scratch**, and always read `errorsOnly=true` after a
reset rather than trusting `added`.

So a destination listing showing twice as many documents as you migrated - and, under the default
strategy, none of the names you recognise - is the expected shape rather than a fault. Say so before
the user sees it, and set `namingStrategy` deliberately: "where are my filenames?" is otherwise the
first question you will be asked. `insertMode: document` removes the doubling but not the naming
problem, and on a destination that stores no metadata it removes the companion that held the
original name - so it makes `namingStrategy` matter more, not less.

Other target types arrange things their own way. Check the destination with `insertable-objects`
rather than assuming this layout, and remember that under `parts` `list/identifiers` counts the
metadata companions as documents in their own right.
