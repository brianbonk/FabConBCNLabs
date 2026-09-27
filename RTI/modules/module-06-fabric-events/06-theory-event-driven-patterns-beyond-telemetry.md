# Module 06 Theory: Event-Driven Architectures Beyond Telemetry

**Duration:** 10 minutes (7 concepts + 3 live demo)
**Prerequisites:** Modules 02–05 complete.

**Learning objectives**
- Recognise that the detect-and-act pattern applies to *platform* events (files, jobs, items, capacity) as well as to telemetry.
- Know the Fabric and Azure event sources available in Real-Time hub and what each is for.
- Know five reusable event-driven patterns and which Fabric pieces implement each.
- Understand where **Business events** (preview) and the **custom endpoint** destination fit.

## The same engine, a different kind of event

Everything so far reacted to *bus predictions*. But look at Real-Time hub's **Fabric events** page: **OneLake
events** (a file or folder was created, deleted, renamed), **Job events** (a notebook, pipeline or refresh
started, succeeded, failed), **Workspace item events** (an item was created, updated, deleted), **Capacity
events** (utilisation, throttling). Plus **Azure events**: Blob Storage created/deleted. Each of these is a
CloudEvents-shaped record with a `subject`, a `type`, a timestamp and a payload, and you can subscribe with the
same two tools: send it to an **Eventstream**, or **Set alert** on it with Activator.

## Five patterns, and the Fabric pieces that implement them

| Pattern | Trigger | Reaction | Fabric pieces | Today |
|---|---|---|---|---|
| **Event-driven ETL** | File lands in OneLake / Blob | Load or transform it | OneLake or Blob event → Activator → **Run notebook / pipeline / copy job** | **Lab 06 Part B–C** |
| **Operational alerting** | Job fails / runs long | Notify, retry | Job event → Activator → Teams/email, or → **Run pipeline** to retry | Mentioned; 2-minute demo if time |
| **Governance / audit trail** | Item created, updated, deleted | Record it, react to policy breaches | Workspace item event → Eventstream → **Eventhouse** table (+ Activator on "Warehouse created in Finance workspace") | **Lab 06 Part D** (presenter demo) |
| **Fan-out to external consumers** | Any stream | Let other systems subscribe | Eventstream **Custom endpoint destination** (Event Hubs/Kafka-compatible) or Activator → **Power Automate** | Theory only |
| **Business events** (preview) | A *business-level* fact ("order shipped", "long wait detected") | Decoupled downstream subscribers | Activator action **Publish business event** → Real-Time hub → subscribers; Eventhouse is the default store | Theory only |

Notice the shape is identical every time: **source of events → (optional shaping) → detect → act**. What changes
is only what "event" and "act" mean.

## Why this matters architecturally

- **Choreography instead of orchestration.** A pipeline that runs at 02:00 "because the file is usually there
  by then" is a schedule pretending to be a dependency. A pipeline that runs *because the file arrived* is the
  dependency, made explicit, with no idle waiting and no race.
- **Decoupling.** The producer (whoever drops the file, whoever runs the job) needs to know nothing about the
  consumers. Add a second consumer by subscribing, not by editing the producer.
- **One skill set.** Your team already learned Eventstream/Eventhouse/Activator for telemetry this morning. The
  platform-automation use cases cost nothing extra to learn.

## What's in preview vs GA (as of Sept 2026)

- GA: Eventstream sources for OneLake events, Job events, Workspace item events, Capacity overview events,
  Azure Blob Storage events; Activator **Run Fabric item** actions; **Set alert** from Real-Time hub.
- Preview: **Business events**, **Publish business event** action, passing **parameters** to Fabric items from
  Activator, Capacity *operation* events, Spark-notebook Eventstream destination.

Design with GA pieces; prototype with preview ones.

## Live demo before the lab (3 minutes, instructor workspace)

1. Real-Time hub → **Fabric events**: hover **OneLake events**, click **Set alert**, walk the **Add rule** pane
   (source events, filter on `subject`, action **Run notebook**) and close it without saving.
2. Upload a file to your own `Files/reference/`, switch to the **Monitor** hub, and leave it on the projector.
   By the time attendees reach Part C, your run has appeared; that's the proof it works before they try.

## Link to the afternoon

This afternoon's **Operations Agent** is the natural extension of this module: instead of you writing the rule,
an agent watches ontology entities against a goal you describe in natural language and *proposes* the action,
with Activator underneath doing what it did for you today.

*Sources: [Real-Time hub overview](https://learn.microsoft.com/fabric/real-time-hub/real-time-hub-overview),
[Set alerts on OneLake events](https://learn.microsoft.com/fabric/real-time-hub/set-alerts-fabric-onelake-events),
[Fabric workspace item events source](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-source-fabric-workspace),
[Trigger Fabric items](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-trigger-fabric-items),
[Activator introduction — orchestration patterns](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-introduction)*

Continue to [Lab 06: OneLake events trigger automation](lab-06-onelake-events-trigger-automation.md).
