# Fabric IQ setup

This folder provisions the plumbing for the Fabric IQ workshop: a `Fabric IQ`
workspace, pinned to a non-trial capacity, containing a Lakehouse, an
Eventhouse/KQL database, an Eventstream, and a reference-data notebook.

**Attendees**: you run this live, with the room, as Part A of
[Lab 00](../modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md) — the steps
below are the same ones that lab walks you through. Running it here ahead of time is optional (see
[`prerequisites/PREREQUISITES.md`](../prerequisites/PREREQUISITES.md)), not required.

## Quick start

Pick whichever launcher matches your OS, or call the Python script directly.

**macOS / Linux:**
```bash
cd setup
pip install -r requirements.txt
./run-setup.sh
```

**Windows (PowerShell):**
```powershell
cd setup
pip install -r requirements.txt
.\run-setup.ps1
```

**Direct (any OS):**
```bash
cd setup
pip install -r requirements.txt
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

## What this script explicitly does NOT do

- **It does not create the Ontology, Data Agent, or Operations Agent items.**
  These are still-preview item types without confirmed `fab` support for
  scripted creation, and — more importantly — building them live is the
  entire point of Modules 03 and 04. You build these by hand, in the lab.
- **It does not run the `00_LoadReferenceData` notebook for you.** Importing
  a notebook doesn't execute it. Running it — and watching the `Customers`,
  `Stores`, `Freezers` Delta tables appear — is a deliberate, visible step in
  the early lab guides.
- **It does not configure the Eventstream's connection string** into
  `artifacts/generator/freezer_telemetry_generator.py`. That connection
  string is only obtainable from the Fabric portal after the Eventstream
  item exists in *your* workspace, so it's a one-time manual copy/paste step
  covered in `lab-02`, not something this script can do for you.

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

## Troubleshooting

Each of these maps to a numbered section in
[`../prerequisites/PREREQUISITES.md`](../prerequisites/PREREQUISITES.md) —
check there first for the underlying fix.

| Symptom | Likely cause | Fix |
|---|---|---|
| `Command not found: fab` | Fabric CLI isn't installed. | `pip install ms-fabric-cli` (or `pip install -r requirements.txt`), confirm with `fab --version`. See Lab 00, Part A, steps 1 and 3. |
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
- **Capacity listing parsing**: confirmed live that
  `fab -c "ls .capacities -l"` columns (`name`, `id`, `sku`, `region`,
  `state`, `subscriptionId`, `resourceGroup`, `admins`, `tags`) are padded
  with runs of 2+ spaces, and that capacity names themselves can contain
  single spaces (e.g. `Premium Per User - Reserved.Capacity`) — a plain
  `.split()` truncates those to their first word. `list_capacities()` splits
  on `\s{2,}` instead, and checks the `sku` column (plus the full line as a
  fallback) for trial-SKU keywords (`trial`, `ft1`, `free`).
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
