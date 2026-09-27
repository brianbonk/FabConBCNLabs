# Lab 04: Build the Transit Ops Dashboard

**Duration:** 15 minutes
**Prerequisites:** Module 03 complete. `BusArrivalsEnriched` is filling, `BusNextArrivalLatest` is healthy,
and `TransitQueries` holds the saved E-queries. Tile queries are also collected in
[`artifacts/Dashboard/tile-queries.kql`](../../artifacts/Dashboard/tile-queries.kql).

**Learning objectives**
- Create a Real-Time Dashboard and connect it to a KQL database.
- Add a **map** tile (latitude/longitude), a **time chart** and a **table**.
- Add a **parameter** and use it in a query.
- Turn on **live refresh**.
- Optional: add a KPI tile and set an alert from a tile.

## Before you begin

- [ ] `BusNextArrivalLatest | count` returns roughly the number of stop/line pairs in the feed (tens, not thousands).
- [ ] `BusNextArrivalLatest | where isnotnull(Lat) | count` returns the same number (if not, re-check `StopsDim`).

## Steps

### Part A — Create the dashboard and its data source

1. In the **RTI Transit** workspace, **click** **+ New item**, **select** **Real-Time Dashboard**, **type**
   `TransitOpsDashboard`, and **click** **Create**.

2. **Click** **+ Add data source** → **KQL Database**. In the **OneLake catalog** window **select**
   `TransitEventhouse` → database **TransitEventhouse**, and **click** **Connect**.

   ![Step 2](../../assets/screenshots/lab-04/step-01.png)

   > ✅ Expected result: the data source appears in the dashboard's **Data sources** list, and the toolbar's
   > tile/parameter buttons are enabled.

   *Adapted from: [Create a Real-Time Dashboard — Add data source](https://learn.microsoft.com/fabric/real-time-intelligence/dashboard-real-time-create#add-data-source)*

### Part B — Map tile: longest current wait per stop

3. **Click** **New visual** (or **Add tile**). In the query pane **paste** tile query **T1** (below) and
   **click** **Run**:

   ```kql
   BusNextArrivalLatest
   | where isnotnull(Lat) and isnotnull(Lon)
   | summarize LongestWaitMin = max(MinutesToArrival), Lines = strcat_array(make_set(LineCode), ", ")
             by StopCode, StopName, Zone, Lat, Lon
   | project StopName, Zone, Lines, LongestWaitMin, Lat, Lon
   ```

4. On the **Visual setup** tab of the pane on the left, **set** **Visual type** to **Map**. Under **Data**, **set** **Define location by**
   to **Latitude and longitude**, **Latitude column** `Lat`, **Longitude column** `Lon`. Under **Size**, **turn
   on** sizing and **set** **Size column** to `LongestWaitMin`. **Label** column `StopName` if offered.

   ![Step 4](../../assets/screenshots/lab-04/step-02.png)

   > ✅ Expected result: Barcelona appears with a cluster of points at the Fòrum, a string along the
   > Poblenou/Diagonal corridor, and single points at Catalunya, Sants and Sagrada Família. Bigger dot = longer
   > wait. Hover a point to see the stop name and lines.

5. **Click** **Done**, then **rename** the tile (tile menu **…** → **Rename**) to `Longest wait per stop`.

   *Adapted from: [Customize Real-Time Dashboard visuals — Map](https://learn.microsoft.com/fabric/real-time-intelligence/dashboard-visuals-customize)*

### Part C — Parameter + time chart

6. **Click** **+ Add parameter** (toolbar, or **Manage** → **Parameters** → **+ Add**). Configure:
   - **Label**: `Line` — **Parameter type**: **Multiple selection** — **Variable name**: `_line`
   - **Data type**: `string` — **Source**: **Query** — **Data source**: `TransitEventhouse`
   - **Query**: `LinesDim | distinct LineCode | order by LineCode asc`
   - **Value column** `LineCode`; **Default value**: **Select all**
   - **Click** **Done**.

   > ✅ Expected result: a **Line** dropdown appears at the top of the dashboard, listing every line in the feed.

   *Adapted from: [Use parameters in Real-Time Dashboards](https://learn.microsoft.com/fabric/real-time-intelligence/dashboard-parameters)*

7. **Click** **New visual**, **paste** tile query **T2**, **Run**:

   ```kql
   BusArrivalsEnriched
   | where PolledAtUtc > ago(2h) and Rank == 1
   | where isempty(_line) or LineCode in (_line)
   | summarize AvgWaitMin = avg(MinutesToArrival) by bin(PolledAtUtc, 5m), LineCode
   ```

   On the **Visual setup** tab, **set** **Visual type** to **Time chart**. Under **Data**, in the order the pane
   shows them: **Y columns** `AvgWaitMin`, **X column** `PolledAtUtc`, **Series columns** `LineCode` (the pane
   defaults to *Infer* for each; the inferred choice is usually right, but set them explicitly). Under
   **General**, **Tile name** `Average wait by line (5 min)`. **Click** **Done**.

   > ✅ Expected result: one line per bus line. **Change** the **Line** dropdown to a single line and the chart
   > re-queries with only that series: the filter is pushed into the KQL, not applied on top of a big result.

### Part D — Venue table

8. **Click** **New visual**, **paste** **T3**, **Run**, **Visual type** **Table**, **Done**, **rename** to
   `Next buses at the venue`:

   ```kql
   BusNextArrivalLatest
   | where Zone == "Venue"
   | where isempty(_line) or LineCode in (_line)
   | project Stop = StopName, Line = LineCode, To = Destination, Minutes = MinutesToArrival,
             AsOf = datetime_utc_to_local(PolledAtUtc, 'Europe/Madrid')
   | order by Minutes asc
   ```

### Part E — Live refresh and save

9. **Click** **Manage** → **Refresh settings** (or **Auto refresh**). **Turn on** **Live refresh** (if offered)
   with a **Refresh rate limit** of `30 seconds`, or set **Auto refresh** to **Continuous**/`30s`. **Click**
   **Done**.

10. **Click** **Save**, then **switch** from **Editing** to **Viewing**.

    ![Step 10](../../assets/screenshots/lab-04/step-03.png)

    > ✅ Expected result: within a minute the venue table's **Minutes** values tick down and the map dots
    > resize without you touching anything. Compare the venue table with TMB's own arrival board for the same
    > stop (the facilitator has it on screen): the numbers match within a minute.

    *Adapted from: [Enable live refresh](https://learn.microsoft.com/fabric/real-time-intelligence/dashboard-real-time-create#enable-live-refresh)*

### Part F — Optional: Table tile and an alert from a tile

11. **New visual**, **paste** **T4**, **Visual type** **Table** (mode **Number**), thresholds **Good** `< 2`,
    **Warning** `2–4`, **Critical** `> 4`, **Higher is worse**. **Rename** to `Stops with a long wait`:

    ```kql
    BusNextArrivalLatest
    | where MinutesToArrival > 12
    | summarize StopsWaiting = dcount(StopCode)
    ```

12. On the `Next buses at the venue` **table** tile, **click** **…** → **Set alert**. Notice the **Add rule** pane
    opens with the tile's query as the monitored source. **Close** it without creating the rule.

    > ✅ Expected result: you've seen the third way into Activator (eventstream, Fabric events, dashboard tile).
    > Module 05 builds real rules on the stream, where latency is seconds rather than the dashboard's refresh
    > interval. The **KPI** visual doesn't offer **Set alert** (its query returns a single number and the tile
    > type is newer than the alerting integration), which is why this step uses the table tile.

<!-- facilitator: if running behind, stop after Part B. The map is the memorable tile. -->

## Checkpoint

At the end of this lab, your workspace contains `TransitOpsDashboard` with:
- Data source `TransitEventhouse`
- Tiles: `Longest wait per stop` (map), `Average wait by line (5 min)` (time chart, parameter-driven),
  `Next buses at the venue` (table), optionally `Stops with a long wait` (KPI)
- Parameter **Line** (`_line`, multi-select)
- Live/auto refresh on

Continue to [Module 05: Activator](../module-05-activator/lab-05-activator-rules-on-live-arrivals.md).
