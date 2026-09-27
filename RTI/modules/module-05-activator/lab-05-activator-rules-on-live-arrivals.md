# Lab 05: Activator Rules on Live Arrivals

**Duration:** 23 minutes
**Prerequisites:** Module 02 complete: `BusArrivalsEventstream` is published with the derived stream
`ForumNextBus` from the SQL operator (one row per line at your venue stop per minute, with `MinutesToArrival`).
You know your own email address on the event account (and whether Teams is available; the facilitator says so).

**Learning objectives**
- Add an Activator destination to a derived stream and create the `TransitAlerts` item.
- Create a **sustained threshold** rule per object (`LineCode`).
- Create a **heartbeat** rule that fires when a line at the stop goes silent.
- Test a rule against history, start it, and read its **Analytics**.
- Optional: create a **stateful** (change) rule and compare its firing behaviour.

## Before you begin

- [ ] `BusArrivalsEventstream` → Live view → `ForumNextBus` → **Data preview** shows rows once a minute, all with
      your venue `StopCode`, one per `LineCode`, and a decimal `MinutesToArrival` column.
- [ ] If the derived stream doesn't exist (you skipped Lab 02 Part D), add it now per Lab 02 steps 24–29.
- [ ] **If you used Lab 02's no-code fallback** (no SQL operator in your tenant), your stream carries `MIN_ArrivalMs`
      (an epoch instant) instead of minutes, and Activator can't subtract. Build rule 2 (heartbeat) exactly as
      written below, skip rule 3, and build rule 1 as a **KQL Queryset alert** instead: in `TransitQueries`, run
      `BusNextArrivalLatest | where Zone == "Venue" and MinutesToArrival > 12`, click **Set alert** on the ribbon,
      condition **when the query returns rows**, action email, save into `TransitAlerts`. It evaluates on a schedule
      rather than per event, which is the trade-off to name out loud.

## Steps

### Part A — Attach Activator to the derived stream

1. **Open** `BusArrivalsEventstream` and **click** **Edit**.

2. **Hover** over the **ForumNextBus** derived-stream node, **click** **+**, **select** **Activator**.

3. In the **Activator** pane: **Destination name** `TransitAlertsDest`, **Workspace** `RTI Transit`,
   **Activator** → **Create new** → `TransitAlerts`. **Click** **Save**, then **Publish**.

   ![Step 3](../../assets/screenshots/lab-05/step-01.png)

   > ✅ Expected result: Live view shows `ForumNextBus → TransitAlertsDest`. The node carries a bell/alert icon.

   *Adapted from: [Add a Fabric Activator destination to an eventstream](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-destination-activator)*

### Part B — Rule 1: `Long wait at the Fòrum` (sustained threshold, per line)

4. **Click** the alert icon on **TransitAlertsDest**. The **Rules** pane opens (empty). **Click** **…** →
   **Open in Activator** so you get the full editor (the in-pane form is fine for simple rules, but we want an
   occurrence setting and the analytics).

5. In the Activator editor's **Explorer**, **select** the **ForumNextBus**
   stream and **click** **New object** (ribbon). In the pane:
   - **Object name**: `VenueLine`
   - **Object ID** (the field that identifies one instance): `LineCode`
   - **Properties**: `MinutesToArrival`, `StopCode`, `StopName`, `Destination`, `WindowEnd`
   - **Click** **Create**.

   > ✅ Expected result: `VenueLine` appears in the Explorer with its five properties underneath. This is the "one
   > state per line" the theory talked about: from now on every rule on this object is evaluated separately for
   > H16, 7 and 136.

   *Adapted from: [Assign data to objects in Activator](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-assign-data-objects)*

6. **Select** the **`MinutesToArrival`** property under `VenueLine` and **click** **New rule** (ribbon). In the
   **Definition** pane:
   - **Rule name**: `Long wait at the Fòrum`
   - **Monitor**: already set to `MinutesToArrival` of `VenueLine`
   - **Condition**: **Is greater than** → `12`
   - **Occurrence**: **When it has been true for** → `5` **minutes** (the shortest duration the picker offers)

   ![Step 6](../../assets/screenshots/lab-05/step-02.png)

   > ✅ Expected result: the **Definition** tab's preview chart shows the next-bus minutes per line over the last
   > while, with the 12-minute threshold drawn. You can already see whether any line has been above it. Because the
   > stream carries one value per line per minute, "true for 5 minutes" means five consecutive windows: a real
   > gap in service, not one wobbly prediction.

   <details>
   <summary>Troubleshooting — the editor offers "On each event grouped by a field" instead of objects</summary>

   Some tenants show the newer, object-less form. Then: **Check** → **On each event grouped by a field**;
   **Group by** `LineCode`; **field to check** `MinutesToArrival`; same condition and occurrence. Same result:
   one state per line.
   </details>

   *Adapted from: [Detection settings in Activator](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-detection-conditions)*

7. **Action**: **Select action** → **Email** (or **Teams → Message to individuals** if the facilitator
   confirmed Teams works).
   - **To**: your event-account email
   - **Subject**: `Long wait for line @LineCode at the Fòrum`
   - **Headline**: `Next @LineCode bus in @MinutesToArrival min`
   - **Context**: add `StopCode` and the window timestamp

   > ✅ Expected result: typing `@` offers the stream's fields; the preview under **Edit action** renders the
   > message with real values.

8. **Click** **Save**, then **Send me a test alert**.

   > ✅ Expected result: an email arrives within a minute, built from a *past* window that satisfied the rule.
   > If the button is disabled, no line has been over 12 minutes for 5 consecutive minutes yet; carry on, start the
   > rule, and check back after the break.

9. **Click** **Start**.

   > ✅ Expected result: the rule card shows **Running**. From now on, each *line* at the venue stop is tracked
   > independently; a line whose next bus stays more than 12 minutes away for five minutes triggers one
   > message, and won't message again until it recovers and re-enters the state.

   *Adapted from: [Create Activator rules](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-create-activators)*

<!-- facilitator: this is the "sustained" moment. Ask: what would happen with "Every time the condition is met" instead? Answer: one email per minute for every late line. -->

### Part C — Rule 2: `Stop went silent` (heartbeat)

10. **Select** the **`MinutesToArrival`** property of `VenueLine` again and **click** **New rule**.
    - **Rule name**: `Stop went silent`
    - **Monitor**: `MinutesToArrival` of `VenueLine` (any property works; the heartbeat is about the object's events)
    - **Condition**: category **Heartbeat** → **No presence of data**; **duration** `10` **minutes**
    - **Action**: **Email**, **Subject** `No arrival data for line @LineCode at the Fòrum for 10 minutes`,
      **Headline** `Check the feed (Function / Event Hubs) before blaming TMB.`
    - **Save**, **Start**.

    > ✅ Expected result: **Running**. A line normally produces one window every minute, so ten minutes of silence
    > means the pipeline broke (Function down, Event Hubs unreachable, TMB failing for that stop on every poll),
    > not the buses. If the facilitator pauses the feed during the break, everyone's inbox proves it.

### Part D — Optional: Rule 3 `Bus arriving now` (stateful change)

11. **New rule** on the `MinutesToArrival` property of `VenueLine`: name `Bus arriving now`; condition category
    **Numeric change** → **Decreases below** → `2`; action Teams or email, headline
    `@LineCode is arriving at the Fòrum now`. **Save**, **Start**.

    > ✅ Expected result: this one fires once per line each time the prediction *crosses* below 2 minutes, not
    > on every window under 2 minutes. Compare with rule 1's model: **change** conditions are inherently
    > stateful; **state** conditions need an occurrence to avoid repeats.

### Part E — Read the analytics

12. **Select** `Long wait at the Fòrum` and **click** the **Analytics** tab.

    ![Step 12](../../assets/screenshots/lab-05/step-03.png)

    > ✅ Expected result: two charts: total activations over time, and activations by the top object IDs
    > (lines). Even before anything fired live, the **Definition** chart shows how often the rule *would have*
    > fired on the history the stream has already delivered.

13. **Go back** to `BusArrivalsEventstream` (Live view) and **click** the alert icon on `TransitAlertsDest`.

    > ✅ Expected result: the **Rules** pane lists all your rules with start/stop toggles. This is where Module
    > 07 stops them before lunch.

> 🎤 Facilitator note: keep your own `Long wait` email from the dry run ready to show. Real data may be
> perfectly punctual for the 23 minutes this lab runs, and that's a fine teaching point too.

<!-- facilitator: check three things for anyone whose rule "does nothing": the object's ID is LineCode (not StopCode), the rule sits on the MinutesToArrival property, and the rule is started. Then Send me a test alert. -->

## Checkpoint

At the end of this lab, your workspace contains Activator item **`TransitAlerts`**, fed by the `ForumNextBus`
derived stream, with object **`VenueLine`** (ID `LineCode`) and:
- `Long wait at the Fòrum` — `MinutesToArrival` **Is greater than 12**, **true for 5 minutes**, **Running**
- `Stop went silent` — **No presence of data** for 10 minutes, **Running**
- optionally `Bus arriving now` — **Decreases below 2**, **Running**

You've turned a stream into a per-line state machine with actions. Take the break, then continue to
[Module 06: Event-driven beyond telemetry](../module-06-fabric-events/lab-06-onelake-events-trigger-automation.md).
