# Module 00 Theory: Kickoff — Event-Driven Architectures with Fabric RTI

**Duration:** 10 minutes
**Format:** Presenter-led framing, no hands-on activity.

**Learning objectives**
- Know the shape of the whole day: RTI building blocks this morning, Fabric IQ's ontology/agent layer this afternoon.
- Understand what "event-driven" means beyond "streaming telemetry": events as the trigger for *any* action, including data-platform automation.
- Know the single scenario every morning module builds on, and the three values you need to write down before Module 02.

## Welcome

This is a full-day, hands-on workshop in two halves. This morning (Johan) is **Real-Time Intelligence**: getting
events in, storing and querying them, visualising them, and reacting to them. This afternoon (Brian) is **Fabric
IQ**: putting an ontology and AI agents on top of exactly the kind of pipeline you build this morning. The
afternoon assumes you know Eventstream, Eventhouse and Activator at a working level — that's the morning's job.

## Event-driven, in one slide

An **event** is a fact about something that happened, with a timestamp: *"bus H16 is predicted at stop 1497 in 4
minutes, as of 08:15:02"*, *"a file landed in `Files/reference/`"*, *"pipeline X failed"*. Event-driven
architecture means systems **react to events as they arrive** instead of polling or running on a clock.

Three things follow from that, and each maps to a Fabric item:

| Need | Fabric RTI item | This morning |
|---|---|---|
| Get events in, shape them, route them | **Eventstream** (via **Real-Time hub**) | Module 02 |
| Keep them, query them at any grain, enrich them | **Eventhouse** (KQL) | Module 03 |
| See them | **Real-Time Dashboard** | Module 04 |
| Detect a condition and *do something* | **Activator** | Module 05 |
| Apply the same pattern to the platform itself (files, jobs, items) | **Fabric events** + Activator | Module 06 |

The last row is the one people forget. "Event-driven" isn't only IoT and clickstreams. A file landing in OneLake
is an event. A notebook failing is an event. A new item being created in a workspace is an event. The same
detect-and-act engine handles all of them, and Module 06 is where we make that concrete.

## The scenario: live Barcelona transit

Most of you got here by metro L4 to El Maresme | Fòrum, or on bus H16 or 7. All morning we work with the **live
TMB arrival predictions** for the stops around this building and the city's main interchanges: which bus is
next, in how many minutes, at which stop, and how that changes minute by minute.

A presenter-hosted Azure Function polls TMB's iBus and metro APIs every 30–60 seconds and publishes each raw
response, as it came off the wire, to Azure Event Hubs. You each connect your own Eventstream to that feed. By
13:00 you will have:

1. The raw API responses flowing into your own Eventhouse, and a flattened, per-bus version of the same stream
   built with no-code operators (Module 02).
2. Those events flattened again inside the database, enriched with stop names, coordinates and line details, plus
   a "latest prediction per stop and line" view you authored yourself (Module 03).
3. A live dashboard with a map of wait times across the city (Module 04).
4. An alert that fires when your bus home from the Fòrum is running late, and another that fires when a stop
   goes silent (Module 05).
5. A notebook that runs *by itself* the moment a reference file lands in your lakehouse (Module 06).

This afternoon, Brian swaps buses for freezers and shows you how an ontology turns "stop 1497, line H16, 4 min"
style facts into business entities an AI agent can reason over. Same building blocks, one level up.

## Four values to write down (given at the start of Module 02)

- The Event Hubs **namespace name**
- **Your two hub names**: `tmb-ibus-1-65` + `tmb-metro-1-65`, or `tmb-ibus-66-130` + `tmb-metro-66-130` (the feed
  is duplicated into two hubs because a hub allows 100 consumer groups and there are 120 of us)
- The listen-only **shared access key** (name + value)
- **Your** consumer group, `user-NNN`. Every attendee has a different one; do not use `$Default`.

## How every module works

Teach, show, do. Each component gets a short theory block, then a live click-through on my workspace, then you
build the same thing on yours with an expected-result check after every step. If your screen doesn't match the
✅ line, stop and raise a hand; two helpers are walking the room.

## Housekeeping

- Breaks after Module 03 (~2:00) and Module 05 (~3:10). Lunch between the halves.
- Everything is in the Fabric portal. Nothing to install this morning; the afternoon installs a CLI live.
- Module 07 ends with **parking your workspace** (pause streams, stop rules). Please don't skip it; the afternoon
  runs on the same capacity.

> 🎤 Facilitator note: keep this to ten minutes. The one idea to land is the table above, especially the last
> row. Everything else is repeated inside the modules.

<!-- facilitator: ask for a show of hands on "who has built an Eventstream before" and "who has written KQL" — it tells you how much of Module 02/03's theory to compress. -->

Continue to [Module 01: Workspace & Real-Time hub](../module-01-workspace-and-real-time-hub/01-theory-rti-landscape.md).
