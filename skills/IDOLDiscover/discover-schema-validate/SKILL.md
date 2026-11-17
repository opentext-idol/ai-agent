---
name: discover-schema-validate
description: Validate an OpenText Discover custom entity schema (the YAML in dataEntity.customEntitySchema, or a values file holding it) before deploying it - structure, property flags and types, names, references to entity and link types in the chart and the API's built-in schema, extensions of built-in types, and demo problems such as types the UI won't show. Use after writing or changing an entity schema, before helm install/upgrade, or when api-init rejects a schema.
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

# Validating a Discover entity schema

Run this after every edit to a custom entity schema, and fix every ERROR before deploying. A schema the API
rejects stops `api-0` in `Init`. Some mistakes can't be fixed later without a fresh install (discover-values,
"First-install-only settings").

## Run the check

Needs `python3` with PyYAML and `jsonschema` 4.x (`pip install pyyaml jsonschema` if missing). Pass:
1. the path of `entity-schema.schema.json`, which is in this skill's own folder (next to this `SKILL.md`);
2. the schema file: either the bare schema YAML or a values file containing `dataEntity.customEntitySchema`;
3. the discover chart (`.tgz` or the unpacked folder);
4. optionally, a running deployment's types (step "With a running deployment" below).

```
python3 - <SKILL_DIR>/entity-schema.schema.json <SCHEMA_OR_VALUES.yaml> <CHART.tgz-or-dir> [types.json] <<'EOF'
import glob, json, os, sys, tarfile, yaml, jsonschema
if len(sys.argv) < 4:
    sys.exit("usage: <entity-schema.schema.json> <SCHEMA_OR_VALUES.yaml> <CHART.tgz-or-dir> [types.json]")
SKILL, custom_path, chart = sys.argv[1], sys.argv[2], sys.argv[3]
if not os.path.isfile(SKILL):
    sys.exit("ERROR can't find " + SKILL + " - pass the entity-schema.schema.json from this skill's folder")
types_json = sys.argv[4] if len(sys.argv) > 4 else None
errors, warnings = [], []

d = yaml.safe_load(open(custom_path))
if isinstance(d, dict) and "dataEntity" in d:
    d = yaml.safe_load(d["dataEntity"]["customEntitySchema"])

# 1. structure (JSON Schema)
v = jsonschema.Draft202012Validator(json.load(open(SKILL)))
for e in sorted(v.iter_errors(d), key=lambda e: list(e.absolute_path)):
    errors.append(f"structure at {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message[:300]}")
if errors:
    print("\n".join("ERROR " + x for x in errors)); sys.exit(1)

# 2. what already exists: API built-in schema (26.4) + the chart's schema [+ a running deployment]
NON_EXT = set("AccessProxyEntity AccessRequestEntity AnalysisJobEntity ClothingResultEntity EductionResultEntity FaceDetectResultEntity FaceRecognitionResultEntity FaceRegionEntity LicenseEntity LicenseExpiryEntity LiveProcessorEntity NotificationEntity ObjectClassRecognitionResultEntity PublicEntity ResultGroupEntity ScheduledTaskEntity ScheduledTaskFailureEntity SchemaInitializationEntity SpeechToTextResultEntity SystemInitializationEntity SystemStatisticsEntity TrackedRegionEntity TrainedFaceEntity UserEntity VehicleDetectResultEntity".split())
EXT = dict((k, set(filter(None, v.split(",")))) for k, v in (x.split("=") for x in "FileEntity=dataRef,dataType,description,graphicContent,mimeType,originalFilename,recordingEndDate,recordingStartDate,sizeBytes,title FileMetadataEntity=metadata,mimeType LicensePlateEntity=licensePlate,subPlate,vehicleType PersonEntity= StoredGraphEntity=clusters,initialCluster,traversalFilter StreamableMediaClipEntity=clipType,duration,startTime StreamableMediaEntity=duration TeamEntity=title TrainedFaceDatabaseEntity=title TrainedFaceIdentityEntity= VideoStreamInputEntity=excludeEncodingAudio,streamFormat,url VideoStreamOutputEntity=maxResultGroupDurationHours,maxResultGroups,title WatchlistEntity=checkedAuditEventDate,dateChecked,title WatchlistRulesEntity=description,title,trackedLinks,trackedProperties WatchlistUpdateEntity=date,linkDirection,linkTypeId,operation,properties".split()))
links = set("AccessibleBy AnalysisJobTarget Attached AttachedMedia BestDetectionImage BestDetectionLocation ClippedFrom ClothingResult CombinedDetectionLocation Contains CreatedBy DerivedFrom DetectedIn DirectlyAccessibleBy Identity Linked LiveResult Media MemberOfTeam Notifies OwnerOfTeam Preview Processing Proxy ProxyFor Received RecognisedIdentity RecognitionResult Requestor Result Source Subject Track TranscodedFrom UpgradeJob WatchRules Watched".split())
base_props = set("id typeId dateCreated dateModified expiryDate expiryConfirmed idolAcl".split())
types = {t: {"props": None, "extensible": False} for t in NON_EXT}   # props None = unknown
types.update({t: {"props": set(p), "extensible": True} for t, p in EXT.items()})

if chart.endswith(".tgz"):
    with tarfile.open(chart) as t:
        layers = [yaml.safe_load(t.extractfile(m)) for m in t.getmembers() if "/resources/data-entity/" in m.name and m.name.endswith(".yaml")]
else:
    layers = [yaml.safe_load(open(f)) for f in sorted(glob.glob(os.path.join(chart, "resources/data-entity/*.yaml")))]
if not layers:
    sys.exit("ERROR no resources/data-entity/*.yaml found in the chart")
for layer in layers:
    base_props |= set(((layer.get("baseEntity") or {}).get("properties") or {}))
    links |= set(layer.get("links") or {})
    for name, ent in (layer.get("entities") or {}).items():
        props = set(ent.get("properties") or {})
        if name in types:
            if types[name]["props"] is not None: types[name]["props"] |= props
        else:
            types[name] = {"props": props, "extensible": ent.get("extensible", True) is not False}

deployed, deployed_links = set(), set()   # only on the deployment: from an earlier custom schema
redeployed = set()
if types_json:
    tj = json.load(open(types_json))
    for name, ent in tj["types"].items():
        if name not in types:
            deployed.add(name)
            types[name] = {"props": set(), "extensible": None}
        types[name]["deployed"] = set(ent.get("properties") or {}) - base_props
    deployed_links = set(tj["linkTypes"]) - links

# 3. the custom file against what exists
ents = d.get("entities") or {}
new_links = d.get("links") or {}
cbase = set(((d.get("baseEntity") or {}).get("properties") or {}))
for p in cbase & base_props:
    errors.append(f"baseEntity: property '{p}' already exists on the base entity")
all_base = base_props | cbase
for name, ent in ents.items():
    props = ent.get("properties") or {}
    if name in deployed:
        pass                                        # reported once below
    elif name in types and not ent.get("extension"):
        errors.append(f"{name}: type already exists: set 'extension: true' and only add new properties/links")
    elif name not in types and ent.get("extension"):
        errors.append(f"{name}: 'extension: true' but no such type exists to extend")
    for p in set(props) & all_base:
        errors.append(f"{name}.{p}: property already exists on the base entity")
    if ent.get("extension") and name in types:
        known = types[name]["props"] or set()
        for p in set(props) & known:
            errors.append(f"{name}.{p}: property already exists on {name}")
        for p in (set(props) & types[name].get("deployed", set())) - known:
            if types[name]["props"] is not None:      # built-in properties known: so this came from a custom schema
                redeployed.add(f"{name}.{p}")
            else:
                warnings.append(f"{name}.{p}: already on the deployment - fine if an earlier custom schema added it, "
                                "an ERROR if it is built in")
    if ent.get("extension") and name in types:
        req = [p for p, s in props.items() if s.get("required")]
        if req and types[name]["extensible"] is False:
            errors.append(f"{name}: is not extensible, so it can't get required properties: {req}")
        elif req:
            warnings.append(f"{name}: required properties {req} on an existing type only work on a FIRST install")
    for p, s in props.items():
        for vp in s.get("vectorProperties") or []:
            if vp not in props:
                errors.append(f"{name}.{p}: vectorProperties names unknown property '{vp}'")
        if s.get("vectorModelId"):
            warnings.append(f"{name}.{p}: vectorModelId '{s['vectorModelId']}' must exist in the entity vector config")
    # demo checks for new types
    if not ent.get("extension") and name not in deployed:
        if ent.get("category") not in ("Entity", "Document"):
            warnings.append(f"{name}: category '{ent.get('category')}' - the UI only offers Entity/Document types in the query builder")
        if not any(s.get("isTitle") for s in props.values()):
            warnings.append(f"{name}: no isTitle property - the UI uses it to label entities")
        if not any(s.get("filterable") for s in props.values()):
            warnings.append(f"{name}: no filterable property - nothing to filter on in the UI")
        if not name.endswith("Entity"):
            warnings.append(f"{name}: by convention entity type IDs end in 'Entity' (the UI strips it for display)")
linkers = dict(ents, baseEntity=d.get("baseEntity") or {})
for name, ent in linkers.items():
    lk = ent.get("links") or {}
    for target, lts in (lk.get("entities") or {}).items():
        if target not in types and target not in ents:
            errors.append(f"{name}.links.entities: unknown target entity type '{target}'")
        for lt in lts:
            if lt not in links and lt not in deployed_links and lt not in new_links:
                errors.append(f"{name}.links.entities.{target}: unknown link type '{lt}'")
    for lt in lk.get("baseEntities") or []:
        if lt not in links and lt not in deployed_links and lt not in new_links:
            errors.append(f"{name}.links.baseEntities: unknown link type '{lt}'")
for name, l in new_links.items():
    if name in links:
        errors.append(f"links.{name}: link type already exists (link types can't be redefined or extended)")
    if l.get("category") not in ("Entity", "Document", "General"):
        warnings.append(f"links.{name}: category '{l.get('category')}' - the UI only offers Entity/Document/General links")
used = {lt for e in linkers.values() for lts in ((e.get("links") or {}).get("entities") or {}).values() for lt in lts}
used |= {lt for e in linkers.values() for lt in ((e.get("links") or {}).get("baseEntities") or [])}
for name in set(new_links) - used:
    warnings.append(f"links.{name}: defined but no entity type allows it (add it under some type's links.entities)")

again = sorted((set(ents) & deployed) | (set(new_links) & deployed_links) | redeployed)
if again:
    print(f"INFO  already on the deployment (from this or an earlier custom schema): {', '.join(again)}. "
          "Changes to these must follow 'Schema changes on a running system' in discover-troubleshoot.")
for x in errors: print("ERROR", x)
for x in warnings: print("WARN ", x)
print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(1 if errors else 0)
EOF
```

`<SKILL_DIR>` is this skill's folder, wherever it is installed. Exit code 0 means no errors.

## Reading the result

- **ERROR `structure at <path>`**: the file breaks a rule of the format. The message says which: a misspelt key, a
  flag on the wrong type, a `1` in a name, a missing `category` or `multiplicity`, and so on. Fix it at that path.
- **ERROR on references**: a link or target type that doesn't exist, a built-in type redefined without
  `extension: true`, or a property that already exists.
- **WARN**: it will deploy, but check it's what you want. Category and `isTitle` warnings usually mean the type
  won't show up properly in the UI.

Common fixes:

| Want | Write |
|---|---|
| a full-text field (plot, body) | `valueSchema: {type: string}, searchable: true` (not filterable) |
| a facet / filter (genre, country) | `valueSchema: {type: string}, filterable: true`; multi-valued: `{type: array, items: {type: string}}` |
| a date | `valueSchema: {type: string, format: date-time}, filterable: true, sortable: true` |
| a number to chart | `valueSchema: {type: integer}` (or `number`), `filterable: true` (`canAggregate` defaults on) |
| the display name | one string property with `isTitle: true` (usually also `filterable` and `sortable`) |
| extend a built-in type | `extension: true`, no `category`, only new properties |

## With a running deployment

Use the deployment's own types instead of the built-in list. They are more accurate, and include an
earlier custom schema. Fetch them with a token (discover-api-access) and pass the file as the last argument:
```
curl -s -H "Authorization: Bearer $T" -H 'Isol-Tenant-Id: demo' \
  http://discover.<ns>.<ip>.nip.io/api/entities/types > types.json
```
Changing the schema of a system that already holds data has extra limits (discover-troubleshoot, "Schema changes
on a running system"). A clean check here doesn't guarantee the change can be applied in place.
