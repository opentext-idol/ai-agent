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

# ExecuteDocumentLua - AI context bundle

Everything an AI (or a human) needs to write Lua scripts for the
`ExecuteDocumentLua` NiFi processor.

## Contents

| File                              | Purpose                                    |
|-----------------------------------|--------------------------------------------|
| `lua_functionality.lua`           | Typed API surface.  LuaLS / EmmyLua annotated stub covering every class, method, global function, type alias and named-parameter group.  `---@meta` at the top marks it as declarations-only - it is not meant to be executed. |
| `executedocumentlua_context.md`   | How the processor invokes the script - the `handler` entry point, routing rules, FlowFile parts, session operations.  This is the semantic context the stub does not describe. |
| `samples/`                        | Ready-to-run sample scripts, grouped by topic.  Each sample has a header comment naming it; these double as few-shot examples. |

## Using it with an AI

The simplest recipe: drop all three of the top-level items
(`lua_functionality.lua`, `executedocumentlua_context.md`, and the
`samples/` directory) into whatever context mechanism the tool offers -
a "project" in Claude / ChatGPT, a `repomix` bundle, a Cursor workspace,
or the working tree a command-line coding agent is pointed at.

Then ask for the script you want.  The stub gives the AI the exact call
signatures, the context file explains how the script is invoked and how
routing works, and the samples give a feel for idiomatic usage.

## Using it with a Lua Language Server

If you're using a Lua Language Server, `lua_functionality.lua` needs to
sit in your workspace (or in a path configured via `Lua.workspace.library`)
for completions to work.

Point `Lua.workspace.library` at the directory containing
`lua_functionality.lua` (for example in VS Code's `settings.json`):

```json
{
    "Lua.workspace.library": ["/path/to/unpacked/bundle"]
}
```

You will then get type-aware completions, hover docs and diagnostics in
your editor when you write ExecuteDocumentLua scripts.
