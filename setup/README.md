# Fabric IQ setup

This folder provisions the plumbing for the Fabric IQ workshop: a `Fabric IQ`
workspace, pinned to a non-trial capacity, containing a Lakehouse, an
Eventhouse/KQL database, an Eventstream, and a reference-data notebook.

**Attendees**: you run this live, with the room, as Part A of
[Lab 00](../modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md) — the steps
below are the same ones that lab walks you through. Running it here ahead of time is optional (see
[`prerequisites/PREREQUISITES.md`](../prerequisites/PREREQUISITES.md)), not required.

## Quick start

**First, check your machine has what this needs** (Git, Python 3.10-3.13,
and a working, isolated pip) and let it fix what it safely can:

```bash
cd setup
python3 check_environment.py          # or: ./check-environment.sh / .\check-environment.ps1
```

If it created a virtual environment, activate it as instructed and re-run
with `--install-deps` — see [`check_environment.py`](check_environment.py)
or the "Missing or broken tools" section below for details. Once it reports
`ENVIRONMENT READY`, pick whichever launcher matches your OS, or call the
Python script directly.

**macOS / Linux:**
```bash
./run-setup.sh
```

**Windows (PowerShell):**
```powershell
.\run-setup.ps1
```

**Direct (any OS):**
```bash
python3 provision_fabric_iq.py
```

The script is interactive by default: it will list your eligible Fabric
capacities and ask you to pick one, then create (or reuse) the `Fabric IQ`
workspace and import the four items.

## What this script does

1. Preflight-checks Python (3.10+) and the Fabric CLI (`fab --version`).
2. Confirms you're signed in to Fabric, or runs `fab auth login` for you.
3. Lists your eligible capacities and has you pick one. **Trial capacities
   are hard-blocked** unless you explicitly override the warning (or pass
   `--force`) — Fabric IQ's Ontology/Graph preview features don't work on
   trial (FT1) capacities.
4. Creates a workspace named `Fabric IQ` (or reuses one if it already exists).
5. Locates the `artifacts/` folder (using the local checkout this script
   lives in, or cloning the repo fresh if run standalone).
6. Provisions, in order:
   - `ColdChainLakehouse` (Lakehouse) — created via `fab mkdir` + `fab cp`
     (the three sample CSVs), since `fab export`/`fab import` don't support
     the Lakehouse item type at all.
   - `ColdChainEventhouse` (Eventhouse) → `FreezerTelemetryEventstream`
     (Eventstream) — `fab import`'d from a pre-captured, tenant-verified
     item-definition folder (see each item's `HOW-TO-EXPORT.md`).
   - `00_LoadReferenceData` (Notebook) — `fab import`'d directly from its
     checked-in git-source `.py` file, with its default-Lakehouse binding
     filled in at import time (real Lakehouse/workspace IDs substituted into
     the file's placeholders) — no pre-captured export needed, since a
     notebook's git-source format is public and plain-text.
7. Verifies all four items landed in the workspace.
8. Prints a summary with a workspace deep link and a pointer to
   `modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md`.

## Flags

| Flag | Description |
|---|---|
| `--dry-run` | Print every command that would run, without creating or importing anything. Read-only checks (version, auth, capacity listing) still actually run so you see real state. |
| `--non-interactive` | Never prompt. **Requires** `--capacity`. Intended for presenter testing/CI, not for attendees. |
| `--capacity <name>` | Exact capacity name to use, skipping the interactive picker. |
| `--workspace-name <name>` | Name of the workspace to create/reuse (default: `Fabric IQ`). |
| `--force` | Reuse an existing workspace without prompting, override the trial-capacity warning, and force-overwrite items on import. Use with care. |

Every step is designed to be safe to re-run: creating an already-existing
workspace is handled by reuse (not a crash), and re-importing an item that
already exists is handled via `fab import ... -f` when `--force` is passed.

## Missing or broken tools

Run `python3 check_environment.py` any time you're not sure your machine is
ready — it checks Git, your Python version (must be 3.10-3.13; ms-fabric-cli
doesn't yet support 3.14+), and whether you're in a virtual environment, and
creates one at the repo root (`.venv`) if you aren't. It can't activate that
venv for you (a script can't change its parent shell's environment) — it
prints the exact `source .venv/bin/activate` / `.venv\Scripts\Activate.ps1`
command to run, after which re-run with `--install-deps` to also install
`requirements.txt`.

This exists because recent Python installs (Homebrew and python.org on
macOS, most current Linux distros) refuse `pip install` outside a virtual
environment and raise `externally-managed-environment` — using a venv for
this workshop's tooling avoids that entirely.

## Troubleshooting

Each of these maps to a numbered section in
[`../prerequisites/PREREQUISITES.md`](../prerequisites/PREREQUISITES.md) —
check there first for the underlying fix.

| Symptom | Likely cause | Fix |
|---|---|---|
| `error: externally-managed-environment` on `pip install` | Your system Python (Homebrew/python.org/most Linux distros) blocks pip installs outside a venv (PEP 668). | Run `python3 check_environment.py`, activate the venv it creates, then re-run `pip install -r requirements.txt`. |
| `Command not found: fab` | Fabric CLI isn't installed. | `pip install ms-fabric-cli` (or `pip install -r requirements.txt`), confirm with `fab --version`. See Lab 00, Part A, steps 1 and 3. |
| `Command not found: git` | Git isn't installed. | Run `python3 check_environment.py` for an OS-specific install command, or see PREREQUISITES.md's "Before you clone" section. |
| Script hangs or fails at "Authentication" | Not signed in, or `fab auth login`'s browser/device-code flow is blocked by a corporate VPN/proxy. | Run `fab auth login` manually and watch for errors. See PREREQUISITES.md §3. |
| "No capacities were returned by the Fabric CLI" | Your account has no visible/eligible Fabric capacity, or lacks Contributor+ role on one. | Confirm capacity access with your tenant admin. See PREREQUISITES.md §2. |
| "Capacity looks like a trial capacity" warning | You selected (or only have) an FT1/trial capacity. | Use a non-trial F2+/P1+ capacity — trial capacities don't support Ontology/Graph/Data Agent features at all, and later modules will fail. See PREREQUISITES.md §1. Do not use `--force` to bypass this unless you fully understand later modules won't work. |
| An import fails with an error mentioning "preview" or "not enabled" | A tenant-level preview setting (Ontology/Data Agent) hasn't been enabled by your Fabric admin. | This can't be fixed live — it needs your tenant admin to enable the setting 2+ weeks ahead of the event. See PREREQUISITES.md §1. |
| "Workspace already exists" prompt / `--force` needed | A previous run (or another attendee) already created a workspace with this name. | Reuse it (default prompt), pick a different `--workspace-name`, or pass `--force` to reuse without prompting. |
| An item import reports a name collision | An item with that name already exists in the target workspace (e.g. from a partial previous run). | Re-run with `--force` to overwrite, or delete the conflicting item manually first. |
| Post-import verification shows a MISSING item | The import step failed silently or the item type isn't yet covered by `fab import` in your CLI version. | Check the printed error for that item, and try the manual `fab import` command the summary prints for you. |

## For maintainers: judgment calls made while writing this script

- **Auth check command**: confirmed live (fab 0.1.10) that `fab auth status`
  exits 0 and prints `✓ Logged in to ...` when authenticated, non-zero
  otherwise. The script uses that directly (`is_authenticated()`).
- **Capacity listing parsing**: `list_capacities()` calls
  `fab -c "ls .capacities -l --output_format json"` and parses the JSON
  `result.data` array, rather than the human-readable text table. This
  replaced an earlier version that split the text table on 2+-space runs —
  confirmed live (against a real attendee run) that `fab`'s text-table
  renderer word-wraps long cell values (capacity names, GUIDs) to fit the
  terminal width, silently splitting one capacity's row across several
  physical lines and corrupting the parsed name entirely (workspace
  creation then failed with `Capacity '...' could not be found`).
  `--output_format json` is not subject to that truncation at all (see
  `fabric_cli/utils/fab_ui.py`'s `print_output_format` docstring: "Only
  applied for text output; JSON output is not modified"), and its `data`
  array's keys match `fabric_cli/commands/fs/ls/fab_fs_ls_capacity.py`'s
  `columns` list exactly (`name`, `id`, `sku`, `region`, `state`,
  `subscriptionId`, `resourceGroup`, `admins`, `tags`) — confirmed by
  reading that module directly in the installed package. Trial-SKU
  detection (`is_trial`) still checks the `sku` field (plus the formatted
  summary string) for keywords (`trial`, `ft1`, `free`).
  `workspace_exists()` and `verify_items()` still parse `fab`'s text output
  and share the same theoretical wrapping risk for very long workspace/item
  names — not yet hit live, so not converted to JSON output here, but worth
  doing the same way if that ever surfaces.
- **Lakehouse provisioning**: `fab export`/`fab import` do not support the
  Lakehouse item type at all — confirmed via
  `fabric_cli/core/fab_config/command_support.yaml` in the installed
  `ms-fabric-cli` package, which lists `lakehouse` in neither command's
  `supported_items`. `create_lakehouse_item()` uses `fab mkdir` + `fab cp`
  instead (one `cp` per file — local-to-OneLake copy doesn't support
  directories), and confirmed live that the destination folder must be
  `mkdir`'d before `cp` will write into it (it does not create intermediate
  folders implicitly).
- **Notebook provisioning**: confirmed live that a Notebook's git-source
  `.py` format (`# Fabric notebook source` / `# METADATA` / `# CELL`
  markers — see
  <https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/notebook-definition>)
  can be `fab import`'d directly with `--format .py`, and that the
  `dependencies.lakehouse` metadata block in that same file is what binds
  the notebook's default Lakehouse (the same block Fabric itself writes when
  you attach a Lakehouse via the portal). `create_notebook_item()`
  substitutes the real workspace/Lakehouse IDs into that file's
  `__LAKEHOUSE_ID__`/`__WORKSPACE_ID__` placeholders at import time. Ran the
  imported notebook end-to-end against a throwaway workspace as part of this
  validation pass — all three Delta tables (`Stores`, `Freezers`,
  `Customers`) landed correctly.
- **`fab import` vs `fab deploy`**: per `BUILD_PLAN.md`, `fab deploy`
  (manifest-driven, wraps `fabric-cicd`) is the preferred long-term path if a
  pre-event dry run confirms it covers the Eventhouse/Eventstream item types.
  This script deliberately uses the more verbose but individually verifiable
  per-item `fab import` loop for those two until that's confirmed — see the
  comment above `import_items()` in `provision_fabric_iq.py`. It doesn't
  apply to the Lakehouse or Notebook either way, since neither goes through
  `fab import` from a pre-captured folder anymore.
- **Notebook execution**: the script does not attempt `fab job run` (or
  similar) to auto-run `00_LoadReferenceData` after import — this was a
  deliberate pedagogical choice (see "What this script explicitly does NOT
  do" above), not a technical limitation. Separately: `fab job run`'s own
  `--timeout` flag crashes client-side in fab 0.1.10 (`'<' not supported
  between instances of 'int' and 'str'`) even though the job itself starts
  fine server-side — a `fab` CLI bug, not something this script's design
  works around, since it never calls `job run` anyway. Worth knowing if you
  manually run the notebook from a terminal rather than the portal.
- **Eventhouse KQL schema on import**: still unresolved (see
  `artifacts/Eventhouse/HOW-TO-EXPORT.md`'s "Note on `fab import` and KQL
  database contents") — no `fab` command or Fabric-audience `fab api` call
  was found that can execute a `.kql` script against a KQL database directly
  (Kusto's own query/management endpoint needs its own token audience, which
  isn't one of `fab api`'s supported audiences: `fabric`, `storage`,
  `azure`, `powerbi`). If the imported Eventhouse doesn't carry the
  Queryset-created tables/view, re-running `ColdChainKQLDB.kql` stays a
  manual step.
