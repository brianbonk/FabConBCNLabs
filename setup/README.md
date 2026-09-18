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
python3 provision_fabric_iq.py          # Windows: python provision_fabric_iq.py
```

The script is interactive by default: it will list your eligible Fabric
capacities and ask you to pick one, then create (or reuse) the `Fabric IQ`
workspace and provision the five items.

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
   - `ColdChainEventhouse` (Eventhouse) — created via a bare `fab mkdir`
     (no item-definition folder needed).
   - `ColdChainKQLDB` (KQL database) — `fab import`'d from a minimal,
     hand-built definition (real export isn't obtainable for this item
     type — see `artifacts/Eventhouse/HOW-TO-EXPORT.md`), with the
     Eventhouse's real item ID substituted in, then the Eventhouse's
     auto-created default database (which always takes the Eventhouse's own
     name) is deleted.
   - `FreezerTelemetryEventstream` (Eventstream) — `fab import`'d from a
     pre-captured, tenant-verified item-definition folder (see its
     `HOW-TO-EXPORT.md`).
   - `00_LoadReferenceData` (Notebook) — `fab import`'d directly from its
     checked-in git-source `.py` file, with its default-Lakehouse binding
     filled in at import time (real Lakehouse/workspace IDs substituted into
     the file's placeholders) — no pre-captured export needed, since a
     notebook's git-source format is public and plain-text.
7. Runs `artifacts/Eventhouse/ColdChainKQLDB.kql` against the live
   `ColdChainKQLDB` database, creating `FreezerTelemetryRaw`, the seeded
   `StoresDim`/`FreezersDim` dimension tables, and the
   `FreezerTelemetryEnriched` materialized view. Does this by importing a
   small throwaway notebook that runs the script server-side (`fab` itself
   has no command that can run a `.kql` script directly) and deleting the
   notebook afterward — reuses the same `fab auth login` session from step
   2, no extra sign-in needed. Skip with `--skip-kql-schema`.
8. Verifies all five items landed in the workspace.
9. Prints a summary with a workspace deep link and a pointer to
   `modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md`.

## Flags

| Flag | Description |
|---|---|
| `--dry-run` | Print every command that would run, without creating or importing anything. Read-only checks (version, auth, capacity listing) still actually run so you see real state. |
| `--non-interactive` | Never prompt. **Requires** `--capacity`. Intended for presenter testing/CI, not for attendees. |
| `--capacity <name>` | Exact capacity name to use, skipping the interactive picker. |
| `--workspace-name <name>` | Name of the workspace to create/reuse (default: `Fabric IQ`). |
| `--force` | Reuse an existing workspace without prompting, and override the trial-capacity warning. Use with care. |
| `--skip-kql-schema` | Don't run `ColdChainKQLDB.kql` against the KQL database. Use this if it's already been applied, or you're re-testing an earlier step and don't need it re-run. |

Every step is designed to be safe to re-run: creating an already-existing
workspace is handled by reuse (not a crash), and every `fab import` call
always passes `-f` (re-importing an existing item overwrites it), regardless
of whether `--force` is passed -- confirmed live that a plain `fab import`
without `-f`, even for a brand-new item, can hang indefinitely in an
interactive terminal or fail with a generic `"UnexpectedError"` under
`--output_format json`. `--force` itself now only controls workspace-reuse
prompting and the trial-capacity override.

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
| `Fabric CLI X.Y.Z is too old (need 1.7.0+)` | An older `fab` is on your PATH — e.g. from a system-wide install, a different venv, or a stale `requirements.txt` resolution. | `pip install -U ms-fabric-cli`, confirm with `fab --version`. |
| `ls .capacities -l --output_format json` fails / "json output mode not supported" | Same root cause as above, but caught late — this is what an old `fab` actually looks like if it slips past Step 1 somehow (e.g. a patched or standalone copy of this script without the version check). | Same fix: `pip install -U ms-fabric-cli`. |
| `Command not found: git` | Git isn't installed. | Run `python3 check_environment.py` for an OS-specific install command, or see PREREQUISITES.md's "Before you clone" section. |
| Script hangs or fails at "Authentication" | Not signed in, or `fab auth login`'s browser/device-code flow is blocked by a corporate VPN/proxy. | Run `fab auth login` manually and watch for errors. See PREREQUISITES.md §3. |
| "No capacities were returned by the Fabric CLI" | Your account has no visible/eligible Fabric capacity, or lacks Contributor+ role on one. | Confirm capacity access with your tenant admin. See PREREQUISITES.md §2. |
| "Capacity looks like a trial capacity" warning | You selected (or only have) an FT1/trial capacity. | Use a non-trial F2+/P1+ capacity — trial capacities don't support Ontology/Graph/Data Agent features at all, and later modules will fail. See PREREQUISITES.md §1. Do not use `--force` to bypass this unless you fully understand later modules won't work. |
| An import fails with an error mentioning "preview" or "not enabled" | A tenant-level preview setting (Ontology/Data Agent) hasn't been enabled by your Fabric admin. | This can't be fixed live — it needs your tenant admin to enable the setting 2+ weeks ahead of the event. See PREREQUISITES.md §1. |
| "Workspace already exists" prompt / `--force` needed | A previous run (or another attendee) already created a workspace with this name. | Reuse it (default prompt), pick a different `--workspace-name`, or pass `--force` to reuse without prompting. |
| An item import reports a name collision | An item with that name already exists in the target workspace (e.g. from a partial previous run). | Re-run with `--force` to overwrite, or delete the conflicting item manually first. |
| Post-import verification shows a MISSING item | The import step failed silently or the item type isn't yet covered by `fab import` in your CLI version. | Check the printed error for that item, and try the manual `fab import` command the summary prints for you. |

## For maintainers: judgment calls made while writing this script

- **Windows console encoding**: reported by a real attendee tester —
  without a fix, this script raised `UnicodeDecodeError` reading `fab`'s
  output, and separately `UnicodeEncodeError` printing it back out, on
  Windows. Root cause: Python's default text encoding for both subprocess
  output and `sys.stdout`/`sys.stderr` follows the OS locale, and Windows'
  legacy console code page (not UTF-8) is still that default even in
  current Python unless the `PYTHONUTF8=1` environment variable is set —
  which `fab`'s own UTF-8 output (colors, symbols) doesn't respect. Fixed
  two ways so attendees don't need to set that variable themselves: every
  `subprocess.run(..., text=True)` call now passes
  `encoding="utf-8", errors="replace"` explicitly (see `run()` in
  `provision_fabric_iq.py`, and the equivalent calls in
  `check_environment.py`), and `main()` in both scripts reconfigures
  `sys.stdout`/`sys.stderr` to UTF-8 (`errors="replace"`) on startup — a
  no-op on macOS/Linux, which already default to UTF-8.
- **`ms-fabric-cli` minimum version pinned to 1.7.0, not left open-ended**:
  also reported by a real attendee tester — `requirements.txt`'s pin used
  to be `ms-fabric-cli>=1.0.0`, and pip resolved an older CLI that doesn't
  support `--output_format json` for `ls`, failing confusingly at Step 3
  ("json output mode not supported") rather than clearly at Step 1.
  `--output_format json` support first shipped in ms-fabric-cli 1.1.0 per
  its release notes, but this script has only ever been tested against
  1.7.0 — earlier versions' exact JSON response shape, field names, and
  error codes aren't verified to match what `list_capacities()`,
  `run_kql_schema()`, etc. parse. `check_fab_installed()` now parses
  `fab --version`'s output and checks it against `MIN_FAB_VERSION`
  explicitly (confirmed live, both against the real installed 1.7.0 and a
  simulated older version), instead of only checking that `fab --version`
  merely responds.
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
  `supported_items`. `create_via_mkdir_item()` uses `fab mkdir` + `fab cp`
  instead (one `cp` per file — local-to-OneLake copy doesn't support
  directories), and confirmed live that the destination folder must be
  `mkdir`'d before `cp` will write into it (it does not create intermediate
  folders implicitly).
- **Eventhouse + KQL database provisioning**: originally planned as a
  `fab import` from a pre-captured, dev-tenant-exported definition folder,
  same as the Eventstream — abandoned after confirming live that
  `fab export`/`fab get` both fail with a generic `"UnexpectedError"` against
  a real KQL database item, so no tenant-verified export is obtainable.
  Separately confirmed live that creating an Eventhouse via `fab mkdir`
  auto-provisions a default KQL database always named the same as the
  Eventhouse (not a chosen name), and that `fab mv`/`fab cp` explicitly
  exclude `eventhouse`/`kql_database` from their supported item types (so
  there's no way to rename it after the fact). The working fix, in
  `create_via_mkdir_item()` (bare `mkdir` for the Eventhouse) and
  `create_kql_database_item()` (KQL database): create the Eventhouse bare,
  `fab import` a second, correctly-named KQL database from a minimal,
  hand-built (not fab-exported) definition folder with the Eventhouse's real
  item ID substituted in, then `fab rm` the auto-created default database.
  All three steps confirmed live end-to-end against a real tenant. Note the
  KQL database `fab import` call always passes `-f`, independent of this
  script's own `--force` flag — confirmed live that a plain import of this
  hand-built definition prompts an interactive confirmation that would
  otherwise hang a non-interactive run.
- **Eventstream provisioning**: `artifacts/Eventstream/FreezerTelemetryEventstream.Eventstream/`'s
  `eventstream.json` had the same class of problem as the old Eventhouse
  folder: its Eventhouse destination **hardcoded** a `workspaceId`/`itemId`
  pointing at the presenter's own dev-tenant Eventhouse. Importing it as-is
  against any other workspace fails live with `EventStreamBadWebRequest:
  "Cross-workspace destination(s) found: Eventhouse in the Eventstream..."`.
  Confirmed live that a plain `fab import` of the checked-in definition
  without `-f` fails first with a generic, unhelpful `"UnexpectedError"` —
  the CLI apparently can't render its usual interactive confirmation prompt
  when `--output_format json` is set. Fixed in `create_eventstream_item()`:
  the hardcoded IDs are now `__WORKSPACE_ID__`/`__KQLDATABASE_ID__`
  placeholders, substituted with real IDs at import time (same pattern as
  the Notebook's `__LAKEHOUSE_ID__`/`__WORKSPACE_ID__`), and the import
  always passes `-f`. One non-obvious wrinkle confirmed live: the
  destination's `itemId` must be the **KQL database's** item ID, not the
  Eventhouse container's — passing the Eventhouse's ID instead fails with a
  different, more specific error (`"Unable to extract cluster URL from the
  Eventhouse KQL database item ID ..."`). Validated end-to-end via a real
  `provision_fabric_iq.py --force` run against a live tenant.
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
  pre-event dry run confirms it covers the Eventstream item type. This
  script deliberately uses the more verbose but individually verifiable
  per-item `fab import` loop for that until it's confirmed — see the
  comment above `import_items()` in `provision_fabric_iq.py`. It doesn't
  apply to the Lakehouse, Eventhouse, KQL database, or Notebook either way,
  since none of those go through `fab import` from a pre-captured folder.
- **Notebook execution**: the script does not attempt `fab job run` (or
  similar) to auto-run `00_LoadReferenceData` after import — this was a
  deliberate pedagogical choice (see "What this script explicitly does NOT
  do" above), not a technical limitation (`run_kql_schema()` DOES call `job
  run`, on a different, throwaway notebook — see below — so this is proven
  to work fine; `00_LoadReferenceData` is just deliberately left for the
  attendee to run themselves). Separately: `fab job run`'s own `--timeout`
  flag crashes client-side in fab 0.1.10 (`'<' not supported between
  instances of 'int' and 'str'`) even though the job itself starts fine
  server-side — a `fab` CLI bug; confirmed live that omitting `--timeout`
  avoids it entirely (`job run` still blocks synchronously and reports the
  real status). Worth knowing if you manually run the notebook from a
  terminal rather than the portal.
- **KQL schema IS now automated, via a throwaway notebook, not a local SDK
  call**: `fab` genuinely has no command for this — its `-A/--audience` flag
  only offers 4 fixed token scopes (`fabric`, `storage`, `azure`, `powerbi`),
  none of which speak Kusto's own protocol, and raw `fab api` calls against
  the cluster's REST endpoint hit ARM-gateway routing mismatches (confirmed
  live). An earlier version of `run_kql_schema()` called Kusto directly from
  the laptop via `azure-kusto-data` (Microsoft's official Kusto Python SDK)
  — that worked, but needed its own separate interactive device-code sign-in
  (the SDK's auth is independent of `fab`'s own private, OS-keychain-backed
  token cache — no supported way to bridge the two). Confirmed live that
  running the same logic from inside a Fabric notebook instead avoids that
  entirely: `notebookutils.credentials.getToken("kusto")` gives the notebook
  a trusted-execution Kusto-audience token for free, no interactive prompt,
  since it runs server-side under `fab job run`'s already-established `fab
  auth login` session. Also confirmed live that `azure-kusto-data` is **not
  usable inside a Fabric notebook** — Fabric's runtime has already imported
  an older, incompatible `azure-core` by the time user code runs, and `pip
  install -U` inside the same kernel session doesn't help (Python's module
  cache keeps serving the already-imported old version, not the upgraded one
  on disk) — so the notebook calls Kusto's REST endpoint directly via
  `requests` instead (`KQL_RUNNER_NOTEBOOK_TEMPLATE` in
  `provision_fabric_iq.py`). Creates `FreezerTelemetryRaw` (with its
  docstring), seeded `StoresDim`/`FreezersDim`, and the
  `FreezerTelemetryEnriched` materialized view, then deletes the throwaway
  notebook. Skip with `--skip-kql-schema`. See
  `artifacts/Eventhouse/HOW-TO-EXPORT.md` for the full writeup, including
  the note on how this changed Module 02's Lab 02 Part E (attendees now
  explain/confirm the view rather than creating it, since it already exists
  by the time they get there).
- **`ifnotexists` is not valid Kusto syntax — a real bug that shipped and
  was masked by stale test state**: an earlier idempotency pass changed
  `.create table X (...)` to `.create table X ifnotexists (...)`, intending
  the same "create if missing" semantics `fab mkdir`/etc. use elsewhere in
  this script. Kusto has no such modifier keyword — the correct idempotent
  verb is `.create-merge table X (...)`. This silently broke
  `run_kql_schema()` completely: with `ContinueOnErrors=false`, the syntax
  error on the very first `.create table` statement aborted the whole
  script, so **nothing** got created, ever, on any run with this bug present
  — not just a missed idempotency edge case. It stayed hidden because the
  very first live validation of the notebook-execution approach ran against
  a database that had already been seeded by an even earlier manual test
  (using the *original*, pre-bug script, via a direct `azure-kusto-data` SDK
  call) — every subsequent "confirmed live" run after that point was
  actually failing silently, but kept finding those leftover
  tables/materialized view already present and reporting false-positive
  success. A genuinely fresh workspace (no prior manual seeding) is what
  exposed it — caught by re-running against one and capturing the actual
  `.execute database script` response body (each statement's individual
  `Result`/`Reason`, not just the overall HTTP status), which showed
  `"Result": "Failed", "Reason": "... Syntax error: SYN0002 ..."` on
  `FreezerTelemetryRaw`. Fixed in `ColdChainKQLDB.kql`
  (`.create-merge table` for `FreezerTelemetryRaw`/`StoresDim`/
  `FreezersDim`) and re-verified against a database with zero prior state:
  `.show tables`, `.show materialized-views`, and real row counts
  (`StoresDim`: 6, `FreezersDim`: 15, view `Status: Active`,
  `IsHealthy: true`) all independently confirmed correct. Lesson for future
  changes to this script: verify against a **freshly deleted/recreated**
  database, not one that's accumulated state across a long testing session.
