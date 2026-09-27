# Module 02 Theory: Eventstream — Sources, Streams, Operators, Destinations

**Duration:** 15 minutes (10 concepts + 5 live demo)
**Prerequisites:** Module 01 complete (`RTI Transit`, `TransitEventhouse`, `TransitLakehouse` exist).

**Learning objectives**
- Describe an eventstream as *sources → default stream → (operators →) destinations*, and know what a derived stream is.
- Pick the right Eventhouse ingestion mode (direct vs processed) for a given need.
- Know the operator catalogue and the one window type we use today (tumbling).
- Understand why every attendee needs their own consumer group on the shared Event Hubs feed.

## The mental model

```
 [source] ──► default stream ──┬─► [destination: Eventhouse, direct ingestion]   (raw envelopes, as-is)
                               │
                               ├─► [Manage fields] ─► [Expand] ─► [Expand] ─► [Expand] ─► [Manage fields] ─► [Group by 1-min] ─► [Eventhouse, processed]
                               │    pick arrays      stops        routes      buses       rename + type      min arrival instant    (flat aggregate)
                               │
                               └─► [SQL operator: flatten + (arrival − now) / 60000 + venue filter + 1-min window] ─► derived stream "ForumNextBus" ─► (Module 05)
```

The middle and bottom of that picture are the lab's real content. The feed delivers **one envelope per API
response** (`source`, `key`, `fetchedAt`, `payload`), and inside `payload` is TMB's JSON: a stop, its lines, the
next buses per line, three arrays deep, with arrival times as absolute epoch instants. That's what most real APIs
give you, and it is useless to a rule or a chart until each innermost element becomes its own flat, typed event with
a number a human cares about ("4 minutes"). Eventstream gives you two ways to get there: the no-code **Manage
fields** (reach into nested objects; pick, rename, re-type) and **Expand** (one event holding an array of N becomes
N events), which can flatten but can't subtract two fields; and the **SQL operator** (preview), which does the same
flattening with `CROSS APPLY GetArrayElements()` and adds arithmetic, windows and filters in one query. The lab
builds both, so you see the same result from clicks and from code.

- **Source**: where events come from. Today: **Azure Event Hubs** (GA, the workhorse connector). The gallery has
  ~30 others: IoT Hub, Service Bus, Kafka, Pub/Sub, Kinesis, MQTT (preview), database CDC feeds, an **HTTP**
  poller (preview), sample data, and every Fabric/Azure event type.
- **Default stream**: the raw feed inside the eventstream, exactly as received.
- **Operators**: no-code transformations placed *between* the stream and a destination: **Manage fields**
  (pick nested fields, rename, remove, change type, add computed fields with built-in string/date/math functions
  such as `Left`, `Substring`, `Replace`, `RegExMatch`; no concatenation), **Expand** (one event per array element),
  **Filter**, **Aggregate**, **Group by** (aggregations over a time window, grouped by fields), **Union**, **Join**
  (stream-to-stream), and a **SQL operator** (preview; Stream Analytics SQL, so `GetArrayElements`, arithmetic,
  `TumblingWindow`, `CASE`) when the no-code shapes aren't enough. The SQL operator runs alone in its path: it
  can't be chained with the other operators, and it needs new destination nodes of its own.
- **Derived stream**: the output of an operator chain published as a *named stream* of its own. It shows up in
  Real-Time hub, can be paused/resumed, and can be consumed by other destinations or other teams without them
  knowing how it was produced. Think "curated topic".
- **Destinations**: **Eventhouse**, **Lakehouse**, **Activator**, **Custom endpoint** (let external apps read
  the stream, i.e. fan-out to consumers outside Fabric), **Derived stream**, **Spark notebook** (preview).

## Two ways into an Eventhouse

| Mode | What happens | Use when |
|---|---|---|
| **Direct ingestion** | Events are handed to the KQL database's own ingestion; you configure the table + mapping in the Eventhouse **Get data** wizard after publishing | You want the raw stream, unchanged, with Kusto doing any shaping later (update policies, materialized views). **Default choice for raw tables.** |
| **Event processing before ingestion** | Operators run in the eventstream; the result is written to a table you name in the destination dialog | You want to *reduce* before storing (aggregates, filters) or *reshape* (flatten) and don't need the raw rows |

Today's raw table (`BusArrivalsRaw`) uses direct ingestion and keeps the envelope's `payload` as a `dynamic`
(JSON) column; the per-minute aggregate (`BusWaitByStopMinute`) uses processed ingestion and is flat. Storing both
is a common pattern: raw for forensics, replay and in-database flattening (Module 03), aggregate for cheap dashboards.

## Windows, briefly

**Group by** needs a window. **Tumbling** windows are fixed, non-overlapping (00:00–00:59, 01:00–01:59…): one
row per stop/line per minute. **Hopping** overlap, **sliding** advance per event, **session** close after a
gap, **snapshot** groups events with identical timestamps. Tumbling is the right default for "per minute"
summaries and it's what we use. A window only emits when it *closes*, so the preview shows nothing for the first
60–90 seconds. That's expected.

## Why consumer groups (and your user range) matter today

Everyone reads the *same* feed. Event Hubs delivers each partition to **one** reader per consumer group. If two
eventstreams share `$Default`, they steal partitions from each other and both see gaps. Your personal `user-NNN`
group gives your eventstream its own cursor over the whole hub. A hub holds at most 100 consumer groups, so with
120 of us the feed is duplicated into two hubs per feed: users 1–65 read `tmb-ibus-1-65` / `tmb-metro-1-65`,
users 66–130 read `tmb-ibus-66-130` / `tmb-metro-66-130`; your seat sheet says which. The key you're given is
**listen-only**; nobody in the room can write to the feed.

## What this morning's stream looks like

```json
{ "source": "tmb.ibus", "key": "1265", "fetchedAt": "2026-09-23T08:47:01.741901+00:00",
  "payload": { "timestamp": 1790153221713,
    "parades": [ { "codi_parada": "1265", "nom_parada": "Pg de Sant Joan - Còrsega",
      "linies_trajectes": [
        { "nom_linia": "H8",  "codi_trajecte": "2081", "id_sentit": 2, "desti_trajecte": "Ernest Lluch",
          "propers_busos": [ { "temps_arribada": 1790153253000, "id_bus": 6405 }, { "temps_arribada": 1790154085000, "id_bus": 6802 } ] },
        { "nom_linia": "47",  "codi_trajecte": "0471", "id_sentit": 2, "desti_trajecte": "Pg. Marítim",
          "propers_busos": [ { "temps_arribada": 1790153675000, "id_bus": 5426 }, { "temps_arribada": 1790154287000, "id_bus": 5010 } ] } ] } ] } }
```

Three things to notice. It's **one event per stop**, not per bus: the buses are an array three levels down
(`parades → linies_trajectes → propers_busos`). There is **no "minutes" anywhere**: `temps_arribada` is an epoch
instant and so is TMB's `timestamp`; the wait is their difference. And apart from the stop's name, the identifiers
are **codes**: a line name, a route id, no coordinates, no zone, no line origin/destination. The lab turns this into
`StopCode`, `LineCode`, `MinutesToArrival` events, and Module 03 adds the meaning from reference tables. This
afternoon Brian makes the same "codes and numbers tell you nothing" point about a `FreezerId` and a temperature;
keep the parallel in mind.

## Live demo before the lab (5 minutes, instructor workspace)

Click through the lab path once, narrating the UI, before anyone touches their own workspace:

1. Open the pre-built `BusArrivalsEventstream` in **Edit** mode. Point at the source node: "this is the Event
   Hubs connection; you'll type a namespace, the hub names from your sheet, the listen key, and *your* consumer group".
2. **Data preview** on the stream node: expand one `payload` cell. "One event, one stop, three lines, six buses,
   three arrays deep. Two epoch clocks and no minutes."
3. Click the three **Expand** nodes in turn, **Test result** each time: "stops, then routes, then buses; the row
   count grows at each step". Click the last **Manage fields** node: show the nested picker
   (`Stops → linies_trajectes → propers_busos → temps_arribada`), a rename, a type change. "This is the whole
   flattening job. What it can't do is subtract."
4. Click the **Group by** node: aggregations, group-by fields, the tumbling window. "Nothing appears for a minute;
   that's the window closing, not a bug. Minimum arrival instant = the next bus."
5. Open the **SQL operator**'s editor: point at the three `CROSS APPLY GetArrayElements` and at
   `(ArrivalMs - PolledMs) / 60000.0`. "Same flattening, in code, plus the arithmetic. This is the branch the
   alerts read from." Note it hangs directly off the stream.
6. Click the two Eventhouse destinations: one **Direct ingestion** (raw envelopes, `payload` stays JSON), one
   **Event processing before ingestion** (flat aggregate). Switch to **Live** view: **Data insights** on a
   destination, and the **ForumNextBus** derived stream. "That's what you build in the next 35 minutes."

> 🎤 Facilitator note: the one thing to protect in this theory slot is the direct-vs-processed table. Attendees
> who pick the wrong mode in the lab lose ten minutes. The demo is not optional: with 120 people, five minutes of
> "you'll see this screen" saves twenty minutes of helpers walking the room.

*Sources: [Eventstream overview](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/overview),
[Add and manage sources](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-manage-eventstream-sources),
[Event processing editor](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/process-events-using-event-processor-editor),
[Eventhouse destination](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-destination-kql-database),
[Derived streams](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-destination-derived-stream)*

Continue to [Lab 02: Build the transit eventstream](lab-02-build-the-transit-eventstream.md).
