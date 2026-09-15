# Module 06: Wrap-up and Resources

**Duration:** 10 minutes
**Format:** Presenter-led recap. Not a lab — no new hands-on steps in this module.

**Learning objectives**
- See the full day's build laid out end to end, from empty workspace to a governed, traceable agent
  action.
- Know where to go on Microsoft Learn and GitHub to keep learning after today.
- Know what to do with the "Fabric IQ" workspace once the workshop ends.

## What you built today

Every module handed off directly to the next. Here's the whole arc in one place:

1. **Workspace and plumbing** (Module 00) — the "Fabric IQ" workspace, provisioned via
   `setup/provision_fabric_iq.py`, with `ColdChainLakehouse` (reference data: Customers, Stores,
   Freezers), `ColdChainEventhouse`, and `FreezerTelemetryEventstream` already in place before hands-on
   work began.
2. **Architecture and context** (Module 01) — where Fabric IQ sits relative to the RTI items you already
   knew from the morning, and why raw events need business context to be interpretable at all.
3. **Grounded telemetry** (Module 02) — live freezer temperature readings combined with static reference
   data and enriched into `FreezerTelemetryEnriched`, the semantically meaningful table everything
   downstream is bound to.
4. **`ColdChainOntology`** (Module 03) — the shared business vocabulary: `Customer`, `Store`, and
   `Freezer` entity types (`Freezer` carrying static `Model`/`Capacity`/`InstallDate` plus live
   `TemperatureC`/`DoorOpen`), connected by `Store —has—> Freezer` and `Customer —shops at—> Store`
   relationships, bound to the Lakehouse and Eventhouse data underneath — without copying it.
5. **Agents grounded in that ontology** (Module 04) — `ColdChainDataAgent` for conversational Q&A, and
   `ColdChainOperationsAgent` paired with the `Freezer running warm` Activator rule for continuous,
   governed monitoring and alerting.
6. **Trust and traceability** (Module 05) — the payoff of all of the above: every agent answer and every
   fired alert traces back through a specific entity instance, specific property values, and the
   underlying Eventhouse/Lakehouse data — not a black-box claim.

**Architecture → grounding → ontology → agents → trust.** That's the whole line, and it's the same line
Module 00's kickoff opened with four hours ago.

## Official Microsoft tutorials this workshop adapted

Every lab in this section traces back to tested, official Microsoft content rather than an untested,
presenter-invented click path. If you want the unmodified originals to re-run on your own:

- [Get started with Fabric IQ](https://learn.microsoft.com/fabric/iq/get-started-with-fabric-iq) — Module 00
- [Fabric IQ overview](https://learn.microsoft.com/fabric/iq/overview) and [Ontology tutorial part 0: Introduction](https://learn.microsoft.com/fabric/iq/ontology/tutorial-0-introduction) — Module 01
- [Digital Twin Builder RTI tutorial, parts 1–2](https://learn.microsoft.com/fabric/real-time-intelligence/digital-twin-builder/tutorial-rti-1-upload-contextual-data), [Kusto update policies](https://learn.microsoft.com/kusto/management/update-policy), and [materialized views](https://learn.microsoft.com/kusto/management/materialized-views/materialized-view-use-cases) — Module 02
- [Ontology tutorial part 1: Create an ontology](https://learn.microsoft.com/fabric/iq/ontology/tutorial-1-create-ontology), the [mslearn-fabric hands-on labs](https://microsoftlearning.github.io/mslearn-fabric/) (labs 23, 24, 27), and [Digital Twin Builder tutorial, parts 3–4](https://learn.microsoft.com/fabric/real-time-intelligence/digital-twin-builder/tutorial-rti-1-upload-contextual-data) — Module 03
- [Ontology tutorial part 4: Consume ontology from agents](https://learn.microsoft.com/fabric/iq/ontology/tutorial-4-create-data-agent), the [mslearn-fabric hands-on labs](https://microsoftlearning.github.io/mslearn-fabric/) (lab 28), [Create an operations agent grounded in an ontology](https://learn.microsoft.com/fabric/iq/ontology/how-to-create-operations-agent), and [Ontology rules](https://learn.microsoft.com/fabric/iq/ontology/how-to-use-rules) — Module 04
- [Agent integration options for ontology (preview)](https://learn.microsoft.com/fabric/iq/ontology/concepts-agent-integration) and [Fabric IQ Ontology MCP (preview)](https://learn.microsoft.com/microsoft-copilot-studio/mcp-fabric-iq-ontology) — Module 05

## Keep exploring after today

- **[Get started with Fabric IQ](https://learn.microsoft.com/fabric/iq/get-started-with-fabric-iq)** —
  your best next stop on Microsoft Learn. It's the entry point into the full guided tutorial series
  (ontology, graph, and data agent tutorials) this workshop drew from, for whenever you want to rebuild
  today's scenario — or a different one — end to end on your own.
- **[mslearn-fabric hands-on labs](https://microsoftlearning.github.io/mslearn-fabric/)** — the full
  Microsoft-maintained lab catalogue this workshop's Module 03/04 labs referenced (labs 23, 24, 27, 28).
  It covers the rest of Fabric too, well beyond Fabric IQ, if you want to go deeper on the platform.
- **[microsoft/Ontology-Playground](https://github.com/microsoft/Ontology-Playground)** — a free,
  open-source, zero-backend web app for learning ontology design outside of Fabric itself: browse a
  catalogue of pre-built ontologies (including a retail one similar in spirit to `ColdChainOntology`),
  design your own visually, and export as RDF/XML. A good low-stakes way to practice entity/relationship
  modeling before your next live Fabric session.

<!-- facilitator: if attendees ask where to find a Microsoft Learn "learning path" for Fabric IQ specifically, be upfront that as of this workshop there isn't a dedicated training learning path (unlike Real-Time Intelligence's "Implement Real-Time Intelligence with Microsoft Fabric" path) — the Get-started page and tutorial series above are the closest equivalent. Don't invent a URL if someone asks and you're not sure; point them to https://learn.microsoft.com/training/browse/?products=fabric to search current offerings. -->

## Feedback and cleanup

Thank you for spending your afternoon on this. A couple of closing housekeeping notes:

- **If you provisioned "Fabric IQ" solely for this workshop** and don't plan to keep building on the
  cold-chain scenario, consider deleting the workspace afterward — the Ontology and Data Agent items in
  particular were running against a paid, non-trial capacity for the duration of the workshop, and
  leaving them in place keeps consuming that capacity's resources after you've gotten the learning value
  out of them. Deleting the workspace removes everything in it (Lakehouse, Eventhouse, Eventstream,
  Ontology, Data Agent, Operations Agent) in one step.
- **If you want to keep it**, that's completely fine too — everything you built is yours to keep exploring
  or extend into a real scenario.
- Please share feedback with your facilitator, or via whatever feedback channel this event is using — it
  directly shapes whether Module 05's time-box buffer, the pacing of Modules 03/04, and the overall
  scenario choice hold up for the next run of this workshop.

That's the end of the Fabric IQ section. Thank you for building the whole cold-chain scenario with us
today.
