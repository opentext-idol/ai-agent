---
name: discover-values
description: Write the Helm values file for an OpenText Discover (Knowledge Discovery) deployment from the discover chart - licence server, hostnames, OTDS auth and demo users, admin/global team owners, NiFi analysis memory, storage classes, image overrides and a custom entity schema. Lists the settings that only take effect on the FIRST install. Use before installing Discover, or when changing any Discover helm values.
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

# Discover values file

Write the values file **before the first install**. Several settings are only applied when the system first
initializes, and fixing them afterwards means removing everything and installing again (discover-teardown).

## Gather first (ask the user if unknown)

| Needed | Example | Used for |
|---|---|---|
| Helm chart (`.tgz` or folder) | `discover-26.4.0-....tgz` | the user provides it |
| kube context and namespace | `k3s`, `discover-demo` | |
| Ingress IP | `192.168.1.20` | hostnames. Use the ingress-nginx controller's address: `kubectl get svc -A \| grep -i ingress-nginx` (EXTERNAL-IP), or the node's InternalIP (`kubectl get nodes -o wide`). It must be reachable from your machine **and** from inside pods |
| Ingress class | `nginx` | `kubectl get ingressclass`. It must be an **ingress-nginx** class (CONTROLLER `k8s.io/ingress-nginx`), not k3s's default `traefik`: the chart's ingresses only work with ingress-nginx (discover-install step 1) |
| Storage class | `local-path` | `kubectl get storageclass` |
| IDOL licence server **DNS name** (port 20000) | `licence.example.net` | must be a name, not an IP |
| Images the cluster can pull | registry + versions | the chart defaults may not be pullable; ask for them |

## Hostnames: use nip.io

Use `<name>.<namespace>.<IP>.nip.io` for every host. It resolves to the node IP **both on your machine and
inside pods**. That matters: OTDS stamps tokens with `iss=http://<auth host>/OTDS/otdsws` and the API checks that
URL from inside its pod. `localhost` never works (inside a pod it is the pod itself), and every API call then fails
with 401.

## The values file

Replace every `<...>`. Keep image versions in a separate file (next section).

```yaml
global:
  imagePullSecrets: ["docker-secret"]   # schema needs >=1 entry; a missing secret only gives warnings

licenseServer:
  hostname: <licence-host>          # content + dataset-locations, via the license-service ExternalName

external:
  protocol: http
  host: discover.<ns>.<ip>.nip.io
  port: 80
  adminHost: ""
ingress:
  className: <ingress-class>        # only the chart's own ingress; the subcharts need their own (auth, analysis, entityIndex)

auth:
  enabled: true
  ingress: {class: <ingress-class>} # OTDS ingress. Without it api-init gets 404 from OTDS and api-0 crash-loops
  simplePasswordPolicy: true        # test systems only
  users:
    demo_user:    {passwordEnv: DEMO_USER_PASS,    compositeRoles: ["user", "admin"], passwordTemporary: false}
    analyst_user: {passwordEnv: ANALYST_USER_PASS, compositeRoles: ["user"],          passwordTemporary: false}
  external:                         # must equal the token issuer, so the same host as publicHostname
    protocol: http
    host: auth.<ns>.<ip>.nip.io
    adminHost: auth.<ns>.<ip>.nip.io
    port: 80
  otdsws:
    ingress: {prependPath: "OTDS"}
    publicHostname: auth.<ns>.<ip>.nip.io
    adminEmail: discover.admin      # the OTDS admin user (a bare name, not an email address)
    adminPassword: <password>       # REQUIRED: otherwise the chart's default, which is public. First install only

discoverUi:
  replicas: 1
  requireHttps: false               # plain-HTTP ingress; otherwise the browser login fails (issuer must use HTTPS)

api:
  replicas: 1
  init:
    adminTeamOwner: demo_user       # REQUIRED: creates the admin team + Admin Project, which the UI needs
    globalTeamOwner: demo_user      # REQUIRED: creates the global team with every user in it
    additionalSecrets:              # the passwords for passwordEnv above (a literal `password:` is rejected)
      DEMO_USER_PASS: <password>
      ANALYST_USER_PASS: <password>

analysis:                           # NiFi. REQUIRED: the licence check goes through it; api-init waits on it
  enabled: true
  ingressClassName: <ingress-class> # all five NiFi and NiFi registry ingresses
  idol-licenseserver: {licenseServerService: license-service, licenseServerPort: "20000"}
  nifi:
    jvmMemoryRatio: 0.3             # heap = memoryMi x ratio; a 6Gi limit with a 3G heap is OOMKilled
    resources:
      requests: {cpu: 100m, memoryMi: 2048}
      limits:   {cpu: 4000m, memoryMi: 10240}
    dataVolume: {storageClass: <storage-class>}
    ingress:
      host: discover-nifi.<ns>.<ip>.nip.io
      proxyHost: discover-nifi.<ns>.<ip>.nip.io
      aciHost: discover-nifi.<ns>.<ip>.nip.io
  nifiRegistry:
    ingress: {host: discover-nifi.<ns>.<ip>.nip.io}
    dataVolume: {storageClass: <storage-class>}

searchAbstractor: {enabled: false}
datasets: {locations: {enabled: true, replicas: 1}}   # api-init waits on it: keep it enabled
filestore: {dataVolumeStorageClass: <storage-class>}
audit: {primary: {persistence: {storageClass: <storage-class>}}}
entityStorage: {global: {defaultStorageClass: <storage-class>}}

entityIndex:
  licenseServerHostname: <licence-host>   # REQUIRED as well as licenseServer.hostname: DAH and DIH read this one
  content: {ingress: {host: idol.<ns>.<ip>.nip.io, className: <ingress-class>}, contentStorageClass: <storage-class>, backupArchiveStorageClass: <storage-class>}
  dah:     {ingress: {host: idol.<ns>.<ip>.nip.io, className: <ingress-class>}}
  dih:     {ingress: {host: idol.<ns>.<ip>.nip.io, className: <ingress-class>}, dihStorageClass: <storage-class>}
```

- **Ingress class: set it in all six places.** `ingress.className` only reaches the chart's own ingress
  (`isol-ingress`, UI and API). OTDS, NiFi and IDOL are subcharts, each with its own key: `auth.ingress.class`,
  `analysis.ingressClassName`, and `entityIndex.{content,dah,dih}.ingress.className`. An ingress without a class
  takes the cluster's default class, which on k3s is often Traefik, and Traefik ignores the chart's nginx
  annotations (404s). Check after rendering:
  `helm template ... --api-versions networking.k8s.io/v1/Ingress | grep -c 'ingressClassName'` gives 10 (without
  `--api-versions`, the OTDS chart renders an old-style ingress and the count is 9).

- Generate a random password for each user (16+ letters and digits) and for the OTDS admin (the same, plus a
  punctuation character, e.g. `python3 -c 'import secrets; print(secrets.token_urlsafe(18) + "!")'`). Put
  `api.init.additionalSecrets` and `auth.otdsws.adminPassword` in their own file, `secrets.yaml`, with `chmod 600`,
  and pass it as an extra `-f` (discover-install). Don't print the passwords. Tell the user they are in
  `secrets.yaml`.
- Don't add `entityIndex.host`: the chart's schema rejects it.

## Image overrides (separate file)

Most Discover images are `{global.image.registry}/<repo>:<version>`. Cassandra (`entityStorage`, image
`solutions-entity-storagedb`), NiFi (`analysis`, image `solutions-analysis-service`), the IDOL servers and OTDS have
their own registry keys. Give those the registry their image is in. OTDS's image is
`{source}/{name}:{tag}`, so for `reg.example/otds/otds-server:25.3.0` use `source: reg.example/otds`.
Note that `entityStorage` uses `tag` where the others use `version`. The NiFi image (`solutions-analysis-service`) is
set with `analysis.idolImage` (not `analysis.nifi.image`, which the chart rejects) and comes from the Discover
registry, not the IDOL one. Pin every version the user gives you:

```yaml
global:
  image: {registry: <registry>, nameSeparator: "/", versionSeparator: ":"}
discoverUi: {image: {version: <v>}}
api: {image: {version: <v>}}
datasets: {locations: {image: {version: <v>}}}
filestore: {image: {version: <v>}}
entity: {vector: {qms: {image: {version: <v>}}}}
entityStorage: {image: {registry: <registry>, tag: <v>}}
analysis: {idolImage: {registry: <registry>, version: <v>}}
entityIndex:
  content: {idolImage: {registry: <idol-registry>, version: <idol-v>}}
  dah:     {idolImage: {registry: <idol-registry>, version: <idol-v>}}
  dih:     {idolImage: {registry: <idol-registry>, version: <idol-v>}}
auth: {otdsws: {image: {source: <otds-registry>, name: otds-server, tag: <otds-v>, pullSecret: ""}}}
```

Check with `helm template ... | grep 'image:' | sort -u` that every image came out as intended. Some pinned images
(e.g. `solutions-entity-vector-qms`) aren't deployed by default, so they don't appear. Third-party images also come
from docker.io (`bitnamilegacy/postgresql`, `apache/nifi-registry`, `zookeeper`, `busybox`). A cluster without
internet access needs those mirrored too.
Prefer immutable release or RC tags. `-SNAPSHOT` tags can be months old, so check an image's age before
trusting it: `docker buildx imagetools inspect <image> --format '{{json .Image}}'` (labels Build.Date, Git.Commit).

## Custom entity schema (optional)

Extra entity types go in `dataEntity.customEntitySchema` (a YAML string). On a system that already holds data
(and api-init's own users, teams and Admin Project count) you can only **add** types, links and optional
properties. A new `required` property on an existing type is refused, api-0 then stays in `Init`
(discover-troubleshoot). So put the schema in before the first install. Check it with discover-schema-validate before every install or upgrade.

## First-install-only settings

Changing any of these later needs discover-teardown and a fresh install:

| Setting | Why |
|---|---|
| `api.init.adminTeamOwner`, `globalTeamOwner` | the teams and Admin Project are created once ("system is already initialized" afterwards) |
| `external.*`, `auth.external.*` (hostnames) | the OTDS clients' redirect URLs are created once and never updated |
| `entityIndex.licenseServerHostname` | DIH writes `dih.cfg` into its volume on first start and never rewrites it |
| `auth.otdsws.adminEmail`, `adminPassword` | OTDS creates its admin user once, when it first creates its database. The API keeps logging in to OTDS with the values, so changing them later breaks that login |
| `dataEntity.customEntitySchema` (required properties) | see above |

Next: discover-install.
