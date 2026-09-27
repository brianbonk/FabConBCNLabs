# Module 08 Theory: Kickoff & Scenario Framing

**Duration:** 5 minutes
**Format:** Presenter-led framing, no hands-on activity in this part.

**Learning objectives**
- Understand how this section connects to the Real-Time Intelligence (RTI) half of the day you just completed.
- Know the single scenario every module for the next four hours builds toward.
- Have a mental map of the four-hour arc before diving into Module 08's lab.

## Welcome back

You've just spent the morning (or first half of today) in Johan's Real-Time Intelligence session, working
with Eventstream, Eventhouse, and Activator. This half of the day is co-presented content, not a fresh
start — everything from here on assumes you already know what those RTI items are and how event data
flows through them. We won't re-teach RTI fundamentals; Module 08 and Module 09 give only a light recap
before we build on top of what you already have running.

This half of the day is about **Fabric IQ** — Microsoft's ontology, semantic, and agent layer that sits on
top of the Fabric items you already know. Where RTI is about getting event data flowing, Fabric IQ is
about making that data *mean something* to the business, and letting AI agents reason over it safely.

## The scenario: retail cold-chain monitoring

Every module for the rest of the day builds toward one connected scenario. You work for a retail chain
that operates freezers in its stores to keep perishable goods cold. Each freezer streams live temperature
telemetry. On its own, a stream of numbers from a `FreezerId` tells you nothing about whether anything is
wrong — you need to know it's a freezer (not an ambient sensor), which store it's in, which customer
account owns that store, and what a "problem" even means in business terms.

By the end of the day you will have:

- Verified the pre-provisioned Fabric environment for this scenario (Module 08).
- Understood where Fabric IQ sits in the architecture and why raw events need business context to be
  interpretable (Module 09).
- Combined live freezer telemetry with static business reference data and grounded it with semantic
  meaning (Module 10).
- Designed a retail cold-chain ontology — Customer, Store, Freezer entities and their relationships —
  using the Fabric IQ Ontology (preview) item (Module 11).
- Built a Data Agent and an Operations Agent that reason over that ontology to answer questions and take
  governed action on live data (Module 12).
- Learned how to prompt, validate, and trust agent output — and trace every answer back to its source
  (Module 13).

None of the ontology, agent, or graph items exist yet — those get built live, starting in Module 11. Right
now, the only thing that needs to exist in your workspace is the plumbing: a Lakehouse with reference
data, an Eventhouse ready to receive telemetry, an Eventstream, and a notebook. Module 08's lab gets that
plumbing in place — live, right now, if you haven't already — and confirms it before we go any further.

## The arc, in one line

**Architecture → grounding → ontology → agents → trust.** Each module hands off directly to the next —
watch for the "Checkpoint" section at the end of every lab, it tells you exactly what should exist in your
workspace before you move on.

> 🎤 Facilitator note: keep this to five minutes flat — this is framing, not a lecture. Save the depth for
> Module 09's theory, which has dedicated time for the architecture and context-matters discussion.

<!-- facilitator: if the room is running early, use spare time here to ask who attended Johan's session live vs. is picking up mid-day, so you know how much RTI vocabulary you can assume in Module 08's lab. -->

Continue to [Lab 08: Environment Setup and Verify](lab-08-environment-setup-and-verify.md).
