# Module 05 Theory: Activator — Detect and Act

**Duration:** 12 minutes (8 concepts + 4 live demo)
**Prerequisites:** Module 02 complete (derived stream `ForumNextBus` publishing).

**Learning objectives**
- Describe Activator's model: events → **objects** (by an object ID) → **properties** → **rules** → **actions**.
- Distinguish stateless, stateful and heartbeat conditions, and explain why "sustained for N minutes" matters.
- Know the five places a rule can be authored from, and which one we use today.
- Know what actions exist beyond email/Teams (Fabric items, Power Automate, business events).

## The model

Activator is a no-code event-detection engine. It subscribes to a stream (or to Fabric/Azure events, a Power BI
visual, a dashboard tile, a KQL/SQL query on a schedule, or, this afternoon, an ontology entity) and evaluates
rules **per object**:

- **Object**: the thing you track, identified by one field: a bus line, a package, a freezer. Every rule is
  evaluated independently per object instance, so "line H16 at the Fòrum" and "line 7 at the Fòrum" have their own
  state.
- **Property**: a field of the event (or a computed one you define once and reuse across rules).
- **Rule**: a condition on a property plus an action.
- **Action**: email; Teams (person, group chat, channel); **run a Fabric item** (pipeline, notebook, Spark job,
  dataflow, user data function, copy job); **publish a business event** (preview); custom action via Power
  Automate.

You pay only while rules are **started**. Rules are created stopped.

## Three kinds of conditions

| Kind | Examples (UI names) | Fires when |
|---|---|---|
| **Stateless** (numeric/text/logical *state*) | **Is greater than**, **Is between**, **Contains**, **Is equal to** | Each event where the condition holds. Add an **Occurrence** of **When it has been true for** *N minutes* to require it to *stay* true. |
| **Stateful** (numeric/text/logical *change*) | **Increases above**, **Decreases below**, **Changes to**, **Becomes true**, **Changes** | On the *transition* into the state, once per object, not on every event while it stays there. |
| **Heartbeat** | **No presence of data**, **Object first appearance** | No event for the object within a window / an object ID is seen for the first time. |

Plus **Summarization** (average/min/max/sum/count over a rolling window) and up to three **Property filters**
(e.g. `Rank == 1`) that narrow which events a rule sees.

**Why "sustained" matters.** A bus prediction of 13 minutes for one poll is noise (TMB's estimate wobbles). Thirteen
minutes for five consecutive minutes is a gap in service. Stateless-with-occurrence, or a stateful "Increases
above", is what separates an alert from spam. This afternoon Brian's `Freezer running warm` rule makes the same
choice ("above -12 °C, sustained 5 minutes") on the ontology; you build the bus version now.

## Where you can author a rule

1. **Inside an eventstream** (Live view → Activator destination → **Rules** pane → **Add rule**) — quick, in
   context. **Today's route.**
2. **The Activator item itself** — full editor: objects, properties, summarisation, filters, analytics.
3. **Real-Time hub → Set alert** on any stream or Fabric/Azure event — Module 06's route.
4. **A Real-Time Dashboard tile** or **a Power BI visual** — "alert me when this number…".
5. **An Ontology entity** (preview) — this afternoon.

## Actions beyond notifications

An action that *runs a Fabric item* is what turns detection into automation: files land → pipeline runs;
anomaly detected → notebook scores it; threshold crossed → user data function calls an external API.
Parameters can be passed from event fields (preview). Module 06 uses **Run notebook**; Module 05 sticks to
email so you can watch a rule fire end-to-end within minutes.

## What we build

In Activator item **`TransitAlerts`**, fed by the `ForumNextBus` derived stream (the venue stops, one row per
line per minute with the minimum, i.e. next-bus, prediction), object **`VenueLine`** with ID `LineCode`:

| Rule | Condition | Occurrence | Action |
|---|---|---|---|
| `Long wait at the Fòrum` | `MinutesToArrival` **Is greater than** `12` | **When it has been true for** `5 minutes` (five consecutive windows; the shortest the picker offers) | Email (Teams if available) |
| `Stop went silent` | **No presence of data** | `10 minutes` | Email |
| `Bus arriving now` (optional) | `MinutesToArrival` **Decreases below** `2` | — | Teams/email |

Why the stream is pre-aggregated: the raw feed has two predictions per line (next bus and the one after). A rule on
the raw per-bus events would see the second bus's 15 minutes and cry wolf. Taking the **minimum per minute** in the
eventstream gives Activator one clean number per line. The alternative is Activator's own **Summarization**
(Minimum over a window) on the raw stream; same idea, different place.

*Sources: [What is Fabric Activator?](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-introduction),
[Detection settings](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-detection-conditions),
[Create rules](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-create-activators),
[Trigger Fabric items](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-trigger-fabric-items)*

## Live demo before the lab (4 minutes, instructor workspace)

1. Open `TransitAlerts`. Select `Long wait at the Fòrum`: walk the **Definition** pane top to bottom: grouped
   by `LineCode` (the `VenueLine` object), `MinutesToArrival` **Is greater than 12**, **When it has been true for 5 minutes**, the email
   action with `@LineCode` in the headline. Point at the chart with the threshold line.
2. Open the **Analytics** tab: activations over time, per line.
3. Show your inbox with the email the rule sent during the dry run.
4. Back in `BusArrivalsEventstream` Live view, click the bell on the Activator destination: "this **Rules** pane is
   where you'll start; **Open in Activator** gets you the full editor you just saw".

> 🎤 Facilitator note: say once, clearly, whether the event accounts have Teams. If not, everyone uses email
> and nobody wastes five minutes on the Teams option.

Continue to [Lab 05: Activator rules on live arrivals](lab-05-activator-rules-on-live-arrivals.md).
