---
name: discover-teardown
description: Completely remove an OpenText Discover (Knowledge Discovery) Helm install from Kubernetes - release, pods, volumes (PVCs/PVs) and namespace - so the next install starts from empty state, without force-deleting anything. Use before a fresh install, when first-install-only settings must change, or when asked to uninstall, undeploy, clean up or reset Discover.
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

# Removing Discover

A clean removal leaves no volumes behind. Old volumes keep old configuration (DIH's `dih.cfg`, the entity graph,
OTDS clients), and a new install on top of them inherits it.

**This deletes all data in the namespace. Confirm with the user first**, naming the namespace and release.

## Rules

- **Never** use `--force` or `--grace-period=0`, and never remove finalizers. A force-deleted `idol-content` or
  `analysis` pod keeps running on the node and holding its volumes, which then reappear in the next install.
- Run each step and check its result before the next one. If a step doesn't finish, stop and investigate.
  Don't escalate to forcing.

## Steps

`C="--context <ctx>"`, namespace `<ns>`, release `discover`.

1. **Uninstall the release** and let pods stop gracefully:
   ```
   helm --kube-context <ctx> -n <ns> uninstall discover --wait --timeout 10m
   ```
2. **Wait for the pods to go.** Repeat every 15 s, for up to 5 minutes, until there are none:
   ```
   kubectl $C -n <ns> get pods
   ```
   A pod still `Terminating` after 5 minutes is usually a postStart hook that never returned. See "A content pod
   that won't terminate" in discover-troubleshoot. Don't force it.
3. **Delete the volumes.** StatefulSet PVCs are not part of the release, so helm leaves them:
   ```
   kubectl $C -n <ns> delete pvc --all
   kubectl $C -n <ns> get pvc        # repeat until empty
   ```
   A PVC that stays `Terminating` is still mounted by something (pvc-protection). Look for an orphaned container
   (step 2).
4. **Delete the namespace:**
   ```
   kubectl $C delete namespace <ns> --timeout=3m
   kubectl $C get namespace <ns>      # NotFound
   ```
   If it stays `Terminating`, `kubectl $C get namespace <ns> -o jsonpath='{.status.conditions[*].message}'` says
   what is left. Resolve that resource. Don't strip finalizers.
5. **Check the persistent volumes have been released.** Dynamic provisioners delete them shortly after their PVC:
   ```
   kubectl $C get pv | grep '<ns>/'      # repeat until nothing is printed (up to 2 minutes)
   ```
6. **Check for orphaned processes** (only if the cluster runs on this machine):
   ```
   pgrep -af '[c]ontent_postStart.sh'    # should print nothing (the [c] stops pgrep matching its own shell)
   ```

Then install again with discover-install.
