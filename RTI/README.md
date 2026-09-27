# Real-Time Intelligence Workshop — Attendee Materials

Labs and reference files for the **Real-Time Intelligence** half (morning) of
*Building Intelligent, Event-Driven Architectures with Fabric Real-Time Intelligence*.

## Scenario

Live Barcelona transit. A presenter-hosted feed publishes TMB's raw real-time API responses for bus stops and
metro stations around the conference venue (CCIB) and the city's main interchanges. You ingest them, flatten the
nested JSON into events, enrich, visualize, and act on them, entirely in the Fabric portal. No software to install.

## Folder guide

| Folder | Contents |
|---|---|
| `prerequisites/` | The short pre-event checklist. Read this first. |
| `modules/` | Hands-on labs, one per module, in delivery order. Theory is presented live and isn't included here. |
| `artifacts/` | KQL scripts, CSV reference data, notebook code and dashboard queries you paste from during the labs. |
| `assets/screenshots/` | Reference screenshots the labs link to. |

## Quick start

1. Read [`prerequisites/PREREQUISITES.md`](prerequisites/PREREQUISITES.md).
2. Start at [`modules/module-01-workspace-and-real-time-hub/lab-01-create-workspace-and-explore-real-time-hub.md`](modules/module-01-workspace-and-real-time-hub/lab-01-create-workspace-and-explore-real-time-hub.md).
3. Work through Modules 01–06 in order. Each lab's **Checkpoint** section tells you what should exist in your
   workspace before you move on.
4. The facilitator gives you four values at the start of Module 02: the Event Hubs **namespace name**, your
   **two hub names** (`tmb-ibus-1-65` + `tmb-metro-1-65`, or `tmb-ibus-66-130` + `tmb-metro-66-130`), the
   **listen-only shared access key**, and your personal **consumer group** (for example `user-017`). Write them
   down; every attendee has a different consumer group and only your own hubs have it.
