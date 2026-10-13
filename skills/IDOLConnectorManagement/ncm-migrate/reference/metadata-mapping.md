# Mapping metadata onto the destination

How to get a source document's fields into the destination repository's **own** properties, rather
than into a companion file beside the document.

This is Phase 5's mechanism. Read it once you know the destination is a connector and the user
wants their fields queryable at the destination.

## When you need this

| `insertMode` on the target | What happens to metadata | Mapping needed? |
|---|---|---|
| `parts` (default) | written verbatim as a `<name>.metadata` XML companion beside the content | rarely - every field is already there, under its source name |
| `document` | handed to the destination with the content; the destination stores what its insert schema accepts and **discards the rest** | yes, if the names differ - and they almost always do |

So the decision to map is downstream of the decision in `configuration.md` §`insertMode`. Under
`parts` a mapping is a convenience; under `document` an unmapped field is a dropped field.

A mapping step is harmless under `parts` - the companion simply carries the mapped names - so
building the graph once and switching modes later is safe in that direction. Switching modes needs
a new target either way: `insertMode` cannot be changed by an update.

## The three sets of field names

A mapping needs both sides named. Two sides have a schema endpoint; the third does not.

**1. What the source emits.**

```
POST /v1/connectors/{sourceConnectorId}/identifiers/metadata-schema
{ "identifier": "<a specific source document>" }
```

Returns `fields`, each with `name`, `type`, `attributes` and `aliases`. See `discovery.md` - and
heed its warning that this **understates** what documents actually carry.

**2. What the destination will accept.**

```
POST /v1/connectors/{destinationConnectorId}/identifiers/insertable-objects
{ "identifier": "<the location documents will land in>" }
```

Each definition's `metaSchema` is the destination's own statement of the metadata a new object
accepts, in the same shape as a source schema - which is what makes the two directly comparable.
Ask at the specific location, not at a parent: different locations offer different definitions.

**An empty or absent `metaSchema` is the answer, not a missing answer.** It means the destination
stores no metadata of its own, so `document` mode would discard all of it and there is nothing to
map to. Recommend `parts` there and say why.

**3. What the processing graph adds. There is no schema for these.**

Fields written by steps in the graph - `DetectContentLanguage`'s `OutputField`, `Eduction`'s
`EntityField` entries, `HashDocument`'s output, anything a `document` mode mapping should also
carry - exist only once the graph has run. No endpoint reports them, and no endpoint reports the
extra fields a connector emits beyond its declared schema either.

Determine them by running one document, not by reasoning about the types:

1. Build the graph you actually intend, on a **scratch target with `insertMode: parts`**, pointed
   at a throwaway destination location.
2. Fetch or synchronize **one** document into it.
3. Read the `<name>.metadata` companion that lands. That XML is the complete, authoritative list of
   element names as they exist at the moment of insert - source fields, framework fields and every
   field the graph added, under the exact names the mapping script will see.
4. Write the mapping from that list, then create the real target with `insertMode: document` and
   the mapping step appended.

The probe is worth its cost. A mapping written from the two schemas alone will miss the
graph-added fields entirely, and will usually get some source field names wrong as well.

**Read the companion for structure, not just for names.** Step 3 above is not a list of strings -
it is a tree, and both ends of a mapping are routinely nested. Neither is an edge case, and the flat
`{source: destination}` skeleton further down handles neither.

## Neither end is necessarily flat

**A nested source field is invisible to a flat scan.** `getChildren()` returns only the top level, so
a field one level down is never seen and the mapping silently sets nothing - the step still routes
`success`. Measured on a Web source: `identifiers/metadata-schema` declared fifteen fields and no
title at all, while the page title arrived as `PAGE_METADATA/DRETITLE`, inside an `open` object
field. Reach it by XPath:

```python
values = meta.getValuesByXPath("PAGE_METADATA/DRETITLE")   # list; empty when absent
title = values[0].strip() if values else ""
```

An `open` or `object` field in the source schema (`discovery.md`) is the signal to expect this
before the probe confirms it.

**A destination `metaSchema` may describe a structure rather than a set of names.** Where it does,
the mapping *builds an element* - there is no name to rename to, and a flat `MAPPING` dict cannot
express it. Read the `metaSchema` shape before writing the script. Measured on a SharePoint document
library, `insertable-objects` returned:

```
CONTENTTYPEID  string
FIELD          object, multivalued
  NAME         string, required     <- the destination column's internal name
  TITLE        string               <- its display name, not a value
  VALUE        string               <- what you are setting
  EDITVALUE    string
  FIELDTYPE    object { KIND, NAME }
  REQUIRED     boolean
```

So setting one column means adding a `FIELD` element carrying `NAME` and `VALUE`, not writing a
`Title` element:

```python
field = meta["FIELD"]          # dict-style access gets or creates
field["NAME"]      = "Title"   # the column's internal name
field["VALUE"]     = title
field["EDITVALUE"] = title
```

Two things to get right here. **`NAME` is the column's *internal* name**, which is not its display
name - confirm it by reading `view/metadata` on a document already at the destination and matching
`FIELD/NAME` against `FIELD/TITLE`, rather than guessing from what the UI shows. And **`meta["X"]`
returns the first `X` or creates one**, so it writes a second column only where the document carries
no `FIELD` elements already; where the source emits its own, collect and append instead.

A destination of this shape also changes what "unmapped" means: every source field is unmapped
until you emit a `FIELD` for it, and a `FIELD` naming a column the library does not have is accepted
and stored nowhere. Verify against the destination, as below.

## Where the mapping step goes

**Last, immediately before `@ingest`.** Every other step's output has to be mappable, and a step
that runs after the mapping can add fields the mapping never saw.

```json
"processing": {
  "entry": "extract",
  "steps": [
    { "id": "extract",  "type": "KeyViewFilterDocument",
      "properties": [ { "id": "ExtractContentText", "value": "true" } ],
      "routes": { "success": "language", "failure": "@error" } },
    { "id": "language", "type": "DetectContentLanguage",
      "properties": [ { "id": "OutputField", "value": "DETECTED_LANGUAGE" } ],
      "routes": { "success": "map", "failure": "@error" } },
    { "id": "map",      "type": "ExecuteDocumentPython",
      "properties": [ { "id": "PythonScriptFile", "value": "<the script>" } ],
      "routes": { "success": "@ingest", "failure": "@error" } }
  ]
}
```

The three steps do not all mean the same thing by `success`. `KeyViewFilterDocument` and
`DetectContentLanguage` declare `success` and `failure` as relationships of their own; the
scripting step declares only `failure`, and its `success` is simply the default value of its
`RouteTo` property - a name you may change. See *Naming the relationship* below.

Nothing between `@ingest` and the destination renames anything: the target's own ingest path sets
the write location, merges paged content and strips subfile parts, and then inserts. So the
document the mapping step emits is the document the destination receives.

## Configuring the step

Both scripting types take the script **as a property value** - the property is documented as
"filename or body", and a body is what you want here, since a filename would have to exist on the
NiFi host.

**A processing type's API properties are not the same list as its NiFi processor's properties.**
The type's own definition decides what the API exposes, and controller-service properties are
lifted out of it. Take the ids from `GET /v1/types/processing/{type}` rather than from a NiFi
screen or the processor's documentation. For these two the API-configurable set is:

`ExecuteDocumentPython`:

| Property id | Notes |
|---|---|
| `PythonScriptFile` | required; the script body |
| `PythonScriptFunction` | defaults to `handler` |
| `RouteTo` | defaults to `success` - names the relationship the input document leaves by |
| `RouteReturnedTo`, `RouteUntransferredTo` | leave unset for a mapping step |
| `AdditionalOutputRelationships` | comma-separated; only if the script transfers to relationships of its own |

`ExecuteDocumentLua` is the same shape with `LuaScriptFile` / `LuaScriptFunction`, plus:

| Property id | Notes |
|---|---|
| `LuaScriptFunctionArguments` | `LuaDocument`, `LuaFlowFileDocument,LuaProcessorSession` (the default) or `LuaFlowFile`. Get it wrong and every document goes to `failure`. |
| `EnableDebugger` | `true`/`false`; irrelevant to a mapping step |

**The license and document-registry controller services are not in that list and must not be set.**
They are controller-service properties, so the type detail does not report them and the deployment
supplies them - resolving an existing instance, or creating one at deploy where the deployment is
configured to. Where neither is possible the create fails with
`Unsatisfied controller service: <type>`, which is an operator matter (see `configuration.md`), not
a property to fill in.

Both types also accept user-named dynamic properties, which is how a script reads configuration
instead of hard-coding it: any name you choose becomes readable inside the script, and the prefixes
`py:` / `lua:` declare additional script modules. Dynamic property values are never tokenised, so
no credentials in them.

**On these two types a mistyped property id is not rejected.** Their dynamic-property family has no
prefix, so *any* name is accepted - `PythonScriptFil` is taken as a script configuration option and
the create returns `201` with no script set. The loud `400 Property '<id>' not found` that
`configuration.md` describes protects the types that declare no catch-all family, and these are not
among them. Check the ids against the type detail before sending, and check the step actually did
something afterwards.

### Naming the relationship

**Where a type supports dynamic relationships, `routes` accepts any relationship name you like** -
it is not restricted to the names in `relationships`. These two types declare only `failure`; every
other relationship they have is one you named yourself, in `RouteTo` or in
`AdditionalOutputRelationships`. So the name in the property and the key in `routes` are the same
string, and you choose it:

```json
{ "id": "map", "type": "ExecuteDocumentPython",
  "properties": [
    { "id": "PythonScriptFile", "value": "<the script>" },
    { "id": "RouteTo", "value": "mapped" },
    { "id": "AdditionalOutputRelationships", "value": "skipped" }
  ],
  "routes": { "mapped": "@ingest", "skipped": "@drop", "failure": "@error" } }
```

That freedom is the useful part: a mapping script can `session.transfer(...)` a document it cannot
map to a relationship of its own, and the graph sends that relationship to `@drop` or `@error`
independently of the documents that mapped cleanly.

The corollary is that **nothing checks these names for you**. NCM's "every emitted relationship
must be routed" rule covers the declared, non-optional ones, so a step whose `routes` omit the name in `RouteTo`
passes validation; the processor then creates that relationship at runtime with nothing connected
to it, and the target comes back `201` with `enabled: false` and the reason in `validationErrors`.
Route every name you named. A non-empty `dynamicRelationships` on
`GET /v1/types/processing/{type}` is the signal that a type works this way.

### Before you commit to a scripting step

- **Check the type is offered**: `GET /v1/types/processing`. A deployment can restrict which
  processing types it serves, and these two are plausible things to withhold.
- **They are NiFi restricted components** - they execute arbitrary code. If the deployment's NiFi
  identity lacks that permission the target create fails rather than the step misbehaving. That is
  an operator matter, not something the payload can fix.
- **Content-dependent mappings need the content extracted first**, exactly as `configuration.md`
  warns for `DetectContentLanguage`: a script reading page text of a document whose file was never
  extracted sees nothing, silently.

## Writing the script

The handler receives the document, edits its XML metadata in place, and returns nothing - the
document routes on by `RouteTo`.

**Both skeletons below map flat name to flat name, which is the simple case and not the common one.**
Where the source field is nested, or the destination takes a structure rather than a name, keep the
skeleton's shape - the `updatingAttributes` block, the snapshot before editing, the deletes after
every write - and replace the lookups per *Neither end is necessarily flat* above.

### Python

```python
#@ PythonScriptFunction=handler

from idolnifi import logInfo

# Destination field <- source field. Built from the probe above, not from the schema alone.
MAPPING = {
    "AUTN_MIGRATION_URI": "sourcePath",
    "DETECTED_LANGUAGE":  "language",
    "title":              "displayName",
}

KEEP = {"AUTN_IDENTIFIER"}

def handler(doc):
    with doc.updatingAttributes() as action:
        meta = action.getXmlMetadata()

        # Snapshot every element name that actually arrived, before changing anything.
        present = {child.getName(): child.getValue() for child in meta.getChildren()}
        destinations = set(MAPPING.values())

        for source, destination in MAPPING.items():
            if source in present:
                meta[destination] = present[source]

        # Drop the old names only after every write, and never one that is also a
        # destination - otherwise a chained rename deletes what it has just written.
        for source in MAPPING:
            if source in present and source not in destinations and source not in KEEP:
                del meta[source]

        unmapped = sorted(set(present) - set(MAPPING) - KEEP)
        if unmapped:
            logInfo("Unmapped fields on %s: %s" % (doc.getReference(), ", ".join(unmapped)))
```

`XmlElement` supports dict-style access: `meta["Name"]` gets **or creates** a child (so it is not a
membership test - use `getChildren()` or `getFirstChild()` for that), `meta["Name"] = value` sets a
child's text, `del meta["Name"]` removes every child of that name, and `meta["@attr"]` reads an XML
attribute. `getChildren()` returns a list; the element is iterable too. `getElementsByXPath` and
`getValuesByXPath` handle nested structures - a repeated or structured field such as an Eduction
match is an element with children, not a string, so map those by moving the element rather than by
reading a value.

Logging the unmapped set on the first run turns the processor log into a second, cheaper version of
the probe - useful when the destination has already been cleared.

### Lua

```lua
--@ LuaScriptFunctionArguments=LuaFlowFileDocument,LuaProcessorSession

local MAPPING = {
    AUTN_MIGRATION_URI = "sourcePath",
    DETECTED_LANGUAGE  = "language",
    title              = "displayName",
}

function handler(ffdocument, session)
    ffdocument:updateAttributes(function(action)
        local meta = action:getXmlMetadata()

        local present, destinations = {}, {}
        for _, child in ipairs({ meta:getChildren() }) do
            present[child:getName()] = child:getValue()
        end
        for _, destination in pairs(MAPPING) do destinations[destination] = true end

        for source, destination in pairs(MAPPING) do
            if present[source] ~= nil then
                meta:getOrAddChild(destination):setValue(present[source])
            end
        end

        -- Drop the old names only after every write, and never one that is also a
        -- destination - otherwise a chained rename deletes what it has just written.
        for source in pairs(MAPPING) do
            if present[source] ~= nil and not destinations[source]
                and source ~= "AUTN_IDENTIFIER" then
                local existing = meta:getFirstChild(source)
                if existing then existing:remove() end
            end
        end
    end)
end
```

`getChildren()` and `getElementsByXPath()` return **multiple values**, not a table - wrap the call
in braces (`{ meta:getChildren() }`) before iterating, or the loop sees only the first element.
`getFirstChild` returns nil when absent; `getOrAddChild` creates.

Prefer `updateAttributes` (Lua) / `updatingAttributes` (Python) over `modify` for a mapping step:
they permit exactly attribute and metadata edits and reject part writes, so a script that
accidentally touches content fails loudly instead of corrupting the document.

### Fields to leave alone

- **`AUTN_IDENTIFIER`** - the insert reads it to reconstruct the object's identifier properties,
  then removes it itself. Renaming or deleting it changes what the destination records the document
  as being.
- **`AUTN_MIGRATION_URI`** is safe to rename or drop. The write location is decided from a flowfile
  *attribute* that the source connector set before any processing ran, not from this field - so
  removing it does not affect `namingStrategy: original`. It is only the field a *reader* of the
  destination would use to trace a document back to its source, which is a reason to map it
  somewhere rather than to keep its name.

## Confirming it worked

The graph reports nothing about a mapping - a step that mapped nothing still routes `success`. Read
the result at the destination:

```
POST /v1/connectors/{destinationConnectorId}/view/metadata
{ "identifier": "<the landed document>" }
```

Returns the destination's own metadata as XML. Under `document` mode this is the whole answer: the
fields present are the fields the destination kept, and anything from your mapping that is missing
was not in the destination's `metaSchema` after all.

Do this on one document before running a corpus. A mapping that names a destination field the
insert schema does not declare fails silently - the value is simply not stored - and the run
reports `finished` either way.
