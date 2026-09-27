# Lab 06: OneLake Events Trigger Automation

**Duration:** 18 minutes
**Prerequisites:** Module 01 complete (`TransitLakehouse` with an empty `Files/reference` folder). You have
`stops.csv` from [`artifacts/SampleData/`](../../artifacts/SampleData/) locally and
[`artifacts/Notebooks/LoadStopsReference.py`](../../artifacts/Notebooks/LoadStopsReference.py) open to copy from.

**Learning objectives**
- Create a notebook that loads a reference CSV into a Lakehouse table.
- Subscribe to **OneLake events** from Real-Time hub with a path filter, and make Activator **run the notebook** when a file lands.
- Prove it by dropping a file and watching the run appear in the **Monitor** hub.
- (Presenter demo) Route **workspace item events** into an Eventhouse table as an audit trail.

## Before you begin

- [ ] `TransitLakehouse` → **Files** → `reference` exists and is **empty**. If a `stops.csv` is already there from
      an earlier attempt, delete it first (the trigger is *FileCreated*; re-uploading counts as "created or
      replaced", which also fires, but starting empty keeps the story clean).
- [ ] Real-Time hub → **Fabric events** lists **OneLake events**. If it doesn't, Fabric events are disabled on this
      tenant; follow Part D as a demo and skip B–C.

## Steps

### Part A — The notebook that will be triggered

1. In **RTI Transit**, **click** **+ New item**, **select** **Notebook**, and **rename** it (click the title)
   to `LoadStopsReference`.

2. In the **Explorer** pane, **click** **Add data items** → **Existing data sources**, **select**
   `TransitLakehouse`, **click** **Connect**.

   > ✅ Expected result: `TransitLakehouse` appears as the notebook's default lakehouse, with `Files/reference`
   > visible under it.

3. **Delete** the default empty cell's content and **paste** the whole of
   [`artifacts/Notebooks/LoadStopsReference.py`](../../artifacts/Notebooks/LoadStopsReference.py) into the cell.

4. **Click** **Run all**.

   ![Step 4](../../assets/screenshots/lab-06/step-01.png)

   > ✅ Expected result: after a Spark start-up of 1–3 minutes the cell prints `No files in Files/reference yet;
   > nothing to load.` and finishes green. That's intended: it proves the notebook runs; the *event* provides the
   > file.

   <details>
   <summary>Troubleshooting</summary>

   `Path does not exist`: the default lakehouse isn't attached (step 2). `Session timed out`: run again;
   cold sessions on a fresh capacity occasionally time out once.
   </details>

### Part B — The rule: file lands → run the notebook

5. **Click** **Real-Time** in the left navigation, then **Fabric events**. **Hover** over **OneLake events** and
   **click** **Set alert**.

   ![Step 5](../../assets/screenshots/lab-06/step-02.png)

6. In the **Add rule** pane, **Details** → **Rule name**: `Reference file landed`.

7. **Monitor** → **Source** → **Select source events**. The **Connect data source** wizard opens on its
   **Configure** page (**OneLake events → Set alert** shown at the top):
   - **Select event type(s)**: **select only** `Microsoft.Fabric.OneLake.FileCreated`
   - **Select data source for events**: **Add a OneLake source** → **My data** → **select** `TransitLakehouse` →
     **Next** → **select all** (or the **Files** entry) → **Add**. `TransitLakehouse` now shows under the heading
     with "(1 selected)".
   - **Set filters** → **+ Filter**: **Field** `subject`, **Operator** **String contains**, **Value**: **type**
     `Files/reference/` and **click** **Add new value**
   - **Next** → **Review + connect** → **Save**

   > ✅ Expected result: back in **Add rule**, the **Monitor** section reads **Source: OneLake events**, and
   > **Show event types** / **Show applied filters** expand to the one type and the one filter you set.

   > ℹ️ Don't filter on `contentLength > 0`: portal uploads can emit events with `contentLength = 0`.

   *Adapted from: [Set alerts on OneLake events in Real-Time hub](https://learn.microsoft.com/fabric/real-time-hub/set-alerts-fabric-onelake-events)*

8. **Condition** → **Check**: **On each event**. Every `FileCreated` event that survived the filter should trigger
   the run, so no grouping and no value test are needed.

   <details>
   <summary>If the Check dropdown only offers "On each event when"</summary>

   Then a field test is mandatory: **Grouping field**: leave empty; **When**: `subject`; **Condition**:
   **Contains** (or **Is not equal to** with an empty value if *Contains* isn't listed); **Value**:
   `Files/reference/`. It duplicates the filter from step 7, which is harmless.
   </details>

9. **Action** → **Select action** (it defaults to **Message to individuals**; change it) → under **Run Fabric
   activities** **select** **Notebook** → **Select Fabric item to run** → `LoadStopsReference`. (No parameters.)

   ![Step 9](../../assets/screenshots/lab-06/step-03.png)

   > ✅ Expected result: the action reads *Run notebook: LoadStopsReference*. The other entries in that list
   > (Pipeline, Dataflow, Spark job, Function, Copy job, Publish business event (preview)) are the same pattern
   > with a different target.

   *Adapted from: [Trigger Fabric items](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-trigger-fabric-items)*

10. **Save location** → **Workspace**: your workspace; **Item**: open the dropdown (it defaults to **My activator**)
    → **Create a new item** → `TransitAutomation`.
    **Click** **Create**, then on **Alert created** **click** **Open** (or **Done** and open `TransitAutomation`
    from the workspace).

11. In the Activator editor, **select** `Reference file landed` and **confirm** it shows **Running**. If it says
    stopped, **click** **Start**.

    > ✅ Expected result: **Running**. Nothing has happened yet; the folder is empty.

### Part C — Fire it

12. **Open** `TransitLakehouse` → **Files** → **reference**. **Click** **Upload** → **Upload files**, **select**
    your local `stops.csv`, **Upload**.

    > ✅ Expected result: `stops.csv` appears in the folder.

13. **Click** **Monitor** in the left navigation (the Monitor hub). **Wait** 30–90 seconds and **refresh**.

    ![Step 13](../../assets/screenshots/lab-06/step-04.png)

    > ✅ Expected result: a run of **LoadStopsReference** appears with **Submitted by** your account and a
    > status of **In progress**, triggered without anyone clicking Run. Give it 1–3 minutes (Spark start-up).

14. When the run shows **Succeeded**, **open** `TransitLakehouse` → **Tables** → **refresh**.

    > ✅ Expected result: a `Stops` Delta table exists with one row per stop (~16). The event, not a schedule,
    > loaded it.

15. **Back in `TransitAutomation`**, **select** the rule → **Analytics**.

    > ✅ Expected result: one activation, at the upload time.

    <details>
    <summary>Troubleshooting — no run appeared</summary>

    1. Rule not started (step 11).
    2. Filter typo: `subject` values look like `/<workspaceId>/<lakehouseId>/Files/reference/stops.csv`; the filter
       is case-sensitive and must be `Files/reference/`, not `files/reference`.
    3. You uploaded to `Files` root, not `Files/reference`.
    4. Give it two full minutes; discrete-event delivery is usually 10–30 s but can lag.
    Then re-upload the file (a replace also raises `FileCreated`).
    </details>

<!-- facilitator: keep the Monitor hub on the projector from step 12 on. Runs appearing by themselves across the room is the module. -->

> 🎤 Facilitator note: ask what would change to make this a *pipeline* instead of a notebook (nothing but the
> action target), and what would change to react to a file landing in **Azure Blob Storage** instead (the event
> source; the rest is identical).

### Part D — Presenter demo: workspace item events as an audit trail

*Attendees follow on screen; build it yourself only if the room is ahead.*

16. **Real-Time** → **+ Connect to data source** → **Fabric Workspace item events** → **Connect**. **Event types**:
    keep all six (`ItemCreateSucceeded/Failed`, `ItemUpdateSucceeded/Failed`, `ItemDeleteSucceeded/Failed`).
    **Event source**: **By workspace** → `RTI Transit`. **Stream details**: workspace `RTI Transit`, eventstream name
    `WorkspaceAuditEventstream`. **Next** → **Connect** → **Open eventstream**.

17. **Edit** → **Add destination** → **Eventhouse** → **Direct ingestion** → `TransitEventhouse`; **Publish**;
    **Configure** → new table `WorkspaceItemEvents` (JSON; the payload arrives as columns `id`, `source`,
    `subject`, `type`, `time`, `data` where `data` is `dynamic`).

18. **Create** a throwaway item in the workspace (a KQL Queryset named `DeleteMe`), then **delete** it. In
    `TransitQueries` **run**:

    ```kql
    WorkspaceItemEvents
    | project time, type, ItemName = tostring(data.itemName), ItemKind = tostring(data.itemKind), Actor = tostring(data.executingUserId)
    | top 20 by time desc
    ```

    > ✅ Expected result: two rows for `DeleteMe`, create then delete, with who did it. Add an Activator rule on
    > `type == Microsoft.Fabric.ItemCreateSucceeded and data.itemKind == "Warehouse"` and you have a policy alert.

    *Adapted from: [Add Fabric workspace item event source](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-source-fabric-workspace)*

## Checkpoint

At the end of this lab, your workspace contains:
- Notebook `LoadStopsReference`, attached to `TransitLakehouse`
- Activator item **`TransitAutomation`** with rule `Reference file landed` (OneLake `FileCreated`, filter
  `Files/reference/`, action **Run notebook**), **Running**, with one activation in its Analytics
- `TransitLakehouse` → `Files/reference/stops.csv` and table `Stops`, loaded by the triggered run
- (Presenter workspace only) `WorkspaceAuditEventstream` → `WorkspaceItemEvents`

Same engine, different event. Continue to
[Module 07: Wrap-up and handoff](../module-07-wrapup/07-wrapup-and-handoff.md).
