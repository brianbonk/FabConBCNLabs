# Module 11 Theory: Ontology Design Essentials for Operational AI

**Duration:** 15 minutes
**Prerequisites:** Module 10 complete — `ColdChainKQLDB` contains a populated `FreezerTelemetryEnriched` table with live, grounded `TemperatureC` and `DoorOpen` readings per `FreezerId`.

**Learning objectives**
- Define entity type, property, and relationship as they exist in Fabric IQ's **Ontology (preview)** item.
- Understand data binding: how an ontology attaches to OneLake data by reference, without copying it.
- Understand that an ontology becomes a queryable graph — traversable with GQL, backed by KQL for live signals, and reachable through natural language (NL2Ontology).
- Apply three design essentials for operational AI scenarios when modeling the retail cold-chain ontology in Lab 11.
- Know exactly which prerequisite you cannot fix live if it's missing.

## Where we are in the story

Module 10 ended with a working pipeline: raw freezer telemetry, landed in `ColdChainEventhouse`, transformed by an update policy and a materialized view into `FreezerTelemetryEnriched` — live temperature and door-state readings, each one already tagged with the `FreezerId` that produced it. That's real-time data with a little bit of shape, but it still isn't *business meaning*. `FreezerTelemetryEnriched` doesn't know that a `FreezerId` belongs to a store, that the store belongs to a region, or that a customer's loyalty tier might matter when you decide how urgently to respond to a warm freezer.

That durable layer of business meaning — the thing that lets a person or an AI agent ask "which stores have a freezer running warm right now?" instead of writing a KQL join by hand every time — is what Fabric IQ's **Ontology** item provides. This module builds it, live, on top of the plumbing you already have.

> ⚠️ **This feature is in preview.** Everything in this module operates on the **Ontology (preview)** item. Preview features can change UI labels or behavior between when this was written and when you run it — if something on screen doesn't match a screenshot exactly, trust the described *intent* of the step over the exact pixels.

## What an ontology actually is

Per Microsoft's own framing, an ontology is "a shared, machine-understandable vocabulary of your business" — the things in your environment, their facts, and the ways they connect, with constraints that keep everyone's representation consistent. Concretely, it's built from three concepts:

- **Entity type** — the reusable logical model of a real-world concept, like *Store*, *Customer*, or *Freezer*. It standardizes a name, an identifying key, and a set of properties so every team and every tool means the same thing when they say "freezer" — instead of five different definitions scattered across five tables.
- **Property** — a named, typed fact about an entity type, like a Freezer's `Model` or its live `TemperatureC`. Properties carry a declared data type and a binding to source data.
- **Relationship** — a typed, directional link between entity types, like *Store has Freezer* or *Customer shops at Store*. Relationships make connections explicit and queryable instead of buried in join logic that only the person who wrote the query understands.

An **entity instance** is a concrete occurrence of an entity type — one specific freezer, populated from whatever data is bound to the `Freezer` entity type. You never hand-create instances; they appear automatically once bindings exist.

You build all of this in a no-code **configuration canvas** — you add entity types and relationships as visual cards, and attach data through a **data binding** wizard, rather than writing DDL or Python.

## Binding is a reference, not a copy

This is the single most important mental model for today: when you bind an entity type's properties to a Lakehouse table or an Eventhouse table, **the ontology does not copy that data anywhere.** OneLake data (whether it lives in `ColdChainLakehouse` or `ColdChainEventhouse`) stays exactly where it is. The ontology stores a *description* — which table, which columns, which column is the identifying key — and reads through that description at query time. Update a row in `Stores`, and the ontology sees the new value the next time it's asked, with no ETL pipeline of your own to maintain.

Practical implications this brings for design:

- **One static binding per entity type, but multiple time-series bindings are allowed.** An entity type can pull its unchanging attributes from exactly one Lakehouse (or semantic model) source, but it can pull live, fast-moving signals from more than one Eventhouse or Lakehouse time-series source simultaneously. This is exactly the shape `Freezer` needs today: one static binding (to `Freezers`) plus one time-series binding (to `FreezerTelemetryEnriched`).
- **Bindable sources have real constraints.** Lakehouse tables must be **managed** tables (not shortcuts to an external location) with OneLake security *disabled* and column mapping *disabled*. If your source doesn't meet these, ontology binding will fail or behave oddly — this is a documented limitation, not a workshop-specific quirk.
- **Refresh is not automatic for new rows.** Changes to your ontology's *schema* (adding a property, adding a relationship) trigger an automatic re-sync. But new *rows* arriving in an already-bound source table — like a fresh telemetry event landing in `FreezerTelemetryEnriched` — do **not** appear in the ontology graph until you trigger a refresh (on demand, or on a schedule) of the Graph item that Fabric creates alongside your ontology. Keep this in mind for the lab: the ontology is "live" in the sense that it always answers from the current source, once refreshed — it is not a literal streaming push feed into the graph view.

## The ontology becomes a queryable graph

Creating an ontology item automatically provisions a paired **Graph in Microsoft Fabric** item. Nodes in that graph are entity instances; edges are relationship instances. This gives you:

- **Federated querying** — the ontology layer routes a query to whichever engine actually holds the answer (GQL against the graph, KQL against Eventhouse) and returns a single, business-shaped result, instead of you writing cross-engine joins by hand.
- **Natural-language querying (NL2Ontology)** — a Fabric Data Agent can translate a plain-English question like "which freezers are above their safe temperature right now?" into a structured query that respects the ontology's definitions: the right filters, the right joins via relationships, the right units. Module 12 builds this agent directly on top of what you create today.
- **Visual exploration** — the entity type details view (Configure / Instances / Overview tabs) lets you browse instances, inspect a single Freezer's static and live properties side by side, and expand a full graph view to see how everything connects.

## Design essentials for operational AI

Three things matter more here than in a general-purpose data model, because this ontology is going to be queried by an AI agent, not just read by a person who already knows the business:

**1. Bind each property to the source that changes at the right cadence.** Static, slow-changing attributes (a freezer's `Model`, `Capacity`, `InstallDate`) belong on a Lakehouse binding. Fast-changing operational signals (`TemperatureC`, `DoorOpen`) belong on a time-series binding to Eventhouse. Binding a live signal to a Lakehouse snapshot — or vice versa — either starves your agent of freshness it needs, or wastes refresh cost on data that never changes. `Freezer` in today's lab deliberately carries both binding types on one entity type to make this distinction concrete.

**2. Keep relationships meaningful to the business, not just foreign-key mechanics.** A relationship type is named like a verb a business person would actually say — *Store has Freezer*, *Customer shops at Store* — not "StoreFreezerLink" or "FK_Store_Freezer". The underlying mechanism is still a matched key column (`StoreId`, `HomeStoreId`), but the name is what an agent and a human both read when reasoning about the graph. Microsoft's own troubleshooting guidance for data agents backs this up directly: vague or generic query results are frequently traced back to entity and relationship names that aren't meaningful or documented.

**3. Design for what an agent will need to ask later.** Every entity, property, and relationship name you choose today becomes part of the vocabulary Module 12's Data Agent uses to answer questions. If "is this freezer's temperature outside a safe range, and which store and customer does that affect" isn't answerable by walking the entities and relationships you build today, no amount of clever prompting in Module 12 will fix it after the fact. Model the business question first; the schema follows.

## Prerequisites — the one thing you cannot fix live

The Ontology (preview) item type will simply **not appear** under **+ New item** unless a Fabric tenant administrator has explicitly enabled it — there is no in-session workaround. Before today, your tenant admin needed to enable:

- **Enable Ontology item (preview)** (tenant setting)
- The Azure OpenAI / Copilot tenant settings required for Fabric Data Agent (needed later, in Module 12, but worth confirming now since it's the same admin action)
- A non-trial capacity (F2+ or P1+) — Ontology, Graph, and Data Agent are not supported on trial capacities

See [`prerequisites/PREREQUISITES.md`](../../prerequisites/PREREQUISITES.md) for the full checklist. If Lab 11's first step shows no "Ontology (preview)" option, stop immediately rather than troubleshooting in place — see the lab's troubleshooting block for what to do instead.

## The worked example: `ColdChainOntology`

Today you build one ontology item, named `ColdChainOntology`, with this design:

| Entity type | Entity type key | Static properties (Lakehouse) | Live properties (Eventhouse) |
|---|---|---|---|
| `Store` | `StoreId` | `StoreId`, `StoreName`, `Region`, `City` (from `ColdChainLakehouse.Stores`) | — |
| `Customer` | `CustomerId` | `CustomerId`, `Name`, `HomeStoreId`, `LoyaltyTier` (from `ColdChainLakehouse.Customers`) | — |
| `Freezer` | `FreezerId` | `FreezerId`, `StoreId`, `Model`, `Capacity`, `InstallDate` (from `ColdChainLakehouse.Freezers`) | `TemperatureC`, `DoorOpen` (from `ColdChainEventhouse.ColdChainKQLDB.FreezerTelemetryEnriched`) |

| Relationship type | Origin → Target | Matched on |
|---|---|---|
| `has` | `Store` → `Freezer` | `Store.StoreId` = `Freezer.StoreId` |
| `ShopsAt` | `Customer` → `Store` | `Customer.HomeStoreId` = `Store.StoreId` |

`Freezer` is the entity to watch closely in the lab: it's the one entity type in this whole workshop that binds to **two different sources at once** — proof, in your own workspace, that binding is a reference layer over OneLake, not a copy of it.

> 🎤 Facilitator note: if the room is tight on time, the binding-not-copying concept and the "refresh isn't automatic" caveat are the two ideas worth protecting — cutting the rest of the conceptual framing is safer than cutting either of those, since both prevent confusion five minutes into the lab.

<!-- facilitator: this is also the natural moment to preview that Module 12's Data Agent quality is directly downstream of how well-named these entities/relationships/properties are — plant that seed here so it lands again in Module 12 instead of feeling new. -->

Continue to [Lab 11: Build the Retail Cold-Chain Ontology](lab-11-build-retail-coldchain-ontology.md).
