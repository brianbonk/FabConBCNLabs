# Module 13 Theory: Prompting, Grounding, Validation, and Trust

**Duration:** 10 minutes (this module's time was cut from 35 to 15 minutes total to fund Module 08's
expanded live setup — see `docs/agenda.md`; trim discussion depth here first if you're still running
long, before touching the lab)
**Format:** Presenter-led discussion, no hands-on activity in this part.

**Learning objectives**
- Understand how grounding an agent in an ontology acts as a validation mechanism, not just a
  convenience — the agent can only talk about entities, properties, and relationships that were
  explicitly modeled.
- Know how to prompt an ontology-grounded agent effectively: in the business vocabulary the ontology
  defines, not in terms of raw tables and columns.
- Be able to explain, concretely, what trust, transparency, and traceability mean for an agent action —
  using `ColdChainOperationsAgent`'s `Freezer running warm` rule as the running example.

## Why this module exists

You've now built the whole chain: telemetry grounded with business context (Module 10), a
`ColdChainOntology` that formalizes Customer, Store, and Freezer as entity types with real relationships
(Module 11), and two agents — `ColdChainDataAgent` for conversational Q&A and `ColdChainOperationsAgent`
for continuous monitoring — that reason over that ontology (Module 12). This module asks the question
that actually matters once agents start answering questions and taking action on real operational data:
**why should anyone trust what they say or do?**

The answer isn't "because it's AI and it sounded confident." It's structural, and it comes directly from
the ontology-grounding pattern you've already built.

## Grounding is a validation mechanism, not just a nicety

Compare two ways of asking a question about your freezers:

**Ungrounded — an LLM over raw tables.** You point a general-purpose language model at
`ColdChainLakehouse` and `ColdChainEventhouse` directly, and ask it "which freezers are at risk of
spoiling stock?" Nothing stops the model from inventing a plausible-sounding column, misjoining
`Freezers` to the wrong `StoreId`, or answering confidently about a `WarrantyExpiryDate` field that was
never in the schema at all. The model's fluency is completely decoupled from whether its answer is
actually correct — it will produce a well-formed sentence whether or not the underlying claim is true.
This is the classic hallucination problem: a free-form model over raw data has no structural reason to
say "I don't know."

**Grounded — an agent over `ColdChainOntology`.** `ColdChainDataAgent` doesn't see raw tables at all. It
sees the ontology: entity types `Customer`, `Store`, `Freezer`; the static and live properties actually
defined on `Freezer` (`Model`, `Capacity`, `InstallDate`, `TemperatureC`, `DoorOpen`); and the
relationships `Store —has—> Freezer` and `Customer —shops at—> Store`. As Microsoft's own agent
integration guidance puts it, an ontology gives an agent "a governed, shared understanding of your
business" so its responses are "more grounded, explainable, and consistent" than answers produced from
raw data or prompts alone (see [Agent integration options for ontology (preview)](https://learn.microsoft.com/fabric/iq/ontology/concepts-agent-integration)
in Further reading, below). The practical effect: the agent can only reason about concepts that
were deliberately modeled. If you ask about a property that doesn't exist — a warranty date, a supplier
contract term, anything outside the ontology — there is no column for the model to hallucinate a value
from, because it isn't reasoning over columns in the first place. It's reasoning over a constrained
graph of typed entities and defined relationships. **That constraint is itself a validation step,
enforced before the model ever generates a sentence** — not a best-effort instruction you hope the model
follows.

This is the core idea to land in this module: grounding doesn't just make agent answers *nicer to read*
(business language instead of column names) — it makes a whole class of answers *structurally
unavailable* to the model. An agent grounded in `ColdChainOntology` cannot correctly answer a question
about an entity or property outside that ontology, because that concept simply doesn't exist in its
world. The best it can do is say so.

## Prompting strategy: speak the ontology's vocabulary

Because the agent's entire reasoning surface is the ontology, the most effective prompts are the ones
written in the ontology's own terms:

- **Good:** "Which freezers does the customer Nordic Frost operate, and are any of them currently above
  threshold?" — this maps directly onto `Customer —shops at—> Store —has—> Freezer` and the
  `TemperatureC` property.
- **Weaker:** "Query the `Freezers` table joined to `Stores` where `temp_c` > threshold" — this asks the
  agent to think in raw-table terms it was deliberately insulated from. It may still work (the agent can
  often infer the mapping), but it isn't playing to the grounding you built, and it's a habit worth
  breaking in front of attendees now.

The mslearn ontology tutorials show exactly this pattern: example prompts like *"For each store, show any
freezers operated by that store that ever had a humidity lower than 46 percent"* deliberately use entity
and property names, and Microsoft calls out that a well-grounded agent's response references those
entity types and relationships back to you, "not just raw tables and columns" — that's your signal the
grounding is actually working, not just present ([Ontology tutorial part 4](https://learn.microsoft.com/fabric/iq/ontology/tutorial-4-create-data-agent)).
When you demo `ColdChainDataAgent` questions
later (or recap Module 12's), point this out explicitly: a good response *names* `Freezer`, `Store`, and
the property it checked, rather than reading like a black-box summary.

## Trust, transparency, and traceability — made concrete

These three words get used loosely in AI discussions. For an ontology-grounded agent, they have precise,
checkable meanings:

- **Trust**: can you rely on the agent's output being correct without independently re-verifying it every
  time? Grounding buys you a structural reason to trust — the agent's vocabulary is constrained to
  defined, governed concepts — but Microsoft is explicit that this doesn't eliminate the underlying LLM's
  probabilistic nature: outputs "can be incorrect," and results and recommendations still need review,
  particularly for an operations agent taking real action ([Operations agent best practices and limitations](https://learn.microsoft.com/fabric/real-time-intelligence/operations-agent-limitations)).
  Trust is earned by the combination of
  structural grounding *and* a working audit trail, not by grounding alone.
- **Transparency**: can you see *why* the agent said or did something, not just *what* it said? An
  operations agent rule isn't a black box — you can open the rule and see the actual query it runs
  against the ontology or Eventhouse, in terms of the real properties and conditions it evaluates.
- **Traceability**: can you walk backward from an agent's action to the specific data that caused it?
  This is the one worth walking through concretely, because it's exactly what Lab 13 does hands-on (or as
  a facilitator-led walkthrough, if time is short).

### Worked example: tracing `Freezer running warm`

`ColdChainOperationsAgent` continuously monitors `ColdChainOntology` and, when its `Freezer running warm`
rule condition is met, fires an alert. Trust in that alert isn't a matter of taking the agent's word for
it — it's a matter of being able to walk the full chain, backward, from the alert to the raw signal:

1. **The alert** — a specific notification, at a specific time, naming a specific `Freezer` instance.
2. **The entity instance** — that `Freezer` in the ontology graph, with its current `TemperatureC` and
   `DoorOpen` property values, and its relationship back to a `Store` and, through it, a `Customer`.
3. **The triggering event** — the actual row in `FreezerTelemetryEnriched` (Eventhouse) whose
   `TemperatureC` value crossed the rule's threshold at that timestamp.
4. **The rule configuration** — the condition itself (a state or transition condition against
   `TemperatureC`, evaluated on a running interval), which you can open and read like any other query,
   not reverse-engineer from behavior.

Every link in that chain is inspectable. Nothing about the alert depends on trusting an opaque model
output — the alert is a *pointer* into governed, queryable data, and the ontology is what makes that
pointer resolve to something specific (a named entity, a named property, a named relationship) instead of
"the AI flagged something." This is the concrete contrast with an ungrounded system: if a free-form LLM
looked at a dashboard and said "freezer 12 seems concerning," there would be no equivalent chain to walk
— just a claim, with no defined path back to the data that produced it.

> 🎤 Facilitator note: if you're short on time, this worked example is the one thing worth keeping even in
> a compressed pass — it's the concrete anchor for everything else in this module. Everything else
> (prompting phrasing, the ungrounded-vs-grounded contrast) can be delivered faster if needed.

<!-- facilitator: this module doubles as the section's time-box buffer. If Module 11 or 12 ran long, cut
straight to the "worked example" above and treat Lab 13 as a single facilitator-led walkthrough rather
than individual hands-on steps — see docs/risk-fallback-plan.md. -->

## Further reading

- [Agent integration options for ontology (preview)](https://learn.microsoft.com/fabric/iq/ontology/concepts-agent-integration) —
  how ontology grounding shapes agent responses, and which agents (data agent, operations agent, Foundry
  IQ, Copilot Studio, custom MCP clients) can consume an ontology as a source.
- [Fabric IQ Ontology MCP (preview)](https://learn.microsoft.com/microsoft-copilot-studio/mcp-fabric-iq-ontology) —
  how an ontology can be exposed as a Model Context Protocol server, so external and custom agents get
  the same grounded, governed access as native Fabric agents.
- [Create and configure operations agents — rule conditions](https://learn.microsoft.com/fabric/real-time-intelligence/operations-agent#understand-operations-agent-rules) —
  how to open a rule and inspect the actual query it evaluates, which is the mechanism behind the
  traceability example above.
- [Operations agent best practices and limitations](https://learn.microsoft.com/fabric/real-time-intelligence/operations-agent-limitations) —
  the explicit reminder that LLM-driven outputs remain probabilistic and require review, even when
  grounded.

Continue to [Lab 13: Validate and Audit Agent Responses](lab-13-validate-and-audit-agent-responses.md).
