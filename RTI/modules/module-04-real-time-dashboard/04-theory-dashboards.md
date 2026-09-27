# Module 04 Theory: Real-Time Dashboards

**Duration:** 5 minutes (2 concepts + 3 live demo)
**Format:** Presenter-led, two slides at most, then the demo.

**Learning objectives**
- Know what a Real-Time Dashboard is (KQL tiles over an Eventhouse) and when to use it instead of Power BI.
- Know the three features that matter today: **map visual**, **parameters**, **live refresh**.

## What it is

A Real-Time Dashboard is a workspace item made of **tiles**, each backed by a KQL query against a KQL database
(or Azure Data Explorer / Azure Monitor). Tiles support every `render` visual plus dashboard-only ones (map,
KPI, multi-stat, table). **Parameters** become filters that are pushed *into* the queries, so filtering stays
fast. **Live refresh** re-runs tiles when new data lands, without reloading the page. Dashboards can be shared,
exported as JSON, embedded, and each tile can spawn an **Activator alert**.

## When to use it vs Power BI

| | Real-Time Dashboard | Power BI report |
|---|---|---|
| Latency | Seconds; live refresh | Minutes (DirectQuery) to hours (import) |
| Author | Someone who writes KQL | Someone who models data |
| Best for | Operations screens, NOC walls, "what is happening now" | Business reporting, semantic models, governance |
| Data | KQL databases | Anything, including Eventhouse via Direct Lake / DirectQuery |

Both can sit on the same Eventhouse. Today we need seconds, so it's a Real-Time Dashboard.

## The tiles we build

1. **Map**: stops as points, sized by the current longest wait (query E4).
2. **Time chart**: average wait per line over the last two hours (E1), filtered by a `LineCode` parameter.
3. **Table**: next buses at the venue (D2).
4. **KPI** (optional): how many stops currently have a next bus more than 12 minutes away.

## Live demo before the lab (3 minutes, instructor workspace)

Open the finished `TransitOpsDashboard` in **Viewing** mode: let the venue table tick once. Switch to **Editing**,
open the map tile's editor, show the query pane and the **Visual setup** pane (**Map**, **Latitude and
longitude**). Change the **Line** parameter and watch the time chart re-query. Show **Manage → Refresh settings**.
Done; that's the whole lab.

> 🎤 Facilitator note: this module is the morning's buffer. Two tiles is a pass.

*Sources: [Create a Real-Time Dashboard](https://learn.microsoft.com/fabric/real-time-intelligence/dashboard-real-time-create),
[Customize visuals](https://learn.microsoft.com/fabric/real-time-intelligence/dashboard-visuals-customize),
[Parameters](https://learn.microsoft.com/fabric/real-time-intelligence/dashboard-parameters)*

Continue to [Lab 04: Build the transit ops dashboard](lab-04-build-transit-ops-dashboard.md).
