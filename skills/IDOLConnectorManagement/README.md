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

# IDOL Connector Management skills

Two agent skills for the IDOL Connector Management API (NCM): one to stand a deployment up, one to
move data through it.

| Skill | Purpose |
|---|---|
| [`ncm-deploy`](ncm-deploy/SKILL.md) | Stand up and configure a deployment - the Helm chart on a cluster, or the same containers under plain Docker - from published release artifacts, including connector resources and IDOL licensing. |
| [`ncm-migrate`](ncm-migrate/SKILL.md) | Drive the REST API to investigate source and destination repositories, map their metadata, configure connectors, targets and processing, then run, monitor and verify a migration. Reference material under [`ncm-migrate/reference/`](ncm-migrate/reference). |

Each skill is a directory holding a `SKILL.md` and any files it references. Nothing here depends on
anything else on your machine.

## Usage

Describe what you want and the agent should pick the right skill, or name one directly
(`/ncm-deploy`, `/ncm-migrate`). For example:

> Deploy the connector management API and the NiFi it drives on my Kubernetes cluster from the
> published release charts. My licence server is `licences.example.com` port 20000.

> Migrate the documents under `/Claims/2026` from our Documentum repository into an IDOL index, and
> show me the field mapping before you move anything.

> Show me what my connector can see in the source repository, and what metadata a document carries.

## What they expect of you

- **A reachable deployment**, for `ncm-migrate` - the public API on port 8080 by default. If you do
  not have one, `ncm-deploy` builds it first.
- **Credentials for the repositories you are migrating between**, and network access to them from
  wherever NiFi runs. The skills will tell you which properties a connector type needs; they cannot
  guess hostnames or passwords.
- **Decisions.** `ncm-migrate` deliberately stops and shows you the metadata mapping before it
  configures anything, because which fields are carried, converted or dropped is your call and it is
  far cheaper to correct before a run than after one.

## What they will tell you rather than assume

Both skills navigate to whatever your own deployment reports rather than restating a fixed list:
the OpenAPI spec it serves at `<host>/spec/public_api.yaml`, the connector, target and processing
types it offers at `/v1/types/*`, and the packaged chart's own documentation through
`helm show readme`. So the catalogue you get is the one your deployment actually has, and a
repository that is missing from it is a configuration decision that can be revisited rather than an
unsupported repository.
