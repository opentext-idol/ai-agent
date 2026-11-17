---
name: discover-schema-apply
description: Apply an OpenText Discover custom entity schema to a deployment and prove it is live - helm upgrade with the schema values file, restart the pods that read the schema, watch api-init accept or refuse it, compare the deployed types (GET /api/entities/types) with the schema file, and roll back a refused change. Use after discover-schema-validate passes, whenever a schema is added or changed on an install, or to check what schema a deployment is really running.
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

# Applying a Discover entity schema

Validate first (discover-schema-validate). Then pick the route.

| Situation | Route |
|---|---|
| No install yet | add the schema file as an extra `-f` to the install (discover-install), then do steps 3–4 below |
| Running install, change only **adds** entity types, link types or optional properties | steps 1–4 below |
| Running install, change adds a `required` property to an existing type, or changes/removes an existing property or a link's multiplicity | api-init will refuse it once any data exists. Do a fresh install with the new schema (discover-teardown, then discover-install), and confirm with the user first because it deletes all data |

## 1. Upgrade

Use the same values files as the install, plus the schema file, in the same order:
```
helm --kube-context <ctx> -n <ns> history discover | tail -1      # note the current revision, for a rollback
helm upgrade discover <chart> --kube-context <ctx> -n <ns> \
  -f <values.yaml> -f <secrets.yaml> -f <images.yaml> -f <schema.yaml> --timeout 20m
```

## 2. Restart the schema readers

The schema is mounted into four workloads in a way that never refreshes, and helm doesn't restart them:
```
kubectl --context <ctx> -n <ns> rollout restart sts/api sts/analysis sts/analysis-reg deploy/api-schedule
```

## 3. Watch api-init

Wait 4–7 minutes. NiFi (`analysis-0`) comes back first, then `api-0`. Check every 30 s or so:
```
kubectl --context <ctx> -n <ns> get pods | grep -E 'api|analysis'
kubectl --context <ctx> -n <ns> logs api-0 -c api-init | grep -v -E 'OBJECT1|PROPERTY1|INDEX1' | grep -E -i 'schema|exception' | tail -5
```
- **Accepted**: the log goes past "Waiting for schema initialized" to "Waiting for license" / "Waiting for init",
  and all pods return to `1/1`. "Could not resolve hostname analysis" lines while NiFi restarts are normal.
- **Refused**: `UnsupportedEntitySchemaMigrationException` (the change isn't allowed on existing data) or
  `EntitySchemaValidationException` (the schema is invalid). The exception text names the type and property.
  `api-0` stays in `Init` and the API is down. Roll back (step 5).

## 4. Prove it is live

Get a token (discover-api-access), fetch the deployed types, and compare them with the schema file:
```
curl -s -H "Authorization: Bearer $T" -H 'Isol-Tenant-Id: demo' \
  http://discover.<ns>.<ip>.nip.io/api/entities/types > types.json
python3 - <schema.yaml> types.json <<'EOF'
import json, sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
if isinstance(d, dict) and "dataEntity" in d:
    d = yaml.safe_load(d["dataEntity"]["customEntitySchema"])
live = json.load(open(sys.argv[2])); T, L = live["types"], live["linkTypes"]
TYPE = {"boolean": "boolean", "integer": "integer", "number": "float", "object": "object", "geo": "geo",
        "idolacl": "idolacl", "vector": "vector"}
def expect_type(vs):
    multi = vs.get("type") == "array"
    s = vs.get("items", {}) if multi else vs
    t = "date" if s.get("type") == "string" and s.get("format") == "date-time" else TYPE.get(s.get("type"), "string")
    return t, multi
bad = 0
def report(ok, msg):
    global bad
    bad += not ok
    print(("ok      " if ok else "PROBLEM ") + msg)
for name, ent in (d.get("entities") or {}).items():
    if name not in T:
        report(False, f"{name}: type not deployed"); continue
    for p, s in (ent.get("properties") or {}).items():
        lp = T[name]["properties"].get(p)
        if lp is None:
            report(False, f"{name}.{p}: property not deployed (or internal)"); continue
        diffs = [f"{f}={lp.get(f)}" for f in ("filterable", "sortable", "searchable", "isTitle", "required")
                 if bool(s.get(f, False)) != bool(lp.get(f))]
        t, multi = expect_type(s.get("valueSchema", {}))
        if (lp.get("type"), bool(lp.get("isMultiValue"))) != (t, multi):
            diffs.append(f"type={lp.get('type')}{'[]' if lp.get('isMultiValue') else ''}")
        report(not diffs, f"{name}.{p}" + (": deployed differs: " + ", ".join(diffs) if diffs else ""))
    for target, lts in ((ent.get("links") or {}).get("entities") or {}).items():
        missing = [lt for lt in lts if lt not in T[name].get("links", {}).get(target, [])]
        report(not missing, f"{name} -> {target}: {', '.join(lts)}" + (f" (missing: {missing})" if missing else ""))
for name, lk in (d.get("links") or {}).items():
    ll = L.get(name)
    ok = ll is not None and ll.get("multiplicity") == lk.get("multiplicity") and ll.get("category") == lk.get("category")
    report(ok, f"link {name}" + ("" if ok else f": deployed {ll and (ll.get('category'), ll.get('multiplicity'))}"))
print(f"{bad} problem(s)")
sys.exit(1 if bad else 0)
EOF
```
`0 problem(s)` means everything in the file is live as written. Multi-valued properties show `canAggregate` off in
`types.json`. That is expected: arrays can't be charted.

A "property not deployed" for a property that is in the file usually means the readers weren't restarted (step 2),
or the upgrade used different values files.

## 5. Roll back a refused change

```
helm --kube-context <ctx> -n <ns> rollback discover <revision-from-step-1>
kubectl --context <ctx> -n <ns> rollout restart sts/api sts/analysis sts/analysis-reg deploy/api-schedule
```
The stuck `api-0` is **not** replaced by the restart: a StatefulSet waits for a pod that never became ready.
Check its revision, and if it is still the old one, delete it with a normal delete. This is safe for `api-0`
because its init container only waits. Never use `--force` (see discover-troubleshoot rules):
```
kubectl --context <ctx> -n <ns> get pod api-0 -o jsonpath='{.metadata.labels.controller-revision-hash}{"\n"}'
kubectl --context <ctx> -n <ns> get sts api -o jsonpath='{.status.updateRevision}{"\n"}'   # should match
kubectl --context <ctx> -n <ns> delete pod api-0                                          # if they differ
```
Then repeat step 3: api-init should accept the old schema again and all pods return to `1/1`. Fix the schema
(discover-schema-design / discover-schema-validate). If the change really is needed, use the fresh-install route.
