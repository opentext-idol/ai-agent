# IDOL NiFi Policy - AI authoring bundle

This bundle lets an AI assistant generate and repair **policy trees** for the NiFi Policy
processor. A policy tree is the JSON supplied to the processor's *Policies JSON* property (or
its advanced UI); it describes how each FlowFile is processed.

Hand-writing this JSON is awkward, which is the main reason the processor is hard to adopt.
This bundle removes that step: the descriptors are a precise, machine-readable spec an assistant
targets, and every generated tree can be **deterministically validated** before it is run.

It can also be downloaded from the processor's advanced UI, so `descriptors.json` reflects the
policies actually available in **that** processor instance - including any custom policies on its
*Policies Class Path*. Re-download it if the processor's policy set changes.

## Contents

| File | Source | Purpose |
| --- | --- | --- |
| `descriptors.json` | generated live | The complete policy set: every policy, its config, types, defaults, allowed values, required context, result type, and which configs name exit relationships. The source of truth. Includes low-level building blocks (`advanced: true`) - prefer the high-level policies. |
| `policy-reference.md` | generated live | Human-readable reference, rendered from `descriptors.json`. |
| `system-prompt.md` | static | Instructions for the assistant: output format and the rules it must follow. |
| `examples/` | static | Worked problem -> policy-tree examples for few-shot prompting. |

## How to use

1. Give the assistant `system-prompt.md`, `descriptors.json`, and the `examples/` as context.
2. Ask in plain language (e.g. "route invoices to the `invoices` relationship and everything
   else to `success`").
3. The assistant returns a policy tree as JSON.
4. **Validate** it (see below). On failure, hand the path-annotated errors back to the
   assistant to repair, and repeat. This validate/repair loop is what makes generation
   reliable - it is not possible with a free-form scripting processor.

## Validating a generated tree

Validation is a pure-Java call - no running NiFi required. Prefer `validatePolicy`, which returns
an empty string when the tree is valid, or the error chain when it is not (one line per problem),
so the result can be fed straight back to the assistant:

```java
String errors = new PolicyFactory(classLoader)
    .validatePolicy("getFlowFileRootPolicy", generatedJson);   // "" if valid
```

Each error line is `at <path> [<policy-type>]: <message>`, e.g.

    at policies[0].then [set-context-attribute]: Policy configuration 'name' is required

where `<path>` addresses the node in the authored JSON (config keys joined with `.`, list
elements `[n]`; `$` is the root). This points the assistant straight at the sub-tree to fix.

Interactively, the processor's advanced UI has a **Validate** button that runs exactly this and
highlights each offending node in the editor with the same message.

(`getFlowFileRootPolicy` seeds a FlowFile at the root - the right choice for a tree that runs on
the FlowFilePolicyProcessor or otherwise assumes an incoming FlowFile. Use `getRootPolicy` for a
plain PolicyProcessor tree that acquires its own FlowFiles.)

The processor's *Output Relationships* property must include every relationship the tree can
route to. Configs flagged `isRelationship` in the descriptors name those exits (their value, or
its default); collect them across the tree to know the full set. (The advanced UI keeps this
property in sync automatically when you save.)
