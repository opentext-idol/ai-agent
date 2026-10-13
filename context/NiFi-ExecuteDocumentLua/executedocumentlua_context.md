# ExecuteDocumentLua - processor context

This document describes how the `ExecuteDocumentLua` NiFi processor invokes a Lua
script and how the script is expected to interact with the FlowFile pipeline.
It is intended as supporting context for a developer (or AI) writing scripts
against the Lua API surface defined in the accompanying API reference.

---

## Execution model

Each invocation of the processor runs the configured Lua script against a
single input FlowFile.  The script must define a global function called
`handler` (or whatever the `Lua script function` property names).  The
processor calls `handler` once per FlowFile.

The argument types of the `handler` are selected by the processor's
`Lua script function arguments` property.  The allowed values are:

| Property value                          | Handler signature                                          |
|-----------------------------------------|------------------------------------------------------------|
| `LuaDocument` (default)                 | `function handler(document)`                               |
| `LuaFlowFileDocument,LuaProcessorSession` | `function handler(ffdocument, session)`                  |
| `LuaFlowFile`                           | `function handler(flowfile, session)`                      |

```lua
-- LuaDocument form: in-memory IDOL document
function handler(document)
    -- document is a LuaDocument
end

-- LuaFlowFileDocument form: structured FlowFile with parts
function handler(ffdocument, session)
    -- ffdocument is a LuaFlowFileDocument
    -- session is a LuaProcessorSession
end

-- LuaFlowFile form: plain FlowFile surface, no IDOL document structure
function handler(flowfile, session)
    -- flowfile is a LuaFlowFile (opaque byte stream + attributes)
    -- session is a LuaProcessorSession
end
```

Choose based on the shape of the incoming data:

- `LuaDocument` - convenient when the script only needs to read or rewrite
  IDOL fields and content text.  Requires the input to be in
  FlowFileDocument format.
- `LuaFlowFileDocument,LuaProcessorSession` - the most powerful option when
  the input **is** in FlowFileDocument format: streams large embedded files,
  manipulates parts, manages FlowFile attributes and XML metadata, and can
  create/transfer/remove FlowFiles via the session.
- `LuaFlowFile` - use this when the input is **not** in FlowFileDocument
  format (an arbitrary FlowFile, e.g. straight from another processor that
  does not produce IDOL documents).  Using `LuaDocument` or
  `LuaFlowFileDocument` with such an input raises `FlowFileFormatException`
  and the FlowFile goes to the `failure` relationship.

The script file may contain any supporting Lua code (locals, helpers,
`require`s), but `handler` is the only entry point the processor calls.

---

## Script header directives

The processor scans the **leading comment block** of the main script for
directive lines of the form:

```lua
--@ <PropertyName>=<value>
```

Any such directive overrides the corresponding processor property for this
script, both at runtime in the native processor and persisted back into the
processor's stored properties on save.  Use this to make a script
self-describing: a reviewer (or the `ExecuteDocumentLua` processor UI) can
tell from the script itself which argument style, handler name, and routing
it needs.

### Recognised directives

| Directive                             | What it sets                                              |
|---------------------------------------|-----------------------------------------------------------|
| `LuaScriptFunctionArguments`          | Which handler signature is expected.  Accepted values: `LuaDocument`, `LuaFlowFileDocument` or `LuaFlowFileDocument,LuaProcessorSession`, `LuaFlowFile` or `LuaFlowFile,LuaProcessorSession`.  Whitespace around commas is tolerated. |
| `LuaScriptFunction`                   | Handler function name (default `handler`).                |
| `RouteTo`                             | Relationship the input FlowFile is routed to by default.  Empty value = no default routing. |
| `RouteReturnedTo`                     | Relationship FlowFiles returned by the handler are routed to. |
| `RouteUntransferredTo`                | Relationship for any FlowFile the handler created but did not explicitly transfer, return, or remove. |
| `AdditionalOutputRelationships`       | Comma-separated list of extra relationship names the script wants available for `session:transfer(...)`. |

Other `-- ...` comments in the header are ignored by the parser and remain
as plain prose for the reader.  The directive form requires the `@` sigil
on the comment: a bare `-- LuaScriptFunction=handler` is not parsed.

### When a script should declare directives

When generating or authoring a script, include directives for every
configuration option the script depends on, so the processor is set up
correctly without the user having to remember to tick boxes in the UI.
In particular:

- **Always declare `LuaScriptFunctionArguments`** - it decides which
  handler signature the script is written for and which input formats are
  accepted.  Getting this wrong causes a `FlowFileFormatException`.
- **Declare `AdditionalOutputRelationships`** whenever the script calls
  `session:transfer(ff, relName)` with anything other than the already-wired
  relationships.  The relationships named here become available in the
  NiFi graph so the user can connect them downstream.
- **Declare `RouteTo` / `RouteReturnedTo` / `RouteUntransferredTo`** when
  the script is built around a specific routing contract (for example, a
  script that always returns new FlowFiles and expects them routed to
  `split`).
- **Declare `LuaScriptFunction`** only if using a non-default handler
  function name.

### Example

A script that parses the input, emits two categories of derived FlowFiles
on different relationships, and drops the original:

```lua
--@ LuaScriptFunctionArguments=LuaFlowFileDocument,LuaProcessorSession
--@ AdditionalOutputRelationships=text,binary

function handler(ffdocument, session)
    local ref = ffdocument:getReference()
    local textFf = session:create(ref .. ":text")
    local binaryFf = session:create(ref .. ":binary")
    -- ... populate textFf and binaryFf ...
    session:transfer(textFf, "text")
    session:transfer(binaryFf, "binary")
    session:remove(ffdocument)
end
```

Loading this script into the processor automatically sets the argument
style and adds `text` and `binary` as output relationships - no manual UI
configuration required beyond connecting those relationships in the flow.

### Values, empty values, invalid values

- Non-empty value → that value is used.
- Empty value (`--@ RouteTo=`) → explicit clear; the property is treated
  as unset.
- For the free-text properties any string is accepted.
- For `LuaScriptFunctionArguments`, unrecognised values are rejected at
  runtime (log + route to `failure`).

---

## Routing

Two processor properties drive routing:

| Property          | Applies to                              |
|-------------------|-----------------------------------------|
| `RouteTo`         | The input document, by default          |
| `RouteReturnedTo` | Documents returned from `handler`       |

### One-argument (`LuaDocument`) form

- By default the input `document` is routed to the `RouteTo` relationship.
- Any `LuaDocument` values returned from `handler` are routed to
  `RouteReturnedTo`.
- If the input `document` is explicitly returned, it is routed via
  `RouteReturnedTo` instead of `RouteTo`.
- Any new `LuaDocument` values that the handler created but did **not**
  return are discarded.

### Two-argument (`LuaFlowFileDocument`, `LuaProcessorSession`) form

- By default the input `ffdocument` is routed to `RouteTo`.
- `LuaFlowFileDocument` values returned from `handler` are routed to
  `RouteReturnedTo`.
- If the input `ffdocument` is explicitly returned, transferred
  (`session:transfer(...)`), or removed (`session:remove(...)`), the default
  routing to `RouteTo` is skipped.
- Any FlowFile created via `session:create(...)` that is not returned,
  transferred, or removed before `handler` completes causes the script to
  fail.  Every created FlowFile must have a disposition.

---

## LuaDocument vs LuaFlowFileDocument vs LuaFlowFile

- `LuaFlowFileDocument` is the **preferred** interface when the input is in
  IDOL FlowFileDocument format.  It represents a NiFi FlowFile and exposes
  FlowFile attributes, XML metadata, and the FlowFile's *parts* - the
  content text, any embedded files, external file references, and filename
  references.  It can stream large bodies, manipulate part structure, and
  access the full FlowFile surface.

- `LuaDocument` is an older in-memory IDOL document interface: a reference,
  a set of metadata fields, content text, and document sections.  It also
  requires the input to be in FlowFileDocument format.  Supported for
  simple field/content edits; for new work prefer `LuaFlowFileDocument`.
  `ffdocument:modifyDocument(fn)` provides a bridge when a
  `LuaFlowFileDocument` handler wants to apply a `LuaDocument`-style edit.

- `LuaFlowFile` is for inputs that are **not** in FlowFileDocument format -
  arbitrary FlowFiles produced by non-IDOL processors.  Select the
  `LuaFlowFile` value of the `Lua script function arguments` property and
  the handler receives a plain FlowFile surface plus a session.  Attempting
  to use `LuaDocument` or `LuaFlowFileDocument` on such inputs throws
  `FlowFileFormatException` and routes the FlowFile to the `failure`
  relationship.

Conversion is available in both directions for scripts that need it:

```lua
local document = ffdocument:getAsLuaDocument()  -- pull a LuaDocument view
-- edit document ...
ffdocument:setFromLuaDocument(document)         -- push changes back

-- or, more commonly, a scoped transform:
ffdocument:modifyDocument(function(document)
    document:appendContent("Hello world")
    return true  -- returning false causes modifyDocument to return false
end)
```

Changes to a `LuaDocument` obtained via `getAsLuaDocument()` are **not**
live - `setFromLuaDocument` must be called to commit them.

---

## FlowFile parts

A `LuaFlowFileDocument` can contain multiple parts.  Parts come in three
kinds:

| Part kind        | Callback name       | Accessor                       |
|------------------|---------------------|--------------------------------|
| Text content     | `onContent`         | `action:readContent`, `action:transformContent` |
| Embedded file    | `onContentFile`     | `action:readFile`, `action:writeFile`           |
| External file    | `onContentFilename` | `action:getFilename`, `action:transferFilenameToFile` |

Scripts iterate parts via one of three traversal methods on
`LuaFlowFileDocument`, each of which takes a table of callbacks:

- `ffdocument:read({...})` - read-only iteration.
- `ffdocument:modify({...})` - read/write iteration; returned actions can
  rewrite or delete parts in place.
- `ffdocument:append({...})` - iteration intended to append new parts; can
  also rewrite or delete existing parts.

In addition to the `onContent*` callbacks, the table may contain:

- `preAction(action)` / `postAction(action)` - run once before/after the
  per-part callbacks.  Useful for accumulating state or finalising XML
  metadata.
- `defaultFileAction(action)` - fallback for `onContentFile` /
  `onContentFilename` when you want to handle all file-ish parts the
  same way.

All callbacks receive an `action` object that exposes part-specific
methods.  Common ones:

- `action:getXmlMetadata()` - the XML metadata node for the current
  document / part
- `action:getPartId()`, `action:getPartXmlMetadata()` - part identity
  and metadata
- `action:readContent(fn)`, `action:readFile(fn)`, `action:writeFile(fn)`,
  `action:transformContent(fn)` - stream I/O helpers that pass a
  `LuaInputStream` / `LuaOutputStream` to `fn`
- `action:addContent(str)` - append new content text
- `action:deletePart()` - mark the current part for removal (use with
  `ffdocument:compact()` or via `modify`)
- `action:transferFilenameToFile()` - promote an external filename part
  to an embedded file part

A minimal append example:

```lua
function handler(ffdocument, session)
    ffdocument:append(function(action)
        action:addContent("Hello world")
        action:getXmlMetadata():addChild("said_hello"):setValue("true")
    end)
end
```

A read-only traversal that hashes each part:

```lua
function handler(ffdocument, session)
    local hashes = {}
    ffdocument:read({
        onContent = function(action)
            action:readContent(function(inputstream)
                table.insert(hashes, hash_string(inputstream:read("a")))
            end)
        end,
        onContentFile = function(action)
            action:readFile(function(inputstream)
                table.insert(hashes, hash_string(inputstream:read("a")))
            end)
        end,
    })
end
```

---

## FlowFile attributes

`LuaFlowFileDocument` exposes getters and setters for FlowFile attributes:

```lua
local ref       = ffdocument:getReference()         -- idol.reference
local refAction = ffdocument:getReferenceAction()   -- idol.reference.action
local state     = ffdocument:getAttribute("luahandlerstate")

ffdocument:setAttributes({ luahandlerstate = "done" })
```

`getReference` / `getReferenceAction` are convenience accessors for the
well-known `idol.reference` and `idol.reference.action` attributes.  Any
other attribute is reachable via `getAttribute` / `setAttributes`.

---

## Session operations

`LuaProcessorSession` methods let the script step outside the default
single-in / single-out flow:

```lua
-- Create a new FlowFile inheriting from the input
local new_ff = session:create(ref .. ":" .. create_uuid(), "add", ffdocument)

-- Route a FlowFile to a specific relationship
session:transfer(new_ff, "success")

-- Drop a FlowFile from the session
session:remove(ffdocument)

-- Query the graph around this processor
if session:hasConnection("session") then
    if session:relationshipAvailable("session") then
        log_info("ready to transfer to session")
    end
end

log_info(session:getName())  -- the processor name
```

Recall from the routing rules above: every FlowFile that enters the
session (the input, plus anything from `session:create`) must end up
returned, transferred, or removed by the time `handler` exits.

---

## Logging and utilities

Within a handler, the processor exposes the usual Lua globals plus a set
of convenience functions and classes from the IDOL Lua library.  The full
list is in the API reference; the ones used most often are:

- `log_info(msg)`, `log_warn(msg)`, `log_error(msg)`, `log_debug(msg)`
  etc. - log to the NiFi processor log stream
- `create_uuid()` - generate a UUID string, handy when minting references
  for new documents
- `hash_string(s, algo?)`, `hash_file(reader_fn, algo?)` - checksums
- `parse_document_idx(...)`, `parse_document_xml(...)`,
  `parse_document_csv(...)` - parse a file or string into one or more
  `LuaDocument` values via a handler callback
- `LuaInputStream(filename)` - wrap a filesystem path as a stream that
  supports `:read(n)` / `:read("a")`

---

## Putting it together

A typical two-argument handler follows this shape:

```lua
function handler(ffdocument, session)
    -- Optional: read attributes / reference to decide what to do
    local ref = ffdocument:getReference()

    -- Work on parts, or call modifyDocument for field-level edits
    ffdocument:modify({
        onContent = function(action)
            action:transformContent(function(inputstream, outputstream)
                local text = inputstream:read("a")
                outputstream:write(text:gsub("%s+", " "))
            end)
        end,
    })

    -- Optional: create sibling FlowFiles and either return or transfer them
    local child = session:create(ref .. ":" .. create_uuid(), "add", ffdocument)
    session:transfer(child, "success")

    -- The input ffdocument will route via RouteTo unless you return,
    -- transfer or remove it here.
end
```

If the script needs to route multiple documents back from a one-argument
form, return them as multiple values:

```lua
function handler(document)
    local child1 = LuaDocument:new(document:getReference() .. ":a")
    local child2 = LuaDocument:new(document:getReference() .. ":b")
    return child1, child2  -- both go to RouteReturnedTo
end
```
