# Module 07: Wrap-up and Handoff to Fabric IQ

**Duration:** 7 minutes
**Format:** Three required clicks per attendee first ("park your workspace"), then the recap.

**Learning objectives**
- See the morning's build end to end and name the pattern it implements.
- Park the `RTI Transit` workspace so the afternoon's capacity isn't consumed by idle streams.
- Know what the Fabric IQ half assumes from this morning, and where to keep learning.

## What you built this morning

1. **Workspace & hub** (Module 01): `RTI Transit`, `TransitEventhouse`, `TransitLakehouse`; a tour of Real-Time hub.
2. **Ingest & shape** (Module 02): `BusArrivalsEventstream` reading the shared TMB feed through *your* consumer
   group; raw envelopes → `BusArrivalsRaw` (direct); **flattened three arrays deep** with Manage fields + Expand,
   then a 1-minute tumbling aggregate → `BusWaitByStopMinute` (processed); the same flattening plus the
   minutes arithmetic in the **SQL operator** → venue-only derived stream `ForumNextBus`; a second stream created
   from the hub for metro.
3. **Store, flatten again, enrich, summarise** (Module 03): reference CSVs as `StopsDim`/`LinesDim`; an **update
   policy** (`EnrichBusArrivals()`: `mv-expand` + `lookup` + `Rank` → `BusArrivalsEnriched`); a **materialized
   view** (`BusNextArrivalLatest`); saved analysis queries; the four-level metro flatten as a stretch.
4. **See** (Module 04): `TransitOpsDashboard` with a map of wait times, a parameter-driven time chart, a venue
   table, live refresh.
5. **Act** (Module 05): `TransitAlerts` with a sustained per-line threshold rule and a heartbeat rule.
6. **Act on the platform** (Module 06): `TransitAutomation` running `LoadStopsReference` the moment a file lands
   in `Files/reference/`.

**Ingest → store/enrich → visualise → detect → act**, applied first to telemetry and then to the platform
itself. That's the pattern; the components are just how Fabric spells it.

## Park your workspace (required, 3 minutes)

The afternoon's Ontology and Data Agent labs run on the **same P1 capacity** as this workspace, shared with the
other attendees on it, and a P1 can't be resized on the day. Idle streams
and a live-refreshing dashboard keep consuming it. Do these now:

1. **Open** `BusArrivalsEventstream` (Live view). **Click** the Event Hubs source node **TMBBusArrivals** and
   **Pause** it (if the option is on the destination nodes instead, **Pause** each destination:
   `BusArrivalsRaw`, `BusWaitByStopMinute`, `ForumNextBus`, `TransitAlertsDest`). **Repeat** for
   `MetroArrivalsEventstream`.
   > ✅ Expected result: the nodes show a paused state; **Data insights** stops climbing.
2. **Open** `BusArrivalsEventstream` → alert icon on `TransitAlertsDest` → **Rules** pane → **toggle off** every
   rule. **Open** `TransitAutomation` → **Stop** `Reference file landed`.
3. **Close** the `TransitOpsDashboard` browser tab (live refresh only runs while it's open).

Everything is preserved; **Resume** and **Start** bring it all back after the conference. Brian's Module 08
lab checks this state before you provision the `Fabric IQ` workspace.

*Adapted from: [Pause and resume data streams](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/pause-resume-data-streams)*

## What this afternoon assumes from you

Brian's Fabric IQ half won't re-teach any of the morning. Specifically it assumes you can:

- Read an eventstream canvas and its Live-view data preview (his Lab 02 uses a *custom endpoint* source and a
  Python generator instead of Event Hubs; same UI otherwise).
- Recognise a raw → enriched table pair and an `arg_max` materialized view (`FreezerTelemetryRaw` →
  `FreezerTelemetryEnriched` is the freezer version of what you built in Module 03).
- Understand an Activator rule with a threshold and a sustained duration (`Freezer running warm`, above -12 °C
  for 5 minutes, is the ontology version of `Long wait at the Fòrum`).

What's new this afternoon: the **Ontology** item (entities, relationships, bindings to your Lakehouse and
Eventhouse), the **Data Agent** and **Operations Agent**, and rules authored in business language on entities
instead of on stream fields. Different data (freezers, not buses), a fresh `Fabric IQ` workspace, one layer up.

## Keep exploring

- [Implement Real-Time Intelligence with Microsoft Fabric](https://learn.microsoft.com/training/paths/explore-real-time-analytics-microsoft-fabric/) — the Microsoft Learn path covering everything in this half.
- [Real-Time Intelligence tutorial](https://learn.microsoft.com/fabric/real-time-intelligence/tutorial-introduction) — Microsoft's end-to-end tutorial, same shape as this morning with sample data.
- [Kusto Query Language reference](https://learn.microsoft.com/kusto/query/) and the [KQL Detective Agency](https://detective.kusto.io/) for practice.
- [Eventstream connectors](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-manage-eventstream-sources), [Activator detection settings](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-detection-conditions), [Business events (preview)](https://learn.microsoft.com/fabric/real-time-intelligence/business-events/).
- TMB's [developer portal](https://developer.tmb.cat/) if you want to rebuild the feed yourself: the event
  schema is in [`docs/data-feed-contract.md`](../../docs/data-feed-contract.md).

## Cleanup after the conference

If you don't want to keep the scenario: delete the `RTI Transit` workspace (removes everything in it). If you
do: **Resume** the two eventstreams and **Start** the rules; the feed is switched off after the event, so
point the Event Hubs source at your own producer or switch it to the **Sample data → Buses** source to keep
experimenting.

> 🎤 Facilitator note: don't let the recap eat the parking step. If time is tight, do the three parking clicks
> first, together, then recap while people pack up for lunch.

<!-- facilitator: tell Brian the headcount and whether anyone is on a shared capacity or skipped parking. -->
