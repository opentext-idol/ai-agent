---
name: ncm-migrate
description: Drive the IDOL Connector Management REST API to investigate a source repository's structure and metadata, work out how documents can be inserted into a destination repository, and configure the connectors, targets and processing steps that move data between them - then run, monitor and verify the migration. Use when asked to migrate or ingest content between repositories, to explore what a connector can see, or to build/operate an NCM pipeline through the API.
---

# Migrating content with the Connector Management API

This skill turns "move this content from repository A to repository B" into a configured,
running NCM pipeline. It needs a running NCM deployment to talk to; if the user has not got one,
offer to stand one up with the `ncm-deploy` skill rather than treating its absence as a blocker.

The essential shape, and the thing to understand before anything else:

```
source connector (get)  ->  target  ->  processing graph  ->  destination
```

**A target's type may be a connector type.** A connector whose definition supports the `put`
operation is offered as a target type, configured with that connector's `put` properties - unless
the deployment restricts which ones may act as targets (`CONNECTOR_TARGET_TYPES`), which is
unset by default. So
repository-to-repository migration is: a source connector doing `get`, ingesting into a target
whose type is the destination connector. Targets can equally be IDOL or IDOLGraph - it depends
where the content is going.

**A connector target is write-only, and a migration into one goes one way.** Documents are
written, and a document written again replaces the copy already there when the naming strategy
gives it a stable name (`original`, `originalunique`, `identifierhash`) - that is how a changed
document is updated at the destination. What never happens is removal: when the source connector
reports that a document has been deleted, or changed in place, the destination is left alone and
the document is simply recorded as processed. So a destination accumulates everything the source
has sent over time, which is not the same as what the source holds now. Tell a user that before
they run a second sync expecting the two sides to match, and do not offer a connector target as a
way of keeping two repositories in step - it cannot do it, and nothing in the job counts or the
reports will say so.

**`Pipeline` is a poor choice of destination.** It is listed in `/v1/types/targets` whether or not
any pipeline is configured, and it names an always-running NiFi flow this deployment does not own.
Validate and update are refused on any pipeline target, and the instances that come from deployment
configuration (`TARGET_PIPELINE_*`) are additionally read-only, refusing modify and remove. Treat a
`Pipeline` entry as "this deployment may route into an external flow", not as a destination you
build and verify here.

Work in phases. Each phase's output is what makes the next phase decidable, and skipping the
investigation phases produces a pipeline that deploys cleanly and migrates the wrong fields.

**The phase numbers below are for your own sequencing. Never say them to the user** - "Phase 0" means
nothing to someone who has not read this file. Say what you are doing and why: "I need a few details
before I can look at either repository", not "starting Phase 0".

## Phase 0 - connect

**First establish whether there is a deployment to talk to at all.** Do not assume one exists and ask
only for its address: a user who has just been handed these skills may have nothing running yet. Ask
whether they have an NCM deployment and, if they do not, offer to stand one up with the `ncm-deploy`
skill and continue here afterwards. When you do ask for an address, make "I do not have one yet" one of
the answers rather than something they have to volunteer.

If a deployment is meant to be running, `GET /v1/health/ready` is the cheapest way to confirm you can
reach it before asking anything else - a failure here is worth reporting before collecting credentials
the user might not need to hand over yet.

**Work out how the deployment is configured by asking it, not the user.** Whether authentication is on
and how tenant context is carried are both observable in two calls, so do not offer them as questions:

1. `GET /v1/types/connectors` with **no** token and **no** tenant parameters.
   - **200** - authentication is disabled, and type listings need no tenant context. Note that a
     deployment with authentication off *ignores* a bearer token rather than rejecting it, so a token
     being accepted proves nothing; this call answering 200 is the only reliable signal.
   - **401** - authentication is enabled. Now you do need a token, and tenant context comes from its
     `tid` / `scrid` claims, so **do not ask for tenant ids at all** in this case. The API validates
     tokens but issues none, so the user must supply one; see the roles table, since a token that
     creates connectors happily may still 403 on discovery.
2. `GET /v1/connectors` with no tenant parameters. With authentication off this answers
   **400 `tenantId and subscriptionId are required`** - the API names exactly what it wants. Entity
   operations need that context even though type listings do not.

That leaves genuinely unknowable things to ask for: the base URL, a token if step 1 said 401, the tenant
and subscription ids if it said 200, and credentials for **both** repositories. Ask for those together
rather than stopping three times.

On the ids: nothing enumerates existing tenants, so if the deployment already holds connectors you
cannot discover which tenant they are under - it has to come from the user. For a deployment with
nothing in it yet you can offer to pick some.

**Generate UUIDs for ids you invent - but do not tell a user theirs are wrong.** The contract is
`type: string, maxLength: 40` with no format and no pattern, the examples in the spec are
`tenant-acme` and `subscription-acme-prod`, and `tenantId=migration` is accepted and creates a
working connector - so nothing here is validated. The platform may also legitimately issue
identifiers that are not UUID-shaped, which is why the code treats them as opaque strings. But a
deployment carries these in the JWT's `tid`/`scrid` claims, where they are UUIDs in practice, and an
id you made up outlives the migration in every entity it scopes. Generate a UUID for each rather
than inventing a memorable string - 40 characters leaves little room for anything longer than the 36
a UUID takes - and take whatever the user gives you as-is.

See `reference/api-surface.md` for calling conventions, tenant handling and the full operation list.
Confirm the catalogue is populated before going on: do not proceed until `/v1/types/connectors`,
`/v1/types/targets` and `/v1/types/processing` all answer with content.

Distinguish the two ways that can fail. A **503** means the resource set is still being copied -
wait and retry. A call that simply takes a long time is normal on a cold cache: the first listing
of a category can take the better part of a minute against a remote provider, and is near-instant
afterwards. Use a generous client timeout on these first calls rather than concluding the
deployment is broken.

## Phase 1 - choose the connector types

`GET /v1/types/connectors` lists what this deployment can talk to; `GET /v1/types/targets` lists
where it can write, which includes put-capable connector types. Identify a type for the source and
one for the destination.

**A scoping property may not scope the discovery walk.** Check the property's `operations` before
assuming it applies everywhere: a folder-list property may be declared for `get` only, so setting it
narrows a *synchronize* while `list/identifiers` still returns the whole repository. Do not rely on a
scoping property to keep exploration cheap.

**Do not expect a description to tell you what a type is for.** Connector and target types carry no
type-level description at all - neither listing nor detail has the field - so identification rests on
the `id` and `name` (plus `category` on a connector, `supportedOperations` on a target) and on the
per-property descriptions in the detail, which are detailed. Only **processing** types carry a
one-line `description` saying what the step does, in both the listing and the detail.

These listings are what this deployment is **configured** to serve, not the set of connectors that
exist. Any released connector can be added to the resource provider's type list. So when a
repository is missing, the finding is "this deployment does not currently serve it" and the
question is whether to add it - not that the migration is impossible. Two things constrain the
answer: the type must exist as a release, and its version must match the `idol-nifi-framework`
version baked into the running NiFi image, or it will not license. See the `ncm-deploy` skill; it
is a deployment change, so it is the operator's call and needs a `POST /v1/admin/resources/resync`
or a restart to take effect.

If the destination genuinely cannot be written to - no put-capable type exists for it at all -
say so rather than quietly substituting a different destination.

`GET /v1/types/connectors/{type}` and `GET /v1/types/targets/{type}` return the property schema:
which properties are required (`optional: false` - there is no `required` field), which are
`secure`, their `allowableValues`, `dependsOn` conditions, `valueTemplates` (how OAuth
credentials are supplied), and `constraints` with `propertyGroups`. Read the schema before writing
any configuration - property ids are type-specific and cannot be guessed, and a required property
left out is a 400.

**Read `constraints` before writing a configuration.** They are rules spanning several
properties - mutually exclusive options, one-of-these-is-required, a value that obliges another
property to be set - and they are the only place such a rule is stated. Each carries a `message`
written for whoever is configuring it, so a violation is worth catching before submitting rather
than reading back off a 400.

For **connectors and targets** the server evaluates them, and breaking one is a 400 naming the
constraint and its message. For **processing steps it does not** - those configurations are not
validated at all, so a broken rule there is created quietly and surfaces later as a runtime
failure. See `reference/configuration.md` for the node vocabulary and the traps in reading it.

A type id is a plain name - `FileSystem`, `Documentum`, `Web` - and that is what goes in `"type"`.
What varies between deployments is **which** ids are served, not their form, so read the listing to
confirm a type is there rather than to discover how it is spelled.

## Phase 2 - create exploration connectors

The investigation endpoints operate on a **created connector**, not on a type, because they
actually talk to the repository. So both repositories need a connector entity before anything can
be discovered.

**Give both connectors `get`, `list` and `view`.** The operation each endpoint demands is not the
one its name suggests:

| Endpoint | Requires |
|---|---|
| `list/identifiers` | the `list` operation |
| `view` | the `view` operation - though the check happens later, so a missing one surfaces as an internal error rather than a clean 400 |
| `identifiers/metadata-schema` | the **`get`** operation |
| `identifiers/insertable-objects` | the **`get`** operation |

Without `get`, the two schema endpoints - the ones Phases 3 and 4 depend on - answer **400
`Connector is not configured for GET operations`**. That applies to the destination connector too,
which needs `get` purely to be asked what may be inserted into it.

Because `get` is present, the create request **must** carry an explicit target entry for it. There
is no target yet at this stage, so pass null:

```json
{ "type": "...", "operations": ["get", "list", "view"],
  "target": { "get": null },
  "properties": [ ... ] }
```

Omitting it is rejected with `GET operation requires an explicit target (use null for no target)`.

`null` is not a default or a placeholder that resolves later: an operation with no target discards
every document it produces. That is exactly right while investigating a source, which is what this
connector is for - but it is also why a connector left like this appears to run perfectly and
deliver nothing. Give `get` a real target before anyone expects documents to arrive, and note that
the mapping cannot be changed by an update, so that means creating the connector again.

**A property declared `type: file`** needs care: it may want file *contents* you upload (a
certificate, a key file) or simply a *path on the connector's host* - a folder list, for instance.
Read its description and decide. For a path, pass an ordinary
JSON string - uploading instead silently points the connector at a temporary file. To upload, send
the whole request as `multipart/form-data`: the JSON above in a part named `request`, and each file
in a part whose **name matches the string value** you gave that property. `reference/configuration.md`
has the detail and the failure it produces.

All four endpoints also require the connector to be **enabled** (409 otherwise). Note `enabled`
defaults to `true` on create, so creation itself deploys into NiFi and can fail on NiFi's terms -
a create that returns an error may still have left an entity behind. Then run
`GET /v1/connectors/{id}/validate`, which checks the configuration *and the connection* and is
where bad credentials surface.

## Phase 3 - investigate the source

**Before descending: scope is applied through a connector property in the repository's own path
form, never through the identifiers you are about to walk.** Check the type schema for that property
first (see below) - it decides whether this walk is for understanding only, or whether you also need
a path string from the user. Then walk the repository and learn its metadata. This is the half of
the job that decides everything downstream; `reference/discovery.md` covers it in full, including the identifier walk from `ROOT`,
reading a metadata schema, and fetching a document's actual content to check assumptions.

Come out of this phase with: which part of the repository is in scope, what a document there
looks like, and the concrete metadata field names, types and cardinalities.

Look in `GET /v1/types/connectors/{type}` for a start-path, root-folder or include/exclude
property - the id and syntax are type-specific and cannot be guessed, and such a property takes the
repository's own path form rather than the opaque identifier you discovered. If the type offers
none, a synchronize covers everything the credentials can see, and the only way to migrate a subset
is `fetch` with an explicit identifier list. Establish which of those you are in before Phase 6:
it decides whether the migration is a synchronize at all.

If it is fetch-only and the subtree exceeds the 1000-identifier cap, the migration becomes a
sequence of fetches - walk the tree, batch the identifiers, and submit batches in turn, respecting
the fetch parallelism cap (429 means back off and retry the same batch). Say up front that this is
the shape, and get agreement: it is materially slower than a synchronize and there is no single job
to watch.

**Read the defaults that gate *ingestion*, not just those that gate discovery.** A property can
leave a document crawled but never ingested, which looks like a successful run with a short document
count rather than like an error. Measured on a Web source: `MaxLinksPerPage` defaults to 100, so
every link beyond the hundredth on a page is silently not ingested. Scan the type's property
descriptions for per-item and per-page limits, not only for the scoping properties, and state the
ones you are relying on.

## Phase 4 - investigate the destination

The mirror of Phase 3, but the question is different: not "what is there" but "what may be
created here, and how". `POST /v1/connectors/{id}/identifiers/insertable-objects` answers it -
for a location in the destination it returns each insertable object type, a reference template
and property templates (literal segments plus named placeholders you must supply), and often a
metadata schema for the new object.

**This phase only exists when the destination is a connector.** `insertable-objects` is a connector
endpoint, so an IDOL, IDOLGraph or Pipeline destination has no equivalent - there is no entity to
ask. For those, the destination's own statement of what it accepts is the target type's
`dynamicProperties` from `GET /v1/types/targets/{type}` (Phase 1), and **if it declares none there
is no field mapping to be had**: whatever metadata the connector emits is what gets written. Say
that plainly rather than implying a mapping you cannot configure. Skip to Phase 5 with that in
hand, and note you will not be able to verify arrival through this API (see Phase 8).

For a connector destination, read on.

**This is informational - no payload takes a template.** Nothing in the configuration accepts an
insertable-object definition; it is the destination telling you what it will accept and how it
forms identifiers. Use it to answer three questions, then move on:

- can the object type you need be created at this location at all?
- what metadata will the destination accept (`metaSchema`) - the other half of the Phase 5 mapping?
- what does a resulting identifier look like, so you can recognise your documents afterwards?

**The write location itself is a target property**, not a template: look in
`GET /v1/types/targets/{type}` for a bucket, path or prefix property and set it in the target's
`properties`. If you cannot find one, say so rather than assuming the template governs placement.

`reference/discovery.md` has the detail.

## Phase 5 - map the metadata

Now put the two schemas side by side and decide, field by field, what becomes what. Points that
decide the design:

- **Names rarely match.** Check `aliases` on each `MetaField` before concluding a field is absent.
- **Cardinality and type must be compatible.** A `multivalued` source field into a single-valued
  destination field needs a rule, not a hope. `required` destination fields with no source
  equivalent need a default.
- **Content transformation is a processing step, not a mapping.** Text extraction, filtering,
  language detection, sectioning, hashing and format conversion are configured as steps in the
  target's processing graph.
- **Say what is unmapped, and check before calling it lost - the answer depends on the target's
  `insertMode`.** A field with no counterpart in the destination's insert `metaSchema` is not
  mapped into the destination's own attributes. Under the default `insertMode: parts` a
  connector-type target also writes a companion metadata document holding what the connector
  emitted, so the field is usually still there beside the document: report it as "carried
  alongside, not queryable as destination metadata" rather than as data loss, and confirm by
  migrating one document and reading the companion. Under `insertMode: document` there is no
  companion, so an unmapped field really is dropped. Establish which mode the target will use
  before describing the outcome; genuine loss does happen, and asserting it means having looked.
- **Fields the processing graph adds have no schema at all.** Neither endpoint reports them, and
  neither reports the extra fields a connector emits beyond its declared schema. The only way to
  learn their names is to run one document through the intended graph into a `parts`-mode scratch
  target and read the `.metadata` companion that lands - see `reference/metadata-mapping.md`. Do
  that before writing a mapping, not after it disappoints someone.

**Where the mapping is expressed:** in the **declared properties** of whichever component does the
work - most often a processing step, sometimes the target. There is no separate mapping field in any
payload. Read the property lists and look for properties that *name fields*: `DetectContentLanguage`
declares `OutputField` (name the field the result lands in), while `Eduction` declares the
multi-valued pair `Entity` / `EntityField`, paired by position. Dynamic properties are usually
**not** the mapping - they are per-type configuration passthrough, and most types declare none.
`reference/configuration.md` has both shapes and the traps.

An unknown property name is rejected with `400 Property '<id>' not found on processing type '<type>'`,
so a mistyped mapping fails the create loudly rather than passing silently - **except on a type
whose dynamic-property family has no prefix**, where any name is accepted as configuration and a
typo returns `201` having set nothing. The scripting types are the case that matters; check ids
against `GET /v1/types/processing/{type}` there.

Check what the chosen components actually declare before promising a mapping. If nothing in the
pipeline names a field, the connector's own metadata output is what gets written - which changes what
you can offer the user.

Present the mapping before building anything. It is the one part a user must agree with, and it
is far cheaper to correct here than after a run.

**For a connector-type destination, how much mapping is needed is decided by the target's
`insertMode` - so decide that first.** Under the default `parts` the target writes a companion
metadata document carrying every field the connector emitted, verbatim, whatever the insert
`metaSchema` declares: "map the metadata across" is already satisfied, and the useful answer to the
user is *where* their fields will be (in the companion, not as native destination metadata) rather
than a mapping table. Under `document` the destination keeps only what its `metaSchema` accepts and
there is no companion, so a real mapping is required - and that is the mode to choose when the user
wants their fields queryable at the destination rather than sitting in a file beside it.

**Where a real mapping is needed, `ExecuteDocumentPython` or `ExecuteDocumentLua` as the final
step before `@ingest` is the mechanism.** They rename and set metadata fields directly, which the
declared-property mapping above cannot do for arbitrary names - most connector-type targets declare
no `dynamicProperties` at all. Put the step last so every other step's output is mappable, and
build its field list from a probe run rather than from the schemas. `reference/metadata-mapping.md`
has the probe, the property ids, the script skeletons in both languages, the routing trap these two
types carry, and the fields to leave alone.

Say plainly which of the two situations you are in before Phase 6, because it changes what the
target needs.

## Phase 6 - build the pipeline

In this order, because each references the last:

1. **Create the target** - type is the destination connector type, properties are its `put`
   properties, including the write location. If Phase 5 found a field mapping to express, it goes
   here as dynamic properties or as a processing step; **most connector-type targets declare no
   dynamic properties and need none** - see Phase 5.

   **Set `insertMode` deliberately.** `parts` (the default) writes each document as its content
   plus a `.metadata` companion, and a `.text` companion where the graph extracted text - two or
   three objects per source document, with every field preserved under its source name. `document`
   writes one object and hands the metadata to the destination, which keeps what its insert
   `metaSchema` accepts. Choose `document` when the user wants fields queryable at the destination,
   and pair it with a mapping step (Phase 5); choose `parts` when the destination stores no
   metadata of its own, since `document` would discard it there. Like the two strategies, it cannot
   be changed by an update.

   **Where Phase 5 found a mapping, add the scripting step as the graph's last step, routed to
   `@ingest`.** Its output relationship is one you name yourself, in the step's `RouteTo` property
   (`success` by default) - a type supporting dynamic relationships accepts any name in `routes` -
   and nothing checks that the two agree: omit the route and the create passes while the deploy
   fails NiFi-side validation. See `reference/metadata-mapping.md`.

   **`namingStrategy: "original"` preserves structure, but only where the source supplies a path.**
   It builds the destination path from the document's `AUTN_MIGRATION_URI`. Any document whose
   source supplies no usable path for it - a web crawl, for instance, where documents are pages
   rather than files - is named from a hash of its identifier instead, exactly as `identifierhash`
   would.
   It is written, and a re-run overwrites it rather than adding a copy, but **its source structure
   is not reproduced** - so a target configured `original` can silently produce a flat tree of
   hash-named objects.

   **Check before choosing it**, on one document, with the call from Phase 3:

   ```
   POST /v1/connectors/{id}/view/metadata     {"identifier": "<opaque>"}
   ```

   If `AUTN_MIGRATION_URI` is absent, neither `original` nor `originalunique` can reproduce the
   hierarchy - set `identifierhash` deliberately rather than leaning on the fallback, so the
   configuration says what it actually does, and record that the source hierarchy is not
   reproducible. Do not infer support from the type: it is a per-connector capability, and the
   field's absence is the whole answer.

   **Where the URI is present, prefer `originalunique` to `original`.** It keeps the source folders
   exactly and puts a short hash before the file extension, so two source documents sharing a name
   cannot silently overwrite one another - the failure `original` has in any repository that
   identifies objects by an internal id rather than by name.

   The default is `uuid`, which generates names and strips the source path, silently flattening a
   migration meant to preserve folders. Every strategy also writes beneath a fixed
   `/<tenantId>/<subscriptionId>/<connectorId>` prefix, so paths are never byte-identical to the
   source - say so before the user discovers it.

   **On an IDOL, IDOLGraph or Pipeline target both strategies are accepted and do nothing**, prefix
   included. Do not promise structure preservation there; ask what the destination does with paths.

   `processing` is **optional** - omit it entirely for a straight copy. Where you do want it, the
   graph is a DAG: an `entry` step, and each step routing its output relationships to another step
   or to `@ingest` / `@error` / `@drop`.
2. **Create the migration connector** with the `get` operation targeted at that target, plus
   `fetch` if you need to pull named documents - give it a `target` entry too if those documents
   should be written to the destination rather than just collected.
   **Give it `list` and `view` as well** - operations
   cannot be added later, and without `list` this connector cannot enumerate its own identifiers,
   which a fetch rehearsal and any later re-check both need.

   **Do not set `cronSchedules` if you intend to run the migration yourself.** A connector with a
   schedule for an operation refuses a manual synchronize of it - 409 `Cannot manually synchronize
   a connector with a configured schedule`. Schedule it, or drive it from Phase 7, not both.

   **The Phase 2 exploration connector cannot be reused for this.** An update applies only
   `cronSchedules`, `properties` and `enabled` - it cannot change a connector's target or its
   operations - and is refused outright while the connector is deployed and enabled. Retargeting
   therefore means delete and recreate. Either create the migration connector alongside the
   exploration one, or delete the latter once investigation is finished.
3. **Validate, then confirm it is enabled.** `enabled` defaults to true on create, so the deploy
   into NiFi happens at create time; `enabled` only reads back true once NiFi confirms.

`reference/configuration.md` has the payload shapes, the routing sentinels, the enable/deploy
lifecycle and what each failure mode means.

## Phase 7 - run it

Two ways, and they answer different questions:

- **`POST /v1/connectors/{id}/get/synchronize`** - the real migration. Walks the source and
  ingests everything in scope. Returns a job token immediately.
- **`POST /v1/connectors/{id}/fetch`** - a named list of up to 1000 identifiers from Phase 3.

`fetch` collects the documents you name and nothing more - it does not insert anything itself. It
reaches a destination only through its own `target` entry, so give it one pointing at the same target
`get` uses if you want it to write there.

**With that in place the two share the whole downstream path.** The ingest flow's
`RouteIngestAction` step routes on `idol.reference.action`, with outputs for `add`, `update` and
`remove`; a collected document carries no action and is routed as `add`, and it carries
`idol.put.migrationuri`, so `namingStrategy: original` resolves to the source path just as it does
for a synchronize. Processing, mapping, naming and insertion are then the same code either way, which
is what makes a fetch into a put-capable target a usable rehearsal.

**What it cannot rehearse is discovery.** It works from identifiers you already hold, so it says
nothing about whether the connector's scoping property (a folder list, a select statement) selects
the documents you meant, or how many that is. To rehearse that as well, narrow the scoping property
to a handful of documents, run `get/synchronize`, and widen it afterwards.

Whichever you run, **verify the destination rather than trusting the job status** - a job reports
`finished` on the strength of its own reports, which describe what the connector did, not what
arrived.

## Phase 8 - monitor and verify

- `GET /v1/connectors/{id}/jobs/{token}` - the job: status, operation, when it started, and what it
  did. **Read the counts, not just the status.** `documentsFailed` counts documents the destination
  refused and `documentsErrored` counts documents the connector could not process - either above zero
  means documents are missing, and the job still says `finished`. For a fetch or delete,
  `documentsProcessed` against `documentsExpected` shows whether it accounted for everything it
  dispatched.
- `GET /v1/connectors/{id}/jobs/{token}/progress` - progress for the job.
- `GET /v1/connectors/{id}/progress` - live snapshot of the whole connector, per operation and
  per flow stage, with documents remaining and an estimated time to completion.
- `GET /v1/connectors/{id}/reports?errorsOnly=true` - what actually went wrong, per document.

Then verify at the destination rather than trusting a completed job. **This only works when the
destination is a connector** - the three calls below are connector endpoints. For an IDOL,
IDOLGraph or Pipeline destination there is no API-side verification: say so, and ask the user to
check the destination directly (an IDOL query for a migrated title, for instance) before the run is
called done. Do not present a finished job as evidence of arrival.

Where the destination is a connector: list identifiers on the
destination connector where the documents should have landed, and check a document's metadata
against the Phase 5 mapping. A job that finishes having ingested nothing is a successful job.

**The first listing will not show your documents, and that is not a failure.** Every strategy writes
beneath the fixed `/<tenantId>/<subscriptionId>/<connectorId>` prefix, so a listing of the location
you configured shows **one new container** - named for the tenant id - however many documents
arrived. The documents are three descents down, under subscription and connector. Walk the three
levels before concluding anything: a migration of a thousand documents and a migration of none look
identical at the top. Ask for `meta` on the listing that finally reaches the files, so the size check
below costs no extra call.

The job's failure counts are the cheap first check and will catch most losses, but they are not a
substitute for looking: they count what the connector was *told* went wrong. A processing step
routing documents to `@drop` reports nothing, and a destination that accepted a document says nothing
about whether it is the document you wanted.

**Verify sizes, not just presence - and it need not cost a download.** Ask the destination listing
for them: `{"identifier": "...", "meta": ["sizeBytes"]}` returns each item's size in its `meta` map,
so a whole directory can be checked in one call. Compare against the source's own size field,
gathered the same way. Do not settle for names alone - under the default `insertMode: parts`, a
companion `.metadata` document beside a zero-byte content file lists identically to a successful
pair. Under `insertMode: document` there is no companion, so a listing is one item per source
document and the size check is the only signal that anything arrived.

Where a connector does not report `sizeBytes`, fall back to `view` and read its `Content-Length`,
which transfers the document to learn one number: fine for two or three spot-checks, not for a
corpus. `view/metadata` is usually the cheaper middle ground when what you want to confirm
is metadata rather than bytes - though on a connector that cannot skip the retrieval it costs the
same as a `view`: measured at 7s and 146 KB transferred for a single web page. Time one before
relying on it for a sweep.

`reference/configuration.md` covers job states, cancellation and the concurrency limits
(one synchronize at a time per connector AND operation, so get and groups run concurrently; a 409
means one is already running, a 429 means the fetch or delete parallelism cap was hit).

## Phase 9 - tidy up

Investigation leaves entities behind: exploration connectors, targets created to test a
configuration, and whatever the rehearsal wrote at the destination. None of it disappears on its own,
and a connector left enabled keeps a deployed NiFi flow.

- **Delete the exploration connectors and any test targets** once the migration connector is
  configured - `DELETE /v1/connectors/{id}` and `DELETE /v1/targets/{id}`. A target cannot be deleted
  while a connector still references it, so connectors go first.
- **Say what the rehearsal wrote, and where.** Rehearsal documents are real documents at the
  destination; under `uuid` naming a re-run re-uses the same names, but they are still there. Either
  remove them or tell the user they are part of the destination now.
- **Leave the migration connector's state deliberate.** Disabled if it was a one-off; enabled with a
  schedule if it is meant to keep running (see below). Do not leave it enabled by accident - it holds
  a deployed flow and, with a schedule, will run again.

Deleting a connector is not a way to undo an ingest: documents already written to the destination
stay there. `reference/api-surface.md` covers the admin bulk deletes, which are a different and
irreversible thing.

## Keeping a destination up to date

A migration is often a one-off, but the same connector can keep a destination current: `synchronize`
is incremental by default - the connector's datastore tracks what it has seen, so a second run
carries only what changed, including deletions where the source reports them.

To run that automatically, give the connector `cronSchedules` per operation at create time. Two
consequences worth stating to the user before doing so:

- **A scheduled operation cannot also be run by hand** - a manual synchronize of a scheduled
  operation is refused with 409. Schedule it or drive it, not both.
- **`cronSchedules` is one of the three things an update can change**, so a schedule can be added or
  removed later without recreating the connector - unlike its target or operations.

Only offer this where the user wants ongoing replication rather than a migration. A schedule left on
a connector created for a one-off run is how a repository quietly gets re-crawled next week.

## Things that will bite

- **Discovery needs a live connection.** Every identifier/metadata/view call reaches the
  repository. A 409 usually means the connector is not enabled or not deployed.
- **Identifiers are opaque.** Pass back exactly what was returned; never construct one by string
  manipulation. The one reserved value is `ROOT`.
  Opaque does **not** mean connector-scoped: an identifier gathered by one connector is usable by
  another of the same type against the same repository, and by any operation. The section name
  visible inside it is replaced on use, so it constrains nothing - do not re-walk a tree just
  because a different connector will do the work.
- **Secure properties are write-only.** They come back redacted, so a round-trip of GET then PUT
  will blank them unless they are re-supplied.
- **A deployed, enabled entity cannot be updated at all** - connector or target, PUT or PATCH, 409
  `cannot be updated while enabled`. Disable, update, re-enable; and since disable tears the flow
  down, do it when nothing is running.
- **An update that omits `enabled` disables the entity.** Send `enabled: true` explicitly to keep
  it up - the opposite of create, where omitting it means enabled.
- **An update applies `name`; omitting it keeps the existing one.** To clear synchronize state,
  call `reset` - an update cannot do it, and no longer accepts a `clearState` field.
- **Cross-property constraints are enforced for connectors and targets, but not for processing
  steps.** A connector or target configuration that breaks one is a 400 quoting the rule. A
  processing step's is not validated at all, so it is created quietly and fails at run time
  without mentioning the rule - check those yourself.
- **A field the request schema does not declare is rejected with 400**, naming the field and what
  is permitted. Server-generated metadata (`id`, `createdAt`, `deploymentStatus`, `_links` and the
  like) is the exception: it is accepted and ignored, so a fetched object can be edited and sent
  back.
- **Target and operations are fixed at create time.** No update request can change them. Getting
  either wrong means delete and recreate.
- **A scheduled connector refuses a manual synchronize** of the scheduled operation (409).
- **PUT replaces, PATCH merges.** Only PUT accepts a replacement `processing` graph; sending one
  to PATCH is rejected with 400 rather than dropped.
- **Disable is a fast teardown, not a pause.** It undeploys and stops whatever is running. A job
  in flight is written off, not resumed.
- **Deleting a connector does not delete what it ingested.** Nothing at the destination is
  reversed by removing the pipeline.
- **A migration is a write to someone's repository.** Confirm scope and destination before the
  first run that is not a rehearsal, and be explicit about what will be created.

## Reference

| File | Contents |
|---|---|
| `reference/api-surface.md` | Calling conventions, tenant context, and every operation grouped by purpose |
| `reference/discovery.md` | Walking a repository, metadata schemas, insertable objects, viewing content |
| `reference/configuration.md` | Connector/target/processing payload shapes, lifecycle, jobs, progress, reports |
| `reference/metadata-mapping.md` | Mapping source fields onto destination properties: schemas, the probe for graph-added fields, the scripting steps |
