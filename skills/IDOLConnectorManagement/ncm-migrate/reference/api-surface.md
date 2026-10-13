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

# API surface and calling conventions

The authoritative definition is the OpenAPI spec **the deployment itself serves**: browse it at
`<host>/swagger-ui.html`, or fetch the bundled document from `<host>/spec/public_api.yaml`. That
is the contract for the version actually running, so prefer it to any other source whenever a
payload detail matters. This file is the map, not the specification.

Tenant context goes in `X-Tenant-Id` and `X-Subscription-Id` headers or as `tenantId` and
`subscriptionId` query parameters - **prefer the headers**, so a tenant id never lands in a log line
or a shell history alongside the URL. `name` is optional on a create (only `type` is required) and is
a label rather than a key: it need not be unique, and an update ignores it.

## Base URL and ports

| Port | Base | Who uses it |
|---|---|---|
| 8080 | `/v1/...` | you |
| 8081 | `/internal/v1/...` | NiFi, calling back with reports |

Port access is enforced, so a public call to 8081 fails and vice versa. Never call the internal
API; it exists for the flow to report into.

## Tenant context

Every connector and target belongs to a tenant and subscription.

**The JWT is the real mechanism.** With authentication enabled, send
`Authorization: Bearer <jwt>` and tenant context is taken from the `tid` and `scrid` claims. This
is why you will not find `tenantId`/`subscriptionId` among the parameters in the spec - they are
not part of the contract, and their absence is deliberate rather than an omission.

**With authentication disabled** (`connectors.auth.enabled=false`, the default) there are no claims
to read, so the same context is taken from query parameters `tenantId` / `subscriptionId` or headers
`X-Tenant-Id` / `X-Subscription-Id`. Treat that as a development affordance, not an API: Swagger UI
supplies it for you through custom scripting, injecting the two headers from a dev panel. **Both
values are still required on every connector and target endpoint**, listings included - omitting
either is a **400 `tenantId and subscriptionId are required`**, not an unscoped listing. The caller
is otherwise treated as a cloud admin.

Only the `/v1/admin` operations take a tenant or subscription id as an explicit path parameter,
because they act *on* one rather than within it.

Health, Swagger UI and the internal callbacks are always unauthenticated.

Use the same tenant and subscription for every call in a migration - a connector created under one
is invisible to the other.

## Permissions

When authentication is enabled, **a valid token is not sufficient**: each operation additionally
requires a specific permission, and a token that lacks it gets **403**, not 401. Permissions are
granted through roles, and a migration crosses several of them:

| Role | Covers |
|---|---|
| `Viewer` | catalogue, configuration and job/report status - read-only |
| `Editor` | authoring configuration (create/update/validate) - but **cannot** deploy, run or delete |
| `Operator` | deploy/enable, synchronize/fetch, cancel jobs - but **cannot** edit configuration |
| `Contributor` | Editor + Operator + reset and single-item delete |
| `DataViewer` | everything Viewer has, plus `connectors:identifiers:read` and `connectors:documents:view` - held separately because enumerating identifiers and reading documents exposes indexed content |
| `DataAdmin` | DataViewer + document delete and config delete (single and bulk) |
| `SubscriptionAdmin` / `TenantAdmin` | everything within the scope |
| `PlatformAdmin` | every permission - but note it is **not** what grants cross-tenant reach |

Three consequences worth planning for. The investigation phases need **DataViewer**, which an
otherwise well-provisioned Editor or Contributor token does not include - so discovery can fail
with 403 on a token that creates connectors happily. Editor alone cannot enable or run anything,
so a full migration needs Contributor or the equivalent pair. And deleting documents
(`POST /v1/connectors/{id}/delete`) needs `connectors:documents:delete`, which lives in
**DataAdmin** - not in Contributor, and not in DataViewer.

**Cross-tenant reach is a separate signal, not a role.** It comes from a cloud-admin claim in the
token, independent of the roles above, and it satisfies the permission check on **every** endpoint -
so such a token needs no role grants at all. `resources/resync` and `reconcile` then check the claim
*again* on its own, which is why a `PlatformAdmin` token without it still gets 403 on
`resources/resync` despite holding every permission. That 403 says only "Cloud admin privileges required" and names no permission.
The two `DELETE`s instead take the role's permission, within the caller's own tenant:
`SubscriptionAdmin` may delete the subscription it is acting as, `TenantAdmin` its own tenant and any
subscription in it. Only a cloud admin may delete another tenant's data.

**Where roles come from depends on the deployment.** With an Entitlement Service configured (as on
OCP), they are the roles it lists for the caller on the subscription the request acts as, and the
token's roles and scopes are ignored. Without one, they come from the token's `role` claim - each
written `<role>@<subscription>`, of which only the subscription the request acts as counts - or,
when it names none for that subscription, from the `scope`/`scp` claim (a `SCOPE_` prefix is
stripped); a `roles` or `groups` claim is ignored without error. Either way a
caller who looks correctly provisioned can get a 403 naming a permission they believe they have -
check the subscription's roles, or those claims, first.

Otherwise a 403 names the permission required; report it as a permission problem rather than
retrying or working around it.

## Conventions

- List endpoints page with `offset` (default 0) and `count` (default 100, max 1000), and return
  `_links`.
- Errors carry a JSON `Error` body. 409 is a state conflict - not enabled, not deployed, a job
  already running, an entity that is deployed and enabled being updated, or a manual synchronize
  of an operation that has a cron schedule; 429 is a throttle and carries `Retry-After`; 503 means
  a dependency or the resource catalogue is not ready.
- Asynchronous operations return **202** with a `JobSubmission` holding a job token; poll the job
  endpoints for the outcome.
- `validate` is a **GET**, and checks the connection as well as the configuration.
- Job cancellation is a **DELETE** on the job.

## Types - what this deployment can do

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/types/connectors` | connector types available, with versions |
| GET | `/v1/types/connectors/{connectorTypeId}` | property schema, supported operations, docs link |
| GET | `/v1/types/targets` | target types - includes put-capable connector types, subject to the deployment CONNECTOR_TARGET_TYPES allow-list |
| GET | `/v1/types/targets/{targetTypeId}` | target property schema and dynamic properties |
| GET | `/v1/types/processing` | processing step types available |
| GET | `/v1/types/processing/{processingTypeId}` | processing step property schema |
| GET | `/v1/types/processing/Eduction/grammars` | the grammars available to Eduction steps and the entities each defines - filter with `group`, `search`, `category`, `language`, `country`; `?version=` as for the detail endpoints |
| GET | `/v1/types/processing/KeyView/file-types` | the document classes and formats KeyView recognises, each with the token a file type routing step takes - filter with `search`, `class`, `extension`, `mimeType`, `group` |

The three detail endpoints accept `?version=`; the latest is returned by default. Property
definitions carry `id`, `type` (`ValueType`), `optional`, `secure`, `multiValued`,
`defaultValue` or `defaultValueFrom`, `allowableValues`, `dependsOn`, `section` and `valueTemplates`.

## Connectors

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/connectors` | list; filter by `type`, `enabled` |
| POST | `/v1/connectors` | create |
| GET | `/v1/connectors/{id}` | detail, with validation state |
| PUT | `/v1/connectors/{id}` | full update |
| PATCH | `/v1/connectors/{id}` | partial update |
| DELETE | `/v1/connectors/{id}` | delete |
| DELETE | `/v1/connectors` | delete all in scope |
| GET | `/v1/connectors/{id}/validate` | validate configuration and connection |
| POST | `/v1/connectors/{id}/enable` | enable - deploys the flow into NiFi |
| POST | `/v1/connectors/{id}/disable` | disable - undeploys, fast teardown |

## Investigating a repository

All are POST because the identifier is an opaque value in the body.

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/connectors/{id}/list/identifiers` | direct descendants of an identifier (`ROOT` for the top level) |
| POST | `/v1/connectors/{id}/identifiers/metadata-schema` | metadata fields a document at this identifier exposes |
| POST | `/v1/connectors/{id}/view/metadata` | the metadata a document actually carries, **without** transferring it (`text/xml`) |
| POST | `/v1/connectors/{id}/identifiers/insertable-objects` | what may be created here, and how its identifier is built |
| POST | `/v1/connectors/{id}/view` | the document's content, served with its own MIME type and a `Content-Disposition` filename |

Two of those save a download. `view/metadata` answers "what does this document hold" without
transferring the document, where `/view` transfers it in full - so prefer it whenever the content
itself is not what you need. It is the VIEW operation asked for metadata only, so it needs `view`
among the connector's operations; `metadata-schema` and `insertable-objects` are served by the GET
processor instead. And `list/identifiers` accepts a `meta` array
(`createdDate`, `modifiedDate`, `sizeBytes`), returning each requested value in every descendant's
`meta` map, which is the only way to get sizes without fetching anything.

See `discovery.md`.

## Running work

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/connectors/{id}/{get\|groups}/synchronize` | full synchronize; 202 + job token |
| POST | `/v1/connectors/{id}/{get\|groups}/reset` | reset synchronize state |
| POST | `/v1/connectors/{id}/fetch` | fetch and ingest up to 1000 named identifiers; 202 |
| POST | `/v1/connectors/{id}/delete` | delete up to 1000 named identifiers **from the source repository**; 202 |

`delete` removes documents from the repository the connector is attached to. It is not a way to
undo an ingest, and there is no dry run.

## Monitoring

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/connectors/{id}/jobs` | job history, filterable by status, operation, time |
| GET | `/v1/connectors/{id}/jobs/{jobToken}` | one job: status, operation, when it was recorded, and what it did - `documentsProcessed`/`documentsExpected` where the work is a known set, plus `documentsFailed` and `documentsErrored` for documents that did not arrive |
| DELETE | `/v1/connectors/{id}/jobs/{jobToken}` | request cancellation (best-effort, async) |
| GET | `/v1/connectors/{id}/jobs/{jobToken}/progress` | progress for that job |
| GET | `/v1/connectors/{id}/progress` | live connector snapshot, per operation and stage |
| GET | `/v1/connectors/{id}/reports` | per-document reports; filter by `operation`, `since`, `until`, `errorsOnly`, `messageType`, `messagePattern` |

## Targets

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/targets` | list; filter by `type`, `enabled` |
| POST | `/v1/targets` | create, including the processing graph |
| GET | `/v1/targets/{id}` | detail |
| PUT | `/v1/targets/{id}` | full update - the only way to replace `processing` |
| PATCH | `/v1/targets/{id}` | partial update - rejects `processing`, use PUT |
| DELETE | `/v1/targets/{id}` | delete |
| DELETE | `/v1/targets` | delete all in scope |
| GET | `/v1/targets/{id}/validate` | validate |
| POST | `/v1/targets/{id}/processing/{stepId}/test` | run an Eduction step, as configured, over sample `content` (and optional `fields`); returns each match with its field, entity, value and offset. Needs the same permission as validate |
| POST | `/v1/targets/{id}/enable` | enable |
| POST | `/v1/targets/{id}/disable` | disable |

A connector referencing a target that is disabled or in an incompatible state is downgraded with
it, so check the target's state when a connector will not enable.

## Health and admin

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/health/live` | the application is running |
| GET | `/v1/health/ready` | database and NiFi always required; resource provider and key store required only until each has first answered |
| POST | `/v1/admin/resources/resync` | re-read the resource source and drop cached listings |
| POST | `/v1/admin/reconcile` | redeploy connectors and targets that should be running but have been lost; `dryRun=true` reports only |
| DELETE | `/v1/admin/tenants/{tenantId}` | delete all data for a tenant |
| DELETE | `/v1/admin/subscriptions/{subscriptionId}` | delete all data for a subscription |

`resync` and `reconcile` are cloud-admin only; the two `DELETE`s need `TenantAdmin` /
`SubscriptionAdmin` within the caller's own tenant, or a cloud admin. The two `DELETE`s are irreversible - do not call them to "clean up"
without being asked. `resources/resync` is safe and routine: it re-reads the resource source and
drops cached listings, serving throughout. `reconcile` changes deployments, so run it with
`dryRun=true` first, and only redeploy when asked to.

## Operations vocabulary

A connector declares which operations it supports; a connector entity enables a subset.

- **Synchronize operations**: `get` (documents), `groups` (security/user-group information).
- **Others**: `view`, `list`, `fetch`, `delete`, `put`, `patch`, `hold`.

`put` is what makes a connector type usable as a target. `list` and `view` are what make it
explorable. Only `get` requires an explicit target entry at create time (pass `null` for none).
