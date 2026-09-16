# Pre-Event Prerequisites

**Microsoft is providing the Fabric tenant/capacity and a dedicated user account for every attendee at
this event.** This isn't run on your own organization's Fabric tenant, so the tenant-admin actions that
would normally block a workshop like this — enabling the Ontology/Data Agent preview settings, assigning
a non-trial capacity, granting Contributor access — are **Microsoft's responsibility, not the
presenter's or any attendee's.** Neither side needs to arrange any of that, and there is no "forward this
to your tenant admin" step anymore.

What's left in this checklist is small: confirming Microsoft's environment is what this workshop needs,
and how attendees actually get signed in on the day.

## 1. Confirm with Microsoft ahead of time (presenter action, 2+ weeks lead time)

Fabric IQ's Ontology and Graph items are still **(preview)** as of this writing and require explicit
tenant-level enablement. Confirm directly with the Microsoft team supporting this event that the
environment they're providing has:

- [ ] The **"Ontology item (preview)"** tenant setting enabled.
      See [Ontology required tenant settings](https://learn.microsoft.com/fabric/iq/ontology/overview-tenant-settings).
- [ ] The Azure OpenAI / Copilot tenant settings required for **Fabric Data Agent** enabled.
- [ ] A capacity per attendee that is **F2 SKU or higher** (or **P1+** for Premium-based capacities), and
      explicitly **not** a trial (FT1) capacity — Ontology, Graph, and Data Agent features aren't
      supported on trial capacities. This remains the single most common failure mode for this kind of
      session even when Microsoft is providing the environment; Module 00's lab hard-blocks it live as a
      safety net, but by then there's no way to swap in a working capacity — so confirm this explicitly
      with Microsoft rather than assuming it, and re-confirm close to the event date.
- [ ] Contributor (or higher) role and workspace-creation rights already granted on each attendee's
      provided account — this shouldn't need any action from the attendee at all.

## 2. How attendees sign in

Each attendee signs in with the **Microsoft-provided account for this event**, not their own
organization's Fabric login.

## 3. Network caveat (worth testing ahead of time, not required)

- [ ] If the venue is on a restrictive network, test that `fab auth login`'s browser/device-code flow and
      `git clone` both succeed from it before the day. Module 00's lab handles this live as a
      troubleshooting path if it comes up unexpectedly, but knowing about it ahead of time saves room
      time.

## 4. Before you clone: Git and Python

Every attendee needs **Git** (to clone this repo) and **Python 3.10-3.13** (to run the setup scripts) on
their own laptop — this is on each attendee, not something Microsoft's tenant setup covers. Note the
Python range: ms-fabric-cli, which this workshop's tooling depends on, does not yet support Python 3.14+,
so a brand-new default install on some systems can be *too new*. If you're not sure what you have:

**Windows:**
```powershell
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.12 -e
```
(or download installers from [git-scm.com](https://git-scm.com/download/win) and
[python.org](https://www.python.org/downloads/) — tick "Add python.exe to PATH" during Python setup)

**macOS:**
```bash
xcode-select --install   # installs Git via Apple's Command Line Tools
brew install python@3.12 # if you use Homebrew; otherwise use the python.org installer
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip
# Fedora/RHEL
sudo dnf install -y git python3 python3-pip
```

Once you've cloned the repo, run `python3 setup/check_environment.py` from
`FabricIQ/` — it re-checks both of these, plus pip, and sets up an isolated
virtual environment for you so `pip install` doesn't fail with
`externally-managed-environment` (a common error on recent Homebrew/Linux
Python installs). See [`setup/README.md`](../setup/README.md) for details.

## Optional: doing Module 00's setup ahead of time

Nothing above requires it, but any attendee who already has their Microsoft-provided account and wants to
save room time on the day is welcome to run Module 00's Part A themselves beforehand: install Git and
Python 3.10-3.13 (section 4 above), then follow [`setup/README.md`](../setup/README.md) to run
`check_environment.py` and `provision_fabric_iq.py`. If you do, just skip straight to Part B when Module
00 starts. This is a convenience, not something to assume — the agenda is built assuming most people
haven't.

## Support contact

Questions or issues with any of the above: contact Brian ahead of the event — problems caught a week
out are a five-minute fix; problems discovered live in the room are not.
