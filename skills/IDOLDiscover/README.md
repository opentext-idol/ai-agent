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

# IDOL Discover skills

Nine agent skills for standing up a *demo* of OpenText Discover (Knowledge Discovery) on a small
Kubernetes cluster from the discover Helm chart: three to install it, four to design, check, apply and
load an entity schema for your own dataset, and two to fix or remove a deployment.

### Deployment

| Skill | Purpose |
|---|---|
| [`discover-values`](discover-values/SKILL.md) | Write the Helm values file - licence, hostnames, ingress class, auth and users, team owners, NiFi, storage, images and schema - and list the settings that only take effect on the first install. |
| [`discover-install`](discover-install/SKILL.md) | Check the cluster, install with Helm, wait for start-up, and verify the UI, OTDS login and API. |
| [`discover-api-access`](discover-api-access/SKILL.md) | Get a token with curl, call the Discover API, and inspect OTDS clients and users. |

### Entity schema and data

| Skill | Purpose |
|---|---|
| [`discover-schema-design`](discover-schema-design/SKILL.md) | Turn a dataset (such as an IDX export) into an entity schema - profile the fields, decide what becomes an entity, a link, a filter or searchable text, reuse the built-in types, and map the fields. |
| [`discover-schema-validate`](discover-schema-validate/SKILL.md) | Check a custom entity schema before deploying it - structure, flags, names, references and UI visibility. |
| [`discover-schema-apply`](discover-schema-apply/SKILL.md) | Apply a schema to an install, watch api-init accept it, prove it is live, and roll back a refusal. |
| [`discover-data-load`](discover-data-load/SKILL.md) | Load a dataset - a one-off transform to JSON-lines records, a dry run against the live schema, a safe-to-re-run loader, and graph checks. |

### Operations

| Skill | Purpose |
|---|---|
| [`discover-troubleshoot`](discover-troubleshoot/SKILL.md) | Symptom → cause → fix for a deployment that doesn't come up or misbehaves. |
| [`discover-teardown`](discover-teardown/SKILL.md) | Remove an install completely - release, volumes and namespace - without forcing anything. |

Each skill is a directory holding a `SKILL.md` and any files it references. The skills name each
other where one hands over to another, so install them as a set. For a new deployment the usual
order is `discover-values` → (`discover-schema-design` → `discover-schema-validate`, for your own
data) → `discover-install` → `discover-schema-apply` → `discover-data-load`.

## Usage

Describe what you want and the agent should pick the right skill, or name one directly
(`/discover-install`, `/discover-schema-design`, `/discover-data-load`). Take it a stage at a time
and check each result before moving on. For example:

> Profile `cases.idx` and propose a Discover entity schema. The demo should show which people appear
> together across cases and which organisations they belong to.

> Install Discover in namespace `discover-demo` on context `k3s`, using `discover-26.4.0.tgz` and the
> schema we just designed. Ingress class `nginx`, ingress IP `192.168.1.20`, licence server
> `licences.example.com`.

> Load `cases.idx` into the deployment using the schema mapping. Do a dry run first.

> How many people and organisations were loaded? Pick a well-known person, show me their links and
> check them against the source data.

> `api-0` has been in `Init` for 15 minutes. What's wrong?

> Add a `Witness` link from cases to people and apply it to the running deployment.

## What they expect of you

- **A single-node Kubernetes cluster** with a default storage class, and `kubectl` and `helm` on the
  machine the agent runs on. The skills assume k3s, on Linux, in a Linux VM or in its own WSL2
  distro.
- **The ingress-nginx controller.** The chart's ingresses rely on ingress-nginx annotations
  (`rewrite-target`, `configuration-snippet`), with `allow-snippet-annotations: "true"` and
  `annotations-risk-level: Critical`. Other controllers, including the Traefik that k3s installs by
  default, ignore them and the UI and API return 404. `discover-install` checks this before
  installing and tells you what to change.
- **The discover Helm chart and images the cluster can pull**, and an IDOL License Server reachable
  from the pods. `discover-values` asks for the chart, the image registries and versions, and the
  License Server's DNS name (not an IP; port 20000).
- **`python3`** with PyYAML and `jsonschema` 4.x, **`curl`**, and network access from the agent's
  machine to the `*.nip.io` hostnames the deployment uses.
- **Data**, for `discover-schema-design` and `discover-data-load`. An IDOL IDX export works best;
  CSV and JSON also work, and the agent writes the reader. A few thousand documents is plenty.
- **Decisions.** What becomes an entity, a link or a filter depends on the questions the demo should
  answer. Give the agent two to four of them; `discover-schema-design` proposes a schema and shows
  you the mapping before anything is deployed.

## Before you use them

These skills build demos, not production systems.

- **Security.** The deployment uses plain HTTP, `nip.io` hostnames, simple passwords, single
  replicas and no TLS, and every entity loaded is visible to every user. Follow the product
  documentation to secure a real deployment.
- **Credentials.** Generated passwords are kept in `secrets.yaml` in the working folder. As with any
  LLM-based agent, mistakes can happen; change or revoke them once your demo is configured.
- **First-install-only settings.** Hostnames, team owners, the licence server for DIH and required
  schema properties only take effect on the first install. Changing them later means a teardown and
  reinstall, so settle them first.
- **Deleting things.** The skills ask before deleting volumes, namespaces or data. Read what the
  agent proposes before you approve it.
- **Your data.** `discover-schema-design` and `discover-data-load` read the documents you load in
  order to profile fields and design the schema. **Do not use them with sensitive data**, as it may
  be sent to the agent's model provider.

## Known limitations

- **Entity icons.** The UI picks an entity's icon from its type ID and only knows the built-in types
  (`PersonEntity`, `LocationEntity`, `OrganizationEntity`, `DocumentEntity`, ...). Custom types show
  a "?" in the Connectivity view, and the schema has no setting for icons, so
  `discover-schema-design` reuses the built-in types where they fit.
