---
name: discover-api-access
description: Call the OpenText Discover REST API and the OTDS admin API from the command line with curl - get an OAuth token for a Discover user (password grant), send the required Authorization and Isol-Tenant-Id headers, decode a token's issuer, and inspect or fix OTDS clients and users. Use when you need to check the Discover API, load data through it, or debug login, 401 or redirect problems.
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

# Discover API access

The commands below need `curl` and `python3` (with PyYAML for reading `secrets.yaml`).

The API is at `http://discover.<ns>.<ip>.nip.io/api/`. Every request needs two headers:
- `Authorization: Bearer <token>`, a token from OTDS;
- `Isol-Tenant-Id: <any short name>`, for example `demo`. Always send it.

## Get a token (password grant)

The API client is `auth.apiClient` (default `discover_api`) and its secret is `auth.apiClientSecret`. Read the
secret from the release, don't guess it:
```
SECRET=$(helm --kube-context <ctx> -n <ns> get values discover --all -o json | python3 -c 'import json,sys; print(json.load(sys.stdin)["auth"]["apiClientSecret"])')
```

```
AUTH=http://auth.<ns>.<ip>.nip.io/OTDS/otdsws
T=$(curl -s -X POST "$AUTH/oauth2/token" \
  --data-urlencode grant_type=password --data-urlencode client_id=discover_api \
  --data-urlencode "client_secret=$SECRET" \
  --data-urlencode username=demo_user --data-urlencode "password=$PASSWORD" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```
- Read the password from `secrets.yaml` (`api.init.additionalSecrets`) without printing it:
  `PASSWORD=$(python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["api"]["init"]["additionalSecrets"]["DEMO_USER_PASS"])' secrets.yaml)`
- Tokens last `auth.tokenExpiryTimeSeconds` (300 s by default), so get a fresh one for each batch of calls.

## Call the API

```
curl -s -w '\nHTTP %{http_code}\n' -H "Authorization: Bearer $T" -H 'Isol-Tenant-Id: demo' \
  http://discover.<ns>.<ip>.nip.io/api/users/current
```
Expect `200` and `{"entityId":"..."}`.

| Response | Meaning |
|---|---|
| 401 | Wrong token issuer. Decode the token (below). `iss` must be exactly `http://<auth.external.host>/OTDS/otdsws` |
| 503 from nginx | `api-0` isn't ready yet (still in api-init) |
| 400 `invalid entity type` | the entity type isn't in the deployed schema (discover-values, custom entity schema) |

Decode a token's claims without any extra tools:
```
python3 -c 'import sys,json,base64; p=sys.argv[1].split(".")[1]; p+="="*(-len(p)%4); c=json.loads(base64.urlsafe_b64decode(p)); print(c["iss"], c.get("name"))' "$T"
```

## OTDS admin API

Use this to check what OTDS really holds; the Helm values may differ from it. Admin user and password are
`auth.otdsws.adminEmail` (in the values) and `adminPassword` (in `secrets.yaml`), also in secret `otdsws-secrets`,
keys `OTDS_DIRECTORY_BOOTSTRAP_INITIALUSEREMAIL` and `..._INITIALPASSWORD`. Read the password without printing it.

```
TK=$(curl -s -X POST "$AUTH/rest/authentication/credentials" -H 'Content-Type: application/json' \
  -d "{\"userName\":\"$ADMIN\",\"password\":\"$ADMIN_PW\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["ticket"])')
curl -s -H "OTDSTicket: $TK" "$AUTH/rest/oauthclients/discover_ui"     # redirectURLs
curl -s -H "OTDSTicket: $TK" "$AUTH/rest/users/demo_user@discover/roles"
curl -s -H "OTDSTicket: $TK" "$AUTH/rest/systemconfig/whitelist"       # CORS origins
```
The admin user is the bare name (for example `discover.admin`), not `otadmin@otds.admin`.

- `discover_ui`'s `redirectURLs` must be `http://discover.<ns>.<ip>.nip.io/discover`. Anything else (for example
  `http://localhost/discover`) means the hostnames changed after the first install.
- api-init only **creates** OTDS clients, and leaves an existing one unchanged. To recreate them with the
  current hosts: `curl -X DELETE -H "OTDSTicket: $TK" "$AUTH/rest/oauthclients/discover_ui"` (and
  `discover_api`), then `kubectl -n <ns> rollout restart sts/api`. Check the result afterwards.
- A user's admin rights in the UI come from the `admin@discover` role (`compositeRoles: ["user","admin"]`).
