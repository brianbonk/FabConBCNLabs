# Module 03 Theory: Eventhouse and the KQL Patterns That Make Streams Useful

**Duration:** 15 minutes (10 concepts + 5 live demo)
**Prerequisites:** Module 02 complete: `BusArrivalsRaw` and `BusWaitByStopMinute` are filling.

**Learning objectives**
- Explain what an Eventhouse is good at (append-only, time-indexed, fast aggregation) and what it isn't (row updates).
- Describe the four database-side building blocks used today: tables, functions, **update policies**, **materialized views**.
- Know when to use an update policy versus a materialized view, in one sentence each.
- Recognise the "raw → enriched → latest state" shape as the standard RTI pattern (and the one the afternoon reuses).

## What an Eventhouse is

An Eventhouse hosts KQL databases on the Kusto engine: columnar, append-only, indexed on time, built for
"a lot of small events, queried by time range and a few keys". You get:

- **Ingestion** from eventstreams (what you did), files, pipelines, SDKs.
- **KQL**: a pipe-based query language (`Table | where … | summarize … by bin(Time, 5m)`) with first-class
  time series (`make-series`, `series_decompose_anomalies`), geo functions, and `render`.
- **Database-side processing** that runs *as data arrives*, so query time stays cheap.

What it isn't: an OLTP store. There are no `UPDATE`s. "Latest value per key" is a query (or a materialized
view), not an in-place overwrite.

## The four building blocks you author today

| Block | What it does | Today |
|---|---|---|
| **Table** | Append-only columns | `StopsDim`, `LinesDim` (loaded from CSV), `BusArrivalsEnriched` (target) |
| **Function** | Named, parameter-less query you can call like a table | `EnrichBusArrivals()` : `BusArrivalsRaw` → `mv-expand` → `lookup` to the dimensions |
| **Update policy** | "When a batch lands in *source*, run *function* and append the result to *target*". Runs per ingestion batch, at ingestion time. One rule to know: if the function reads *other* tables (our `lookup`s), the source table must be on **queued** ingestion, not streaming; the lab flips that switch (a 10-second batching window) before attaching the policy. | `BusArrivalsRaw` → `EnrichBusArrivals()` → `BusArrivalsEnriched` |
| **Materialized view** | A `summarize` over a table, kept up to date in the background. Query it like a table; it returns the materialized part plus a fresh delta. | `BusNextArrivalLatest = arg_max(PolledAtUtc, *) by StopCode, LineCode` |

### Update policy vs materialized view, in one sentence each

- **Update policy**: per-row *transformation/enrichment* at ingestion time; it only ever sees the batch being
  ingested, so it can't answer "latest across everything".
- **Materialized view**: *aggregation* across all ingested data (`arg_max`, `count`, `avg`…), maintained
  incrementally; it can't enrich a single row with a lookup unless the dimension is declared, and it's a
  summarize, not a reshape.

Chain them: policy for shape, view for state. That's exactly what you build in the lab, and it's the same
shape Brian's cold-chain scenario ships pre-built this afternoon (`FreezerTelemetryRaw` →
`FreezerTelemetryEnriched`). Having built it by hand once, you'll read his in ten seconds.

### Why not do all of this in the Eventstream?

You *could* filter and aggregate in Eventstream operators (you did, for the per-minute table). The trade-off:
eventstream operators run **before** storage, so they reduce what you keep; Kusto-side policies and views run
**after** raw storage, so you keep everything and can re-derive. Rule of thumb: reduce in the stream when you
don't need the rows; enrich and summarise in Kusto when you do.

## KQL in five operators

Most attendees have seen SQL; few have written KQL. Five operators cover everything in Lab 03:

| KQL | Reads as | SQL cousin |
|---|---|---|
| `BusArrivalsRaw \| where PolledAtUtc > ago(15m)` | filter rows | `WHERE` |
| `\| summarize count() by bin(PolledAtUtc, 1m), LineCode` | aggregate into time buckets | `GROUP BY` with a time truncation |
| `\| extend Local = datetime_utc_to_local(PolledAtUtc, 'Europe/Madrid')` | add a computed column | `SELECT …, expr AS Local` |
| `\| project A, B, C` / `\| top 20 by PolledAtUtc desc` | pick columns / newest N | `SELECT` / `ORDER BY … LIMIT` |
| `\| lookup kind=leftouter StopsDim on StopCode` | enrich from a small table | `LEFT JOIN` |

Data flows top to bottom through the pipes; every line narrows or reshapes what the previous one produced. Management
commands start with a dot (`.create-merge table`, `.alter table … policy update`) and are what Lab 03 Parts C–D use.

## Two KQL ideas to internalise: `mv-expand` and `lookup`

The raw table holds the feed's envelopes with TMB's JSON in a `dynamic` column. Kusto reads into JSON with a dot
path (`payload.timestamp`, `payload.parades[0].nom_parada`) and **`mv-expand`** turns an array into one row per
element; three in a row for the bus feed's three levels. That's Eventstream's three Expand operators, as three
lines, plus the arithmetic the no-code operators couldn't do:

```kql
BusArrivalsRaw
| extend TmbTimestamp = unixtime_milliseconds_todatetime(tolong(payload.timestamp))
| mv-expand stop = payload.parades
| mv-expand route = stop.linies_trajectes
| mv-expand bus = route.propers_busos
| project PolledAtUtc = fetchedAt, StopCode = tolong(stop.codi_parada), LineCode = tostring(route.nom_linia),
          MinutesToArrival = (unixtime_milliseconds_todatetime(tolong(bus.temps_arribada)) - TmbTimestamp) / 1m
| lookup kind=leftouter StopsDim on StopCode
| lookup kind=leftouter LinesDim on LineCode
```

**`lookup`** is a join optimised for "big fact table, small dimension table": the dimension is broadcast, the fact
side streams. Flatten, compute, then look up: it's what turns `{"key":"1265", …, "nom_linia":"H8", "temps_arribada":
1790153253000}` into "Pg de Sant Joan – Còrsega, 41.40, 2.17, zone Interchange, line H8 to Ernest Lluch, 0.5
minutes". Put those lines inside a function and attach it as an update policy, and the database does it for every
batch that lands. That's Lab 03 Part C.

The metro payload nests one level deeper (`linies → estacions → linies_trajectes → propers_trens`). Four
`mv-expand`s in a row flatten it; the stretch part of the lab does exactly that.

## Time in this dataset

Events carry `PolledAtUtc` (the Function's clock, UTC). The prediction itself is relative ("in 4 minutes"), so
the **predicted arrival** is `PolledAtUtc + SecondsToArrival * 1s`. Barcelona is UTC+2 during the workshop;
use `datetime_utc_to_local(PolledAtUtc, 'Europe/Madrid')` for anything a human reads.

## Live demo before the lab (5 minutes, instructor workspace)

1. Open `TransitQueries`. Run `BusArrivalsRaw | top 5 by fetchedAt desc` and expand a `payload` cell. Then add one
   pipe at a time in front of the room: `| mv-expand stop = payload.parades`, `| mv-expand route = stop.linies_trajectes`,
   `| mv-expand bus = route.propers_busos`, `| project … tostring(route.nom_linia) …`, `| summarize count() by bin(…)`,
   `| render timechart`. Six edits, six results; watch the row count grow at each mv-expand.
2. Run `EnrichBusArrivals() | take 5` on your workspace: "this function is what the update policy runs on every
   batch". Then `.show table BusArrivalsEnriched policy update` to show the policy is just JSON on the table.
3. Run `BusNextArrivalLatest | where Zone == "Venue"`: "one row per stop and line, always current; that's the
   materialized view".
4. Show **Get data → Local file** as far as the **Inspect** page and the **Edit columns** type dropdown. Close it.
   "Watch `StopCode`: it must be `long`."

> 🎤 Facilitator note: if you're short on time, the update-policy-vs-materialized-view table and demo steps 2–3
> are the parts to protect. Brian's Module 10 theory covers the same comparison in depth from the other side; tell the room they'll
> hear it again this afternoon and that's on purpose.

*Sources: [Eventhouse overview](https://learn.microsoft.com/fabric/real-time-intelligence/eventhouse),
[Update policy](https://learn.microsoft.com/kusto/management/update-policy),
[Materialized views overview](https://learn.microsoft.com/kusto/management/materialized-views/materialized-view-overview),
[lookup operator](https://learn.microsoft.com/kusto/query/lookup-operator)*

Continue to [Lab 03: Enrich and analyse in the Eventhouse](lab-03-enrich-and-analyze-in-eventhouse.md).
