---
name: discover-troubleshoot
description: Diagnose and fix a broken OpenText Discover (Knowledge Discovery) Kubernetes deployment - UI or API 404s from the wrong ingress controller or a missing ingress class (Traefik instead of ingress-nginx), pods stuck in ContainerCreating or Init, licence errors, NiFi OOMKilled, api-init timeouts, 401s, browser login errors (requireHttps, invalid redirect URL), a missing Admin Project, and refused entity schema migrations. A symptom to cause to fix table, with the commands to confirm each. Use when a Discover install doesn't come up or the UI or API misbehaves.
---

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

# Troubleshooting Discover

## Rules

1. **Never force-delete a pod** (`--force --grace-period=0`), and **never remove a namespace's finalizers**.
   `idol-content` and `analysis` (NiFi) have postStart hooks. A forced delete removes the pod from Kubernetes, but
   its container keeps running on the node and holding its volumes. They reappear in the next install.
2. Find the cause in the logs before changing values. Many settings only apply on the first install
   (discover-values), so a values change on a running system often does nothing.
3. Ask the user before deleting anything that holds data (volumes, the namespace).

Useful commands:
```
kubectl -n <ns> get pods
kubectl -n <ns> describe pod <pod> | tail -30            # events, probe failures, OOMKilled
kubectl -n <ns> logs <pod> [-c <container>] --tail=100   # api-0 has containers api-init and api-container
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail -20
```

## Symptoms

| Symptom | Cause | Fix |
|---|---|---|
| UI or API returns **404** (often a plain `404 page not found`, from Traefik) | the ingresses are served by a controller other than ingress-nginx, e.g. k3s's default Traefik, which ignores the chart's nginx rewrite and snippet annotations | `kubectl -n <ns> get ingress`: CLASS must be the ingress-nginx class on all 10. Install ingress-nginx and turn off Traefik (discover-install step 1), set the class everywhere (below), run the same `helm upgrade` |
| Some ingresses have no CLASS or the wrong one (`auth-ingress`, `analysis*`, `idol-*`) while `isol-ingress` is right | only `ingress.className` was set: it doesn't reach the subcharts, whose ingresses take the cluster default | set `auth.ingress.class`, `analysis.ingressClassName`, `entityIndex.{content,dah,dih}.ingress.className` too (discover-values), run the same `helm upgrade` |
| `api-0` in `CrashLoopBackOff` / `Init:CrashLoopBackOff`, api-init gets **HTTP 404** when it asks OTDS for a token | `auth-ingress` isn't served by ingress-nginx (`auth.ingress.class` unset) | as above; then `kubectl -n <ns> delete pod api-0` (normal delete) if it doesn't recover on its next restart |
| `helm install` fails: admission webhook `validate.nginx.ingress.kubernetes.io` denied the request, mentioning snippet directives being disabled or a risky annotation | ingress-nginx blocks `configuration-snippet` by default in recent versions | ask the user to allow it on the controller: `controller.allowSnippetAnnotations=true` and `controller.config.annotations-risk-level=Critical` (discover-install step 1), then re-run the install |
| ingress-nginx service `EXTERNAL-IP` stays `<pending>` (k3s) | Traefik's load balancer already holds ports 80/443 | turn off Traefik (discover-install step 1) |
| `ImagePullBackOff`, `insufficient_scope` | the cluster can't pull that image | ask the user for pullable registries/versions (discover-values, image overrides) |
| `idol-content-0` stays `ContainerCreating`, `describe` shows `PodReadyToStartContainers=False` | its postStart hook loops on `https://idol-dih:9070/a=getpid`, and DIH has no licence | set `entityIndex.licenseServerHostname` (as well as `licenseServer.hostname`), then **fresh install**: DIH keeps its first `dih.cfg` in its volume |
| content log: "failed to connect to license server" | `licenseServer.hostname` wrong or unreachable | must be a DNS name reachable from pods, port 20000 |
| api-init repeats "Waiting for license" / "Timed out waiting for license" | NiFi (`analysis`) disabled or not ready | `analysis.enabled: true`; wait for `analysis-0` |
| `analysis-0` `OOMKilled` | NiFi heap + native memory exceed the limit | `limits.memoryMi: 10240`, `jvmMemoryRatio: 0.3` |
| `analysis-0` OOMKilled and not replaced | StatefulSet waits on the dead pod | `kubectl -n <ns> delete pod analysis-0` (normal delete, not forced) |
| api-init: `URISyntaxException ://:/otdsws` | `auth.external` missing | set `auth.external.*` (discover-values) |
| api-init: "password cannot be null" | user defined with `password:` | use `passwordEnv` + `api.init.additionalSecrets` |
| API 401 for every token | token `iss` ≠ the URL the API expects | use the same nip.io auth host for `auth.external.host` and `auth.otdsws.publicHostname`, `prependPath: OTDS`; then restart `sts/api deploy/discover-ui deploy/api-schedule` |
| Browser: "issuer must use HTTPS (with TLS), or ... 'requireHttps' must be set to 'false'" | plain-HTTP OTDS | `discoverUi.requireHttps: false`, then `rollout restart deploy/discover-ui` |
| OTDS login page: invalid redirect URL | OTDS clients still have the first install's hosts | recreate the clients (discover-api-access), or fresh install |
| Logged in, but no Admin Project and the UI is unusable | `api.init.adminTeamOwner` / `globalTeamOwner` unset on the first install | set both, then **fresh install** (api-init logs "system is already initialized" otherwise) |
| api-0 stuck in `Init`, api-init: `UnsupportedEntitySchemaMigrationException` | the schema change can't be applied to existing data (for example "Cannot create required property for pre-existing entity/link") | revert the schema and restart the consumers, or fresh install with the new schema |
| After a rollback/restart, `api-0` still in `Init` with the same error | the StatefulSet doesn't replace a pod that never became ready | `kubectl -n <ns> delete pod api-0` (normal delete; safe for api-0) |
| Graph import HTTP 500, api-container log `NoHttpResponseException ... idol-dah:9060` | IDOL DAH not answering (can happen briefly after start-up) | re-run the load (it is safe to repeat); if it persists, check `idol-dah` logs |
| API 400 `invalid entity type` | type not in the deployed schema | add it to `dataEntity.customEntitySchema` (discover-values) |
| `api-schedule` restarts a few times | it waits for `api` / entity storage | normal during start-up |
| After a reboot: `analysis-0 Error`, `api-0 Unknown` | the shutdown killed them | wait about 5 minutes |

## Schema changes on a running system

api-init compares the new `dataEntity.customEntitySchema` with the one stored in the graph:

| Allowed | Refused once the graph holds data |
|---|---|
| add/remove entity types, links, entity links; add optional properties; change a description, `internal` or `isTitle` | add a `required` property to an existing type; make an optional property required; change a property's type or flags; change a link's multiplicity |

A refused change stops api-0 in `Init`. The schema is mounted with `subPath`, so after any schema change restart
all its readers: `kubectl -n <ns> rollout restart sts/api sts/analysis sts/analysis-reg deploy/api-schedule`.

## A content pod that won't terminate

If `idol-content-0` hangs in `Terminating`, its postStart hook is still running. On the node, check it and ask the
user to stop it (stopping processes may need their permission):
```
pgrep -af '[c]ontent_postStart.sh|[c]ontent.exe'
pkill -f content_postStart.sh; pkill -f 'content.exe -configfile /etc/config/idol/content.cfg'
```
Other deployments on the same node may run their own `content.exe` with a different config file. Leave those alone.
