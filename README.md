# Fabric IQ Workshop — Attendee Materials

Labs, setup, and reference data for the **Fabric IQ** half of
*Building Intelligent, Event-Driven Architectures with Fabric Real-Time Intelligence*.

This is the attendee-facing subset of the presenter's source repo, published automatically before each
event — see [`prerequisites/PREREQUISITES.md`](prerequisites/PREREQUISITES.md) for what (little) you need
to know before you arrive.

## Scenario

Everything here — labs, sample data, the provisioning script — runs on a single connecting narrative:
**retail cold-chain monitoring**. Live freezer temperature telemetry (Eventstream/Eventhouse) is grounded
with business context (Customer/Store/Freezer entities in a Fabric IQ Ontology), and agents are built on
top to reason over both.

## Folder guide

| Folder | Contents |
|---|---|
| `prerequisites/` | The short pre-event checklist — read this first. |
| `setup/` | The provisioning script (`provision_fabric_iq.py`) that creates your "Fabric IQ" workspace and its RTI plumbing (Lakehouse, Eventhouse, Eventstream, notebook) via the Fabric CLI (`fab`). |
| `artifacts/` | Fabric item definitions and sample data the provisioning script uses. |
| `modules/` | Theory + hands-on lab content, one pair per module, in delivery order. |
| `assets/screenshots/` | Reference screenshots the labs link to for each step. |

## Quick start

1. Read [`prerequisites/PREREQUISITES.md`](prerequisites/PREREQUISITES.md) — it's short.
2. Start at [`modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md`](modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md).
   Part A of that lab walks you through cloning this repo, installing dependencies, and running the
   provisioning script live.
3. Work through Modules 00–06 in order — each one's "Checkpoint" section tells you what should exist in
   your workspace before you move on.
