---
name: discover-install
description: Install OpenText Discover (Knowledge Discovery) on Kubernetes with Helm from the discover chart, wait for it to start, and prove it works (pods, UI, OTDS login, API token). Covers prerequisite checks (including the ingress-nginx controller the chart requires, and replacing k3s Traefik), the helm command, what a normal start-up looks like and how long it takes, and the end-to-end checks. Use when asked to deploy, install, upgrade or verify a Discover deployment.
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

# Installing Discover

Write the values file first (discover-values). Then follow these steps in order.

## 1. Check the cluster

```
kubectl --context <ctx> get nodes                 # Ready
kubectl --context <ctx> get storageclass          # the class used in the values file exists
kubectl --context <ctx> get ingressclass          # the class used in the values file exists, CONTROLLER k8s.io/ingress-nginx
getent hosts discover.<ns>.<ip>.nip.io            # resolves to <ip>
getent hosts <licence-host>                       # the licence server resolves
kubectl --context <ctx> get ns <ns>               # should NOT exist yet (or be empty)
```

### The ingress controller must be ingress-nginx

The chart's ingresses use regex paths with `nginx.ingress.kubernetes.io/rewrite-target` and
`configuration-snippet` annotations. Only the community ingress-nginx controller understands them. Any other
controller (Traefik, which k3s installs by default, or the NGINX Inc. controller with `nginx.org/*` annotations)
ignores them: the UI and API return 404, and `api-0` crash-loops because api-init gets a 404 from OTDS.

```
kubectl --context <ctx> get pods -A | grep -iE 'traefik|ingress-nginx'      # ingress-nginx running, no traefik
kubectl --context <ctx> get svc -A | grep ingress-nginx-controller          # has an EXTERNAL-IP: the <ip> for the hostnames
kubectl --context <ctx> get cm -A | grep ingress-nginx-controller           # then, in that namespace:
kubectl --context <ctx> -n <ingress-ns> get cm ingress-nginx-controller -o jsonpath='{.data}'
```
The controller's configmap must have `allow-snippet-annotations: "true"` and `annotations-risk-level: Critical`.
Recent ingress-nginx versions block snippets by default, and the install then fails at the admission webhook.

If any of this is wrong, **stop and tell the user**. Fixing it changes the cluster, so it's theirs to do or approve.
On k3s:
1. Turn off Traefik: add `disable: [traefik]` to `/etc/rancher/k3s/config.yaml` and `sudo systemctl restart k3s`
   (needs root: ask the user to do it). Traefik's load balancer otherwise holds ports 80 and 443, and the
   ingress-nginx service never gets an EXTERNAL-IP.
2. Install ingress-nginx:
   ```
   helm upgrade --install ingress-nginx ingress-nginx --repo https://kubernetes.github.io/ingress-nginx \
     --kube-context <ctx> -n ingress-nginx --create-namespace \
     --set controller.allowSnippetAnnotations=true \
     --set controller.config.annotations-risk-level=Critical \
     --set controller.ingressClassResource.default=true
   ```
3. Run the checks above again. The `nginx` class is the one for the values file, and the controller's EXTERNAL-IP is
   the `<ip>` in the hostnames.

Check the values file sets the class on **every** ingress, not only `ingress.className` (discover-values, "Ingress
class: set it in all six places").

If the namespace already holds an old install, remove it first (discover-teardown). Old volumes keep old
configuration (see "First-install-only settings" in discover-values).

Render the chart once to catch values mistakes before installing:
```
helm template discover <chart> -n <ns> -f <values.yaml> -f <secrets.yaml> -f <images.yaml> > /dev/null && echo OK
```

## 2. Install

```
helm upgrade --install discover <chart> --kube-context <ctx> -n <ns> --create-namespace \
  -f <values.yaml> -f <secrets.yaml> -f <images.yaml> [-f <schema.yaml>] --timeout 20m
```

`helm` returns as soon as the objects exist. The pods take about **4–7 minutes** to start.

## 3. Wait for start-up

Wait with one command (it returns as soon as every pod is ready, or fails after 10 minutes):
```
kubectl --context <ctx> -n <ns> wait --for=condition=Ready pod --all --timeout=600s
```
Run it again if it times out while pods are still starting. Don't write your own watcher: a check that never
matches looks exactly like a stuck install. Then confirm with `kubectl --context <ctx> -n <ns> get pods` (15 pods,
all `1/1 Running`).

Normal on the way, so don't intervene:
- `analysis-0` (NiFi) is slowest, about 4 minutes.
- `api-0` stays in `Init:0/1` until NiFi is up. Its `api-init` container logs, in order: "Waiting for volume",
  "Waiting for schema initialized", "Waiting for license", "Waiting for init".
  Follow it with `kubectl -n <ns> logs api-0 -c api-init -f`.
- `api-schedule` restarts once or twice while it waits for `api`.
- `FailedToRetrieveImagePullSecret` warnings are harmless when the registry doesn't need a secret.
- api-init warning `Unknown keyword valueSchema` is harmless.

Stop and use discover-troubleshoot if you see `ImagePullBackOff`, `OOMKilled`, `CrashLoopBackOff`,
`idol-content-0` in `ContainerCreating` for more than 5 minutes, or api-init logging the same "Waiting for"
line for more than 10 minutes. **Never force-delete a pod** (see discover-teardown for why).

On the first install, check that api-init created the teams:
```
kubectl --context <ctx> -n <ns> logs api-0 -c api-init | grep -E 'creating (admin|global) team|create client'
```
You should see `creating admin team with owner: demo_user`, `creating global team ...` and
`create client: discover_ui` / `discover_api`. If you see "system is already initialized" on what should be a
fresh install, old data survived: tear down and reinstall.

## 4. Verify end to end

| Check | Command | Expect |
|---|---|---|
| Ingresses | `kubectl -n <ns> get ingress` | 10 ingresses, CLASS `nginx` (the values file's class) on every one |
| UI | `curl -s -o /dev/null -w '%{http_code}' http://discover.<ns>.<ip>.nip.io/discover/` | 200 |
| UI config | `kubectl -n <ns> exec deploy/discover-ui -- cat /usr/share/nginx/html/assets/config.json` | `"requireHttps": false`, issuer `http://auth.<ns>.<ip>.nip.io/OTDS/otdsws` |
| OTDS login page | `curl -s -o /dev/null -w '%{http_code}' 'http://auth.<ns>.<ip>.nip.io/OTDS/otdsws/login?response_type=code&client_id=discover_ui&redirect_uri=http%3A%2F%2Fdiscover.<ns>.<ip>.nip.io%2Fdiscover%2F&scope=openid&state=x'` | 200 (not an "invalid redirect URL" page) |
| API | token + `GET /api/users/current` (discover-api-access) | 200 with `{"entityId": ...}` |

Then tell the user to open `http://discover.<ns>.<ip>.nip.io/discover/` and log in as `demo_user`. They should see
the **Admin Project**. If they had the UI open before a reinstall, they need a hard refresh and a new login.

## Upgrades and restarts

- `helm upgrade` with the same command changes configmaps, but most pods do **not** restart by themselves. After
  changing hosts or auth values: `kubectl -n <ns> rollout restart sts/api deploy/discover-ui deploy/api-schedule`.
- After changing the entity schema, restart every pod that reads it:
  `kubectl -n <ns> rollout restart sts/api sts/analysis sts/analysis-reg deploy/api-schedule`.
- After a machine reboot the install recovers by itself in about 5 minutes. `analysis-0` shows `Error` and `api-0`
  shows `Unknown` for a while. Just wait.
