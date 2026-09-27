# Lab 03: Enrich and Analyse in the Eventhouse

**Duration:** 35 minutes
**Prerequisites:** Module 02 complete. `TransitEventhouse`'s default database contains `BusArrivalsRaw` and
`BusWaitByStopMinute` with rows arriving (and `MetroArrivalsRaw` if you did Part D). You have this repo's
[`artifacts/SampleData/`](../../artifacts/SampleData/) CSVs and
[`artifacts/Eventhouse/TransitEventhouse.kql`](../../artifacts/Eventhouse/TransitEventhouse.kql) open in a browser tab
to copy from.

**Learning objectives**
- Query a raw table of API envelopes with KQL: `top`, `summarize … by bin()`, `render`, and reach into JSON with
  `payload.parades[0].nom_parada`, `tostring()`, `tolong()`, `unixtime_milliseconds_todatetime()`.
- **Flatten** three nested arrays with `mv-expand`, compute the wait from two epoch clocks, and compute a rank with
  `row_number()`.
- Load reference CSVs into KQL tables through the portal and fix an inferred type.
- Author an **update policy** (target table + function + policy) that flattens and enriches at ingestion time.
- Author a **materialized view** that keeps the newest prediction per stop and line.
- Save analysis queries in a **KQL Queryset** for the dashboard module.
- Stretch: flatten the metro envelope's four nested arrays; join bus and metro at the venue; turn on **OneLake
  availability**.

## Before you begin

Confirm your environment matches this state before starting:
- [ ] `BusArrivalsRaw | count` returns a growing number (run it twice, a minute apart), and
      `BusArrivalsRaw | getschema` shows `payload` as `dynamic`.
- [ ] `BusWaitByStopMinute` exists (it may still have few rows; that's fine).
- [ ] You have `stops.csv` and `lines.csv` downloaded locally from `artifacts/SampleData/` (and
      `metro_stations.csv` if you did the metro part).

## Steps

### Part A — Explore the raw stream

1. **Open** `TransitEventhouse`, **click** the **TransitEventhouse** database, then **click** **Query with code**
   (or **New KQL Queryset** on the ribbon). **Name** the queryset `TransitQueries` when prompted.

   ![Step 1](../../assets/screenshots/lab-03/step-01.png)

   > ✅ Expected result: a query editor opens attached to the `TransitEventhouse` database, tables listed on the left.

   > ℹ️ **Run one statement at a time.** The editor runs the blank-line-separated block your cursor is in. Pasting
   > two statements together (for example both `.show` commands of C6) and running them as one fails with
   > `Syntax error: A recognition error occurred.` Every statement in the script is separated by a blank line; put
   > the cursor inside it and press **Run** (or Shift+Enter). F3 is the one multi-line exception: its `let` lines
   > and the `union` are a single query.

2. **Paste** and **run** query **A1** from the KQL script (latest 5 envelopes), then **A2** (envelopes per minute).

   > ✅ Expected result: A1 shows four columns: `source`, `key`, `fetchedAt`, and `payload`, the last one TMB's
   > JSON exactly as it arrived (**click** a cell to expand it). A2 draws a steady line of envelopes per minute,
   > one per stop per poll.

3. **Run** **A3** (reach into the JSON) and **A4** (`mv-expand` three times: one row per bus).

   > ✅ Expected result: A3 converts `payload.timestamp` with `unixtime_milliseconds_todatetime()`, reads the stop's
   > name at `payload.parades[0].nom_parada` and counts its lines with `array_length()`: the dot path into a
   > `dynamic` column is the whole trick. A4 turns each envelope into one row per upcoming bus (stops → routes →
   > buses), typed with `tostring()` / `tolong()`, and computes `MinutesToArrival` as the difference between TMB's
   > arrival instant and TMB's own timestamp. This is exactly what Lab 02's three Expands, the Manage fields and the
   > SQL operator did, in eight lines of KQL.

4. **Run** **A5** (observations by line) and **A6** (local time and predicted arrival).

   > ✅ Expected result: A5 lists line codes like `H8`, `47`, `V19` with stop counts, and nothing else about them:
   > no origin, no destination name beyond what the trip says, no map position. A6 shows both times two hours
   > ahead of UTC.

<!-- facilitator: A5 is the "codes only" cliffhanger. Ask "which of these goes to the Fòrum, and where on the map is this stop?" Nobody can tell from the feed alone. Part B fixes that. -->

### Part B — Load the reference data

5. **Go back** to the **TransitEventhouse** database page (breadcrumb), **click** **Get data** on the ribbon, and
   **select** **Local file**.

6. **Click** **+ New table**, **type** `StopsDim`, then **drag** `stops.csv` into the window (or **Browse for
   files**). **Click** **Next**.

   ![Step 6](../../assets/screenshots/lab-03/step-02.png)

7. On **Inspect**, **confirm** **Format** is **CSV** and **First row is column header** is **on**. **Click**
   **Edit columns** and **check** the types: `StopCode` must be **long**, `Lat` and `Lon` **real**, `IsPrimary`
   **bool**, everything else **string**. Fix any that differ, **Apply**, then **Finish**. **Close** when the
   three steps are green.

   <details>
   <summary>Troubleshooting — <code>StopCode</code> was inferred as string and I already finished</summary>

   Run **B3** from the script (it rebuilds the table with `tolong(StopCode)`). A string/long mismatch makes
   every `lookup` in Part C return nulls, so don't skip this check.
   </details>

   <details>
   <summary>Troubleshooting — the lookups return empty <code>StopName</code>/<code>Zone</code> for every row</summary>

   Check the left side first: `BusArrivalsRaw | top 5 by fetchedAt desc | mv-expand stop = payload.parades |
   project key, StopCode = tolong(stop.codi_parada)`. If `key` is empty but `StopCode` has a value, the raw
   table's `key` column was typed `long` in Lab 02 step 13 and ingests as null (the envelope sends it quoted).
   Every query in this lab derives the stop code from `codi_parada` in the payload for exactly that reason, so
   you can carry on; just don't use `key`. At night you'll also see `LineName` empty for `N`-lines: `LinesDim`
   only lists the day lines.
   </details>

   *Adapted from: [Get data from file](https://learn.microsoft.com/fabric/real-time-intelligence/get-data-local-file)*

8. **Repeat** steps 5–7 for `lines.csv` → new table `LinesDim` (all columns string). **[metro]** Repeat for
   `metro_stations.csv` → `MetroStationsDim` (`StationCode` long, `Lat`/`Lon` real, rest string).

9. **Back in `TransitQueries`**, **run** **B1** and **B2**.

   > ✅ Expected result: `StopsDim` shows ~16 rows with `StopName`, `Zone`, `Lat`, `Lon`; `LinesDim` shows
   > the lines with `LineName`, `LineOrigin`, `LineDestination`. B2 reports `StopCode` as `long`.

10. **Run** **B4**.

    > ✅ Expected result: the same flattened predictions as A4, now with `StopName`, `Zone`, `LineName`, `Lat`,
    > `Lon`. Find your venue stop by name. Flatten, then look up: this query is what we're about to automate.

### Part C — Author the update policy (flatten + enrich, at ingestion time)

11. **Paste** and **run** **C1** (create `BusArrivalsEnriched`).

    > ✅ Expected result: the table appears under **Tables** in the left pane (refresh it if needed). Empty. Note
    > its columns are the *flat* ones: no `payload`, no `key`; one row will mean one bus.

12. **Paste** and **run** **C2** (create the `EnrichBusArrivals()` function). **Read** it before running: the three
    `mv-expand`s (A4), `project` with `tolong`/`tostring`/`unixtime_milliseconds_todatetime`, the wait computed
    against TMB's clock, an `order by` followed by `row_number()` that restarts whenever the stop, line or poll time
    changes (that's `Rank`: 1 = next bus), then the two `lookup`s (B4) and a `coalesce` that prefers our stop name
    over TMB's.

    > ✅ Expected result: `EnrichBusArrivals` appears under **Functions** (folder `Enrichment`). **Run**
    > `EnrichBusArrivals() | where Rank == 2 | take 5` to prove it behaves like a table and that `Rank` works.

13. **Paste** and **run** **C3a**: the two `.alter … policy` commands that switch `BusArrivalsRaw` from streaming to
    queued ingestion with a 10-second batching window, then the two `.show … policy` commands.

    > ✅ Expected result: `.show table BusArrivalsRaw policy streamingingestion` shows `"IsEnabled": false` and the
    > batching policy shows `00:00:10`. Why this step exists: Kusto only lets an update policy reference *other*
    > tables (our two `lookup`s) when the source table is on queued ingestion, and the Eventstream destination
    > switched `BusArrivalsRaw` to streaming ingestion. Queued means events land in 10–20 seconds instead of ~1;
    > nothing in the rest of the morning notices, and it's the trade-off every production Eventhouse makes when
    > it enriches at ingestion time. `BusWaitByStopMinute` and `MetroArrivalsRaw` are untouched.

    <details>
    <summary>Troubleshooting — C3b fails with "Referencing additional tables from update policy is not allowed when streaming ingestion is enabled"</summary>

    You skipped C3a, or ran it against the wrong table. Run C3a again, confirm with the `.show` commands, then
    re-run C3b. The error is permanent-looking but the fix is instant.
    </details>

    *Adapted from: [Streaming ingestion policy](https://learn.microsoft.com/kusto/management/show-table-streaming-ingestion-policy-command),
    [Ingestion batching policy](https://learn.microsoft.com/kusto/management/batching-policy),
    [Update policy restrictions](https://learn.microsoft.com/kusto/management/update-policy#limitations)*

14. **Paste** and **run** **C3b** (attach the update policy), then **immediately** **C4** (backfill).

    > ✅ Expected result: C3b returns one row describing the policy. C4 returns an ingestion summary; it backfills
    > only the last 30 minutes, which is all the dashboard and alerts care about (and keeps 120 simultaneous
    > backfills from spiking the capacity). From this moment, every batch of envelopes that lands in
    > `BusArrivalsRaw` is flattened and enriched into `BusArrivalsEnriched` by the engine, with no eventstream
    > change and no schedule. (A handful of rows ingested in the seconds between C3b and C4 may appear twice;
    > harmless for everything downstream.)

    *Adapted from: [Update policy](https://learn.microsoft.com/kusto/management/update-policy)*

15. **Wait** about a minute, then **run** **C5** twice, 30 seconds apart.

    ![Step 15](../../assets/screenshots/lab-03/step-03.png)

    > ✅ Expected result: `BusArrivalsEnriched` has fresh rows each time, one per bus, each carrying `StopName`,
    > `Zone`, `LineName`, `Rank` and `PredictedArrivalUtc`. You didn't write a pipeline; the database is doing it
    > per ingestion batch, and the raw envelopes are still there in `BusArrivalsRaw` if you ever need to re-derive.

    <details>
    <summary>Troubleshooting — <code>BusArrivalsEnriched</code> stays empty</summary>

    Run **C6**. If `.show ingestion failures` lists rows for this table, the message tells you why; the common
    ones are a `StopCode` type mismatch (Part B step 7) or a function/table schema mismatch (re-run C1 and C2,
    which are idempotent). If there are no failures, wait one more minute; ingestion batches every ~30–60 s.
    </details>

### Part D — Author the materialized view

16. **Paste** and **run** the `.create-or-alter materialized-view` statement in **Part D**.

    > ✅ Expected result: `BusNextArrivalLatest` appears under **Materialized views**. With `backfill = true` it
    > is populated from existing rows within a minute or so.

    *Adapted from: [Create materialized view](https://learn.microsoft.com/kusto/management/materialized-views/materialized-view-create)*

17. **Run** **D1**, then **D2**.

    > ✅ Expected result: D1 shows exactly one row per stop/line combination (no duplicates, unlike the raw
    > table), ordered by wait. D2 shows the venue's next buses with an `AgeSeconds` column under ~60. That's
    > "what's the wait right now?" as a table you can point a dashboard or an alert at.

18. **Run** **D3**.

    > ✅ Expected result: `IsHealthy = true`, `Status = Active`, and a recent `LastRun`.

> 🎤 Facilitator note: stop here and connect the dots. Raw envelopes → flat + enriched (policy) → latest (view).
> This exact chain is what Brian's provisioning script builds for freezers this afternoon; attendees will see
> `FreezerTelemetryRaw` and `FreezerTelemetryEnriched` and know what they're looking at.

### Part E — Save the analysis queries

19. **Paste** each of **E1**–**E5** into its own tab in `TransitQueries` (the **+** next to the tab strip) and
    **run** them. **Rename** the tabs (right-click → **Rename**): `Avg wait by line`, `Wait from aggregate`,
    `Bunching`, `Longest wait map`, `Freshness`.

    > ✅ Expected result:
    > - **E1** renders a time chart, one line per bus line.
    > - **E2** draws nearly the same chart from `BusWaitByStopMinute` with far fewer rows, subtracting the window
    >   end from the `MIN_ArrivalMs` instant to get minutes (the arithmetic the no-code branch couldn't do). If its
    >   column names differ from the script's, run `BusWaitByStopMinute | getschema` and adjust; the eventstream
    >   Group-by names outputs `MIN_<field>` / `COUNT_<field>` style.
    > - **E3** lists stop/line pairs where the next two buses are ≤ 2 minutes apart (bunching). At quiet times
    >   it may be empty; that's real.
    > - **E4** has `Lat`/`Lon` for every row: the map tile's input.
    > - **E5** shows every stop with `SilentForMin` near 0 or 1.

20. **Click** **Save** on the queryset.

    *Adapted from: [KQL Queryset](https://learn.microsoft.com/fabric/real-time-intelligence/kusto-query-set)*

### Part F — Stretch: four nested arrays, the interchange question, and OneLake availability

21. **[metro]** **Paste** and **run** **F1**: the `MetroArrivalsFlat()` function. **Count** the `mv-expand`s: four,
    one per nesting level of TMB's metro payload (`linies → estacions → linies_trajectes → propers_trens`). Note
    `unixtime_milliseconds_todatetime()` for the epoch timestamps, and that `SecondsToArrival` is computed against
    TMB's own `timestamp`, not ours.

    > ✅ Expected result: `MetroArrivalsFlat` appears under **Functions**. **Run** `MetroArrivalsFlat() | take 10`:
    > one row per station × track × route × upcoming train, with `Rank` 1 and 2.

22. **[metro]** **Run** **F2** (next train per station/direction), then **F3** (the interchange question).

    > ✅ Expected result: F3 returns one short table for the venue: bus lines and metro directions mixed, sorted by
    > wait. "Bus or metro first?" answered from two APIs with different shapes, joined on nothing but the venue.
    > Skip if you didn't do Lab 02 Part D. (F5 in the script is the homework: make F1 a permanent table with an
    > update policy, exactly like Part C.)

23. **Go back** to the **TransitEventhouse** database page, **click** the **OneLake availability** toggle in
    the database details (or **…** on `BusArrivalsEnriched` → **Data policies** → **OneLake availability**) and
    **turn it on**. **Click** **Done**.

    > ✅ Expected result: within a few minutes the table's OneLake folder path is shown, and the data is
    > readable as Delta from `TransitLakehouse` via a shortcut, from a notebook, or from Direct Lake. Nothing
    > was copied by you; the Eventhouse writes Parquet/Delta alongside its own storage.

    *Adapted from: [Eventhouse OneLake availability](https://learn.microsoft.com/fabric/real-time-intelligence/event-house-onelake-availability)*

<!-- facilitator: if the room is behind, skip Part F entirely; nothing later depends on it. If ahead, add a OneLake shortcut in TransitLakehouse pointing at the enriched table and open it in the SQL endpoint -- it's the "one copy, many engines" moment. -->

## Checkpoint

At the end of this lab, the `TransitEventhouse` database should contain:
- Tables: `BusArrivalsRaw` (envelopes), `BusWaitByStopMinute`, `StopsDim`, `LinesDim`, `BusArrivalsEnriched` (flat,
  filling automatically via the update policy), **[metro]** `MetroArrivalsRaw` (envelopes), `MetroStationsDim`
- Functions: `EnrichBusArrivals()`, **[metro]** `MetroArrivalsFlat()`
- Materialized view: `BusNextArrivalLatest`, healthy
- Queryset `TransitQueries` with five saved analysis tabs (E1–E5)

Nested API responses have become named stops on a map with a current wait. Take the break, then continue to
[Module 04: Real-Time Dashboard](../module-04-real-time-dashboard/lab-04-build-transit-ops-dashboard.md).
