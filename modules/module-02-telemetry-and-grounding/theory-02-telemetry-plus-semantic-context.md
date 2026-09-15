# Theory 02: Telemetry + Semantic Context

**Duration:** 15 minutes
**Module:** 02 – Telemetry and Grounding
**Topics covered:** 3. Combining real-time telemetry with semantic context · 4. Grounding signals with enterprise meaning

**Learning objectives**
- Explain why fast-moving event data becomes meaningful only when combined with slower-changing reference data.
- Describe the two Kusto mechanisms for performing that combination inside an Eventhouse — update policies and materialized views — and how they differ.
- State which mechanism this lab uses, and why.
- Recognize the general "streaming + reference data" pattern well enough to apply it outside the cold-chain scenario.

## Where Module 01 left off

Module 01 stood up `FreezerTelemetryRaw` in the `ColdChainKQLDB` KQL database — a table of bare events:
`FreezerId`, `StoreId`, `Timestamp`, `TemperatureC`, `DoorOpen`. It also made a deliberately uncomfortable
observation: a row that says `F-1042, -9.0, false` tells you almost nothing on its own. Is -9°C fine? Is it
an emergency? The event doesn't say, because the event *can't* say — a temperature reading has no opinion
about what temperature it's supposed to be. That opinion lives somewhere else: in a store's operating
policy, a freezer model's rated range, a maintenance contract. Module 02 is about closing that gap.

## The general pattern: fast data needs slow context

Almost every real-time intelligence scenario has this same shape:

- A **fast-moving stream** of events — sensor readings, clickstreams, transactions, GPS pings — that
  arrives continuously and changes every second.
- A **slow-changing body of reference data** — customer records, store metadata, equipment
  specifications, org hierarchies — that changes rarely (daily, weekly, or less) but supplies the business
  meaning the stream itself doesn't carry.

Neither half is useful alone. The stream without context is just numbers; the reference data without the
stream is a static catalog with no pulse. The value appears at the join: `FreezerId` in the event stream
resolves to a `Freezers` row, which resolves to a `StoreId`, which resolves to a `Stores` row — and only
then does "-9°C" become "9 degrees warmer than this store's freezer should ever read."

Architecturally, this is why the workshop scenario uses two different Fabric items for two different
speeds of data:

| | Speed of change | Fabric item | Role |
|---|---|---|---|
| Telemetry | Continuous | Eventhouse (`ColdChainEventhouse` / `ColdChainKQLDB`) | Fast ingestion, time-series query |
| Reference data | Rare | Lakehouse (`ColdChainLakehouse`) | Durable system of record for `Customers`, `Stores`, `Freezers` |

Reference data doesn't live in the Eventhouse natively — it's authored and maintained in the Lakehouse,
then copied into the KQL database so it can be joined against telemetry at query speed. That copy is what
makes the join local and fast rather than a cross-item, cross-engine lookup on every query.

## Microsoft's own template for this pattern

This isn't a bespoke design invented for this workshop — it directly follows the pattern Microsoft
documents in its own Digital Twin Builder Real-Time Intelligence tutorial. In that tutorial's first two
parts, static contextual data (bus stop names, locations, boroughs) is uploaded into a lakehouse, while a
live stream of bus location telemetry lands in an Eventhouse — and the rest of the tutorial is about
bringing those two together so raw position pings become "Bus 42 is 3 minutes from Abbey Wood Road." See
[Tutorial: Digital twin builder in Real-Time Intelligence — Part 1: Upload contextual
data](https://learn.microsoft.com/fabric/real-time-intelligence/digital-twin-builder/tutorial-rti-1-upload-contextual-data).

This lab adapts exactly that shape, swapping buses and bus stops for freezers and stores:

| Microsoft's tutorial | This workshop |
|---|---|
| Static bus stop data → Lakehouse | `Customers` / `Stores` / `Freezers` → `ColdChainLakehouse` |
| Live bus location stream → Eventhouse | Live freezer temperature stream → `ColdChainEventhouse` |
| Bus position + stop context joined | Freezer reading + store/model context joined |
| "3 minutes from this named stop" | "9°C above this freezer's rated range" |

## Two ways to join inside Kusto: update policies vs. materialized views

Once reference data has been copied into the KQL database alongside the raw telemetry, Kusto (the query
engine behind Eventhouse) gives you two different mechanisms for combining them. They are not
interchangeable, and picking the wrong one produces either poor performance or the wrong shape of result.

**Update policies** run *at ingestion time*, once per ingestion batch. As each batch of new rows lands in
a source table, the update policy's query — typically using the [`lookup`
operator](https://learn.microsoft.com/kusto/query/lookup-operator) against a dimension table — runs
against just that batch and writes the result into a target table. This makes update policies well suited
to row-level transformation and enrichment: attach a `StoreName` to each incoming row, cast a type, reshape
a column. What they're *not* well suited to is aggregation across batches — an update policy only ever
sees the rows in the batch currently being ingested, so "give me the latest reading per freezer, across all
batches ingested so far" isn't something it can answer correctly.

**Materialized views** run *after* ingestion, on a background cadence, over the whole source table (more
precisely, over the delta of records not yet materialized). Because they operate over accumulated data
rather than a single batch, materialized views are the right tool for aggregations — `arg_max`, `count`,
`sum`, and similar summarize operations — and they can also incorporate joins against dimension tables via
the `dimensionTables` mechanism, in the same way update policies use `lookup`. The tradeoff is that a
materialized view isn't part of the ingestion pipeline: there's a small, bounded lag between a row arriving
and it appearing in the *materialized* part of the view (queries still see it immediately via the
view's unmaterialized delta, just less efficiently).

Microsoft's own guidance states this plainly: "Materialized views are suitable for aggregations, while
update policies aren't. Update policies run separately for each ingestion batch, and therefore can only
perform aggregations within the same ingestion batch." (See [Materialized views vs. update
policies](https://learn.microsoft.com/kusto/management/materialized-views/materialized-view-use-cases#materialized-views-vs-update-policies).)
Full mechanics of each are documented at [Update
policy](https://learn.microsoft.com/kusto/management/update-policy) and [Materialized views use
cases](https://learn.microsoft.com/kusto/management/materialized-views/materialized-view-use-cases).

## Which one this lab uses, and why

`FreezerTelemetryEnriched` — the table this lab builds — needs to answer "what is the *current* state of
every freezer, right now, with full business context attached?" That's an aggregation question
("latest row per `FreezerId`"), not a per-row transformation question. So this lab defines
`FreezerTelemetryEnriched` as a **materialized view**, using `arg_max(Timestamp, *)` grouped by
`FreezerId` to collapse the raw stream down to one current row per freezer, joined against the
`Freezers` and `Stores` dimension data (copied into the KQL database from the Lakehouse) to attach
`Model`, `Capacity`, `StoreName`, and `Region`. An update policy could enrich each row as it lands, but it
has no clean way to also express "and only keep the latest one per freezer" — that collapsing step is
exactly what materialized views exist for. The actual KQL that defines this view lives at
[`artifacts/Eventhouse/ColdChainKQLDB.kql`](../../artifacts/Eventhouse/ColdChainKQLDB.kql); the lab runs it
as-is rather than having you author it from scratch, since Module 03 is where the workshop's hands-on KQL
and ontology authoring time is spent.

> 🎤 Facilitator note: if someone asks "why not both?" — that's a fair question. Real systems often chain
> them: an update policy does cheap per-row cleanup into a staging table, and a materialized view
> aggregates on top of that. This lab keeps it to one mechanism to keep the 25-minute lab focused, but it's
> worth naming the combined pattern out loud.

## Case study: is -9°C fine, or a crisis?

Take a single raw event: `FreezerId = F-1042`, `TemperatureC = -9.0`. Read in isolation, this number is
useless — you cannot say whether it's normal or alarming, because "normal" isn't a property of the number,
it's a property of the *freezer*. Now attach context:

- If `F-1042` is a **blast freezer** rated to hold −18°C, then −9°C is nine degrees above its rated
  ceiling — a potential spoilage event, and depending on the store's SLA, possibly one that needs an
  operations response within minutes.
- If `F-1042` is actually a **beverage cooler** rated for 2–8°C, then −9°C might indicate a *different*
  fault entirely (a stuck compressor running too cold), or, if this is a misconfigured `FreezerId`, no
  fault at all.

The number never changes. What changes is the business context it's read against — and that context has
to come from somewhere *durable*: a dimension table maintained by a store operations team, not a value
baked into the sensor payload. This is the essence of "grounding a signal with enterprise meaning": raw
telemetry earns interpretability only when it's anchored to context that outlives any single event. The
rest of this module's lab makes that anchoring real — you'll watch `FreezerTelemetryRaw` fill with
ungrounded numbers, then watch `FreezerTelemetryEnriched` turn the same numbers into rows that carry
`StoreName`, `Model`, and `Capacity` alongside every reading.

## What's next

The upcoming lab has you:
1. Get live telemetry flowing into `ColdChainEventhouse` for the first time (Module 01 left that table
   empty).
2. Run the materialized view script that produces `FreezerTelemetryEnriched`.
3. Confirm, by querying both tables side by side, that raw events have been grounded with store and
   freezer context.

Continue to [Lab 02: Join Streaming and Reference
Data](lab-02-join-streaming-and-reference-data.md).
