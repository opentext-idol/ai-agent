# ExecuteDocumentPython - processor context

This document describes how the `ExecuteDocumentPython` NiFi processor invokes a
Python script and how the script is expected to interact with the FlowFile
pipeline.  It is intended as supporting context for a developer (or AI) writing
scripts against the `idolnifi` / `idolaci` API surface defined in the
accompanying stub files.

---

## Execution model

Each invocation of the processor runs the configured Python script against a
single input FlowFile.  The script must define a global function whose name is
given by the `Python script function` property (default `handler`).  The
processor calls this function once per FlowFile.

The handler signature is **dispatched by argument name, not position**.
The processor inspects the parameter names of the function and passes the
appropriate object for each.  The recognised names are:

| Parameter name(s)                   | Object passed                    |
|-------------------------------------|----------------------------------|
| `p`, `processor`                    | `idolnifi.Processor`             |
| `c`, `context`                      | `idolnifi.ProcessContext`        |
| `s`, `session`                      | `idolnifi.ProcessSession`        |
| `ff`, `flowfile`                    | `idolnifi.FlowFile` *            |
| `doc`, `ffdoc`, `document`, `flowfiledocument` | `idolnifi.FlowFileDocument` * |

\* Only one of `FlowFile` or `FlowFileDocument` may appear, and only when the
processor has an incoming connection.  Processors with no input connection can
still create FlowFiles/FlowFileDocuments as output, but cannot accept one as a
handler argument.

Choose the `FlowFileDocument` parameter (`doc` / `ffdoc` / `document` /
`flowfiledocument`) when the incoming FlowFile is in IDOL FlowFileDocument
format - this gives access to parts, XML metadata, and the structured
document API.  If the input is **not** in FlowFileDocument format (for
example, raw FlowFiles produced by another processor that does not emit
IDOL documents), a `FlowFileDocument`-typed parameter raises
`FlowFileFormatException` and the FlowFile is routed to the `failure`
relationship.  For arbitrary non-document FlowFiles, use the `FlowFile`
parameter (`ff` / `flowfile`) instead and work with it as an opaque byte
stream plus attributes via `ProcessSession.read` / `.write` /
`.readWrite` / `.putAttribute` etc.

The script may import modules, define helpers, and do module-level setup (for
example `installPackage(...)` calls - see *Packages* below).  Only `handler`
(or the custom function named by the property) is called per FlowFile.

```python
from idolnifi import *

def handler(context, session, flowfile):
    logInfo(context.getName())
    # ... process the FlowFile ...
    return flowfile
```

Module-level code runs once when the processor is scheduled, not per FlowFile.

---

## Script header directives

The processor scans the **leading comment block** of the main script for
directive lines of the form:

```python
#@ <PropertyName>=<value>
```

Any such directive overrides the corresponding processor property for this
script, both at runtime in the native processor and persisted back into the
processor's stored properties on save.  Use this to make a script
self-describing: the `ExecuteDocumentPython` processor picks up the
declared configuration without the user having to remember to set it in
the UI.

### Recognised directives

| Directive                        | What it sets                                              |
|----------------------------------|-----------------------------------------------------------|
| `PythonScriptFunction`           | Handler function name (default `handler`).                |
| `RouteTo`                        | Relationship the input FlowFile is routed to by default.  Empty value = no default routing. |
| `RouteReturnedTo`                | Relationship FlowFiles returned by the handler are routed to. |
| `RouteUntransferredTo`           | Relationship for any FlowFile the handler created but did not explicitly transfer, return, or remove. |
| `AdditionalOutputRelationships`  | Comma-separated list of extra relationship names the script wants available for `session.transfer(...)`. |

Unlike Lua, Python does **not** need a `ScriptFunctionArguments` directive
because handler arguments are dispatched by parameter name at runtime
(see *Execution model*).

Other `# ...` comments in the header are ignored by the parser and remain
as plain prose for the reader.  The directive form requires the `@` sigil
on the comment: a bare `# PythonScriptFunction=handler` is not parsed.

### When a script should declare directives

When generating or authoring a script, include directives for every
configuration option the script depends on, so the processor is set up
correctly without the user having to remember to tick boxes in the UI.
In particular:

- **Declare `AdditionalOutputRelationships`** whenever the script calls
  `session.transfer(ff, relName)` with anything other than the already-wired
  relationships.  The relationships named here become available in the
  NiFi graph so the user can connect them downstream.
- **Declare `RouteTo` / `RouteReturnedTo` / `RouteUntransferredTo`** when
  the script is built around a specific routing contract (for example, a
  script that always returns new FlowFiles and expects them routed to
  `split`).
- **Declare `PythonScriptFunction`** only if using a non-default handler
  function name.

### Example

A script that emits two categories of derived FlowFiles on different
relationships, and drops the original:

```python
#@ PythonScriptFunction=handler
#@ AdditionalOutputRelationships=text,binary

from idolnifi import *

def handler(session, flowfile):
    text_ff = session.create(parent=flowfile)
    binary_ff = session.create(parent=flowfile)
    # ... populate text_ff and binary_ff ...
    session.transfer(text_ff, "text")
    session.transfer(binary_ff, "binary")
    session.remove(flowfile)
```

Loading this script into the processor automatically exposes `text` and
`binary` as output relationships - no manual UI configuration required
beyond connecting those relationships in the flow.

### Values, empty values

- Non-empty value → that value is used.
- Empty value (`#@ RouteTo=`) → explicit clear; the property is treated
  as unset.
- For free-text properties any string is accepted.

---

## The idolnifi and idolaci modules

### `idolnifi`

The primary API module.  Provides:

- **Processor helpers**: `logError/Warn/Info/Debug/Trace`, `getStorageDirectory`,
  `getFilesStorageDirectory`, `getTempFile`, `getPropertyDescriptor`,
  `isScheduled` - each attempts to locate the executing processor and
  forwards to the corresponding `Processor` method.
- **Classes**: `Processor`, `ProcessContext`, `ProcessSession`, `FlowFile`,
  `FlowFileDocument`, `StateManager`, `StateMap`, `PropertyDescriptor`,
  `PropertyValue`, `InputStream`, `OutputStream`, `TextInputStream`,
  `TextOutputStream`, `XmlElement`.
- **Document-action classes** used through `FlowFileDocument` access methods:
  `DocumentAction`, `DocumentPartAction`, `ContentAction`, `FileAction`,
  `ContentFileAction`, `ContentFilenameAction`, `ExternalFileAction`.
- **Modifier types**: `DocumentModifier` (fluent callback registration) and
  `DocMod` (subclass this and define `preAction`/`onContent`/... methods).
- **Package management**: `installPackage`, `getInstalledPackages`,
  `DefaultPackageDirectory`, `PersistentPackageDirectory`.
- **Sub-process helpers**: `executePython`, `executePythonToLines`, `LogStream`.

### `idolaci`

Optional module for sending ACI actions to IDOL servers.  Provides
`send_aci_action(host, port, action, params=..., *, timeout=..., retries=...,
ssl_params=...)` for one-shot calls, plus `Connection`, `Request`, `Response`
classes for reusable connections.  Import with `import idolaci` or
`from idolaci import ...`.

---

## FlowFile vs FlowFileDocument

- `FlowFile` is the raw NiFi FlowFile surface - attributes, `getUuid`,
  `getSize`, and is the value passed to `ProcessSession.read`, `.write`,
  `.transfer`, etc.  Use this when you only need to manipulate the FlowFile as
  an opaque byte stream.

- `FlowFileDocument` wraps a FlowFile as a structured IDOL document,
  exposing: reference (`idol.reference` attribute), XML metadata, and one or
  more *parts* (text content, embedded files, filename references, external
  file references).  Use this when the FlowFile carries IDOL document data
  and you want to read or edit individual parts or metadata.

Get a `FlowFileDocument` for an existing FlowFile with
`session.asFlowFileDocument(flowfile)`, or request one directly in the handler
signature by naming your parameter `doc` / `ffdoc` / `document` /
`flowfiledocument`.

`FlowFileDocument` and `session.asFlowFileDocument` both require the FlowFile
to be in FlowFileDocument format; on any other FlowFile they raise
`FlowFileFormatException`.  If your processor may receive arbitrary
FlowFiles, take a `FlowFile`-typed parameter (`ff` / `flowfile`) and work
with it through the session.

---

## FlowFileDocument operations

Five access methods with matching context-manager variants.  All except
`compact` take a **modifier** that receives one or more action callbacks; the
callback receives an action object (`DocumentAction` or part-specific
subclass) and may mutate attributes, XML metadata, and parts.

| Method           | Intent                                             |
|------------------|----------------------------------------------------|
| `reading()` / `read(mod)`           | Read-only traversal. |
| `updatingAttributes()` / `updateAttributes(mod)`  | Read parts; may update FlowFile attributes and XML metadata only. |
| `appending()` / `append(mod)`       | Read existing parts; append new parts; may also update attributes / metadata. |
| `modifying()` / `modify(mod)`       | Read and fully write existing parts; append new parts; update attributes / metadata. |
| `overwriting()` / `overwrite(mod)`  | Like `modify`, but drops all existing parts unless they are explicitly kept via the modifier. |
| `compact(unwrapSinglePart)`         | Remove parts marked for deletion; optionally unwrap to a single-part FlowFile. |

The context-manager forms (`reading`, `appending`, etc.) are useful when a
script wants imperative code rather than callbacks:

```python
def handler(doc):
    with doc.appending() as action:
        action.addContent("Hello world")
        action.getXmlMetadata()["said_hello"] = "true"
```

The callback form uses a `DocumentModifier` or a `DocMod` subclass:

```python
from idolnifi import DocumentModifier, ContentAction

def on_content(action: ContentAction):
    action.transformContent(lambda inp, out: out.write(inp.read().lower()))

def handler(doc):
    doc.modify(DocumentModifier().onContent(on_content))
```

`DocMod` is a dict-based alternative that carries state alongside the
callbacks:

```python
from idolnifi import DocMod, ContentAction, DocumentAction

class HashPages(DocMod):
    def preAction(self, action: DocumentAction):
        self.hashes = []
    def onContent(self, action: ContentAction):
        action.readContent(lambda inp: self.hashes.append(hash(inp.read())))
    def postAction(self, action: DocumentAction):
        action.setAttribute("page_hashes", ",".join(map(str, self.hashes)))

def handler(doc):
    doc.modify(HashPages())
```

---

## Document parts

Parts come in four kinds; each `DocumentAction` subclass is for a specific
kind.  The modifier callbacks dispatch on kind:

| Part kind       | Action class           | Modifier callback   |
|-----------------|------------------------|---------------------|
| Text content    | `ContentAction`        | `onContent`         |
| Embedded file   | `ContentFileAction`    | `onContentFile`     |
| Filename ref    | `ContentFilenameAction`| `onContentFilename` |
| External file   | `ExternalFileAction`   | `onExternalFile`    |

A `defaultFileAction` callback catches any of the three file-ish kinds that
isn't handled by a more specific callback.  `preAction(action)` and
`postAction(action)` fire before and after the per-part callbacks and get the
top-level `DocumentAction` rather than a part action - useful for setup /
teardown against the document as a whole.

Each action type has part-specific operations.  Highlights:

- `ContentAction`: `readContent`, `writeContent`, `transformContent`,
  `getContent` (list of page strings), `setContent`.  Content text is split
  into *pages* separated by `PageSeparator` (`'\x0C'`).
- `FileAction` (shared by all file kinds): `readAsFilename`, `readFile`,
  `transformFile`, `transferToFile`, `transferToFilename`, `transferToExternalFile`,
  `setFileMimeType`, `setFileDisplayName`.
- `ContentFileAction`: plus `writeFile`.
- `ContentFilenameAction`: plus `getFilename`, `replaceFilename`,
  `hasOwnership`, `disownFile`, `exists`.
- `ExternalFileAction`: plus `getLocator`, `replaceLocator`, `getDownloadUrl`.

All file operations accept either a callable (`fn(InputStream)` etc.) or can
be used as a context manager via `WithCallable`, e.g.
`with action.readFile() as inp:`.

---

## Routing

| Property          | Applies to                                       |
|-------------------|--------------------------------------------------|
| `RouteTo`         | The input FlowFile, by default                   |
| `RouteReturnedTo` | FlowFiles returned by the handler                |

- The input FlowFile is routed to `RouteTo` unless the handler explicitly
  returns, transfers (`session.transfer(ff, rel)`), or removes
  (`session.remove(ff)`) it.
- FlowFiles (or FlowFileDocuments) returned by the handler are routed to
  `RouteReturnedTo`.
- FlowFiles created via `session.create(...)` that are not returned,
  transferred, or removed before the handler exits cause the script to fail.
- A `failure` relationship is always available for error routing.
- Additional relationships can be declared via the `Additional output
  relationships` property and then targeted from `session.transfer`.

---

## Attributes and metadata

- FlowFile attributes via `FlowFileDocument.getAttribute(name, defValue=None)`,
  `getAttributes()`, `setAttribute(name, value)`, `removeAttribute(name)`,
  or (for batch updates) `ProcessSession.putAttributes(ff, {..})`.
- Special well-known attributes: `idol.reference` (accessed via
  `getReference()`) and `idol.reference.action` (`getReferenceAction()`,
  typically `'Add'`, `'Update'`, or `'Remove'`).
- XML metadata via `FlowFileDocument.getXmlMetadata()` (returns a
  `WithXmlElement` context manager) or `DocumentAction.getXmlMetadata()`
  inside a modifier callback.
- `XmlElement` supports dict-style access: `element["child"]` gets or
  creates a child element, `element["@attr"]` reads the attribute,
  `element["child"] = "value"` sets a child's text, `del element["child"]`
  removes all children with that name.  XPath queries via
  `getElementsByXPath(xpath)` and `getValuesByXPath(xpath)`.

---

## Sessions

`ProcessSession` exposes the standard NiFi session operations:

```python
def handler(context, session, flowfile):
    new_ff = session.create(parent=flowfile)
    new_ff = session.putAttribute(new_ff, "source", flowfile.getAttribute("filename"))

    with session.write(new_ff) as out:
        out.write(b"payload")

    session.transfer(new_ff, "success")   # explicit relationship
    session.remove(flowfile)              # drop the input
```

`session.get()` / `session.get(maxResults=N)` are available for scripts that
fetch additional FlowFiles from the queue themselves.  `session.commit()` and
`session.rollback()` are also exposed but are usually handled automatically
by the processor lifecycle.

---

## Packages and sub-processes

Scripts can `import` any module in the default Python environment.  Extra
packages can be installed at module-load time (when the processor is
scheduled) via:

```python
from idolnifi import installPackage, PersistentPackageDirectory
installPackage("numpy", packageDirectory=PersistentPackageDirectory)

import numpy
```

- `DefaultPackageDirectory` is the built-in `site-packages` inside the
  processor's Python distribution.
- `PersistentPackageDirectory` (`idol_repository/pypackages`) survives
  across restarts and can also be populated via the advanced UI's *Packages*
  tab.

Packages may also be installed interactively through the *Packages* tab; the
per-processor `idol_repository` storage keeps them available between runs.

For running external tools, use `executePython(args, ...)` or
`executePythonToLines(args, output, errors)` which spawn `sys.executable` with
pipe-captured stdout/stderr.

---

## Logging

Module-level `logInfo / logWarn / logError / logDebug / logTrace` route to
the current processor's log.  The `Processor` instance exposes the same
methods; both forms are equivalent when you have the processor object.

`idolnifi.LogStream(logFn, sep, end)` is a writable IOBase wrapper around a
log function - useful to pass as `stdout`/`stderr` for subprocesses, or as
a file-like destination to any library that writes to a stream.

---

## Putting it together

```python
from idolnifi import DocMod, DocumentAction, ContentAction, ContentFileAction, logInfo

class Normalise(DocMod):
    def preAction(self, action: DocumentAction):
        self.pages = 0
    def onContent(self, action: ContentAction):
        self.pages += 1
        action.transformContent(
            lambda inp, out: out.write(inp.read().replace("  ", " "))
        )
    def onContentFile(self, action: ContentFileAction):
        action.setFileMimeType("application/octet-stream")
    def postAction(self, action: DocumentAction):
        action.setAttribute("normalised_pages", str(self.pages))
        logInfo(f"Normalised {self.pages} pages for {action.getAttribute('filename')}")

def handler(doc):
    doc.modify(Normalise())
```

The input `FlowFileDocument` is routed to `RouteTo` after the handler
completes.  To send the normalised document somewhere explicit, use the
two-argument form and call `session.transfer(...)` instead.
