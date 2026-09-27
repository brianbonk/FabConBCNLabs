# Lab 02: Build the Transit Eventstream

**Duration:** 35 minutes
**Prerequisites:** Module 01 complete. Your workspace contains `TransitEventhouse` (with its default KQL
database) and `TransitLakehouse`. You have the four values Event Hubs
**namespace name** (`evhns-rtibcn-premium-1976.servicebus.windows.net`), **your two hub names** (`tmb-ibus-1-65` + `tmb-metro-1-65`, or `tmb-ibus-66-130` +
`tmb-metro-66-130`), the **`attendee-listen`** shared access key: `hmUG6ik4kG63LStmc4uKY6EX/DoCsTQ1e+AEhAypPIg=`, and **your** consumer group `user-NNN`.

**Learning objectives**
- Connect an eventstream to an Azure Event Hubs source with a shared-access key and a dedicated consumer group.
- Read a raw API envelope in the data preview and understand why it isn't yet usable as events.
- Route the raw stream to an Eventhouse table with **direct ingestion**, keeping the nested payload as `dynamic`.
- **Flatten** three nested arrays in the stream with **Manage fields** and **Expand**, then **Group by**
  (1-minute tumbling window) into a second table with **event processing before ingestion**.
- Do the same flattening in the **SQL operator**, add the arithmetic the no-code operators can't, and publish a
  **derived stream** with the next bus per line at the venue stop, for Module 05.
- **[metro]** Create a second eventstream from Real-Time hub's **Connect to data source** entry point.

## Before you begin

Confirm your environment matches this state before starting:
- [ ] Your dedicated workspace open; `TransitEventhouse` and `TransitLakehouse` present.
- [ ] Namespace name, your two hub names, the `attendee-listen` key, and your `user-NNN` written down.
      **Do not use `$Default`**, and don't use the other user range's hubs: your consumer group only exists on yours.
- [ ] You know the **venue stop**: **`2689` Diagonal Mar**, the H16 stop on Av. Diagonal in front of the CCIB
      (first row of [`artifacts/SampleData/stops.csv`](../../artifacts/SampleData/stops.csv), `Zone = Venue`,
      `IsPrimary = true`). The other venue stops in that file are 3477 (H16 towards the Fòrum campus), 3347 and
      2259 (line 7 on Av. Diagonal), 1090 (136) and 1878 (V31) at the metro entrance.

## Steps

### Part A — Create the eventstream and add the Event Hubs source

1. In the **RTI Transit** workspace, **click** **+ New item**, **type** `Eventstream`, **select** **Eventstream**,
   **type** `BusArrivalsEventstream` as the name, and **click** **Create**.

   ![Step 1](../../assets/screenshots/lab-02/step-01.png)

   > ✅ Expected result: an empty eventstream canvas opens in **Edit** mode with a **Connect data sources** tile.
   > (Keep the name exactly as written: the SQL operator in Part C doesn't accept eventstream names containing
   > underscores or dots.)

2. **Click** **Connect data sources**. In the **Select a data source** page, **type** `Event Hubs` in the search box
   and **click** **Connect** on the **Azure Event Hubs** tile.

3. On **Configure connection settings**, **confirm** the feature level is **Basic**, then **click** **New connection**.

4. Under **Connection settings**, **type** the **Event Hubs namespace** name and **type** your bus hub from the
   seat sheet as the **Event hub**: `tmb-ibus-1-65` or `tmb-ibus-66-130`.

5. Under **Connection credentials**:
   - **Connection name**: `tmb-ibus-listen`
   - **Authentication kind**: **Shared Access Key**
   - **Shared Access Key Name**: `attendee-listen`
   - **Shared Access Key**: `hmUG6ik4kG63LStmc4uKY6EX/DoCsTQ1e+AEhAypPIg=`
   - **Click** **Connect**.

   ![Step 5](../../assets/screenshots/lab-02/step-02.png)

   <details>
   <summary>Troubleshooting — "Unable to connect" / 401</summary>

   Nine times out of ten this is a trailing space or a truncated paste in the key. Re-copy the key, paste it into
   a plain-text editor first, and check it ends with `=`. Also confirm the key *name* is exactly `attendee-listen`.
   </details>

6. For **Consumer group**, **type** your personal `user-NNN`. For **Data format**, **select** **JSON**.

   > ⚠️ Sixty-five attendees read each hub. If you type `$Default` (or someone else's group) your eventstream
   > will compete for partitions with theirs and the connection will throw an error. If the connection fails with a
   > "consumer group not found" style error, you've typed the other user range's hub.

7. In the **Source details** pane on the right, **click** the pencil next to the source name and **type**
   `TMBBusArrivals`. **Click** **Next**, review the summary, and **click** **Add**.

   > ✅ Expected result: the canvas shows **TMBBusArrivals → BusArrivalsEventstream-stream**.

8. **Click** the **BusArrivalsEventstream-stream** node, then in the bottom pane **click** **Data preview** and
   **Refresh** if it's empty.

   ![Step 8](../../assets/screenshots/lab-02/step-03.png)

   > ✅ Expected result: within ~30 seconds rows appear with four top-level fields: `source` (`tmb.ibus`), `key`
   > (a stop code, as text), `fetchedAt`, and `payload`. **Expand** a `payload` cell: inside is TMB's response as
   > it came off the wire: a `timestamp` (epoch milliseconds, TMB's clock) and a `parades` **array** (the stop),
   > whose element holds `codi_parada`, `nom_parada` and a `linies_trajectes` **array** (one per line and
   > direction serving the stop: `nom_linia`, `codi_trajecte`, `desti_trajecte`), each with a `propers_busos`
   > **array** (the next buses: `temps_arribada`, another epoch, and `id_bus`). Three arrays deep, no "minutes",
   > only two clocks to subtract. One event on the hub is one *stop*, not one bus. That's the shape most real APIs
   > give you; Part C is where you turn it into events.

   <details>
   <summary>Troubleshooting — preview stays empty</summary>

   1. Wait a full minute; the first poll after connecting can take that long.
   2. Check your neighbour. If nobody sees data, the feed itself is down; the facilitator switches to the
      replay and you change nothing.
   3. If only you see nothing, re-open the source (click **TMBBusArrivals** → **Edit**) and check the consumer
      group and the event hub name against your seat sheet.
   </details>

<!-- facilitator: this is where wrong consumer groups surface. Walk the room. Anyone with $Default gets a spare group (user-121..130) now, not later. -->

### Part B — Raw envelopes → Eventhouse (direct ingestion)

9. **Click** **Add destination** on the ribbon and **select** **Eventhouse**.

10. In the **Eventhouse** pane:
    - **Select** **Direct ingestion**
    - **Destination name**: `BusArrivalsRaw`
    - **Workspace**: `RTI Transit`
    - **Eventhouse**: `TransitEventhouse`
    - **KQL Database**: `TransitEventhouse`
    - **Click** **Save**.

    > ✅ Expected result: an **Eventhouse** destination node appears, connected to the stream. If it isn't
    > connected, **drag** from the stream node's right edge to the destination.

11. **Click** **Publish** on the ribbon.

    > ✅ Expected result: the canvas switches to **Live** view. The Eventhouse node shows a **Configure** button
    > with a warning that the destination isn't configured yet. That's expected for direct ingestion.

12. **Click** **Configure** on the Eventhouse node. The Eventhouse's **Get data** wizard opens.
    - **Confirm** the database is **TransitEventhouse**
    - **Click** **+ New table**, **type** `BusArrivalsRaw`, and **confirm**
    - **Keep** the proposed **Data connection name** and **click** **Next**

13. On **Inspect the data**, **wait** for the sample to load, **confirm** **Format** is **JSON**, then **click**
    **Edit columns**. You want exactly four columns; fix any that differ, then **Apply**:

    | Column | Type |
    |---|---|
    | `source` | `string` |
    | `key` | `string` (**not** `long`: the envelope sends it quoted, and a numeric column ingests it as null) |
    | `fetchedAt` | `datetime` |
    | `payload` | `dynamic` |

    ![Step 13](../../assets/screenshots/lab-02/step-04.png)

    > ✅ Expected result: `payload` is `dynamic`, which is Kusto's JSON type. If the wizard instead proposes a
    > flattened list of columns (`payload_timestamp`, `payload_parades`…), set **Nested levels** to `1` (or
    > switch the JSON nesting level back to the top level) so the payload stays as one JSON column: Lab 03
    > flattens it in KQL on purpose.

14. **Click** **Finish**, wait for the three green checks, then **click** **Close**.

    > ✅ Expected result: back in Live view the Eventhouse node reads **BusArrivalsRaw** with a green status.

### Part C — Operators: flatten three arrays, aggregate

15. **Click** **Edit** on the ribbon to return to Edit mode.

16. We want a *second* branch off the stream (the raw destination stays as it is), so **click** on the
    **Transform events** button above the stream and **select** **Manage fields** from the side bar menu.
    Drag the box so it aligns with the **BusArrivalsRaw** box. Then **click** on the **BusArrivalsEventstream** right
    side connection port and drag a connection to the **Transform events** to connect the two.

17. In the **Manage fields** pane, **Operation name** `PickStops`. **Click** **Add field** four times:
    - `key` — keep the name
    - `fetchedAt` — keep the name
    - **expand** `payload` → **select** `timestamp`, and **rename** it to `PolledMs`
    - **expand** `payload` → **select** `parades` (the array), and **rename** it to `Stops`
    - **Click** **Save**

    > ✅ Expected result: the **Test result** tab (bottom pane, **Refresh**) shows four columns: `key`,
    > `fetchedAt`, `PolledMs`, `Stops`, the last one an array with one object per row (this feed asks for one stop
    > per call, but the API's shape allows several). Everything else from the envelope is gone.

    <details>
    <summary>Troubleshooting — I can't see inside <code>payload</code> in the field picker</summary>

    The picker only shows nested fields once the stream has a schema from real data. Make sure the data preview
    on the stream node showed rows (step 8), then re-open the Manage fields pane.
    </details>

18. **Hover** over **PickStops**, **click** **+**, **select** **Transform events**, **select** **Expand** from selection menu. **Operation name** `OnePerStop`,
    **Array field** `Stops`, **click** **Save**.

    ![Step 18](../../assets/screenshots/lab-02/step-05.png)

    > ✅ Expected result: `Stops` is now a single object (`codi_parada`, `nom_parada`, `linies_trajectes`) instead of
    > an array. Same number of rows, one level less nesting. This is the "Expand" operator's only job: one event
    > holding an array of N becomes N events, and it is the single most useful thing to know when an API hands
    > you arrays.

    *Adapted from: [Process event data by using the event processing editor](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/process-events-using-event-processor-editor)*

19. **Hover** over **OnePerStop**, **click** **+**, **select** **Expand**. **Operation name** `OnePerRoute`,
    **Array field** `Stops` → `linies_trajectes`, **click** **Save**.

    > ✅ Expected result: one row per **line and direction** at the stop (three or four per envelope), each with
    > `nom_linia`, `codi_trajecte`, `desti_trajecte` and a `propers_busos` array.

    <details>
    <summary>Troubleshooting — Expand only offers top-level fields</summary>

    Insert a **Manage fields** before the Expand that adds `Stops` → `linies_trajectes` renamed to `Routes` (and
    carries `key`, `fetchedAt`, `PolledMs`, `Stops` → `nom_parada` as `StopName` along), then Expand `Routes`.
    Same pattern for the next step with `propers_busos`. Two extra operators; same result.
    </details>

20. **Hover** over **OnePerRoute**, **click** **+**, **select** **Expand**. **Operation name** `OnePerBus`,
    **Array field** `Stops` → `linies_trajectes` → `propers_busos`, **click** **Save**.

    > ✅ Expected result: **one row per upcoming bus**: six to eight per envelope. Three Expands turned one API
    > response into individual events.

21. **Hover** over **OnePerBus**, **click** **+**, **select** **Manage fields**. **Operation name**
    `ShapeBusArrivals`. **Add** these fields (expand the nested objects to reach them), **renaming** and
    **changing type** where shown:

    | Add | Rename to | Change type |
    |---|---|---|
    | `key` | `StopCode` | **Int64** |
    | `fetchedAt` | `PolledAtUtc` | **DateTime** (if not already) |
    | `PolledMs` | keep | **Int64** |
    | `Stops` → `nom_parada` | `StopName` | |
    | `Stops` → `linies_trajectes` → `nom_linia` | `LineCode` | |
    | `Stops` → `linies_trajectes` → `codi_trajecte` | `RouteId` | |
    | `Stops` → `linies_trajectes` → `desti_trajecte` | `Destination` | |
    | `Stops` → `linies_trajectes` → `propers_busos` → `temps_arribada` | `ArrivalMs` | **Int64** |
    | `Stops` → `linies_trajectes` → `propers_busos` → `id_bus` | `BusId` | |

    Then **Add field** → **Built-in Function** → **String** → **Left**, input `Stops` → `linies_trajectes` →
    `nom_linia`, length `1`, name `LineFamily`. **Click** **Save**.

    > ✅ Expected result: Test result shows flat, typed events: `StopCode 1265, StopName Pg de Sant Joan - Còrsega,
    > LineCode H8, RouteId 2081, Destination Ernest Lluch, ArrivalMs 1790153253000, BusId 6405, LineFamily H`.
    > Compare with step 8: same information, now one bus per row. `LineFamily` is `H`/`V`/`D` for the orthogonal
    > network and a digit for trunk lines like 47. What's still missing is a **wait in minutes**: the API gives two
    > epoch clocks (`PolledMs`, `ArrivalMs`) and Manage fields has no arithmetic. Part D fixes that.

    <details>
    <summary>What else Manage fields can do</summary>

    Rename, remove, reorder, change type, and add computed fields with the built-in functions: string (`Left`,
    `Right`, `Upper`, `Lower`, `Len`, `Trim`, `Replace`, `Substring`, `RegExMatch`, `Json_Parse`, `Json_Stringify`, …),
    date/time and math. There is no concatenation and no subtraction of two fields, which is why the "minutes"
    number comes from the SQL operator in Part D and from KQL in Module 03.
    </details>

22. **Hover** over **ShapeBusArrivals**, **click** **+**, **select** **Group by**. Configure:
    - **Operation name**: `NextBusByStopMinute`
    - **Aggregations**: **Minimum** of `ArrivalMs`, **Count** of `ArrivalMs` (use **Add aggregation** for each)
    - **Group aggregations by**: `StopCode`, `StopName`, `LineCode`, `LineFamily`
    - **Time window**: **Tumbling**, **Duration** `1` **minute**
    - **Click** **Save**

    > ✅ Expected result: after **60–90 seconds** the Test result shows one row per stop/line per minute with
    > `MIN_ArrivalMs` (the next bus's arrival instant), `COUNT_ArrivalMs`, `LineFamily` and a window end timestamp.
    > Nothing appears until the first window closes; that's how tumbling windows work. The minimum is how we get
    > "the next bus" without a rank column: with two predictions per line, the earlier instant is the one arriving
    > first.

23. **Hover** over **NextBusByStopMinute**, **click** **+**, **select** **Eventhouse**. The pane is pre-set to
    **Event processing before ingestion**. Configure:
    - **Destination name**: `BusWaitByStopMinute`
    - **Workspace** `RTI Transit`, **Eventhouse** `TransitEventhouse`, **KQL database** `TransitEventhouse`
    - **Destination table**: **Create new** → `BusWaitByStopMinute`
    - **Input data format**: **JSON**
    - **Leave** **Activate ingestion after adding the data source** checked
    - **Click** **Save**

    *Adapted from: [Add an Eventhouse destination — Event processing before ingestion](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-destination-kql-database#event-processing-before-ingestion)*

### Part D — The SQL operator: same flattening, plus the arithmetic, into a derived stream

The no-code operators got us to one row per bus, but not to "minutes until it arrives". The **SQL operator** can
do both in one step, and it's the escape hatch whenever the click-through operators run out. It has one rule: it
can't be chained with other operators in the same path, so it hangs directly off the stream as a **third branch**.

24. **Click** **Transform events** on the ribbon and **select** **SQL** (or **SQL Code**). **Connect** the new node
    to the **BusArrivalsEventstream-stream** node's right-side port, then **click** the pencil on the SQL node.
    **Operation name**: `VenueNextBusSql`. **Click** **Edit query** to open the full-screen editor.

25. In the **Outputs** section on the left, **click** **+**, **choose** **Stream**, and **rename** the output alias
    to `ForumNextBus`.

26. **Replace** the query with the following. The `WHERE` line keeps the three venue stops in front of the CCIB
    and at the metro entrance: `2689` Diagonal Mar (H16), `3347` Diagonal - Pl Llevant (line 7) and `1090` Metro
    Maresme - Fòrum (136), so the stream carries one row per line. `TRY_CAST(... AS bigint)` makes the compare
    work whether Eventstream inferred `key` as text or as a number. The input alias is the stream's name,
    `[BusArrivalsEventstream-stream]`; check it matches the **Inputs** entry on the left.

    ```sql
    WITH Stops AS (
        SELECT TRY_CAST(e.[key] AS bigint) AS StopCode, e.payload.timestamp AS PolledMs, p.ArrayValue AS Stop
        FROM [BusArrivalsEventstream-stream] e
        CROSS APPLY GetArrayElements(e.payload.parades) AS p
    ),
    Routes AS (
        SELECT s.StopCode, s.PolledMs, s.Stop.nom_parada AS StopName, r.ArrayValue AS Route
        FROM Stops s
        CROSS APPLY GetArrayElements(s.Stop.linies_trajectes) AS r
    ),
    Buses AS (
        SELECT r.StopCode, r.PolledMs, r.StopName,
               r.Route.nom_linia AS LineCode, r.Route.desti_trajecte AS Destination,
               b.ArrayValue.temps_arribada AS ArrivalMs
        FROM Routes r
        CROSS APPLY GetArrayElements(r.Route.propers_busos) AS b
    )
    SELECT System.Timestamp() AS WindowEnd, StopCode, StopName, LineCode, Destination,
           MIN((ArrivalMs - PolledMs) / 60000.0) AS MinutesToArrival,
           COUNT(*) AS Predictions
    INTO [ForumNextBus]
    FROM Buses
    WHERE StopCode IN (2689, 3347, 1090)
    GROUP BY StopCode, StopName, LineCode, Destination, TumblingWindow(minute, 1)
    ```

    **Read** it against Part C: the three `CROSS APPLY GetArrayElements(...)` are the three Expands; the `SELECT`
    columns are the Manage fields; the `GROUP BY … TumblingWindow(minute, 1)` with `MIN(...)` is the Group by. The
    one thing that's new is `(ArrivalMs - PolledMs) / 60000.0`: minutes from now until the bus, using TMB's own
    clock for "now".

27. **Click** **Test query**.

    > ✅ Expected result: after 60–90 seconds the **Test result** tab shows one row per minute per line at the
    > venue: H16 at Diagonal Mar, 7 at Diagonal - Pl Llevant, 136 at Metro Maresme - Fòrum, each with
    > `MinutesToArrival` as a decimal (for example `4.2`) and `Predictions` (usually `2`). If it shows an error
    > about an unknown column, the input alias name differs from what's on the left; copy it from there.

    <details>
    <summary>Troubleshooting — Test query returns 0 rows</summary>

    Work through these in order:
    1. **Is the stop in the feed?** The Function only polls the stops in its `TMB_IBUS_STOPS` setting. Check the
       stream node's **Data preview**: the `key` values you see are the stops being polled. If 2689, 3347 and 1090
       aren't among them, the filter can't match; tell the facilitator (the feed is misconfigured), or temporarily
       put a `key` you *do* see in the `IN (...)` list to continue.
    2. **Windows need time.** `TumblingWindow(minute, 1)` only emits when a window closes; Test query on a short
       sample can show nothing even when everything is right. Remove the last three lines (`WHERE`, `GROUP BY`) and
       the `MIN`/`COUNT` aggregates for a moment: if the flat rows appear, the query is fine; put them back,
       publish, and check the `ForumNextBus` node's data preview after two minutes instead.
    3. **Input alias**: copy it from the **Inputs** pane; a renamed eventstream changes it.
    </details>

    *Adapted from: [Process events using a SQL operator](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/process-events-using-sql-code-editor)*

28. **Click** **Save** in the editor, then **Save** in the **SQL Code** pane. Back on the canvas, the
    **ForumNextBus** output appears as a **Stream** (derived stream) node attached to the SQL operator.

    > ✅ Expected result: the canvas now has three branches off the stream: direct → `BusArrivalsRaw`;
    > `PickStops → OnePerStop → OnePerRoute → OnePerBus → ShapeBusArrivals → NextBusByStopMinute → BusWaitByStopMinute`;
    > and `VenueNextBusSql → ForumNextBus`. Check the **Authoring errors** tab is empty.

    <details>
    <summary>Troubleshooting — the SQL operator isn't offered in this tenant</summary>

    It's a preview feature. Fallback with no-code operators: from **ShapeBusArrivals** add a **Filter**
    (`StopCode` equals `2689`; add a second Filter for `3347` and `1090` if you want lines 7 and 136 too) →
    **Group by** (Minimum of `ArrivalMs` by `LineCode`, `StopCode`,
    tumbling 1 minute) → **Stream** `ForumNextBus`. The derived stream then carries `MIN_ArrivalMs` (an instant)
    instead of `MinutesToArrival`; Module 05 has a matching fallback for its rules.
    </details>

    *Adapted from: [Add a derived stream destination](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-destination-derived-stream)*

29. **Click** **Publish**.

    > ✅ Expected result: Live view. All destination nodes show a healthy status within a minute or two. **Click**
    > **ForumNextBus** → **Data preview**: one row per line at your venue stop per minute, with `MinutesToArrival`.
    > **Click** `BusWaitByStopMinute` → **Data insights**: incoming events climb once a minute.

<!-- facilitator: leave your own Live view on the projector. The three-branch canvas is the picture of the module; point at each branch and say raw / flattened+aggregated (no-code) / flattened+computed (SQL). -->

> 🎤 Facilitator note: ask the room why we kept the raw envelopes *and* built the flat aggregate *and* wrote the
> SQL version. The answers (raw for replay, forensics and Module 03's in-database flattening; aggregate for cheap
> dashboards; SQL because the no-code operators had no subtraction) set up Module 03, where KQL does all of it
> in one function.

### Part E — [metro] A second stream, from Real-Time hub

30. **Click** **Real-Time** in the left navigation, then **+ Connect to data source**. **Search** `Event Hubs`,
    **click** **Connect** on **Azure Event Hubs**.

31. **Click** **New connection** and configure it like step 4–5 but with **Event hub** = your metro hub from the
    seat sheet (`tmb-metro-1-65` or `tmb-metro-66-130`, same user range as your bus hub) and **Connection name**
    `tmb-metro-listen`. **Click** **Connect**. **Consumer group**: your same `user-NNN`. **Data format**: **JSON**.

    > ✅ Expected result: the same key and consumer group work for both hubs: consumer groups are per event hub,
    > so `user-NNN` on the metro hub is a different cursor from `user-NNN` on the bus hub.

32. In **Stream details** on the right, **select** workspace **RTI Transit**, **click** the pencil next to
    **Eventstream name** and **type** `MetroArrivalsEventstream`. **Click** **Next**, then **Connect**.

    > ✅ Expected result: Real-Time hub confirms the stream was created and offers **Open eventstream**. This is
    > the point of Part E: the hub is a front door, the result is an ordinary Eventstream item in your workspace.

33. **Click** **Open eventstream**, **click** **Edit**, **add** an **Eventhouse** destination with **Direct
    ingestion** named `MetroArrivalsRaw` into `TransitEventhouse`, **Publish**, **Configure** the destination
    into a **new table** `MetroArrivalsRaw` exactly as in steps 12–14: `source`, `key` string; `fetchedAt`
    datetime; `payload` dynamic.

    > ✅ Expected result: one envelope per poll, `key` = `"120,122,321"`-style list of every station, and a
    > `payload` with **four** nested arrays (`linies → estacions → linies_trajectes → propers_trens`), the same
    > family of shape as the bus feed with one more level. Lab 03 Part F flattens it in four lines of KQL.

    *Adapted from: [Real-Time hub — connect to data source](https://learn.microsoft.com/fabric/real-time-hub/real-time-hub-overview)*

## Checkpoint

At the end of this lab, your **RTI Transit** workspace should contain:
- `BusArrivalsEventstream` (published, Live view healthy) with source `TMBBusArrivals` and three branches:
  - default stream → Eventhouse **direct ingestion** → table `BusArrivalsRaw` (raw envelopes, `payload` dynamic)
  - `PickStops` → `OnePerStop` → `OnePerRoute` → `OnePerBus` → `ShapeBusArrivals` → `NextBusByStopMinute` →
    Eventhouse **processed** → table `BusWaitByStopMinute` (flat, one row per stop/line/minute, `MIN_ArrivalMs`)
  - `VenueNextBusSql` (SQL operator) → derived stream **`ForumNextBus`** (`MinutesToArrival` per line per minute at the venue stop)
- **[metro]** `MetroArrivalsEventstream` → `MetroArrivalsRaw` (raw envelopes)
- In `TransitEventhouse`: tables `BusArrivalsRaw`, `BusWaitByStopMinute`, `MetroArrivalsRaw` with rows arriving

Real API responses from the streets outside are now landing in your database, and you have already turned them
into flat events twice, once by clicking and once in SQL. Continue to
[Module 03: Eventhouse & KQL](../module-03-eventhouse-kql/lab-03-enrich-and-analyze-in-eventhouse.md), where the
same flattening happens inside the database.
