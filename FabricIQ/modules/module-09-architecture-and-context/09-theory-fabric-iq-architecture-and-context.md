# Module 09 Theory: Fabric IQ Architecture and Context

**Duration:** 10 minutes
**Prerequisites:** Module 08 complete — your "Fabric IQ" workspace is verified and contains
`ColdChainLakehouse`, `ColdChainEventhouse`, `FreezerTelemetryEventstream`, and `00_LoadReferenceData`.

**Learning objectives**
- Topic 1: Understand where Fabric IQ sits in the Fabric stack and what its core items are.
- Topic 2: Understand why raw event data is meaningless without business context, using the cold-chain
  scenario as a concrete case study.

## Topic 1: Fabric IQ concepts in practical architecture

Everything you built or verified in Module 08 — the Lakehouse, the Eventhouse, the Eventstream — is data
plumbing. It moves and stores data, but it doesn't know what any of that data *means* to the business. A
`ColdChainLakehouse.Freezers` table and a `FreezerTelemetryRaw` KQL table are, as far as Fabric is
concerned, just a Delta table and a KQL table. Nothing tells Fabric — or an AI agent — that they describe
the same physical freezers, or what "too warm" means for one of them.

**Fabric IQ is the layer that sits on top of that plumbing and supplies the missing business meaning.**
It's part of Microsoft IQ, the broader enterprise-intelligence layer of the Microsoft stack (alongside
Work IQ and Foundry IQ), and it brings three layers of context to your data:

- **Unified data (OneLake).** Fabric IQ doesn't copy your data — it binds to what's already in OneLake:
  Lakehouses, Eventhouses, Power BI semantic models, even data shortcut-ed in from outside Fabric. This
  is a critical property to internalize before Module 11: when we build the ontology and bind it to
  `ColdChainLakehouse` and `ColdChainEventhouse`, we are not duplicating those tables — we're layering
  meaning on top of the same rows.
- **Business intelligence (Power BI semantic models).** Curated measures, hierarchies, and KPIs. Ontologies
  can be generated from semantic models already in production, so business language stays consistent
  between reports and agents rather than being defined twice.
- **Operational intelligence (ontology).** The layer we spend the rest of today on. An **Ontology** defines
  entity types, relationships, properties, rules, and actions — the shared vocabulary that lets both
  people and AI agents reason in terms of *Customer*, *Store*, and *Freezer* instead of raw table and
  column names.

The IQ workload's core items, several of which we build hands-on later today, are:

| Item | What it does | When we touch it |
|---|---|---|
| **Ontology** (preview) | Shared business vocabulary — entities, relationships, properties, rules | Module 11 |
| **Graph** | Visual/queryable traversal of the relationships the ontology declares | Module 11 |
| **Power BI semantic model** | Curated KPIs and measures; ontologies can be generated from it | Referenced, not built today |
| **Planning** | Collaborative forecasting/planning on the same data foundation | Not used in this scenario |
| **Data agent** | Natural-language Q&A grounded in the ontology / semantic model | Module 12 |
| **Operations agent** | Monitors live data, detects anomalies, triggers governed action | Module 12 |

None of these exist in your workspace yet — you confirmed that in Module 08's lab. What you *do* have is
exactly the unified-data foundation Fabric IQ needs: a Lakehouse with business reference data and an
Eventhouse ready to receive live telemetry. That's the deliberate starting point for everything that
follows this afternoon.

> 🎤 Facilitator note: emphasize "binds, doesn't copy" — it's the single most-asked question later in
> Module 11 ("wait, is the ontology creating a new table?").

*Source: [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)*

## Topic 2: Why context matters for event interpretation

Here's a value straight out of the Eventhouse you verified in Module 08 (once the generator is running in
Module 10, this is what a row of `FreezerTelemetryRaw` will actually look like):

```
FreezerId: "FRZ-0142"
TemperatureC: -9.0
Timestamp: 2026-09-06T14:32:00Z
```

Ask yourself: is this a problem?

You genuinely cannot answer that from the row alone. `-9.0°C` is:

- **Alarming** if `FRZ-0142` is a supermarket freezer that should hold roughly **-18°C** — nine degrees
  warm is a cold-chain breach that risks spoiled inventory and, depending on the product, a food-safety
  incident.
- **Completely unremarkable** if `FRZ-0142` were instead an ambient warehouse temperature sensor, where
  -9°C might just mean it's a cold morning near a loading dock.
- **A different severity of alarming** depending on *which store* it's in, *which customer account* owns
  that store, and whether that store has a service-level agreement that makes a breach contractually
  significant, not just operationally significant.

The raw event — an ID and a number — cannot answer any of that. The meaning lives in business context that
exists nowhere near the telemetry stream: a device registry that says `FRZ-0142` is a *Freezer* (not a
generic sensor), a target-temperature rule that says freezers should read close to -18°C, and a Store/
Customer relationship that tells you who to notify and how urgently.

This is precisely the gap Fabric IQ's ontology layer exists to close, and it's why Microsoft's own product
documentation uses almost this exact scenario as its running example for cross-domain reasoning: an
ontology lets you traverse a relationship chain like **Order → Shipment → Temperature Sensor → Cold Chain
Breach** to explain an outcome, instead of stopping at "here is a number." Today's lab scenario is that
same pattern, built end to end: `Freezer` (device) → `Store` (location) → `Customer` (business account),
with live temperature telemetry bound to the `Freezer` entity so the number always resolves back to a
named, owned, business-meaningful thing.

This is also why Module 10's grounding work and Module 11's ontology design aren't optional plumbing —
they're the entire point of the section. An agent asked "which freezers are at risk right now" cannot give
a trustworthy answer over raw `FreezerTelemetryRaw` rows alone; it needs the same business context you, as
a human reading this table, were just missing.

> 🎤 Facilitator note: pause after the "-9.0°C" example and ask the room to guess whether it's a problem
> before revealing the answer — it lands better as a question than a statement.

<!-- facilitator: if pressed for time, this Topic 2 section is the one to keep — it's the emotional hook for the rest of the day. Topic 1's table can be skipped verbally and left as a reading reference. -->

## Sources

- [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)
- [Get started with Fabric IQ](https://learn.microsoft.com/fabric/iq/get-started-with-fabric-iq)

Continue to [Lab 09: Explore Workspace and Data Landscape](lab-09-explore-workspace-and-data-landscape.md).
