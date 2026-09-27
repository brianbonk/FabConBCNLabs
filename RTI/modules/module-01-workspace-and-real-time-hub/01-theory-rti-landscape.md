# Module 01 Theory: The RTI Landscape in Fabric

**Duration:** 5 minutes
**Format:** Presenter-led, no hands-on activity.

**Learning objectives**
- Name the RTI items and where each one lives (workspace vs tenant-wide).
- Understand that Real-Time hub is a *view*, not a container: it lists streams and events you can already reach.
- Know the two containers we create before touching any data: an Eventhouse and a Lakehouse.

## Where things live

| Item | Scope | Created by you? |
|---|---|---|
| **Real-Time hub** | Tenant-wide, one per tenant, always there | No. It's the discovery surface for every stream, KQL table and event source you have access to. |
| **Eventstream** | Workspace item | Yes (Module 02) |
| **Eventhouse** → KQL database(s) | Workspace item; the Eventhouse is the container, databases live inside it | Yes (this module). Creating an Eventhouse auto-creates one KQL database **with the same name**. |
| **KQL Queryset** | Workspace item; saved queries against one or more databases | Yes (Module 03) |
| **Real-Time Dashboard** | Workspace item | Yes (Module 04) |
| **Activator** | Workspace item; holds objects + rules | Yes (Modules 05, 06) |
| **Lakehouse** | Workspace item | Yes (this module). Only used for reference files and as an OneLake-event source in Module 06. |

Three points worth saying out loud:

1. **An Eventhouse is a cluster, a KQL database is a database.** Compute (and cost) is at the Eventhouse level;
   tables, functions, policies and materialized views are at the database level. We use the default database.
2. **Real-Time hub doesn't store anything.** It lists what exists: your eventstreams' outputs, your KQL tables,
   Fabric events (OneLake, job, workspace item, capacity), Azure events (Blob Storage), and the connector
   gallery. Every "Connect to data source" you start from the hub ends up creating an Eventstream in a
   workspace you pick.
3. **Capacity.** Every item above runs on the capacity behind the workspace: a **P1**, shared with the other attendees
   assigned to it. This morning each of you runs two eventstreams, an Eventhouse and a dashboard; this afternoon
   Ontology and Data Agent run on the *same* capacity, which is why Module 07 pauses the streams. When a capacity
   is over its limit, Fabric pauses eventstreams rather than slowing them, so "my stream stopped" is a capacity
   symptom before it's a bug.

## Why a Lakehouse in an RTI workshop

Two reasons, both later: Module 06 uses a file landing in the Lakehouse as the *event* that triggers automation,
and Module 03's stretch section makes Eventhouse tables visible as Delta in OneLake so Lakehouse/Spark
consumers can read them. Reference data itself is loaded straight into the KQL database (Module 03), not via
the Lakehouse; the afternoon's cold-chain scenario does it the other way round (Lakehouse first, notebook, then
KQL) so you'll see both.

*Source: [Real-Time Intelligence overview](https://learn.microsoft.com/fabric/real-time-intelligence/overview),
[Real-Time hub overview](https://learn.microsoft.com/fabric/real-time-hub/real-time-hub-overview),
[Eventhouse overview](https://learn.microsoft.com/fabric/real-time-intelligence/eventhouse)*

Continue to [Lab 01: Create the workspace and explore Real-Time hub](lab-01-create-workspace-and-explore-real-time-hub.md).
