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

# What this deployment can be configured to serve

Snapshot of the types published for the **26.4 development channel**, taken 2026-08-21 by
listing the resource provider's Artifactory tree.

**Why this exists.** `/v1/types/*` reports what a deployment *is* serving. Nothing reports what
it *could* serve, so "can we migrate out of Box?" has no API answer - this is that answer. It is
a dated snapshot, not a contract: types are published between releases, so read an absence here
as "check" rather than "unsupported".

One row per type, so it diffs cleanly and can be regenerated mechanically. Connector builds are
named `connectors-nifi-<lowercase type>`, so the id list comes from:

```sh
curl -s "<baseurl>/" | grep -o 'href="connectors-nifi-[^"/]*/"'
```

A type needs an override only where its published directory predates its type name. `-` means
naming the id is the whole configuration.

## Connectors

Name in `..._CONNECTOR_TYPES`. **Notes** flags a type whose configuration does not follow
from its name; a blank note means nothing about this one is unusual.

| Type | Overrides | Notes |
|---|---|---|
| `Aem` | `_DIR=connectors/adobe_aem` |  |
| `AmazonS3` | - |  |
| `AzureAD` | - |  |
| `AzureBlob` | - |  |
| `Box` | - |  |
| `Chatter` | - |  |
| `Cmis` | - |  |
| `Confluence` | `_DIR=connectors/confluence_rest` |  |
| `Database` | - |  |
| `Documentum` | - | docbroker host and port go inside `DfcProperties`, whose value is the content of a `dfc.properties` file (`dfc.docbroker.host[0]=`, `dfc.docbroker.port[0]=`) - there is no separate host or port property |
| `Dropbox` | - |  |
| `Drupal` | - |  |
| `DynamicsCRM` | - |  |
| `ExchangeOData` | `_DIR=connectors/exchange_odata` |  |
| `FTP` | - |  |
| `FacebookWorkplace` | - |  |
| `FileNet` | `_DIR=connectors/filenetp8java4.x` |  |
| `FileSystem` | `_DIR=connectors/newfilesystem` |  |
| `GitHub` | - |  |
| `GoogleCalendar` | - |  |
| `GoogleChat` | - |  |
| `GoogleCloudStorage` | - |  |
| `GoogleDirectory` | - |  |
| `GoogleDrive` | - |  |
| `GoogleMail` | - |  |
| `Guidewire` | - |  |
| `Imap` | - |  |
| `InfoArchive` | - |  |
| `Jama` | - |  |
| `Jira` | - |  |
| `Jive` | - |  |
| `Kafka` | - |  |
| `Lithium` | - |  |
| `MFiles` | - |  |
| `Mmap` | - |  |
| `MongoDB` | - |  |
| `Objective` | `_DIR=connectors/objectiverest` |  |
| `Octane` | - |  |
| `OfficePlanner` | - |  |
| `OfficeTeams` | - |  |
| `OneDrive` | `_DIR=connectors/skydrive` |  |
| `OpenText` | - |  |
| `OpenTextCoreContent` | - |  |
| `OpenTextEDocs` | - |  |
| `OpenTextMediaManagement` | - |  |
| `Qam` | `_DIR=connectors/qamconnector` |  |
| `Records365` | - |  |
| `Rss` | - |  |
| `Salesforce` | `_BUILD=connectors-nifi-salesforcecpp`, `_DIR=connectors/salesforce_cpp` |  |
| `Seedlist` | `_BUILD=connectors-nifi-ibmseedlist`, `_DIR=connectors/ibm_seedlist` |  |
| `ServiceNow` | - |  |
| `SharePointOData` | `_DIR=connectors/flyingPig` |  |
| `Slack` | - |  |
| `Snowflake` | - |  |
| `StackExchange` | - |  |
| `TeamBinder` | - |  |
| `Telegram` | - |  |
| `Telligent` | - |  |
| `Twitter` | - |  |
| `Vantara` | - |  |
| `Web` | - |  |
| `Webex` | - |  |
| `Yammer` | - |  |
| `Zendesk` | - |  |
| `Zoomchat` | - |  |

## Targets

Name in `..._TARGET_TYPES`. Separately, **any put-capable connector type is offered as a target**
without appearing here - that is how repository-to-repository migration works; see `ncm-migrate`.

`UserSecurity` is the only type anywhere needing a non-default `_PLATFORM`: its NiFi resources
really are published under `common`. Do not copy that to another type - a connector's *own*
build often has a `common` platform for its Java artefacts, which is not where its NiFi
resources live.

| Type | Overrides |
|---|---|
| `AMQP` | - |
| `AwsFirehose` | - |
| `Databricks` | - |
| `DigitalSafe` | - |
| `IDOL` | - |
| `IDOLGraph` | - |
| `InfoArchive` | - |
| `Kafka` | - |
| `Metastore` | - |
| `OGS` | - |
| `Vertica` | - |
| `UserSecurity` | `_BUILD=connectors-documentsecurity`, `_DIR=connectors/documentSecurity`, `_PLATFORM=common` |

## Processing

Name in `..._PROCESSING_TYPES`. **Dyn** marks types accepting user-named properties beyond their
declared ones. `AnalyzeMedia` and `KeyViewRouteMedia` are published by NCM itself and are listed
whether or not they appear in a `_TYPES` list; they are also the only flow-backed definitions -
every other type here is a single processor.

| Type | Dyn | Notes |
|---|---|---|
| `AWSTranslate` | - |  |
| `AnalyzeMedia` | - | flow-backed; needs an IDOL Media Server |
| `BatchCallback` | yes |  |
| `CategorizeDocument` | - |  |
| `ContentFromHTML` | yes |  |
| `ContentIntoSections` | - |  |
| `ConvertCSVToDocuments` | - |  |
| `ConvertIDXToDocuments` | - |  |
| `ConvertJSONToDocuments` | - |  |
| `ConvertXMLToDocuments` | - |  |
| `DeduplicateDocuments` | - |  |
| `DetectContentLanguage` | - |  |
| `Eduction` | yes | needs a grammar file in `ResourceFiles` (see below) |
| `EnrichFromDVLA` | - |  |
| `EnrichFromLookup` | yes |  |
| `EnrichUserFromAzureAD` | - |  |
| `EnrichUserFromLDAP` | - |  |
| `ExecuteDocumentLua` | yes |  |
| `ExecuteDocumentPython` | yes |  |
| `FilenameFromMetadata` | yes |  |
| `FilterBadContent` | - |  |
| `HashDocument` | - |  |
| `KeyViewExportToHtml` | - |  |
| `KeyViewExportToXml` | - |  |
| `KeyViewExtractFiles` | - |  |
| `KeyViewFilterDocument` | - |  |
| `KeyViewRouteMedia` | - | flow-backed |
| `KeyViewRouteOnFileType` | yes |  |
| `MediaAnalysis` | - |  |
| `MergeContentPages` | - |  |
| `NISTRDSFilter` | - |  |
| `QueryIDOL` | yes |  |
| `RMSDecrypt` | - |  |
| `RMSEncrypt` | - |  |
| `RenderHTML` | yes |  |
| `SmartCipherDecrypt` | - |  |
| `SmartCipherEncrypt` | - |  |
| `StandardizeMetadata` | - |  |
| `TextToDocuments` | - |  |
| `TrainCategory` | - |  |
| `WriteDocument` | - |  |

Eduction grammars ship inside the eduction NAR. A running deployment lists them, with the entities
each defines and the value `ResourceFiles` takes for it, at
`GET /v1/types/processing/Eduction/grammars`; additional grammar packs installed in NiFi appear
there too, under their own `group`.

## NARs

| Id | Overrides |
|---|---|
| `idol-nifi-aci-nar` | - |
| `idol-nifi-core-nar` | - |
| `idol-nifi-eduction-nar` | - |
| `idol-nifi-indexing-nar` | - |
| `idol-nifi-keyview-nar` | - |
| `idol-nifi-scripting-nar` | - |
| `idol-nifi-services-nar` | - |
| `idol-nifi-viewer-nar` | - |
| `idol-nifi-connector-utils-nar` | `_DIR=connectors/nifiConnectorUtils`, `_BUILD=connectors-nificonnectorutils-nifi2`, `_NARTARGETDIR=modules/nar/target` |
| `idol-nifi-media-nar`, `idol-nifi-media-api-nar` | `_BUILD=mediaserver-nifi2`, `_DIR=servers/mediaserver` |

A connector's own NAR is **not** listed here - it is fetched from the connector's own directory
automatically. Adding one to `nar.types` resolves it against the wrong coordinates and silently
does nothing.
