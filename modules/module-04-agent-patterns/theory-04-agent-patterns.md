# Module 04 Theory: Agent Patterns over Real-Time and Semantic Layers

**Duration:** 15 minutes
**Format:** Presenter-led discussion, no hands-on activity in this part.

**Learning objectives**
- Know the landscape of ways to ground an AI agent in a Fabric IQ ontology, and when to reach for each.
- Distinguish a Fabric Data Agent (conversational Q&A) from an Operations Agent (continuous monitoring
  and action).
- Understand how Activator Ontology Rules are the connective tissue that turns an Operations Agent's
  monitoring into a real alert or action, expressed in business language instead of a raw threshold.
- Preview the two agents and the one rule this module's lab builds.
- Understand — ahead of Module 05 — why an ontology-grounded agent's answers are more trustworthy than
  an agent with free-form access to tables.

## From ontology to action

Module 03 gave you `ColdChainOntology`: entity types `Customer`, `Store`, and `Freezer`, wired together by
relationships (`Store`—has—>`Freezer`, `Customer`—shops at—>`Store`) and bound to real data in
`ColdChainLakehouse` and `ColdChainEventhouse`. Up to this point, the ontology has been **descriptive** —
a governed model of the business that a human can browse and query directly in the Ontology (preview)
canvas.

This module makes it **operational**. An ontology only pays for itself once something — a person asking a
question, or a system watching for a problem — can act on it without first learning the underlying schema.
That "something" is an agent. Fabric IQ doesn't lock you into one agent shape; it exposes the ontology as a
governed context that several different kinds of agents can consume.

## The four ways to ground an agent in an ontology

Per Microsoft's own framing of [agent integration for ontology (preview)](https://learn.microsoft.com/fabric/iq/ontology/concepts-agent-integration),
there are four supported paths. All four see the same entity types, relationships, and definitions — they
differ in *where* the agent lives and *what kind of experience* it offers.

| Agent | Primary experience | Best for | Audience |
|---|---|---|---|
| **Fabric Data Agent** | Conversational Q&A inside Fabric | Interactive analytics over governed data, with ontology context added on top | Data analysts, business users |
| **Fabric Operations Agent** | Continuous monitoring with recommended actions | Real-time monitoring, alerting, and automated actions against business goals | Operations teams |
| **Foundry IQ** | Custom developer agent with tool calling | Advanced, customizable agents that integrate with enterprise systems beyond Fabric | Developers |
| **Copilot Studio (Fabric IQ Ontology MCP connector)** | Low-code conversational agent, or any MCP-compatible client | Building agents in *other* Microsoft tooling that still ground in the same ontology | Business makers, low-code developers, developers wiring up custom/external agents |

Today's lab builds the first two directly. Foundry IQ and the Copilot Studio MCP connector matter for the
same reason a REST API matters even if you're not calling it today: they mean the ontology you designed in
Module 03 isn't a Fabric-only asset. The same governed entity types, relationships, and rules can be
exposed as an MCP server and consumed by a custom agent stack, or wired into a Copilot Studio flow — the
ontology becomes the shared source of truth across whatever surface an agent needs to live on.

### Fabric Data Agent — Q&A over the ontology graph

A [Fabric Data Agent](https://learn.microsoft.com/fabric/data-science/concept-data-agent) is a
conversational agent you build directly in Fabric. You add your ontology as a data source, and from then
on questions asked in plain English are resolved against **entity types and relationships**, not raw table
joins. Ask "which freezers belong to the Eixample store" and the agent doesn't need you to know that
`Freezer` and `Store` live in different Lakehouse tables joined on a foreign key — it walks the
`Store`—has—>`Freezer` relationship that's already defined in the ontology. This module's lab builds
`ColdChainDataAgent` as the worked example.

### Fabric Operations Agent — the direct bridge from RTI to IQ

A [Fabric Operations Agent](https://learn.microsoft.com/fabric/real-time-intelligence/operations-agent)
flips the interaction model: instead of waiting for a question, it continuously watches your ontology data
against goals you describe in natural language, and proactively surfaces insights or recommends actions —
by default, as a Teams message to its creator. Each operations agent is a dedicated Fabric item with its
own Microsoft Entra Agent ID, so its actions are auditable and distinct from a human session; it runs with
the delegated permissions of the person who created it. This is the direct bridge between the RTI half of
today's workshop and the IQ half: it takes the live telemetry Eventstream/Eventhouse pattern you already
know from Johan's session and reasons over it *through* the ontology's entity types instead of raw KQL
tables. This module's lab builds `ColdChainOperationsAgent`, configured to monitor the `Freezer` entity
type specifically.

### Foundry IQ — knowledge-base grounding for custom agent stacks

[Foundry IQ](https://learn.microsoft.com/azure/foundry/what-is-foundry) exposes the ontology as a reusable
knowledge source that a custom Azure AI Foundry agent queries at runtime. This is the path for developers
who need full tool-calling, orchestration, and integration with systems outside Fabric, while still
treating the ontology as the single governed source of truth rather than re-deriving business meaning
inside their own agent code.

### Copilot Studio + the Fabric IQ Ontology MCP connector

The ontology can also function as a **Model Context Protocol (MCP) server**. The Fabric IQ Ontology MCP
connector lets Copilot Studio — or any other MCP-compatible client — discover and query the ontology's
entity types and relationships without a bespoke integration. This is the option for teams standardizing
on Copilot Studio (or another agent framework entirely) who still want their agents to answer with the
same business definitions as the Fabric-native agents.

## The connective tissue: Activator Ontology Rules

An Operations Agent watching for a problem is only half the story — something has to translate "the data
looks wrong" into an actual notification a person acts on. That's what **Activator Ontology Rules** add.
Rules are a feature of the Ontology (preview) item that lets you define alert conditions directly against
an entity type's properties — for example, `Freezer.TemperatureC` — and under the hood, each rule is backed
by [Fabric Activator](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-introduction),
the same no-code event-detection engine from Johan's RTI session. The rule is saved to a Fabric Activator
item, evaluated continuously, and can trigger a Teams message, an email, or a broader set of Activator
action types.

The reason this matters for trust and usability: a rule authored *on the ontology* speaks in business
terms — "Freezer running warm" — rather than "`KQLDatabase.FreezerTelemetryRaw` column `TemperatureC` >
-12". The person receiving the alert doesn't need to know which table or column produced it; they see a
named condition on a named business entity. This module's lab builds exactly one such rule, named
`Freezer running warm`, that fires when a `Freezer`'s `TemperatureC` stays above roughly -12°C for a
sustained window — simulating a door left open or a compressor fault, which is precisely the anomaly the
Module 02 synthetic telemetry generator periodically injects.

> 🎤 Facilitator note: emphasize the word *sustained*. A rule that fires on any single reading above -12°C
> would also fire on a momentary door-open-and-closed blip. A temporal condition — "above threshold for N
> minutes" — is what distinguishes a real fault worth paging someone about from ordinary freezer-door
> traffic. This is a deliberate design choice attendees should notice when they configure the rule's
> condition in the lab, not an incidental detail.

## Today's worked example, end to end

By the end of this module's lab, three new things exist, all grounded in `ColdChainOntology`:

1. **`ColdChainDataAgent`** — ask it natural-language questions and watch it resolve them through entity
   and relationship names.
2. **`ColdChainOperationsAgent`** — configured to continuously monitor the `Freezer` entity type.
3. **`Freezer running warm`** — an Activator Ontology Rule on `Freezer.TemperatureC`, wired to a Teams or
   email action, that fires in business language when the Module 02 generator's synthetic anomaly lands.

## Looking ahead to Module 05

Every answer `ColdChainDataAgent` gives you in the lab is constrained to entities and properties that
*exist in the ontology* — it cannot silently query a table that isn't modeled, or invent a relationship
that wasn't defined. That constraint is exactly what Module 05 picks up: an ontology-grounded agent's
answers are more trustworthy specifically *because* they're boxed in this way, not despite it. Free-form
table access gives an agent more room to hallucinate a plausible-sounding but ungoverned answer; ontology
grounding trades some of that flexibility for an answer you can actually trace back to a defined entity,
property, and binding. Module 05 covers how to prompt, validate, and audit that trust in practice.

<!-- facilitator: if the room is short on time, the four-agent landscape table is the part safest to
compress to a quick read-through — the two hands-on agents (Data Agent, Operations Agent) and the rule are
what the lab actually needs attendees to understand deeply. -->

> 🎤 Facilitator note: keep this to 15 minutes. The lab is where the concepts land — don't over-explain
> Foundry IQ or the MCP connector here, a one-paragraph mention each is enough since neither is built
> hands-on today.

Continue to [Lab 04: Build a Data Agent and Operations Agent](lab-04-build-data-agent-and-operations-agent.md).
