---
name: discover-schema-design
description: Design an OpenText Discover entity schema (graph model) from a dataset such as an IDOL IDX export - profile the fields, decide what becomes an entity, a link, a filter, searchable text or nothing, reuse Discover's built-in types (PersonEntity, LocationEntity, OrganizationEntity), and write the dataEntity.customEntitySchema YAML plus a field mapping for loading. Use when asked to make a schema, model data for Discover, or turn an IDX/CSV/JSON dataset into a Discover demo.
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

# Designing a Discover entity schema

Discover is a graph. A good demo schema turns the **things that recur across documents** (people, organisations,
places) into entities, and the **relationships** between them into links, so the user can ask "who worked with
whom", "what connects these", "where". Everything else becomes filters or searchable text. There is no single right
answer. It depends on the data and on what the user wants to explore, so make the decisions explicit and show them
to the user.

## 1. Profile the data

For an IDX file, run this (prints one row per field: % of documents, max values per document, distinct values,
average length, a type guess, examples):

```
python3 - <FILE.idx> <<'EOF'
import re, sys, collections
docs, cur, body = [], None, False
fre = re.compile(r'^#DREFIELD ([^=]+)="(.*)"\s*$')
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.rstrip("\n")
    if line.startswith("#DREREFERENCE"): cur = collections.defaultdict(list); cur["#REFERENCE"].append(line[14:]); body = False
    elif line.startswith("#DRETITLE"): cur["#TITLE"].append(line[10:])
    elif line.startswith("#DRECONTENT"): body = True; cur["#CONTENT"].append("")
    elif line.startswith("#DREENDDOC"): docs.append(cur); body = False
    elif line.startswith("#DREFIELD"):
        m = fre.match(line)
        if m: cur[m.group(1)].append(m.group(2))
    elif body and cur is not None: cur["#CONTENT"][-1] += line + " "
st = collections.defaultdict(lambda: [0, 0, collections.Counter(), 0])
for d in docs:
    for k, vs in d.items():
        s = st[k]; s[0] += 1; s[1] = max(s[1], len(vs)); s[3] += sum(map(len, vs))
        for v in vs: s[2][v[:100]] += 1
def kind(vs):
    if all(re.fullmatch(r"-?\d+", v) for v in vs): return "int"
    if all(re.fullmatch(r"-?\d+\.?\d*", v) for v in vs): return "num"
    if all(re.fullmatch(r"\d{4}-\d\d-\d\d[T ].*", v) for v in vs): return "date"
    return "str|" if any("|" in v for v in list(vs)[:200]) else "str"
print(len(docs), "documents\nfield                          docs% max/doc distinct avglen kind examples")
for k, s in sorted(st.items(), key=lambda kv: -kv[1][0]):
    print(f"{k[:30]:30} {100*s[0]//len(docs):5} {s[1]:7} {len(s[2]):8} {s[3]//max(1,sum(s[2].values())):6} {kind(s[2]):4} "
          + " | ".join(v for v, _ in s[2].most_common(3))[:100])
EOF
```
For CSV or JSON, compute the same columns yourself. Look at a few whole documents too (`head -80 FILE.idx`).

## 2. Ask what the demo is for

Before choosing, ask the user (or propose and confirm) **2–4 questions the demo should answer**, for example
"which actors work with the same directors?", "where are these films set vs. shot?". Every entity and link should
serve one of them. If the user has no view, propose questions that follow from the recurring names in the profile.

## 3. Decide what each field becomes

| The field looks like | Make it | Why |
|---|---|---|
| Names that recur across documents: people, organisations, places (many distinct values, often several per document) | an **entity type** + a **link type** from the document's type | this is the graph. One entity per real-world thing |
| The same kind of thing in several fields (director, cast, producer) | **one** entity type, **one link type per field** (the role) | a person who directs and acts is one node |
| A small set of categories used to narrow results (genre, country, status; up to a few hundred distinct values) | `filterable` property, an array if several per document | filters/facets, not graph nodes |
| ...and you want to chart it | also a single-valued copy (e.g. `primaryGenre`) with `filterable: true, canAggregate: true` | arrays can't be aggregated, and a string is only chartable with `canAggregate: true` set. It can't be switched on later without a fresh install |
| Long text (summary, body, plot) | `searchable` string, one per field | full-text search. Searchable can't also be filterable |
| Numbers and years | `integer`/`number`, `filterable` + `sortable` | ranges and charts (`canAggregate` turns on by itself for numbers and dates, not for strings) |
| Dates | `string` with `format: date-time`, `filterable` + `sortable`. Also set the main one as `originalDate` when loading: it is a base property every entity type already has, so don't add it to the schema | timelines. Convert to ISO 8601 when loading. Check day/month order: look for values with a part above 12 |
| Identifiers (IMDb ID, case number) | `filterable` string | exact lookup. To use one as the loader's match key it must have `max/doc` 1 and `distinct` = number of documents in the profile (IMDb IDs sometimes have two per film) |
| `a|b|c` in one value | an array property; split on load | |
| Free text hiding structure ("Films set in London", "Born in Paris") | extract entities from it when loading. Places: the built-in `LocationEntity`, extended with a filterable `name`, one link type per role (section 4) | often the best demo material |
| Constant values, ingest metadata (sizes, internal IDs, modified dates) | leave it out | noise |

Every entity type needs one string property with `isTitle: true` (its display name). Every type that is a link
target (people, organisations, places) also needs a **filterable** property that identifies it, usually that same
`name`. The loader matches on it so that each thing is one node. Searchable properties can't be matched.

## 4. Reuse what Discover already has

- **People**: extend the built-in `PersonEntity` (UI person icon). Add a `name` property:
  `PersonEntity: {extension: true, properties: {name: {valueSchema: {type: string}, isTitle: true, filterable: true, sortable: true}}}`.
- **Places**: use the built-in `LocationEntity` (UI pin icon). Its `title` is **required** but searchable, so the
  loader can't match on it. Extend it with a filterable `name`, and when loading set **both** `name` and `title`
  to the place name:
  `LocationEntity: {extension: true, properties: {name: {valueSchema: {type: string, maxLength: 300}, filterable: true, sortable: true}}}`.
  Link to places with one link type per role, like people (`FilmEntity: {links: {entities: {LocationEntity: [SetIn, FilmedIn]}}}`
  plus `SetIn` / `FilmedIn` under `links:`). Don't use the built-in `Location` link with a label for several roles: only
  one link of a type can exist between two entities, so "set in" and "filmed in" the same city would collide.
- **Organisations**: call the type `OrganizationEntity` (the UI has an icon for that ID). It isn't built in, so
  define it with `category: Entity`.
- **Icons**: the UI picks an icon from the type ID and only knows the built-in ones (`PersonEntity`,
  `LocationEntity`, `OrganizationEntity`, `DocumentEntity`, ...). The schema has no icon or display setting, so
  every other type (e.g. `FilmEntity`) shows a "?" in the Connectivity view. Reuse the IDs above wherever the data
  really is people, places or organisations, and tell the user when you propose the schema which types will show "?".
  Don't force data into a built-in type just to get an icon.
- An extension (`extension: true`) has no `category` and only **adds** properties. Never redefine a built-in
  property, and never make an added property `required` (it can't be applied to a running system).

## 5. Write it

Naming and structure rules:
- type IDs `UpperCamelCase` ending in `Entity`; link IDs `UpperCamelCase`, named after the target's role
  (`Director`, `CastMember`); properties `lowerCamelCase`. **No digit `1` in any name.**
- `category: Entity` for new entity types (`Document` only for file-like documents), `Entity` or `General` for links.
  Other categories are hidden in the UI.
- links are declared on the source type: `links: {entities: {PersonEntity: [Director, CastMember]}}`, and each link
  type under `links:` with a `category` and a `multiplicity` (`many-to-many` unless it really is one-sided).

Skeleton (put it in a values file and pass it to helm as an extra `-f`):
```yaml
dataEntity:
  customEntitySchema: |
    entities:
      FilmEntity:
        description: A film
        category: Entity
        properties:
          title: {valueSchema: {type: string, maxLength: 300}, isTitle: true, filterable: true, sortable: true}
          summary: {valueSchema: {type: string}, searchable: true}
          releaseYear: {valueSchema: {type: integer}, filterable: true, sortable: true}
          genres: {valueSchema: {type: array, items: {type: string}}, filterable: true}
        links:
          entities:
            PersonEntity: [Director, CastMember]
      PersonEntity:
        extension: true
        properties:
          name: {valueSchema: {type: string, maxLength: 300}, isTitle: true, filterable: true, sortable: true}
    links:
      Director: {description: Directed the film, category: Entity, multiplicity: many-to-many}
      CastMember: {description: Appears in the film, category: Entity, multiplicity: many-to-many}
```
Put a short comment block at the top of the file explaining the design (what is an entity and why, what was left
out). YAML anchors under `components:` are allowed for repeated property definitions.

## 6. Validate, then record the mapping

1. Run discover-schema-validate, and fix every ERROR and every warning you didn't intend.
2. Show the user the design: entity types, link types, and one line per source field saying where it goes
   (`film_cast → CastMember link → PersonEntity.name`, `film_genre → FilmEntity.genres`, `content_length → dropped`).
   Keep this mapping next to the schema. Loading the data needs it.
3. Apply it and prove it is live with discover-schema-apply (first install or upgrade, restart, check api-init,
   compare `/api/entities/types` with the file).
