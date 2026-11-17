---
name: discover-data-load
description: Load a dataset (such as an IDOL IDX export) into an OpenText Discover deployment as graph entities and links - write a small one-off transform from the source to a simple JSON-lines record format, check every record against the deployed schema with a dry run, then upload with a fixed loader that handles labels, de-duplication, batching, tokens and public access, and count what arrived. Use after the schema is live (discover-schema-apply), when asked to load, import or ingest data into Discover.
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

# Loading data into Discover

There are two parts:
1. **You write a one-off transform** from the source data to *records*, one JSON object per line.
   All the dataset-specific work goes here: which field goes where, splitting, dates, extracting.
2. **The fixed loader below** checks the records against the deployed schema and uploads them. Don't change it.

The schema must already be live (discover-schema-apply step 4) and you need the field mapping from
discover-schema-design.

## 1. The record format

One line per source document. Example:
```json
{"type": "FilmEntity", "match": ["wikipediaId"],
 "properties": {"wikipediaId": 19715, "title": "Miss Congeniality", "releaseYear": 2000, "genres": ["comedy film"],
                "originalDate": "2000-01-01T00:00:00Z"},
 "links": [
   {"type": "Director", "to": {"type": "PersonEntity", "match": ["name"], "properties": {"name": "Donald Petrie"}}},
   {"type": "SetIn", "to": {"type": "LocationEntity", "match": ["name"], "properties": {"name": "San Antonio", "title": "San Antonio"}}}]}
```
- `type`: the entity type. `properties`: property → value, exactly as named in the schema.
- `match`: properties that identify the entity. With `match`, an existing entity with the same values is reused
  instead of creating a new one. **Always give the document a `match` on a unique ID** (so a re-run creates no
  duplicates), and **always give link targets a `match`**, usually `name` or `title`, so one person is one node.
  Match properties must be `filterable` in the schema. The document's match key must be single-valued and unique:
  in the profile, `max/doc` 1 and `distinct` equal to the number of documents (e.g. a source ID, not a field
  that sometimes has two values). Places: match `LocationEntity` on its filterable `name` and also set its
  required `title` (discover-schema-design).
- `links`: `type` is the link type, `to` is the target entity (same format, without its own links), and
  `properties` holds the optional link properties. There can be only **one link of a type between the same two
  entities**, so model different roles as different link types (`SetIn`, `FilmedIn`), not one type with a label.
- Values: arrays for multi-valued properties, numbers as JSON numbers, dates as
  `YYYY-MM-DDThh:mm:ssZ`. Leave out empty values. The loader drops `null`, `""` and `[]`.

## 2. Write the transform

Save this as `transform.py` next to your schema. Edit **only** `to_record`, using the field mapping:
```python
import datetime, json, re, sys
def idx_docs(path):                      # yields {field: [values]}; also #REFERENCE, #TITLE, #CONTENT
    doc, body = None, False
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("#DREREFERENCE"): doc, body = {"#REFERENCE": [line[14:]]}, False
        elif line.startswith("#DRETITLE"): doc["#TITLE"] = [line[10:]]
        elif line.startswith("#DRECONTENT"): body = True; doc["#CONTENT"] = [""]
        elif line.startswith("#DREENDDOC"): yield doc; body = False
        elif line.startswith("#DREFIELD"):
            m = re.match(r'#DREFIELD ([^=]+)="(.*)"\s*$', line)
            if m: doc.setdefault(m.group(1), []).append(m.group(2))
        elif body: doc["#CONTENT"][0] += line + "\n"

def first(d, f): return (d.get(f) or [None])[0]
def all_(d, *fs): return sorted({v.strip() for f in fs for x in d.get(f, []) for v in x.split("|") if v.strip()})
def year(s):                              # "01/01/2001" or "2001-..." -> 2001
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b", s or ""); return int(m.group(1)) if m else None
def iso_date(s, order="dmy"):             # "31/12/2001" -> "2001-12-31T00:00:00Z"; order "mdy" for US dates
    if re.match(r"\d{4}-\d\d-\d\d", s or ""): s = f"{s[8:10]}/{s[5:7]}/{s[:4]}"; order = "dmy"
    m = re.match(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", s or "")
    if not m: return None
    a, b, y = map(int, m.groups()); d, mo = (a, b) if order == "dmy" else (b, a)
    try: return datetime.date(y, mo, d).isoformat() + "T00:00:00Z"
    except ValueError: return None          # not a real date (e.g. 00/00/2001): fall back, e.g. to Jan 1 of the year
def target(type_, key, value, **extra): return {"type": type_, "match": [key], "properties": {key: value, **extra}}

def to_record(d):                         # EDIT THIS: one source document -> one record
    rec = {"type": "FilmEntity", "match": ["wikipediaId"], "properties": {   # match: a unique, single-valued ID
        "wikipediaId": int(first(d, "wikipedia_id")),
        "title": first(d, "#TITLE"),
        "releaseYear": year(first(d, "film_date")),
        "genres": all_(d, "film_genre"),
    }, "links": []}
    for name in all_(d, "film_director"):
        rec["links"].append({"type": "Director", "to": target("PersonEntity", "name", name)})
    return rec

for d in idx_docs(sys.argv[1]):
    r = to_record(d)
    if r: print(json.dumps(r, ensure_ascii=False))
```
```
python3 transform.py <FILE.idx> > records.jsonl
wc -l records.jsonl; head -c 1500 records.jsonl     # one line per document? values look right?
```
Return `None` from `to_record` to skip a document, for example one without the ID you match on.
Dates: decide the day/month order from the profile (any value whose first part is above 12 means day first) and
use `iso_date`. Exports often contain impossible dates like `00/00/2001`; `iso_date` returns `None` for those, so
fall back (for example `iso_date(f"01/01/{year(s)}")`) or leave the property out.

## 3. Dry run, then load

(The loader is long: you can save the code between `<<'EOF'` and `EOF` to `loader.py` and run
`python3 loader.py records.jsonl --dry-run` instead.)

Set the connection (token details as in discover-api-access; don't print the password):
```
export DISCOVER_URL=http://discover.<ns>.<ip>.nip.io DISCOVER_AUTH_URL=http://auth.<ns>.<ip>.nip.io/OTDS/otdsws
export DISCOVER_USERNAME=demo_user DISCOVER_PASSWORD=<from secrets.yaml> DISCOVER_CLIENT_SECRET=<auth.apiClientSecret>
```
Run the loader with `--dry-run` first. It checks every record against the deployed schema and sends nothing.
Fix the transform until it reports no problems, then run it again without `--dry-run`:
```
python3 - records.jsonl --dry-run <<'EOF'
import collections, datetime, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
path, dry = sys.argv[1], "--dry-run" in sys.argv
API, AUTH = os.environ["DISCOVER_URL"].rstrip("/") + "/api", os.environ["DISCOVER_AUTH_URL"].rstrip("/")
MAX_ENTITIES = int(os.environ.get("MAX_ENTITIES", "1000"))      # per request; lower it on HTTP 413
tok = [None, 0.0]
def token():
    if tok[0] is None or time.time() - tok[1] > 200:
        form = urllib.parse.urlencode({"grant_type": "password", "client_id": os.environ.get("DISCOVER_CLIENT_ID", "discover_api"),
            "client_secret": os.environ["DISCOVER_CLIENT_SECRET"], "username": os.environ["DISCOVER_USERNAME"],
            "password": os.environ["DISCOVER_PASSWORD"]}).encode()
        with urllib.request.urlopen(urllib.request.Request(AUTH + "/oauth2/token", data=form)) as r:
            tok[0], tok[1] = json.load(r)["access_token"], time.time()
    return tok[0]
def api(method, p, body=None):
    req = urllib.request.Request(API + p, method=method, data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token(), "Isol-Tenant-Id": os.environ.get("DISCOVER_TENANT", "demo"),
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {method} {p}: {e.read().decode(errors='replace')[:3000]}")

live = api("GET", "/entities/types"); T, L = live["types"], live["linkTypes"]
PY = {"string": str, "integer": int, "float": (int, float), "boolean": bool, "date": str, "object": dict, "geo": dict}
DATE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:\d\d)$")
AUTO = {"id", "typeId", "dateCreated", "dateModified"}
problems = []
def is_date(x):
    try: return bool(DATE.match(x)) and bool(datetime.datetime.fromisoformat(x.replace("Z", "+00:00")))
    except ValueError: return False
def check_props(where, owner, defs, props, required=True):
    for k, v in props.items():
        d = defs.get(k)
        if d is None: problems.append(f"{where}: {owner} has no property '{k}'"); continue
        multi = bool(d.get("isMultiValue"))
        if multi != isinstance(v, list):
            problems.append(f"{where}: {owner}.{k} must be {'a list' if multi else 'a single value'}"); continue
        for x in (v if multi else [v]):
            t = d.get("type")
            if t in PY and (not isinstance(x, PY[t]) or (t in ("integer", "float") and isinstance(x, bool))):
                problems.append(f"{where}: {owner}.{k} expects {t}, got {x!r:.60}")
            elif t == "date" and not is_date(x):
                problems.append(f"{where}: {owner}.{k} needs a date like 2001-01-01T00:00:00Z, got {x!r:.40}")
    if required:
        for k, d in defs.items():
            if d.get("required") and k not in props and k not in AUTO:
                problems.append(f"{where}: {owner}.{k} is required")
def clean(e):
    e["properties"] = {k: v for k, v in (e.get("properties") or {}).items() if v not in (None, "", [])}
def check_entity(where, e):
    if e.get("type") not in T: problems.append(f"{where}: unknown entity type {e.get('type')!r}"); return False
    clean(e); check_props(where, e["type"], T[e["type"]]["properties"], e["properties"])
    for m in e.get("match") or []:
        if m not in e["properties"]: problems.append(f"{where}: match property '{m}' has no value")
        elif not T[e["type"]]["properties"].get(m, {}).get("filterable"):
            problems.append(f"{where}: can't match on {e['type']}.{m}: it isn't filterable (extend the type with a "
                            "filterable property, e.g. name, and match on that - discover-schema-design)")
    return True

records = []
for n, line in enumerate(open(path, encoding="utf-8"), 1):
    if not line.strip(): continue
    try: rec = json.loads(line)
    except ValueError as e: problems.append(f"line {n}: not JSON ({e})"); continue
    records.append(rec); where = f"line {n}"
    if not check_entity(where, rec): continue
    if not rec.get("match"): problems.append(f"{where}: no 'match' - a re-run would duplicate this {rec['type']}")
    seen = {}
    for lk in rec.get("links") or []:
        to, lt = lk.get("to") or {}, lk.get("type")
        key = (lt, to.get("type"), json.dumps([(to.get("properties") or {}).get(m) for m in to.get("match") or []]))
        lp = json.dumps(lk.get("properties") or {}, sort_keys=True)
        if key in seen and seen[key] != lp:
            problems.append(f"{where}: two {lt} links to the same {to.get('type')} with different properties - only one "
                            "link per pair and type is kept, so use separate link types per role or merge them")
        seen[key] = lp
        if lt not in L: problems.append(f"{where}: unknown link type {lt!r}"); continue
        if not check_entity(f"{where} -> {lt}", to): continue
        if not to.get("match"): problems.append(f"{where} -> {lt}: target needs 'match' or it is duplicated per document")
        if lt not in T[rec["type"]].get("links", {}).get(to["type"], []):
            problems.append(f"{where}: the schema doesn't allow {rec['type']} -{lt}-> {to['type']}")
        check_props(f"{where} -> {lt}", "link " + lt, L[lt].get("properties") or {}, lk.get("properties") or {}, False)
if problems:
    for p in problems[:40]: print("PROBLEM", p)
    sys.exit(f"{len(problems)} problem(s) in {len(records)} records - nothing was sent")
nlinks = collections.Counter(lk["type"] for r in records for lk in r.get("links") or [])
print(f"{len(records)} records OK: {dict(collections.Counter(r['type'] for r in records))}; links: {dict(nlinks)}")
if dry: sys.exit(0)

counts, batch, sent = collections.Counter(), None, 0
def new_batch(): return {"entities": {}, "links": [], "access": {"public": True}, "_keys": {}, "_links": set()}
def label(b, e):
    key = (e["type"], json.dumps([e["properties"][m] for m in e["match"]])) if e.get("match") else None
    if key in b["_keys"]: return b["_keys"][key]
    lab = f"e{len(b['entities'])}"
    create = {"typeId": e["type"], "properties": e["properties"]}
    b["entities"][lab] = ({"importType": "FindOrCreate", "find": {"matchProperties": e["match"]}, "create": create}
                          if key else {"importType": "Create", "create": create})
    if key: b["_keys"][key] = lab
    return lab
def flush(b):
    global sent
    if not b["entities"]: return
    body = {k: v for k, v in b.items() if not k.startswith("_")}
    res = api("POST", "/entities/graph", body)
    for lab, r in res.get("entities", {}).items():
        counts[(b["entities"][lab]["create"]["typeId"], r.get("result"))] += 1
    sent += 1; print(f"batch {sent}: {len(b['entities'])} entities, {len(b['links'])} links", flush=True)
batch = new_batch()
for rec in records:
    src = label(batch, rec)
    for lk in rec.get("links") or []:
        tgt = label(batch, lk["to"])
        if (src, tgt, lk["type"]) in batch["_links"]: continue
        batch["_links"].add((src, tgt, lk["type"]))
        link = {"sourceEntityLabel": src, "targetEntityLabel": tgt, "typeId": lk["type"], "existsAction": "succeed"}
        if lk.get("properties"): link["properties"] = {k: v for k, v in lk["properties"].items() if v not in (None, "", [])}
        batch["links"].append(link)
    if len(batch["entities"]) >= MAX_ENTITIES: flush(batch); batch = new_batch()
flush(batch)
for (t, r), c in sorted(counts.items()): print(f"{t:30} {r:8} {c}")
EOF
```
- The upload sends batches one after another, and every entity is `public` (visible to all users).
- Each request is all-or-nothing: a failed batch writes nothing.
- **It is safe to re-run** after a failure. Matched entities are found again rather than duplicated, and existing
  links are skipped. Found entities are **not** updated: to change loaded values, delete the data or reinstall.
- On `HTTP 413` set `MAX_ENTITIES=300` and re-run. On `HTTP 400` the message names the label and property:
  look at that record in `records.jsonl`.
- On `HTTP 500` look for the cause in `kubectl -n <ns> logs api-0 -c api-container | tail -50`. A one-off
  `NoHttpResponseException ... idol-dah` right after start-up is transient: re-run the same command.

## 4. Check what arrived

The load summary prints `created` and `found` counts per type. `found` only counts entities matched from an
earlier batch or an earlier load. Repeats inside one batch (the same person in two films) are merged before
sending and not counted, so `created` + `found` is less than the number of records plus link targets. That is
expected, not lost data. Cross-check a type in the API (`T` is a token from discover-api-access):
```
curl -s -X POST -H "Authorization: Bearer $T" -H 'Isol-Tenant-Id: demo' -H 'Content-Type: application/json' \
  http://discover.<ns>.<ip>.nip.io/api/entities/ids -d '{"filters": ["typeId==FilmEntity and maxResults==10000"]}' \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["traversalSteps"][0]["entities"]))'
```
Then check the **graph**, not just the counts. Follow links from a well-known entity and compare with the source
data. For example, the films a person directed and everyone in their cast:
```
curl -s -X POST -H "Authorization: Bearer $T" -H 'Isol-Tenant-Id: demo' -H 'Content-Type: application/json' \
  http://discover.<ns>.<ip>.nip.io/api/entities/ids -d '{"filters": [
    "typeId==PersonEntity and properties:PersonEntity:name==\"Steven Spielberg\" and maxResults==5",
    "link==Director:out and maxResults==100",
    "link==CastMember:in and maxResults==2000"]}' \
  | python3 -c 'import json,sys; print([len(s["entities"]) for s in json.load(sys.stdin)["traversalSteps"]])'
```
- Properties are named `properties:<Type>:<property>` in filters.
- Direction: from the type that declares the link (the film) to its targets (people, places) use `link==X:in`.
  From a target back to the films use `link==X:out`. For example, the films set in London:
  `"typeId==LocationEntity and properties:LocationEntity:name==\"London\" and maxResults==5", "link==SetIn:out and maxResults==1000"`.
- `maxResults` can be at most 10000 per step.
- `[1, 5, 164]` means one person, 5 films, 164 cast members. `0` in the first place means the match failed.
  Duplicated people show up as a number above 1 there.

Then tell the user to look in the UI (log in as `demo_user`), for example by searching for a well-known title.
