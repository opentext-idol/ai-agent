# ExecuteDocumentPython - AI context bundle

Everything an AI (or a human) needs to write Python scripts for the
`ExecuteDocumentPython` NiFi processor.

## Contents

| File                                  | Purpose                                    |
|---------------------------------------|--------------------------------------------|
| `idolnifi.py`                         | Typed API source for the primary `idolnifi` module.  Covers `Processor`, `ProcessContext`, `ProcessSession`, `FlowFile`, `FlowFileDocument`, document actions, modifiers, logging, package management, and helpers.  Loaded at runtime by the processor; the docstrings and type hints double as the reference. |
| `idolaci.pyi`                         | Typed stub for the optional `idolaci` module (ACI actions).  Declarations only - the native implementation is provided by the processor runtime. |
| `executedocumentpython_context.md`    | How the processor invokes the script - the `handler` entry point (parameters dispatched by name), routing, FlowFileDocument access methods, parts, sessions, packages. |
| `samples/`                            | Ready-to-run sample scripts grouped by topic (attributes, FlowFileDocument read/modify/overwrite/append, content and file parts, package installation).  Each sample has a header comment naming it; these double as few-shot examples. |

## Using it with an AI

Drop all the items above into whatever context mechanism the tool offers -
a project in Claude / ChatGPT, a `repomix` bundle, a Cursor workspace, or the
working tree a command-line coding agent is pointed at.  Then ask for the
script you want.

The stub files give call signatures and type hints, the context file explains
how the script is invoked and how routing works, and the samples show
idiomatic usage.

## Using it with a Python type checker

If you're using Pylance / Pyright or any other Python type checker,
the stub files need to be reachable from your workspace.

Put `idolnifi.py` and `idolaci.pyi` on the import path (for example via
`extraPaths` in a `pyrightconfig.json`, or by dropping them into a
`stubs/` directory configured as a source root).  You will then get
type-aware completions and diagnostics when you write ExecuteDocumentPython
scripts.
