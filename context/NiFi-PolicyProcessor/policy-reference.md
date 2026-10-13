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

# Policy reference

Auto-generated from the policy descriptors. Each policy is a node `{ "type": "<name>", ... }` in the policy tree. Policies marked _building block_ are low-level primitives, hidden from the default authoring surface; prefer the high-level policies.

## Context

### `get-context-attribute` _(building block)_

Reads a workflow-scoped context attribute by name.

**Result:** String

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | policy &rarr; String | yes |  |  |  |  |

### `has-context-attribute` _(building block)_

True when a context attribute with the given name is set.

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | policy &rarr; String | yes |  |  |  |  |

### `set-context-attribute` _(building block)_

Sets a workflow-scoped context attribute and returns its value.

**Result:** String

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | policy &rarr; String | yes |  |  |  |  |
| `value` | policy &rarr; String | yes |  |  |  |  |

## Control

### `throw` _(building block)_

Raises a PolicyException with the given message (caught by an enclosing try).

**Result:** Object

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `message` | policy &rarr; String | yes | `"Policy error"` |  |  |  |

### `try` _(building block)_

Runs 'do'; if it throws one of the 'catch' exception types, runs 'on-exception' instead.

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `do` | policy | yes |  |  |  |  |
| `catch` | string list |  | `["PolicyException","PolicyRuntimeException"]` |  |  | Exception class simple or full names to catch; defaults to PolicyException/PolicyRuntimeException. |
| `on-exception` | policy | yes |  |  |  |  |

## Conversion

### `string-to-boolean` _(building block)_

Parses a string ('true'/'false') into a boolean.

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `value` | policy &rarr; String | yes |  |  |  |  |

### `string-to-number` _(building block)_

Parses a string into a number.

**Result:** Number

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `value` | policy &rarr; String | yes |  |  |  |  |

### `value-to-string` _(building block)_

Converts any value to its string form.

**Result:** String

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `value` | policy &rarr; Object | yes |  |  |  |  |

## Document

### `get-metadata` _(building block)_

Reads IDOL document metadata by XPath, optionally running a for-each policy per matched node. For conditions/values, prefer the idol.xmlmetadata functions of expression.

**Requires context:** `document` (Document)

**Result:** String

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `field-path` | policy &rarr; String | yes |  |  |  |  |
| `for-each` | policy list |  |  |  |  |  |

### `with-document`

Wraps the FlowFile as an IDOL Document and runs 'do' with it in context, reusing an existing Document for the same FlowFile where possible.

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `do` | policy list | yes |  |  |  | Policies to run with the Document (and FlowFile) in scope. |

## FlowFile

### `for-each-flowfile`

Processes a batch of FlowFiles, running 'do' for each with the FlowFile in scope. A FlowFile not transferred or removed by 'do' is transferred to the terminal relationship. Wrap 'do' in 'try' to isolate a single FlowFile's failure; otherwise an error rolls back the whole batch.

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `do` | policy list | yes |  |  |  | Policies to run for each FlowFile. |
| `batch-size` | number |  | `100` |  |  | Maximum number of FlowFiles to process per trigger; 0 for all available. |
| `terminal-relationship` | string |  | `"success"` |  | yes | Relationship an unresolved FlowFile is transferred to after 'do'. Empty or 'none' leaves it for an inner policy to resolve. |

### `get-flowfile-attribute` _(building block)_

Reads a FlowFile attribute by name (empty string if absent).

**Requires context:** `flowfile` (FlowFile)

**Result:** String

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | policy &rarr; String | yes |  |  |  |  |

### `get-flowfile-size` _(building block)_

The FlowFile content size in bytes.

**Requires context:** `flowfile` (FlowFile)

**Result:** Number

### `get-flowfile-start-date` _(building block)_

The FlowFile entry date (or lineage start date) as epoch milliseconds.

**Requires context:** `flowfile` (FlowFile)

**Result:** Number

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `use-lineage` | boolean |  | `false` |  |  | Use the lineage start date (oldest ancestor) instead of this FlowFile's entry date. |

### `has-flowfile-attribute` _(building block)_

True when the FlowFile has the named attribute.

**Requires context:** `flowfile` (FlowFile)

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | policy &rarr; String | yes |  |  |  |  |

### `remove-flowfile` _(building block)_

Removes (drops) the FlowFile from the session.

**Requires context:** `flowfile` (FlowFile)

**Result:** none (statement)

### `set-flowfile-attribute` _(building block)_

Sets a FlowFile attribute and returns the value.

**Requires context:** `flowfile` (FlowFile)

**Result:** String

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | policy &rarr; String | yes |  |  |  |  |
| `value` | policy &rarr; String | yes |  |  |  |  |

### `with-flowfile` _(building block)_

Establishes a FlowFile in context and runs 'do' against it. Acquires the next FlowFile from the queue (source=next) or reuses the one in scope (source=current). After 'do', a FlowFile not already transferred or removed is transferred to the terminal relationship.

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `do` | policy list | yes |  |  |  | Policies to run with the FlowFile in scope. |
| `terminal-relationship` | string |  | `"success"` |  | yes | Relationship an unresolved FlowFile is transferred to after 'do'. Empty or 'none' leaves it for an inner policy to resolve. |

## Logic

### `and` _(building block)_

True when all of the condition policies are true.

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `condition` | policy &rarr; Boolean list | yes |  |  |  |  |

### `equals` _(building block)_

True when the left and right values are equal.

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `left` | policy &rarr; Object | yes |  |  |  |  |
| `right` | policy &rarr; Object | yes |  |  |  |  |

### `if` _(building block)_

Runs the 'then' policy when all conditions are true, otherwise the 'else' policy.

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `condition` | policy &rarr; Boolean list | yes |  |  |  | Conditions to evaluate; all must be true for the 'then' branch to run. |
| `then` | policy |  |  |  |  | Policy run when the conditions are true. |
| `else` | policy |  |  |  |  | Policy run when the conditions are false. |

### `less-than` _(building block)_

True when the left number is less than the right number.

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `left` | policy &rarr; Number | yes |  |  |  |  |
| `right` | policy &rarr; Number | yes |  |  |  |  |

### `matches-regex` _(building block)_

True when the value matches the regular expression; capture groups are exposed as context attributes _1, _2, ...

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `value` | policy &rarr; String | yes |  |  |  |  |
| `regex` | string | yes |  |  |  |  |

### `not` _(building block)_

Negates a boolean condition.

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `condition` | policy &rarr; Boolean | yes |  |  |  |  |

### `or` _(building block)_

True when any of the condition policies is true.

**Result:** Boolean

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `condition` | policy &rarr; Boolean list | yes |  |  |  |  |

## Orchestration

### `orchestrate`

Drives a FlowFile through an ordered set of steps (each a sub-flow reached by a relationship that routes back to this processor), tracking progress via wf.* attributes, until all steps are done (on-complete), an exception is seen (on-exception), or the iteration guard trips (on-loop-limit).

**Requires context:** `flowfile` (FlowFile)

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `steps` | group list | yes |  |  |  | Ordered workflow steps; each is dispatched to its relationship until marked done on return. |
| `state-prefix` | string | yes | `"wf"` |  |  | Namespace for the workflow-state attributes (<prefix>.iter, <prefix>.current, <prefix>.step.<name>); default wf. Use a distinct namespace if more than one orchestrate acts on the same FlowFile, to avoid state collisions. |
| `clean-state` | boolean |  | `true` |  |  | Remove the state-prefix tracking attributes before on-complete. |
| `on-complete` | policy |  | `{"type":"transfer-flowfile","relationship":"success"}` |  |  | Policy run when all steps are complete. |

_`steps` fields:_

| Field | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | string | yes |  |  |  | Unique step name (letters, digits, _ - . :); tracked as wf.step.<name>. It keys workflow state on the FlowFile, so keep it stable - renaming a step strands in-flight FlowFiles that already carry the old wf.step.<name>. |
| `relationship` | string | yes |  |  | yes | Relationship this step is routed to (letters, digits, _ - . :); its sub-flow routes the FlowFile back here. |
| `when` | policy &rarr; Boolean |  |  |  |  | Optional condition; the step runs only when this is true. |

## Routing

### `requeue-flowfile` _(building block)_

Transfers the FlowFile back to the processor's own incoming queue for reprocessing (NiFi's no-relationship transfer), rather than to a named relationship. Use to defer or retry a FlowFile. This is not an output relationship, so it needs no connection.

**Requires context:** `flowfile` (FlowFile)

**Result:** none (statement)

### `route-by-metadata`

Transfers the FlowFile to one relationship when a metadata field matches a pattern, otherwise to another. Matches if any node selected by the field path satisfies the comparison.

**Requires context:** `document` (Document), `flowfile` (FlowFile)

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `field-path` | policy &rarr; String | yes |  |  |  | XPath of the metadata field(s) to test, e.g. "DRECONTENT" or "//author". |
| `mode` | string |  | `"equals"` | `equals` \| `contains` \| `regex` |  | How the field value is compared with the pattern. |
| `pattern` | policy &rarr; String | yes |  |  |  | Value to compare against. A literal for 'equals'/'contains', a regular expression for 'regex'. |
| `match-relationship` | string |  | `"matched"` |  | yes | Relationship the FlowFile is transferred to when the field matches. |
| `else-relationship` | string |  | `"success"` |  | yes | Relationship the FlowFile is transferred to when the field does not match. |

### `transfer-flowfile` _(building block)_

Transfers the FlowFile to a named relationship.

**Requires context:** `flowfile` (FlowFile)

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `relationship` | string | yes | `"success"` |  | yes | Name of the relationship to transfer the FlowFile to. A required, static name (not a policy) so every exit relationship is statically enumerable for auto-population and validation. To send the FlowFile back to the incoming queue instead, use requeue-flowfile. |

## System

### `root-policy` _(building block)_

The implicit root of a policy tree; runs its 'policies' in order. Not selectable as a child.

**Result:** none (statement)

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `policies` | policy list | yes |  |  |  |  |

## Value

### `expression` _(building block)_

Evaluates an IDOL-extended NiFi Expression Language string. Access document metadata with the idol.xmlmetadata:<xpath> token and document properties with idol.doc:<fn>, alongside standard EL. result-type selects string (default), boolean, or number.

**Result:** String

| Config | Type | Required | Default | Allowed | Routes? | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `value` | string | yes |  |  |  | Expression to evaluate, e.g. ${"idol.xmlmetadata:sensitive":equals('true')}. |

