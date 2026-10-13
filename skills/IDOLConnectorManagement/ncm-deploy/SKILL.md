---
name: ncm-deploy
description: Stand up and configure the IDOL Connector Management API (NCM) - the API container, the NiFi it drives, PostgreSQL, and the connector/target/processing/NAR resources it serves - either through the Helm chart on a cluster or the same containers under plain Docker, using published release artifacts. Use when asked to deploy, configure, upgrade or diagnose an NCM installation, or to get an environment ready before configuring connectors.
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

# Deploying IDOL Connector Management

NCM is an API that builds and operates NiFi flows. It is not useful on its own: it needs a
**NiFi** to deploy flows into, a **database** to hold its state, and a **resource set** (connector,
target, processing and NAR packages) to build flows from. Getting all four right is the whole job -
a deployment that starts cleanly but has no resources can create nothing at all.

Deploy first, then use the `ncm-migrate` skill to configure and run pipelines against it.

The step numbers below are for your own sequencing; say what you are doing rather than announcing
them.

## Components

| Component | What it is | Needed? |
|---|---|---|
| `idol-connector-management-api` | The REST API. Public 8080, internal callbacks 8081 | always |
| `idol-connector-management-nifi` | NiFi 2.9 with the IDOL framework NARs baked in | unless pointing at an existing NiFi |
| PostgreSQL | API state, and the bundled NiFi's own store | always in practice (see below) |
| Resource provider | Serves connector/target/processing/NAR packages | always |
| DocumentSecurity API | Only if connectors use the `groups` operation | optional |

**An existing NiFi must be 2.7 or later.** The flows the API builds set standard-processor property
names that only exist from 2.7; against 2.6 or earlier the API refuses the endpoint and
`/v1/health/ready` stays `503` naming the version it found. Do not diagnose that as a credentials or
networking problem. The bundled image is 2.9, so this only applies when `nifi.enabled=false`.

**HSQLDB is not an option for anything real.** The API image falls back to an embedded HSQLDB file
in the container's writable layer when given no connection string. It starts, passes readiness, and
loses every connector on restart. The Helm chart refuses to render rather than allow it; under
plain Docker nothing stops you, so supply a database yourself.

## Step 1 - choose the path

**Helm** if there is a cluster. It is the supported path, models the dependencies, generates
credentials, and has tests. Its README is the reference for everything this skill does not spell
out, and it travels inside the packaged chart:

```sh
# -rel is the normal choice; see "Which channel" below before deciding
helm repo add cs-kd-helm https://artifactory.otxlab.net/artifactory/cs-knowledgediscovery-helm-rel
helm repo update
helm search repo cs-kd-helm/idol-connector-management --versions
helm show readme  cs-kd-helm/idol-connector-management
helm show values  cs-kd-helm/idol-connector-management
```

Swap `-helm-rel` for `-helm-dev` and add `--devel` to every command for a development chart.

**Release charts are plain `27.1.0` and need no flag.** Development charts are
`27.1.0-SNAPSHOT` - a semver pre-release, which Helm hides unless asked, so **`--devel` is required
on every command including `helm install`**. Without it you get "No results found" and a
chart-not-found on install for a chart sitting in the index, which reads exactly like a wrong
repository or a mistyped chart name. Passing `--devel` when it is not needed is harmless, so when
unsure, pass it.

Charts published before the version scheme was tidied carry a `-nifi2` marker (`26.4.0-nifi2`,
`26.4.0-nifi2-SNAPSHOT`) and are pre-releases whichever channel they came from - so an older
release chart does need the flag.

Read it alongside this skill - no source checkout needed.

### Which channel

Both channels carry this chart. They differ in more than freshness:

| | `-dev` | `-rel` |
|---|---|---|
| Repository | `cs-knowledgediscovery-helm-dev` | `cs-knowledgediscovery-helm-rel` |
| Chart/image version | `27.1.0-SNAPSHOT` | `27.1.0` |
| `--devel` needed | yes | no |
| Images | `...-docker-dev` | `...-docker-rel` |
| Built | on every change | **weekly** |

**Use `-rel` unless told otherwise** - a fixed version, no flag, and a build someone stood behind.
`-dev` exists for work not yet released; release builds run on a weekly cadence, so the two are not
in step mid-week.

Whichever you pick, **keep the chart, the images and the resource branch (Step 3) on the same
channel** - packaging aligns the chart and images for you, but the resource branch is separate and
yours to set. Confirm what you actually got rather than trusting this table:

```sh
helm search repo cs-kd-helm/idol-connector-management --versions --devel
helm search repo cs-kd-rel/idol-connector-management --versions
```

**Plain Docker** for a single machine, a demo or a laptop. Same images, wired by hand. Nothing
generates credentials or waits for dependencies for you.

Then decide these four things before running anything - each maps to a section below:

1. Where NiFi comes from: bundled, or an existing one you point at.
2. Where the database comes from: bundled, external, or a connection string you supply.
3. Where connector resources come from: Artifactory directly, Artifactory seeded onto a volume,
   Google Cloud Storage, or a volume you populate yourself.
4. How IDOL is licensed: LicenseServer, or OEM key files.

## Step 2a - Helm

Images default to published, version-tagged artifacts, so a first install needs no image overrides:

```
artifactory.otxlab.net/cs-knowledgediscovery-docker-<channel>/idol-connector-management-api:<version>
artifactory.otxlab.net/cs-knowledgediscovery-docker-<channel>/idol-connector-management-nifi:<version>
```

The packaging step rewrites the channel to match the chart, so a chart from the `-rel` helm
repository already points at `cs-knowledgediscovery-docker-rel`, and a `-dev` chart at
`-dev`. **Confirm what you actually got** rather than assuming - `helm show values` prints the
resolved references:

```sh
helm show values cs-kd-helm/idol-connector-management | grep -E '^\s+image:'
```

The tag is the project build version, which is **not** `Chart.yaml`'s `appVersion` - that is a
separate, shorter value maintained independently, and no image is published under it. To pin different images, set
`connectorManagement.image` and `nifi.image`. For registry credentials the value is
`global.imagePullSecrets` (it already carries a default, so replace rather than assume it is
empty); a plain top-level `imagePullSecrets` is rejected outright (see the schema note below).

### A complete values file

Read Step 3 before running anything - a default install succeeds and serves **nothing**, which is
not the same as failing. This is a whole working configuration: bundled NiFi and database,
resources from Artifactory, LicenseServer licensing.

```yaml
# ncm-values.yaml
# nifi.enabled and postgresql.enabled both default to true - the bundled pair is what you get
# unless you turn them off to point at existing instances.

licenseServerHostname: licensesrv.internal    # top-level, not under nifi:
licenseServerPort: "20000"                    # quote it - an unquoted int is rejected

connectorManagement:
  resourcesVolume:
    enabled: false              # reading Artifactory directly needs no volume

  env:                          # a MAP of NAME: "value", not a list of {name, value}
    # The chart connects a `database` key store to its own database. Leave it out for `noop`
    # (the image default) if you do not need tokenised credentials yet. See "Choosing a keys
    # provider".
    CONNECTORS_KEYS_PROVIDER_TYPE: "database"

    CONNECTORS_STORAGE_PROVIDER_TYPE: "artifactory"
    CONNECTORS_STORAGE_PROVIDER_CACHE_DIR: "/opt/nifi-connector-management/storage_provider_cache"

    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_BASEURL: "https://orgartifactory.swinfra.net/artifactory/cs-knowledgediscovery-generic-dev-local/builds/"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_PLATFORM: "linux64_gcc12"

    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_CONNECTOR_TYPES: "SharePointOData,Web,GoogleCloudStorage"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_CONNECTOR_SHAREPOINTODATA_DIR: "connectors/flyingPig"

    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_TARGET_TYPES: "UserSecurity,IDOL,IDOLGraph"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_TARGET_USERSECURITY_BUILD: "connectors-documentsecurity"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_TARGET_USERSECURITY_PLATFORM: "common"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_TARGET_USERSECURITY_DIR: "connectors/documentSecurity"

    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_PROCESSING_TYPES: "AWSTranslate,CategorizeDocument,ContentIntoSections,ConvertCSVToDocuments,ConvertIDXToDocuments,ConvertJSONToDocuments,ConvertXMLToDocuments,DetectContentLanguage,Eduction,HashDocument,KeyViewExtractFiles,KeyViewFilterDocument,KeyViewRouteMedia,MergeContentPages"

    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_NAR_TYPES: "idol-nifi-connector-utils-nar,idol-nifi-eduction-nar,idol-nifi-indexing-nar,idol-nifi-keyview-nar,idol-nifi-scripting-nar,idol-nifi-viewer-nar"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_NAR_IDOL_NIFI_CONNECTOR_UTILS_NAR_DIR: "connectors/nifiConnectorUtils"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_NAR_IDOL_NIFI_CONNECTOR_UTILS_NAR_BUILD: "connectors-nificonnectorutils-nifi2"
    CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_NAR_IDOL_NIFI_CONNECTOR_UTILS_NAR_NARTARGETDIR: "modules/nar/target"
```

**Two different Artifactory hosts appear above and that is correct**, not a typo: images and the
chart come from `artifactory.otxlab.net`, resources from `orgartifactory.swinfra.net`. Getting the
resource host wrong is the "provider unreachable, never Ready" failure.

```sh
helm install ncm cs-kd-helm/idol-connector-management --devel -f ncm-values.yaml \
    --namespace ncm --create-namespace \
    --wait --timeout 20m
helm test ncm --logs -n ncm
```

`--timeout 20m` is not optional: with a seeding provider the pod stays unready until the copy
finishes (~550MB / ~6 minutes for a full set on an empty volume), and the default 5 minutes
expires first.

**The chart's values schema is strict** - `additionalProperties: false` on the top level and on
the `connectorManagement`, `nifi` and ingress blocks. A misplaced or misspelled key therefore
aborts `helm install` with "Additional property X is not allowed"; it is never silently ignored.
That is a good property, but it means a typo looks like a chart bug rather than yours.

Notes on the values above, each of which has caught someone out:

- **`connectorManagement.env` is a map** of `NAME: "value"`. A list of `{name, value}` is refused
  by the schema, not silently ignored.
- **NiFi, the database and a resources volume are all bundled by default.** Turn each off only to
  point elsewhere: `postgresql.enabled=false` needs the separate `externalPostgresql.*` block,
  `nifi.enabled=false` needs `connectorManagement.nifi.endpoint` (the render fails otherwise), and
  `resourcesVolume.enabled=false` suits any provider that reads a repository directly.
- **Turning the resources volume off later is not an upgrade.** Its PVC comes from a
  `volumeClaimTemplate`, which is immutable, so `helm upgrade` fails and the release has to be
  reinstalled. Decide it at install time.
- **`licenseServerHostname`/`licenseServerPort` are top-level**, despite configuring the NiFi
  container. Under `nifi:` the install is **refused**, not ignored.
- **`CONNECTORS_STORAGE_PROVIDER_CACHE_DIR` needs a path you choose**; the chart backs it with an
  `emptyDir` and the cache is rebuilt after each pod replacement.
- **Pin the chart** with `--version` if the install must be reproducible; `helm search repo
  cs-kd-helm/idol-connector-management --versions --devel` lists what is available.
- **`global.imagePullSecrets` defaults to `["dockerhub-secret"]`, which does not exist in a new
  namespace.** Create that Secret, name your own, or set the list to `[]` where the node already
  has credentials (Docker Desktop, for instance, shares its image store with the cluster, so
  pre-pulled images need no secret at all).
- **The Web connector needs shared memory and a permissive seccomp profile.** The chart already
  defaults `nifi.devShmSize` to 512Mi, which is enough; the seccomp profile is the one to check,
  since its installer needs a root init container and a hostPath write that PodSecurity
  `restricted` and OpenShift reject. See "Known limitations" in the chart README before deploying
  the Web connector to a hardened cluster.
- **NiFi's sensitive-properties key is generated on first install and preserved across upgrades**,
  so nothing needs setting - but it is unrecoverable if replaced, which is why GitOps installs
  should supply their own Secret rather than let generation run on every sync.
- To follow the install: `kubectl -n <ns> get pods`, and logs via the StatefulSet, e.g.
  `kubectl -n <ns> logs statefulset/<release>-idol-connector-management --tail=200 -f`.

(From a source checkout, `helm/idol-connector-management-api` replaces the chart reference. The
chart is named `idol-connector-management`; only the source directory carries the `-api` suffix.)

The chart README (`helm show readme`, above) is the reference for the rest, and it is thorough.
Go to it for:

- **Deployment scenarios** - existing NiFi/PostgreSQL, complete stack, resources from a volume.
- **Credentials and Secrets** - what is generated, and why `helm template | kubectl apply` and
  GitOps rendering must supply their own Secrets instead of relying on generation.
- **Verifying the NiFi certificate** - certificate verification is **off by default**, so an
  `https://` NiFi endpoint is encrypted but unauthenticated until you turn it on.
- **Health probes** - the startup/readiness split, and seeding progress in the readiness body.
- **Upgrading** - the `schemaversion` reconciliation. From 1.0 the service stops rather than
  modify a schema it cannot migrate, so a bad upgrade is a pod that will not start, never an
  emptied database. Back up first; a rollback across a schema version is refused.
- **Changing settings on a running deployment** - NiFi applies every setting again each time it
  starts. That includes the licence, proxy, database and flowfile-storage services held in its flow.
  Switching licence mode or turning the proxy on or off rewires the deployed connectors
  automatically. A rotated database password needs both StatefulSets restarted, since credential
  Secrets deliberately do not roll pods. Edits to those services in the NiFi UI are reverted.
- **Production checklist** - work through it before exposing anything. Authentication is off by
  default and the bundled NiFi has no authentication at all.

## Step 2b - plain Docker

**The images come from a private registry.** `docker run` will pull from
`artifactory.otxlab.net`, which needs a credential: `docker login artifactory.otxlab.net`. Docker
Desktop often already holds one, so try the pull first. If it fails with `Bad Credentials` or
`unauthorized`, stop and ask the user to log in rather than trying other tags or registries - a
pull failure is an access problem, not a wrong-version problem, and guessing tags will not fix it.
The same applies to the `nifi` image, which is large; check whether it is already present with
`docker images` before pulling it again.

The same three images on one user-defined network. Wired by hand:

```sh
docker network create ncm

docker run -d --name ncm-db --network ncm \
    -e POSTGRES_DB=ncm -e POSTGRES_USER=ncm -e POSTGRES_PASSWORD=<password> \
    postgres:16

docker run -d --name ncm-nifi --network ncm -p 8443:8080 \
    -e NIFI_WEB_HTTP_PORT=8080 \
    -e NIFI_SENSITIVE_PROPS_KEY=<a long random string, fixed for the life of the flow> \
    -e NIFI_JVM_HEAP_MAX_PERCENTAGE=50.0 \
    -e NIFI_DB_HOST=ncm-db -e NIFI_DB_PORT=5432 -e NIFI_DB_NAME=ncm \
    -e NIFI_DB_USERNAME=ncm -e NIFI_DB_PASSWORD=<password> \
    -e NIFI_LICENSE_SERVER_HOST=<host> -e NIFI_LICENSE_SERVER_PORT=20000 \
    --shm-size 512m \
    artifactory.otxlab.net/cs-knowledgediscovery-docker-dev/idol-connector-management-nifi:<version>

docker run -d --name ncm-api --network ncm -p 8080:8080 -p 8081:8081 \
    -e NIFI_ENDPOINT=http://ncm-nifi:8080/nifi \
    -e CALLBACKS_ENDPOINT=http://ncm-api:8081 \
    -e CONNECTORS_STATE_PROVIDER_TYPE=database \
    -e CONNECTORS_STATE_PROVIDER_DATABASE_CONNECTIONSTRING=jdbc:postgresql://ncm-db:5432/ncm \
    -e CONNECTORS_STATE_PROVIDER_DATABASE_USERNAME=ncm \
    -e CONNECTORS_STATE_PROVIDER_DATABASE_PASSWORD=<password> \
    -e CONNECTORS_KEYS_PROVIDER_TYPE=database \
    -e CONNECTORS_KEYS_PROVIDER_DATABASE_CONNECTIONSTRING=jdbc:postgresql://ncm-db:5432/ncm \
    -e CONNECTORS_KEYS_PROVIDER_DATABASE_USERNAME=ncm \
    -e CONNECTORS_KEYS_PROVIDER_DATABASE_PASSWORD=<password> \
    <storage provider variables - see Step 3> \
    artifactory.otxlab.net/cs-knowledgediscovery-docker-dev/idol-connector-management-api:<version>
```

`NIFI_ENDPOINT` may be given with or without a trailing `/nifi` - the client appends `/nifi-api`
either way, so both forms work and neither is a likely cause of a connection failure.

Three things that break this if got wrong:

- **`CALLBACKS_ENDPOINT` must be an address NiFi can resolve**, because NiFi calls back into the
  API's internal port with reports. Omitting it is not safe: it defaults to `http://localhost:<INTERNAL_API_PORT>`, which NiFi cannot
  reach from its own container, so reports silently never arrive. `localhost` works only when both
  run in the same container.
- **`--shm-size 512m`** - the Web connector's headless Chrome aborts on the 64MB default once
  several renderers are live. Below 256MB it falls back to a slower file-backed mode and warns.
- **`NIFI_SENSITIVE_PROPS_KEY` is fixed for the life of the flow.** It encrypts every `enc{...}`
  value NiFi holds. Change it later and the existing flow cannot be decrypted; recovery means
  re-keying with NiFi's tooling or discarding the flow and re-entering every credential.

Heap is sized as a **percentage of the container limit**, via `NIFI_JVM_HEAP_INIT_PERCENTAGE`
(default 25.0) and `NIFI_JVM_HEAP_MAX_PERCENTAGE` (default 50.0). Size the container and let the
heap follow; without a memory limit the percentages apply to the host's memory. The API image
works the same way, with `JVM_HEAP_INIT_PERCENTAGE` (10.0) and `JVM_HEAP_MAX_PERCENTAGE` (65.0);
an `-Xms`/`-Xmx` in its `JAVA_OPTS` overrides them. On Helm these are `nifi.jvmHeap*Percentage`
and `connectorManagement.jvmHeap*Percentage`.

The API image generates its configuration from environment variables, in these families:

| Prefix | Configures |
|---|---|
| `CONNECTORS_STORAGE_PROVIDER_*` | resource provider - `_TYPE` selects `filesystem`, `dev`, `artifactory`, `googlecloud`, `seeded` or `composite` (anything else is rejected at startup), then that provider's own settings. `_CACHE_DIR` enables caching; `_CACHE_TTL` (content, default 1 day) and `_CACHE_LISTING_TTL` (listings, default 60s) apply **only** when it is set |
| `CONNECTORS_STATE_PROVIDER_DATABASE_*` | `CONNECTIONSTRING`, `USERNAME`, `PASSWORD` (or `CREDS` as JSON) |
| `CONNECTORS_KEYS_PROVIDER_TYPE` | `noop` (default) or `database` - see below |
| `CONNECTORS_KEYS_PROVIDER_DATABASE_*` | for `database`: `CONNECTIONSTRING` (required), `USERNAME`, `PASSWORD` (or `CREDS` as JSON) - the same shape as the state store's |
| `CONNECTORS_AUTH_*` | `ENABLED`, `JWKS_URI`, `ETS_URL` |
| `CONNECTORS_REPORTS_*` | `STORAGE_ENABLED`, `MAX_DAYS`, `MAX_COUNT`, `CALLBACK_URL` |
| `NIFI_*` | `ENDPOINT`, `USERNAME`, `PASSWORD`, `TLS_VERIFY`, `TLS_VERIFY_HOSTNAME`, `TLS_CA_FILE`, `TLS_TRUSTSTORE`, `TLS_TRUSTSTORE_PASSWORD`, `PROXY_HOST`, `PROXY_PORT` |
| `TYPES_CONNECTORS` | allow-list restricting which connector types are offered at all |
| `TYPES_PROCESSING` | the same for processing types - check this too when a catalogue looks short |
| `TARGET_DEFAULT_NAMING_STRATEGY`, `TARGET_DEFAULT_PARTITION_STRATEGY`, `TARGET_DEFAULT_INSERT_MODE` | deployment-wide target defaults (`uuid`, `none`, `parts`) |
| `CONNECTORS_JOBRUNNER_FETCH_MAXPARALLEL`, `_DELETE_MAXPARALLEL` | raise the per-connector job caps (default 1 each) |
| `TARGET_PIPELINE_IDS` and `TARGET_PIPELINE_<ID>_*` | the only way pipeline target instances come into being |
| `CONNECTOR_TARGET_TYPES` | allow-list restricting which put-capable **connectors** may act as targets; dedicated target types are unaffected |
| `PUBLIC_API_PORT`, `INTERNAL_API_PORT`, `JVM_HEAP_INIT_PERCENTAGE`, `JVM_HEAP_MAX_PERCENTAGE`, `JAVA_OPTS` | `8080`, `8081`, `10.0`, `65.0`, empty |

The chart README describes the same configuration surface in Helm terms, and every option has an
environment-variable equivalent, so `helm show readme cs-kd-helm/idol-connector-management` is the
fuller reference even when deploying under plain Docker.

### Choosing a keys provider

Sensitive connector properties are held through a `KeyStore`, and the choice decides where the
secret physically sits - **neither option encrypts it**.

- **`noop`** - the default the container supplies, though the code itself requires the type to be
  set, which matters if you mount a complete properties file. It returns the secret *as* its own token, so the plaintext sits inline in the
  connector or target's configuration row. Perfectly serviceable, and what a proof of concept
  should use.
- **`database`** stores a random UUID in the configuration row and keeps the secret in a separate
  `keys` table, scoped by tenant, subscription and entity. So it is **tokenisation, not
  encryption**: both end up as plaintext in the same PostgreSQL unless the database itself is
  encrypted at rest. What it buys is that secrets stop travelling with configuration, and that
  deleting an entity purges its values.

Either way the API redacts `secure` properties on read, so this is about storage layout rather
than the API surface. Prefer `database` where credentials are real. On the Helm chart, setting the
type is all it takes - the chart connects the key store to the same database it gives the API, with
the same credentials (the password from the same Secret), and the key store keeps its values in a
`keys` table of its own:

```yaml
connectorManagement:
  env:
    CONNECTORS_KEYS_PROVIDER_TYPE: "database"
```

To keep them in a separate database instead, give its connection explicitly - the chart then leaves
it to you:

```yaml
connectorManagement:
  env:
    CONNECTORS_KEYS_PROVIDER_TYPE: "database"
    CONNECTORS_KEYS_PROVIDER_DATABASE_CONNECTIONSTRING: "jdbc:postgresql://<keys-db-host>:5432/<database>"
    CONNECTORS_KEYS_PROVIDER_DATABASE_USERNAME: "<user>"
  secretEnv:
    CONNECTORS_KEYS_PROVIDER_DATABASE_PASSWORD: "<password>"
```

Under plain Docker there is no chart to wire it: set the connection string, username and password
yourself, as in the `docker run` example.

**Under plain Docker, setting the type without the connection string fails the application
context at startup**, which presents as the container restarting rather than as a configuration
error. The Helm chart supplies the connection itself unless you give one. Images
built before that variable existed can only reach `database` through a mounted properties file.

To bypass generated configuration entirely, mount a complete properties file at
`/opt/nifi-connector-management/config/NiFiConnectorManagementService.properties.custom` - the
entrypoint then uses it as-is and ignores the environment.

## Step 3 - connector resources

Nothing can be created until resources are available: `/v1/types/*` is what the API builds flows
from. Four resource types are served independently - **connector**, **target**, **processing**
and **nar**.

**A default install comes up healthy and completely empty.** The chart provisions a resources
volume and creates the directory layout in it, so readiness passes - but the volume is blank, so
`/v1/types/*` lists nothing and **no connector can be created**. A green `/v1/health/ready` is
therefore not evidence that the deployment is usable; the type listings are. Configuring resources
is a separate act from installing successfully.

The usual choice is `artifactory`. **Any connector, target or processing type released to
Artifactory can be served** - name it in the appropriate `_TYPES` list and the provider discovers
its versions. The lists are what this deployment chooses to offer, not a product limit, so a
repository absent from the catalogue is usually a configuration decision that can be revisited
rather than an unsupported repository.

**[`reference/catalogue.md`](reference/catalogue.md) lists every type published at the time of
writing** - 65 connectors, 12 targets, 41 processing types - with which ones need overrides. Consult it
when the user asks whether some repository can be migrated at all: `/v1/types/*` answers only what a
deployment already serves, and nothing else answers what it could serve. Treat it as a dated snapshot,
so an absence means "check", not "unsupported".

A good starting set, if the user has no particular requirement:

- connectors: `SharePointOData`, `Web`, `GoogleCloudStorage`
- targets: `UserSecurity`, `IDOL`, `IDOLGraph`
- processing: `AWSTranslate`, `CategorizeDocument`, `ContentIntoSections`, `ConvertCSVToDocuments`,
  `ConvertIDXToDocuments`, `ConvertJSONToDocuments`, `ConvertXMLToDocuments`,
  `DetectContentLanguage`, `Eduction`, `HashDocument`, `KeyViewExtractFiles`,
  `KeyViewFilterDocument`, `KeyViewRouteMedia`, `MergeContentPages`
- NARs: `idol-nifi-connector-utils-nar`, `idol-nifi-eduction-nar`, `idol-nifi-indexing-nar`,
  `idol-nifi-keyview-nar`, `idol-nifi-scripting-nar`, `idol-nifi-viewer-nar` (the full artifact id
  is the type id here - a shortened name will not resolve)

### Types whose location is not derivable from their id

A handful of types are published under a directory or build that predates their type name, so they
need `_DIR`, `_BUILD` or (in one case) `_PLATFORM` set. **Which ones, and what to set, is listed per
type in [`reference/catalogue.md`](reference/catalogue.md)** - look the type up there rather than
probing Artifactory or guessing, because nothing about these is inferable.

**`common` is a trap when reading Artifactory directly.** A connector usually has two builds: the one
this provider resolves a *type* from, and the connector's own. The second often publishes a `common`
platform holding its platform-independent Java artefacts, so finding `common` for a connector proves
nothing about where its NiFi resources live - pointing `_PLATFORM` at it yields a path that 404s, and
the type then silently never appears in the catalogue. Only one type genuinely needs a non-default
platform, and `reference/catalogue.md` names it.

If you need to check a type's real layout, list the platforms of the build the provider will actually
use:

```sh
curl -s "<baseurl>/connectors-nifi-<type>/master/" | grep -o 'href="[^"/]*/"'
```

Every resource type must appear in its `_TYPES` list - the per-type overrides below are only
consulted for ids that are listed, so an override without its `types` entry does nothing at all.

**Two different lists are at work, and they are not the same knob.** The provider's
`..._<CATEGORY>_TYPES` lists say which ids the provider knows how to *fetch* (and where from, via the
overrides). They are **additive and cannot subtract**: on the artifactory provider the catalogue is
whatever those lists name **plus** the resources NCM publishes for itself, which are listed
unconditionally from
`connectors-nificonnectormanagement/<branch>/common/build/connectors/nifiConnectorManagement/resources/<category>`.
That is why `AnalyzeMedia` and `KeyViewRouteMedia` appear as processing types on a deployment whose
`..._PROCESSING_TYPES` is empty, and still appear when it names only one of them.

The deployment-wide allow-lists - `TYPES_CONNECTORS`, `TYPES_PROCESSING`, `CONNECTOR_TARGET_TYPES` -
are the only true filter, and an **unset or empty one filters nothing**. So to shorten a catalogue,
set the allow-list; trimming the provider list will not do it. There is no `TYPES_TARGETS`: dedicated
target types cannot be filtered this way, only put-capable connectors acting as targets, via
`CONNECTOR_TARGET_TYPES`.
A type whose artifact does not sit at the conventional path (`connectors/<type>`) needs such an
override - `_DIR` for the path relative to `build/`, `_BUILD` for a different build name,
`_PLATFORM` for a non-default platform. These are not derivable from the type name, so they have
to be known. The **framework** NARs are the exception - `idol-nifi-aci-nar`, `-core-nar`,
`-eduction-nar`, `-indexing-nar`, `-keyview-nar`, `-scripting-nar`, `-services-nar`,
`-viewer-nar` - whose build and directory are fixed, so listing the id is enough. They still honour `_PLATFORM`
and `_BRANCH` per type. Anything else, `idol-nifi-connector-utils-nar` included, is a normal type and does take
`_DIR`/`_BUILD` overrides, which is why the example below sets them for it.

```properties
connectors.storage.provider.type=artifactory
connectors.storage.provider.artifactory.baseurl=https://orgartifactory.swinfra.net/artifactory/cs-knowledgediscovery-generic-dev-local/builds/
connectors.storage.provider.artifactory.platform=linux64_gcc12

connectors.storage.provider.artifactory.connector.types=SharePointOData,Web,GoogleCloudStorage
connectors.storage.provider.artifactory.connector.SharePointOData.dir=connectors/flyingPig

connectors.storage.provider.artifactory.target.types=UserSecurity,IDOL,IDOLGraph
connectors.storage.provider.artifactory.target.UserSecurity.build=connectors-documentsecurity
connectors.storage.provider.artifactory.target.UserSecurity.platform=common
connectors.storage.provider.artifactory.target.UserSecurity.dir=connectors/documentSecurity

connectors.storage.provider.artifactory.processing.types=AWSTranslate,CategorizeDocument,ContentIntoSections,ConvertCSVToDocuments,ConvertIDXToDocuments,ConvertJSONToDocuments,ConvertXMLToDocuments,DetectContentLanguage,Eduction,HashDocument,KeyViewExtractFiles,KeyViewFilterDocument,KeyViewRouteMedia,MergeContentPages

connectors.storage.provider.artifactory.nar.types=idol-nifi-connector-utils-nar,idol-nifi-eduction-nar,idol-nifi-indexing-nar,idol-nifi-keyview-nar,idol-nifi-scripting-nar,idol-nifi-viewer-nar
connectors.storage.provider.artifactory.nar.idol-nifi-connector-utils-nar.dir=connectors/nifiConnectorUtils
connectors.storage.provider.artifactory.nar.idol-nifi-connector-utils-nar.build=connectors-nificonnectorutils-nifi2
connectors.storage.provider.artifactory.nar.idol-nifi-connector-utils-nar.nartargetdir=modules/nar/target
```

As environment variables these become `CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_*`, uppercased with
**every non-alphanumeric character** - dots *and* hyphens - replaced by an underscore. That matters
for the hyphenated ids above: the per-type override for `idol-nifi-connector-utils-nar` is

```
CONNECTORS_STORAGE_PROVIDER_ARTIFACTORY_NAR_IDOL_NIFI_CONNECTOR_UTILS_NAR_DIR
```

Only the fixed set of keys the entrypoint knows about is translated, so an invented
`CONNECTORS_*` name is silently ignored rather than rejected. Under Helm these go in
`connectorManagement.env`; to configure something the entrypoint does not model, mount a complete
properties file instead.

**The Artifactory provider has no authentication of any kind** - no username, password, token or
key setting exists. The repository must be readable anonymously from the cluster. If it is not,
this provider cannot be used and the resources must be staged onto a volume instead.

**The base URL and the branch must be set together.** A repository's artifacts live under
`<build>/<branch>/<platform>/build/...`, and the two channels use different branches: development
builds publish under `master`, release builds under a release branch such as `IDOL27.1.x`. The
release repository has no `master`, so a `-rel-local` base URL with the default branch resolves
nothing at all - for every type.

```properties
# development (the default branch is master, so it may be omitted)
connectors.storage.provider.artifactory.baseurl=https://orgartifactory.swinfra.net/artifactory/cs-knowledgediscovery-generic-dev-local/builds/

# release - the branch is mandatory here
connectors.storage.provider.artifactory.baseurl=https://orgartifactory.swinfra.net/artifactory/cs-knowledgediscovery-generic-rel-local/builds/
connectors.storage.provider.artifactory.branch=IDOL27.1.x
```

`connectors.storage.provider.artifactory.<kind>.<type>.branch` overrides it per type, for a set
spanning branches while a component is promoted. Pick the release branch that matches the images -
that pairing *is* the version-matching rule below.

Resource repositories are **not** on the chart's release cadence - they follow the connector and
framework repository builds. A release deployment can therefore legitimately pair a chart and image
from one build with resources published later, provided the framework version still matches. Check
that pairing rather than assuming a shared release date.

### Controller services some processing steps need

A processing step may require a NiFi **controller service** that nothing creates by default. When one
is missing, the failure is not subtle but it is misleading: creating a *target* whose graph uses the
step returns `500 Unsatisfied controller service: idol.nifi.service.KeyViewFilterService`, which
looks like a payload problem and is actually a deployment one. `DetectContentLanguage` and
`KeyViewFilterDocument` both need the KeyView services, so any text-extraction or language pipeline
hits this.

Tell the deployment to create them. The env var name is the service's type id with every
non-alphanumeric character replaced by an underscore, uppercased:

```
CONNECTOR_DEPLOYMENT_SERVICES_AUTOCREATE_TYPES=idol.nifi.service.KeyViewFilterService,idol.nifi.service.KeyViewExportService
CONNECTOR_DEPLOYMENT_SERVICES_AUTOCREATE_IDOL_NIFI_SERVICE_KEYVIEWFILTERSERVICE_NAR=idol-nifi-keyview-nar
CONNECTOR_DEPLOYMENT_SERVICES_AUTOCREATE_IDOL_NIFI_SERVICE_KEYVIEWFILTERSERVICE_IMPL=idol.nifi.service.KeyViewFilterServiceImpl
CONNECTOR_DEPLOYMENT_SERVICES_AUTOCREATE_IDOL_NIFI_SERVICE_KEYVIEWEXPORTSERVICE_NAR=idol-nifi-keyview-nar
CONNECTOR_DEPLOYMENT_SERVICES_AUTOCREATE_IDOL_NIFI_SERVICE_KEYVIEWEXPORTSERVICE_IMPL=idol.nifi.service.KeyViewExportServiceImpl
```

The NAR named here must also be in `nar.types`, or there is nothing to create the service from. Each
type additionally accepts `_PROPERTIES` and `_PROPERTY_<NAME>` for services that need configuring.

### Versions must match the NiFi image

**This is the constraint that governs which resources a deployment may serve.** The NiFi image
bakes in the framework core and the shared controller services at its own build version. It does
**not** bake in the component NARs - keyview, eduction, scripting, indexing, viewer - which are
pulled from the resource provider at run time and are what the `nar.types` list above is for. A
connector's own NAR is pulled at run time too, but from its `connectors/<Type>/<version>/`
directory - **do not add connector NARs to `nar.types`**, where they resolve against the wrong
coordinates and silently do nothing. **Anything pulled at run time must be built against the
framework version the image carries or it will not license**, which surfaces as connectors failing
when they run rather than when they deploy.

So the resource set and the NiFi image tag move together. When adding a type, take the version
built against the framework the running image carries; when moving the image on, move the
resources with it. A mixed set is the likeliest cause of a connector that deploys cleanly and then
cannot do any work.

To check it on a running deployment, compare the NiFi image tag against the versions being served:

```sh
kubectl get statefulset -o jsonpath='{.items[*].spec.template.spec.containers[*].image}'
curl -s <host>/v1/types/connectors | jq '.connectorTypes[] | {id, versions}'
```

The connector versions in use should correspond to the image's version, allowing for the `-nifi2`
marker that Maven artefact versions carry and image tags do not - so `27.1.0-nifi2-SNAPSHOT`
resources on a `27.1.0-SNAPSHOT` image are correctly paired. What matters is the release line, not
the literal string. If a connector runs but reports licensing failures, this is the first thing to
rule out.

**There is no provider setting that pins a version** - the provider discovers whatever versions
exist, and the override keys cover location only (`_DIR`, `_BUILD`, `_PLATFORM`, `_NARTARGETDIR`).
Pinning happens per entity instead: `version` on a connector or target create request selects the
version to use, and omitting it takes the latest. So the deployment-level lever is the channel and
the image tag; the entity-level lever is that `version` field.

Then choose how it is served:

| Choice | When | Cost |
|---|---|---|
| `artifactory` direct, with `CONNECTORS_STORAGE_PROVIDER_CACHE_DIR` | simplest; cache is an `emptyDir` under Helm | re-downloads after every pod replacement |
| `seeded` (artifactory -> filesystem) onto a volume | repeated restarts, or an air-gapped runtime | first boot is minutes; needs a writable volume |
| `filesystem` on a claim you populate | shared, pre-loaded, read-only | you own the population |
| `filesystem` on a node directory | development, against connectors just built on the machine running the cluster | single-node clusters only |
| `composite` | federate two sources, first-hit-wins | read-only, no copying |

For a locally built connector, `composite` is usually better than `filesystem` alone: the local
build **shadows** the published resource of the same type and version while everything else still
comes from Artifactory, so one connector can be tested without assembling a whole resource set.
Order decides precedence - first hit wins:

```
CONNECTORS_STORAGE_PROVIDER_TYPE=composite
CONNECTORS_STORAGE_PROVIDER_COMPOSITE_PROVIDERS=filesystem,artifactory
```

Each child then reads its own `CONNECTORS_STORAGE_PROVIDER_<TYPE>_*` settings as normal. Mount the directory at a path of its own rather than over
`/opt/nifi-connector-management/resources`. Two volumes on one path produces a pod Kubernetes
rejects at creation time - so the install appears to succeed and then runs nothing - and the chart
fails the render instead, naming both claimants. Since `connectorManagement.resourcesVolume.enabled`
now defaults to true, the chart is mounting that path unless you turned the volume off, so this is
the normal case rather than an edge one. See "Serving a directory from the node" in the chart
README.

For `filesystem`, there are **four** top-level categories under the resources directory:

```
connectors/<Type>/<version>/...
targets/<Type>/<version>/...
processing/<Type>/<version>/...
NARs/<artifactId>/<version>/<artifactId>-<version>.nar
```

**`connectors/` must exist** or readiness fails with `Resource directory not found: connectors/`
and the pod never becomes Ready. **`NARs/` is the one that fails quietly**: readiness only checks
`connectors/`, so a volume populated without it passes every health check and then fails each
deployment that needs a NAR. Populate all four.

A connector's **own** NAR is not one of these: it ships beside its manifest under
`connectors/<Type>/<version>/`. `NARs/` carries the shared components any flow may reference.

**Adding resources to a running deployment:** publish a *new version* (never patch an existing
one - a `type/version` directory is several files and its arrival is not atomic), then
`POST /v1/admin/resources/resync` - which needs cloud-admin privileges when authentication is
enabled, and answers **202**. Only a `seeded` provider then copies anything in the background; on
`artifactory`, `googlecloud` or `filesystem` it just drops cached listings, so do not wait for
progress that will never appear. Without it, type definitions
expire after 600s whatever the
provider, but the 60s listing expiry applies only where a caching layer is in play - the
`filesystem`, `dev` and `seeded` providers are read directly and are not wrapped in one, having
nothing remote to save. Call resync rather than working out which case you are in.

## Step 4 - licensing

IDOL components in the NiFi image need a licence, or connectors fail at run time rather than at
deploy time. Either a LicenseServer:

```sh
helm install --set licenseServerHostname=my-licenseserver --set-string licenseServerPort=20000 ...
```

or OEM key files, as a Secret containing `licensekey.dat` and `versionkey.dat` referenced by
`idolOemLicenseSecret`. Under Docker the equivalents are `NIFI_LICENSE_SERVER_HOST`/`_PORT`, or
mounting the key files into the NiFi container and pointing `NIFI_OEM_LICENSE_KEY_FILE` at
`licensekey.dat` (`versionkey.dat` is read from the same directory).

Licensing can be changed later, including switching from one mode to the other. NiFi applies the
change when it restarts. Both modes are the same licence service to NiFi, so deployed connectors
keep working without being redeployed. Under Docker, restarting the container with the new variables does the same.

## Step 5 - verify

On a cluster, reach the API first. The service is `<release>-idol-connector-management`, public API
on 8080 and internal callbacks on 8081, so the quickest route is a port-forward:

```sh
kubectl -n ncm port-forward svc/ncm-idol-connector-management 8080:8080
```

That is the normal way in, and fine for the work this skill leads to. If browser access is
specifically wanted, see [Ingress](#ingress---for-testing-when-asked-for) - and note the chart
already created an Ingress for the API whether you wanted one or not.

Then work down this list; each answers a different question. The `--max-time` on the type listings
is deliberate - see below.

```sh
curl -s localhost:8080/v1/health/live                        # the application is running
curl -s localhost:8080/v1/health/ready | jq                  # database, NiFi and resources - all three
curl -s --max-time 120 localhost:8080/v1/types/connectors | jq '.connectorTypes[].id'
curl -s --max-time 120 localhost:8080/v1/types/targets    | jq '.targetTypes[].id'
curl -s --max-time 120 localhost:8080/v1/types/processing | jq '.processingTypes[].id'
```

`/v1/health/ready` names the failing dependency in its body, including seeding progress
(`populating resources from the seed source (attempt 1, connectors, 47 copied so far)`). While
seeding, `/v1/types/*` answers **503** with `Retry-After` rather than a partial catalogue - so an
empty-looking catalogue and a 503 mean different things.

**Give the first type listing a generous timeout.** On a cold cache each category fetches its
listing from the provider and reads every type's manifest, so the cost scales with how many types
you configured - a handful takes a few seconds, a full set has been measured in the tens of
seconds, and everything is near-instant once cached. A curl timeout and an unreachable port both
look like nothing came back, so too short a budget reports a working deployment as broken. Allow
at least 90s per category on the first call after an install.

Two things to expect in the output:

- **The listings are a union**, not an echo of your configuration. Expect more than you asked for;
  fewer is the problem. Three things add to it: a fixed extra location the **artifactory** provider always searches
  alongside your configured types (this is where `AnalyzeMedia` and `KeyViewRouteMedia` come from -
  so they appear under `artifactory` and `composite`, and under `seeded` once a copy from an
  artifactory source has run, but never under a bare `filesystem` or `googlecloud`), the built-in `Pipeline` target, and - the one that surprises people - **every
  configured connector whose type supports `put` also appears as a target type**. Configuring three connectors and three targets typically yields six targets.
  That last behaviour is what makes repository-to-repository migration possible; see `ncm-migrate`.
- **Versions should describe the same build as the image tag, but they are not the same string.**
  Resource versions are Maven artefact versions and carry a `-nifi2` line marker
  (`27.1.0-nifi2-SNAPSHOT`); image tags and chart versions drop it (`27.1.0-SNAPSHOT`, and a plain
  `27.1.0` on a release). Compare them with that marker ignored - `27.1.0-nifi2-SNAPSHOT` against
  `27.1.0-SNAPSHOT` is a match; `26.4.x` against `27.1.x` is not. Older images predate the change
  and carry `-nifi2` in the tag too.

A deployment is ready to use when all three type listings return the resources you configured.
Swagger UI is at `/swagger-ui.html`. To prove it end to end, create a connector with
`enabled: false` and read its `validationErrors` - a map keyed by NiFi **component** name (which for a connector's
operation processors reads like an operation name), naming anything still missing (an absent LicenseServer shows up here as an invalid IDOL License Service). Delete it
afterwards.

## Ingress - for testing, when asked for

**Port-forwarding is the normal way to reach a deployment**, and a real deployment fronts these
services on its own terms. Treat what follows as a testing convenience: it is worth knowing how to
make browser access work when someone asks for it, not something to configure by default.

Two things are true whether or not you want an ingress:

- **The chart creates Ingress objects; it does not install a controller.** Without one they are
  inert, which is the usual reason an ingress "does not work" on a fresh cluster - check
  `kubectl get pods -A | grep ingress` before debugging anything else. An `IngressClass` alone
  proves nothing: it is cluster-scoped and routinely outlives the controller that created it.
- **`connectorManagement.ingress.enabled` defaults to true**, so an API Ingress exists already.
  With no `host` and no `contextPath` it renders with **no host and path `/(.*)`**, claiming the
  root of every hostname the controller serves - taking traffic from anything else published
  there, and colliding with a second release in the same namespace. Give it a host or a context
  path, or set `enabled: false` if you do not want it at all.

**API only** - the common case, enough for Swagger UI and every REST call:

```yaml
ingressClassName: nginx

connectorManagement:
  ingress:
    enabled: true
    host: ncm.example.com
    contextPath: /api
    internalEnabled: false        # keep the callback port off the ingress
```

**API and NiFi**, when the NiFi canvas is wanted too - add:

```yaml
nifi:
  ingress:
    enabled: true
    host: ncm.example.com         # same host, different context path
    contextPath: /nifi-ui         # NOT /nifi - NiFi already serves its UI there
```

Both ingresses rewrite with `/$1`, so the context path is stripped before proxying and the backend
sees a root-relative path. Two consequences worth knowing:

- Give NiFi a context path that is not `/nifi`. Its UI already lives at `/nifi`, so `/nifi` as the
  context path makes `/nifi/nifi/` the real UI address and invites a redirect loop at `/nifi/`.
- `nifi.ingress.host` populates `NIFI_WEB_PROXY_HOST`; `nifi.ingress.contextPath` separately populates
  `NIFI_WEB_PROXY_CONTEXT_PATH`. Each follows its own value, not the other - set both.
  Without those NiFi rejects proxied requests with **400, invalid host header**, and generates links
  that ignore the context path. Both are handled for you, but only when the corresponding value is set.
- **The rewrite behaviour is `nginx`-only, and `ingressType` selects it** (default `nginx`) - not
  `ingressClassName`, which merely names the controller. Under `ingressType: haproxy` the annotation
  rewrites to `/` instead and `gateway` sets none, so the context-path stripping these recipes rely
  on does not happen. Check this before trusting the paths on OpenShift.

Verified reachable this way, in a browser: `<host>/api/swagger-ui.html` and `<host>/api/v1/...` for
the API, and `<host>/nifi-ui/nifi/` (UI, assets included) and `<host>/nifi-ui/nifi-api/...` (REST)
for NiFi. Note the trailing slash on the NiFi UI path.

For a local cluster, a hostname under `localtest.me` resolves to `127.0.0.1` without touching any
hosts file, so `ncm.localtest.me` works from a browser against Docker Desktop. Testing with
`curl -H 'Host: ...'` proves the routing but *not* that a browser can reach it - that needs the
name to resolve, so check both.

**This is exactly why it is a testing-only arrangement.** The bundled NiFi runs HTTP-only with no
authentication, so an ingress in front of it is a fully editable NiFi canvas open to anyone who can
reach the host - holding the credentials of every connector. `internalEnabled` deserves the same
caution: the internal callback API is exempt from authentication precisely because it is meant to
be reachable only inside the cluster. Keep both off anywhere they are not bound to loopback.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Pod `0/1 Running`, readiness names `ResourceProvider` | seeding in progress, or the source is unreachable and retries are being exhausted (10 attempts, ~7 minutes) |
| `Resource directory not found: connectors/` | `filesystem` provider reading a path with no `connectors/` directory - now uncommon, since the chart provisions the volume and creates the layout by default. Expect it when the volume was turned off, or when pointing at a node directory or claim you populated yourself |
| Healthy, but `/v1/types/*` all empty | the normal state of a default install: the provisioned volume is blank. Configure a provider, or populate the volume |
| `/v1/types/*` returns 503 with `Retry-After` | first seed has not finished; not an error |
| Target create fails `500 Unsatisfied controller service: <type>` | the graph uses a step needing a controller service nothing creates - set `CONNECTOR_DEPLOYMENT_SERVICES_AUTOCREATE_*` and ensure its NAR is in `nar.types` |
| Type listings empty but healthy | provider unable to see the resource path, or an allow-list excluding them - check `TYPES_CONNECTORS` for connectors and `TYPES_PROCESSING` for processing. Note an *empty* allow-list filters nothing, so this is rarely the cause of an empty listing |
| Type listing shows **more** than configured | expected: provider `_TYPES` lists are additive, and NCM's own published resources (`AnalyzeMedia`, `KeyViewRouteMedia`) are always listed. Use `TYPES_CONNECTORS`/`TYPES_PROCESSING`/`CONNECTOR_TARGET_TYPES` to restrict what is offered |
| Never Ready, log says `Invalid value for 'connectors.storage.provider.type'` | the provider type is misspelled. It is rejected rather than defaulted, but the container keeps running with a failed context - so this looks identical to the row above until you read the log |
| Pod will not start after an upgrade | schema version refused - a rollback, or no migration path. The log names it. Restore the backup |
| Newly published resource invisible | listing cache; `POST /v1/admin/resources/resync` |
| Connector deploys but fails at run time | IDOL licensing - either the NiFi container has no licence, or the connector NAR was built against a different `idol-nifi-framework` version than the image bakes in |
| Web connector's Chrome dies (`DevToolsActivePort file not found`) | `/dev/shm` too small, or the seccomp profile blocking Chrome's user namespace - see the chart's known limitations |
| API cannot reach NiFi | wrong host/port, or TLS verification against a certificate that is not trusted. Not the trailing `/nifi` - either form works |
| Reports never arrive | `CALLBACKS_ENDPOINT` is not an address NiFi can resolve |
| NiFi will not start, log says `Failed to seed or reconcile the flow` | the start script could not apply the settings to NiFi's flow. The output just above it says why. The flow is left untouched, and the previous one is kept at `data/conf/flow.json.gz.previous` |

## Where the detail lives

Everything below is reachable from the published artifacts - no source checkout is assumed.

| For | Read |
|---|---|
| Every Helm value, scenario, limitation and the production checklist | `helm show readme cs-kd-helm/idol-connector-management` |
| Every value and its default, with comments | `helm show values cs-kd-helm/idol-connector-management` |
| The API contract this deployment serves | `<host>/swagger-ui.html`, or `<host>/spec/public_api.yaml` |
| What the deployment currently offers | `/v1/types/connectors`, `/v1/types/targets`, `/v1/types/processing` |
| Why a deployment is unhealthy | `/v1/health/ready` - it names the failing dependency and its progress |

If you do have the source repository, the chart README lives at
`helm/idol-connector-management-api/README.md` and the API image's environment variables are
documented in full in `docker/api/README.md` - but this skill does not depend on either.
