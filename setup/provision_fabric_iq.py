#!/usr/bin/env python3
"""
provision_fabric_iq.py -- Fabric IQ workshop environment provisioner.

Creates a "Fabric IQ" Fabric workspace pinned to a non-trial capacity, and
provisions the five items (Lakehouse, Eventhouse, KQL database, Eventstream,
Notebook) listed in manifest.yaml, via the Fabric CLI (`fab`).

WHAT THIS SCRIPT DOES:
    1. Preflight-checks Python and the `fab` CLI.
    2. Confirms you're signed in to Fabric (or runs `fab auth login`).
    3. Lists your eligible capacities and has you pick one -- hard-blocking
       trial capacities unless explicitly overridden, since Fabric IQ's
       Ontology/Graph preview features are not supported there.
    4. Creates (or reuses) a "Fabric IQ" workspace pinned to that capacity.
    5. Resolves where the `artifacts/` folder lives (local checkout, or a
       fresh `git clone` if this script was handed out standalone).
    6. Provisions the Lakehouse, Eventhouse, KQL database, Eventstream, and
       Notebook items, in that dependency order, from manifest.yaml. The
       Lakehouse (with sample CSVs) and the Eventhouse (bare) are created via
       `fab mkdir` -- `fab export`/`fab import` do not support the Lakehouse
       item type at all (see artifacts/Lakehouse/HOW-TO-EXPORT.md), and an
       Eventhouse's own item-definition import was tried and abandoned (see
       artifacts/Eventhouse/HOW-TO-EXPORT.md). The KQL database is
       `fab import`'d from a minimal, hand-built definition and paired with
       deleting the Eventhouse's auto-created default database, since that
       default always takes the Eventhouse's own name and can't be renamed
       via `fab` -- see create_kql_database_item(). The Eventstream is
       `fab import`'d from a pre-captured item-definition folder.
    7. Runs artifacts/Eventhouse/ColdChainKQLDB.kql against the live
       ColdChainKQLDB database -- creates FreezerTelemetryRaw, StoresDim,
       FreezersDim (seeded), and the FreezerTelemetryEnriched materialized
       view. Does this by importing a small throwaway notebook that executes
       the script server-side (via `fab job run`) and deleting it again --
       `fab` itself has no command that can run a `.kql` script directly, and
       calling Kusto from this laptop would need its own separate
       interactive sign-in; running it from a notebook instead reuses the
       same `fab auth login` session already established in step 2, no
       extra sign-in needed. Skip with --skip-kql-schema. See
       run_kql_schema().
    8. Verifies the workspace now contains all five expected items.
    9. Prints a summary with a deep link into the workspace and a pointer to
       modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md.

WHAT THIS SCRIPT DELIBERATELY DOES NOT DO:
    - It does NOT create the Ontology, Data Agent, or Operations Agent items.
      Those are (a) still preview / not reliably scriptable via `fab`, and
      (b) the whole teaching point of Modules 03-04 -- attendees build them
      live. See BUILD_PLAN.md for the reasoning.
    - It does NOT run the 00_LoadReferenceData notebook for you. Importing a
      notebook item does not execute it; running it (and watching the three
      Delta tables land) is an explicit, visible step in the lab guides
      instead of something that happens invisibly before attendees ever see
      the item. (It DOES run the KQL schema script -- see step 7 above; the
      asymmetry is that a notebook run is a deliberate, visible teaching
      moment, while the KQL schema is just prerequisite plumbing nobody
      needs to watch happen.)
    - It does NOT configure the Eventstream's custom-endpoint connection
      string into the telemetry generator. That connection string is only
      obtainable from the Fabric portal *after* the Eventstream item exists
      in *your* workspace, so it can't be scripted -- lab-02 walks you
      through the one manual copy/paste step.

USAGE:
    python provision_fabric_iq.py                          # interactive
    python provision_fabric_iq.py --dry-run                # preview only, no changes
    python provision_fabric_iq.py --non-interactive --capacity "My Capacity" --workspace-name "Fabric IQ"
    python provision_fabric_iq.py --force                  # reuse/overwrite existing workspace+items
    python provision_fabric_iq.py --skip-kql-schema        # skip the KQL schema step entirely

See setup/README.md for the full flag reference and troubleshooting guide.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # handled explicitly in load_manifest(), with an install hint


# =============================================================================
# Constants
# =============================================================================

MIN_PYTHON = (3, 10)
DEFAULT_WORKSPACE_NAME = "Fabric IQ"

# This script was built against and only ever tested live against fab
# 1.7.0. `--output_format json` exists from fab 1.1.0 (2025-09-10) onward,
# but this script depends on more than its mere existence -- the exact
# response envelope shape (`{"result": {"data": [...]}}`), per-item field
# names, and error-code strings it parses (list_capacities(),
# run_kql_schema(), etc.) were all confirmed live only against 1.7.0.
# Reported by a real attendee tester: with an older CLI resolved by
# `pip install -r requirements.txt` (this pin used to be the much looser
# `ms-fabric-cli>=1.0.0`), `ls .capacities -l --output_format json` failed
# outright with "json output mode not supported" -- a confusing failure at
# Step 3, far from its actual cause. check_fab_installed() below checks this
# explicitly so a too-old CLI fails fast and clearly at Step 1 instead.
MIN_FAB_VERSION = (1, 7, 0)

# Derived from this repo's actual `git remote -v` at authoring time. Used
# only as a fallback when this script is run standalone (not from within a
# checkout that already has artifacts/ next to it).
DEFAULT_REPO_URL = "https://github.com/SQLClause/FabConBCNRTI-workshop.git"
REPO_SUBDIR_TO_FABRICIQ = "FabricIQ"  # FabricIQ/ lives at this path inside the repo

PREREQUISITES_PATH = "prerequisites/PREREQUISITES.md"
LAB00_PATH = "modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md"

# The KQL database's schema is a single, fixed, tightly-coupled pairing (one
# database, one script) -- not manifest-driven like the five workspace items,
# since there's only ever one of these in this workshop. See run_kql_schema().
KQL_DATABASE_NAME = "ColdChainKQLDB"
KQL_SCHEMA_SCRIPT_PATH = "artifacts/Eventhouse/ColdChainKQLDB.kql"
# Throwaway notebook name run_kql_schema() imports, runs, then deletes --
# leading underscore keeps it sorted away from the five real workshop items
# in the portal's item list, in the unlikely event a run is interrupted
# before cleanup.
KQL_RUNNER_NOTEBOOK_NAME = "_ApplyKqlSchema"

# Executed server-side, inside a throwaway Fabric notebook -- NOT run
# locally. `notebookutils.credentials.getToken("kusto")` gives the notebook
# a trusted-execution Kusto-audience token for free, no interactive sign-in
# (confirmed live: this is what makes running from a notebook avoid the
# second device-code login a local azure-kusto-data call would need).
# Calls Kusto's `.execute database script` control command via a direct
# `requests` POST to the cluster's own `/v1/rest/mgmt` endpoint rather than
# using the azure-kusto-data SDK -- confirmed live that the SDK is NOT
# usable inside a Fabric notebook as of this writing: Fabric's runtime has
# already imported an older `azure-core` by the time user code runs, and
# `pip install -U` inside the same kernel session doesn't help (Python's
# module cache keeps serving the already-imported old version, not the
# upgraded one on disk). __CLUSTER_URI__/__DATABASE_NAME__/__KQL_SCRIPT_JSON__
# are substituted by run_kql_schema() before import.
KQL_RUNNER_NOTEBOOK_TEMPLATE = """# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

import requests

CLUSTER_URI = "__CLUSTER_URI__"
DATABASE = "__DATABASE_NAME__"
SCRIPT = __KQL_SCRIPT_JSON__

token = notebookutils.credentials.getToken("kusto")
command = ".execute database script with (ContinueOnErrors=false) <|\\n" + SCRIPT

resp = requests.post(
    f"{CLUSTER_URI}/v1/rest/mgmt",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={"db": DATABASE, "csl": command},
    timeout=120,
)
if resp.status_code != 200:
    raise RuntimeError(f"KQL script execution failed: {resp.status_code} {resp.text[:1000]}")
print("KQL schema applied successfully.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
"""

# Keywords used to flag a capacity as a trial SKU. `fab -c "ls .capacities -l"`
# output format has not been verified against a live tenant as part of this
# authoring pass (no tenant was available) -- see setup/README.md's
# "Judgment calls" note. Validate this list against real output during the
# presenter's pre-event dry run and extend it if trial capacities show up
# under a name/SKU token not covered here.
TRIAL_SKU_KEYWORDS = ("trial", "ft1", "free")

FABRICIQ_ROOT = Path(__file__).resolve().parent.parent


class ProvisioningError(Exception):
    """Raised for any fatal, actionable failure. `hint` is printed alongside
    the message and should point the presenter/attendee at a concrete next
    step (usually a PREREQUISITES.md checklist item)."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.hint = hint


@dataclass
class ManifestItem:
    name: str
    type: str
    # "import" (fab import -i <path>), "create" (fab mkdir + optional fab cp),
    # "notebook_source" (fab import -i <source_py, placeholder-substituted>),
    # or "kql_database_source" (fab import -i <path, placeholder-substituted>,
    # then delete the Eventhouse's auto-created default database)
    mode: str = "import"
    path: Optional[str] = None  # mode: import and kql_database_source
    sample_data_dir: Optional[str] = None  # mode: create only, optional
    sample_data_dest: Optional[str] = None  # mode: create only, if sample_data_dir set
    source_py: Optional[str] = None  # mode: notebook_source only
    default_lakehouse: Optional[str] = None  # mode: notebook_source only
    parent_eventhouse: Optional[str] = None  # mode: kql_database_source only
    parent_kql_database: Optional[str] = None  # mode: eventstream_source only


# =============================================================================
# Low-level helpers
# =============================================================================


def run(cmd: list[str], *, dry_run: bool = False, allow_dry_run_execute: bool = False) -> subprocess.CompletedProcess:
    """Run a subprocess command, printing it first for transparency.

    Read-only commands (checks, listings) should pass allow_dry_run_execute=True
    so --dry-run still actually runs them (there's nothing to preview -- we
    just want the real state). Mutating commands (create/import) should NOT
    set this flag, so --dry-run prints what *would* run instead of running it.
    """
    printable = " ".join(cmd)
    if dry_run and not allow_dry_run_execute:
        print(f"  [dry-run] would run: {printable}")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    print(f"  $ {printable}")
    try:
        # encoding="utf-8" (rather than the default text=True, which decodes
        # using the OS's locale-preferred encoding) is required on Windows:
        # confirmed by a tester that `fab`'s UTF-8 output otherwise raises
        # UnicodeDecodeError under Windows' legacy console code page (e.g.
        # cp1252), before this command's own returncode is even checked.
        # errors="replace" keeps a single unexpected byte from crashing the
        # whole run.
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise ProvisioningError(
            f"Command not found: {cmd[0]}",
            hint=f"Is '{cmd[0]}' installed and on your PATH? See {PREREQUISITES_PATH}, section 4.",
        ) from exc
    return result


def fab(args: list[str], *, dry_run: bool = False, allow_dry_run_execute: bool = False) -> subprocess.CompletedProcess:
    return run(["fab", *args], dry_run=dry_run, allow_dry_run_execute=allow_dry_run_execute)


def fab_c(command: str, *, dry_run: bool = False, allow_dry_run_execute: bool = False) -> subprocess.CompletedProcess:
    """Run a single fab command via `fab -c "<command>"`, the non-interactive
    single-shot invocation form used throughout this script (matches the
    pattern documented in BUILD_PLAN.md, e.g. `fab -c "ls .capacities -l"`)."""
    return fab(["-c", command], dry_run=dry_run, allow_dry_run_execute=allow_dry_run_execute)


def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in ("y", "yes")


# =============================================================================
# Step 1: Preflight
# =============================================================================


def check_python_version() -> None:
    if sys.version_info[:2] < MIN_PYTHON:
        raise ProvisioningError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required "
            f"(found {sys.version_info.major}.{sys.version_info.minor}).",
            hint=f"Install a newer Python 3 and re-run. See {PREREQUISITES_PATH}, section 4.",
        )
    print(f"Python {sys.version_info.major}.{sys.version_info.minor} OK")


def check_fab_installed(dry_run: bool) -> str:
    result = fab(["--version"], dry_run=dry_run, allow_dry_run_execute=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise ProvisioningError(
            "Fabric CLI ('fab') was not found or did not respond to --version.",
            hint=(
                f"Install it with:  pip install ms-fabric-cli>={'.'.join(map(str, MIN_FAB_VERSION))}\n"
                f"    Then confirm with `fab --version`. See {PREREQUISITES_PATH}, section 4."
            ),
        )
    version = result.stdout.strip()

    # `fab --version` prints e.g. "fab version 1.7.0\nhttps://...". A
    # too-old CLI (this script's requirements.txt pin used to be the much
    # looser ms-fabric-cli>=1.0.0) doesn't fail here -- it fails later,
    # confusingly, when --output_format json behaves differently than the
    # version this script was built against. Check explicitly, always (not
    # gated on dry_run -- this is a real, current fact about the installed
    # tool, same as check_python_version() above), so that failure is fast
    # and clear instead.
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    found = tuple(int(g) for g in match.groups()) if match else None
    if found is None or found < MIN_FAB_VERSION:
        raise ProvisioningError(
            f"Fabric CLI {found and '.'.join(map(str, found)) or '(unknown)'} is too old "
            f"(need {'.'.join(map(str, MIN_FAB_VERSION))}+).",
            hint=(
                f"Upgrade with:  pip install -U ms-fabric-cli>={'.'.join(map(str, MIN_FAB_VERSION))}\n"
                f"    Then confirm with `fab --version`. See {PREREQUISITES_PATH}, section 4."
            ),
        )

    print(f"Fabric CLI OK: {version}")
    return version


# =============================================================================
# Step 2: Auth
# =============================================================================


def is_authenticated(dry_run: bool) -> bool:
    # `fab auth status` (confirmed live against fab 0.1.10) exits 0 and
    # prints "Logged in to ..." when authenticated, non-zero otherwise.
    result = fab(["auth", "status"], dry_run=dry_run, allow_dry_run_execute=True)
    return result.returncode == 0


def ensure_authenticated(dry_run: bool, non_interactive: bool) -> None:
    if is_authenticated(dry_run):
        print("Already signed in to Fabric.")
        return

    if non_interactive:
        raise ProvisioningError(
            "Not signed in to Fabric, and --non-interactive was given so this script "
            "cannot open an interactive login prompt.",
            hint=(
                "Run `fab auth login` yourself first (or drop --non-interactive), then re-run this script.\n"
                f"    If the browser/device-code flow doesn't complete, see {PREREQUISITES_PATH}, section 4 (VPN/proxy caveats)."
            ),
        )

    print("Not signed in to Fabric. Launching `fab auth login`...")
    if dry_run:
        print("  [dry-run] would run: fab auth login")
        return

    # Deliberately NOT captured -- this is an interactive flow (browser or
    # device code) and needs to talk directly to the user's terminal/browser.
    result = subprocess.run(["fab", "auth", "login"])
    if result.returncode != 0:
        raise ProvisioningError(
            "`fab auth login` did not complete successfully.",
            hint=(
                "If you're on a corporate VPN/proxy, the browser or device-code flow may be blocked. "
                f"See {PREREQUISITES_PATH}, section 4."
            ),
        )
    if not is_authenticated(dry_run=False):
        raise ProvisioningError(
            "Still not signed in after `fab auth login` reported success.",
            hint=f"Try `fab auth login` manually and inspect the output. See {PREREQUISITES_PATH}, sections 3-4.",
        )
    print("Signed in successfully.")


# =============================================================================
# Step 3: Capacity picker
# =============================================================================


@dataclass
class Capacity:
    name: str
    sku: str
    raw_line: str

    @property
    def is_trial(self) -> bool:
        lowered = f"{self.sku} {self.raw_line}".lower()
        return any(keyword in lowered for keyword in TRIAL_SKU_KEYWORDS)


def list_capacities(dry_run: bool) -> list[Capacity]:
    # Uses --output_format json rather than parsing the human-readable table:
    # confirmed live that fab's text-table renderer word-wraps long cell
    # values (names, GUIDs) to fit the terminal width, which silently
    # splits a single capacity's row across multiple physical lines on a
    # normal-width terminal. A previous version of this function parsed
    # that text table line-by-line (splitting on 2+-space runs) and treated
    # each wrapped line as its own capacity -- on a real attendee laptop
    # this produced garbled, wrong capacity names and made workspace
    # creation fail with a cryptic "Capacity ... could not be found".
    # `--output_format json` is not affected by terminal width at all (see
    # fabric_cli's fab_ui.print_output_format docstring: "truncate_columns
    # ... Only applied for text output; JSON output is not modified"), so
    # this reads the exact same fields Fabric CLI's own capacity-ls command
    # returns (fabric_cli/commands/fs/ls/fab_fs_ls_capacity.py).
    result = fab_c(
        "ls .capacities -l --output_format json", dry_run=dry_run, allow_dry_run_execute=True
    )
    if result.returncode != 0:
        raise ProvisioningError(
            "Could not list capacities (`fab -c \"ls .capacities -l\"` failed).",
            hint=(
                "This usually means your account has no visible/eligible Fabric capacity. "
                f"See {PREREQUISITES_PATH}, section 2."
            ),
        )

    try:
        rows = json.loads(result.stdout)["result"]["data"] or []
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ProvisioningError(
            "Could not parse the capacity listing returned by the Fabric CLI.",
            hint=(
                "This may mean an incompatible `fab` CLI version changed its JSON output shape. "
                "Confirm with `fab --version` and try `pip install -U ms-fabric-cli`."
            ),
        ) from exc

    capacities: list[Capacity] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        raw_line = (
            f"{row['name']}  sku={row.get('sku', '?')}  "
            f"region={row.get('region', '?')}  state={row.get('state', '?')}  "
            f"resourceGroup={row.get('resourceGroup', '?')}  admins={row.get('admins', [])}"
        )
        capacities.append(Capacity(name=row["name"], sku=row.get("sku") or "", raw_line=raw_line))

    if not capacities:
        raise ProvisioningError(
            "No capacities were returned by the Fabric CLI.",
            hint=(
                "You need Contributor+ on at least one non-trial Fabric capacity (F2+/P1+). "
                f"See {PREREQUISITES_PATH}, section 2."
            ),
        )
    return capacities


def pick_capacity(
    capacities: list[Capacity],
    *,
    non_interactive: bool,
    requested_name: Optional[str],
    force: bool,
) -> Capacity:
    if requested_name:
        matches = [c for c in capacities if c.name == requested_name]
        if not matches:
            available = ", ".join(c.name for c in capacities)
            raise ProvisioningError(
                f"Requested capacity '{requested_name}' was not found.",
                hint=f"Available capacities: {available}",
            )
        chosen = matches[0]
    elif non_interactive:
        raise ProvisioningError(
            "--non-interactive requires --capacity <name>.",
            hint="Re-run with --capacity \"<exact capacity name>\".",
        )
    else:
        print("\nAvailable capacities:")
        for i, cap in enumerate(capacities, start=1):
            flag = "  [TRIAL - not supported for Fabric IQ preview features]" if cap.is_trial else ""
            print(f"  {i}. {cap.raw_line}{flag}")
        while True:
            selection = input(f"\nSelect a capacity [1-{len(capacities)}]: ").strip()
            if selection.isdigit() and 1 <= int(selection) <= len(capacities):
                chosen = capacities[int(selection) - 1]
                break
            print("Invalid selection, try again.")

    if chosen.is_trial:
        print(
            "\n*** WARNING: the selected capacity looks like a TRIAL capacity. ***\n"
            "Fabric IQ's Ontology/Graph preview features are not supported on trial\n"
            "(FT1) capacities. Later modules in this workshop WILL fail on this capacity.\n"
            f"See {PREREQUISITES_PATH}, section 1."
        )
        if force:
            print("--force given: proceeding with the trial capacity anyway.")
        elif non_interactive:
            raise ProvisioningError(
                f"Capacity '{chosen.name}' looks like a trial capacity, refusing to proceed non-interactively.",
                hint="Pick a non-trial F2+/P1+ capacity, or pass --force to override this check.",
            )
        elif not confirm("Proceed with this trial capacity anyway? (Ontology/Agent labs will not work)"):
            raise ProvisioningError(
                "Aborted: no non-trial capacity was selected.",
                hint=f"See {PREREQUISITES_PATH}, section 1 for how to get a non-trial capacity.",
            )

    print(f"Using capacity: {chosen.name}")
    return chosen


# =============================================================================
# Step 4: Workspace creation
# =============================================================================


def workspace_exists(name: str, dry_run: bool) -> bool:
    result = fab_c("ls .", dry_run=dry_run, allow_dry_run_execute=True)
    if result.returncode != 0:
        return False
    target = f"{name}.Workspace"
    return any(target in line for line in result.stdout.splitlines())


def create_or_reuse_workspace(
    name: str,
    capacity: Capacity,
    *,
    dry_run: bool,
    non_interactive: bool,
    force: bool,
) -> str:
    workspace_path = f"{name}.Workspace"

    if workspace_exists(name, dry_run):
        print(f"Workspace '{name}' already exists.")
        if force:
            print("--force given: reusing the existing workspace.")
        elif non_interactive:
            print("--non-interactive given: reusing the existing workspace (no destructive action taken).")
        elif not confirm(f"Reuse the existing '{name}' workspace? (No means abort)"):
            raise ProvisioningError(
                f"Aborted: workspace '{name}' already exists and reuse was declined.",
                hint="Pass --workspace-name <other name> to create a differently-named workspace instead.",
            )
        return workspace_path

    result = fab(
        ["create", workspace_path, "-P", f"capacityname={capacity.name}"],
        dry_run=dry_run,
    )
    if not dry_run and result.returncode != 0:
        raise ProvisioningError(
            f"Failed to create workspace '{name}': {result.stderr.strip() or result.stdout.strip()}",
            hint=(
                "Common causes: insufficient workspace-creation rights, or a name collision that "
                f"wasn't caught by the pre-check above. See {PREREQUISITES_PATH}, section 2."
            ),
        )
    print(f"Workspace '{name}' created, pinned to capacity '{capacity.name}'.")
    return workspace_path


# =============================================================================
# Step 5: Resolve artifact source
# =============================================================================


def resolve_artifact_root(dry_run: bool) -> Path:
    local_manifest = FABRICIQ_ROOT / "setup" / "manifest.yaml"
    local_artifacts = FABRICIQ_ROOT / "artifacts"
    if local_manifest.exists() and local_artifacts.exists():
        print(f"Using local artifact checkout at {FABRICIQ_ROOT}")
        return FABRICIQ_ROOT

    print(
        "Local artifacts/ and setup/manifest.yaml were not both found next to this script -- "
        "this looks like a standalone copy of provision_fabric_iq.py."
    )
    print(f"Cloning {DEFAULT_REPO_URL} to fetch the workshop artifacts...")

    if dry_run:
        print(f"  [dry-run] would run: git clone --depth 1 {DEFAULT_REPO_URL} <temp dir>")
        # Return the local root anyway so downstream dry-run steps have a
        # sensible (if nonexistent) path to print without crashing.
        return FABRICIQ_ROOT

    tmp_dir = Path(tempfile.mkdtemp(prefix="fabric-iq-clone-"))
    result = subprocess.run(
        ["git", "clone", "--depth", "1", DEFAULT_REPO_URL, str(tmp_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise ProvisioningError(
            f"git clone of {DEFAULT_REPO_URL} failed: {result.stderr.strip()}",
            hint=(
                "Check your network/VPN access to GitHub, or run this script from inside an "
                f"existing checkout of the repo instead. See {PREREQUISITES_PATH}, section 4."
            ),
        )
    cloned_root = tmp_dir / REPO_SUBDIR_TO_FABRICIQ
    if not (cloned_root / "artifacts").exists():
        raise ProvisioningError(
            f"Cloned repo did not contain the expected {REPO_SUBDIR_TO_FABRICIQ}/artifacts folder.",
            hint="The repo layout may have changed -- check DEFAULT_REPO_URL and REPO_SUBDIR_TO_FABRICIQ at the top of this script.",
        )
    print(f"Cloned to {cloned_root}")
    return cloned_root


# =============================================================================
# Step 6: Import items
# =============================================================================


def load_manifest(artifact_root: Path) -> list[ManifestItem]:
    if yaml is None:
        raise ProvisioningError(
            "The 'pyyaml' package is required to read manifest.yaml.",
            hint="Install dependencies with:  pip install -r setup/requirements.txt",
        )
    manifest_path = artifact_root / "setup" / "manifest.yaml"
    if not manifest_path.exists():
        raise ProvisioningError(f"manifest.yaml not found at {manifest_path}")

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    items = data.get("items", []) if data else []
    if not items:
        raise ProvisioningError(f"manifest.yaml at {manifest_path} has no items.")
    return [
        ManifestItem(
            name=i["name"],
            type=i["type"],
            mode=i.get("mode", "import"),
            path=i.get("path"),
            sample_data_dir=i.get("sample_data_dir"),
            sample_data_dest=i.get("sample_data_dest"),
            source_py=i.get("source_py"),
            default_lakehouse=i.get("default_lakehouse"),
            parent_eventhouse=i.get("parent_eventhouse"),
            parent_kql_database=i.get("parent_kql_database"),
        )
        for i in items
    ]


def create_via_mkdir_item(
    workspace_path: str,
    item: ManifestItem,
    artifact_root: Path,
    *,
    dry_run: bool,
    force: bool,
) -> tuple[bool, str]:
    """Create a `mode: create` item via `fab mkdir`, then (if
    `sample_data_dir` is set) seed it with local files via `fab cp` -- one
    call per file, since local-to-OneLake `cp` doesn't support directories.
    With no `sample_data_dir`, this is just a bare `mkdir` (e.g. Eventhouse).

    Used for:
    - Lakehouse (with sample data): `fab export`/`fab import` do not support
      the Lakehouse item type at all -- see
      artifacts/Lakehouse/HOW-TO-EXPORT.md.
    - Eventhouse (bare, no sample data): confirmed live that `fab mkdir`
      works cleanly for a bare Eventhouse, and is simpler and more reliable
      than `fab import`-ing a hand-built item-definition -- see
      artifacts/Eventhouse/HOW-TO-EXPORT.md and create_kql_database_item()
      below for why an import-based Eventhouse definition was abandoned.
    """
    target = f"{workspace_path}/{item.name}.{item.type}"

    mkdir_result = fab(["mkdir", target], dry_run=dry_run)
    if dry_run:
        status = "dry-run"
    elif mkdir_result.returncode == 0:
        status = "created"
    else:
        # `mkdir` has no force/overwrite flag, and fails if the item already
        # exists. Treat that specific case as a reuse (matching how workspace
        # reuse already works elsewhere in this script) instead of a failure.
        exists_result = fab_c(f'exists "{target}"', allow_dry_run_execute=True)
        if "true" in exists_result.stdout.strip().lower():
            status = "already exists, reused"
        else:
            return False, (mkdir_result.stderr or mkdir_result.stdout).strip()

    if not item.sample_data_dir:
        return True, status

    source_dir = artifact_root / item.sample_data_dir
    if not dry_run and not source_dir.exists():
        return False, f"Sample data source not found: {source_dir}"

    # `fab cp` (local-to-OneLake) refuses to write into a destination folder
    # that doesn't exist yet -- confirmed live: it does NOT create
    # intermediate folders implicitly, unlike a typical blob-store `cp -r`.
    # So the destination folder must be `mkdir`'d first. If it already exists
    # (e.g. this script is being re-run), `mkdir` fails with
    # "PathAlreadyExists" -- harmless, so it isn't treated as fatal here; a
    # genuine problem (permissions, etc.) will surface from the `cp` calls
    # below instead, with a clear per-file error.
    dest_folder = f"{target}/{item.sample_data_dest}"
    fab(["mkdir", dest_folder], dry_run=dry_run)

    csv_paths = sorted(source_dir.glob("*.csv")) if source_dir.exists() else []
    for csv_path in csv_paths:
        dest = f"{target}/{item.sample_data_dest}/{csv_path.name}"
        cp_cmd = ["cp", str(csv_path), dest]
        if force:
            cp_cmd.append("-f")
        cp_result = fab(cp_cmd, dry_run=dry_run)
        if not dry_run and cp_result.returncode != 0:
            error_text = (cp_result.stderr or cp_result.stdout).strip()
            return False, f"Failed to copy {csv_path.name}: {error_text}"

    return True, f"{status}, sample data seeded" if not dry_run else "dry-run"


def create_notebook_item(
    workspace_path: str,
    item: ManifestItem,
    artifact_root: Path,
    *,
    dry_run: bool,
    force: bool,
) -> tuple[bool, str]:
    """Create a `mode: notebook_source` item by `fab import`-ing its raw,
    checked-in notebook git-source `.py` file directly -- no pre-exported
    item-definition folder needed.

    Unlike Eventhouse/Eventstream (whose item-definition JSON shape isn't
    publicly documented), a Notebook's git-source `.py` format IS public and
    plain-text (confirmed live against fab 0.1.10 + documented at
    https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/notebook-definition),
    so the checked-in source *is* the real importable artifact -- see
    artifacts/Notebooks/HOW-TO-EXPORT.md.

    If `item.default_lakehouse` names another manifest item (by its `name`),
    this resolves that Lakehouse's real item ID and this workspace's real ID,
    then substitutes them into the `__LAKEHOUSE_ID__`/`__WORKSPACE_ID__`
    placeholders in the source file before import -- this is what binds the
    notebook's default Lakehouse (confirmed live: this is the same
    `dependencies.lakehouse` metadata block Fabric itself writes when you
    attach a Lakehouse via the portal), removing the manual "Add data items"
    step entirely.

    The `fab import` call here always passes `-f`, independent of this
    script's own `--force` flag -- confirmed live (reproduced directly) that
    a plain `fab import` of this notebook, even for a brand-new item name
    that doesn't already exist, hangs indefinitely in an interactive
    terminal and fails with a generic, unhelpful `"UnexpectedError"` under
    `--output_format json` -- the same class of confirmation-prompt issue
    already worked around with `-f` in create_kql_database_item() and
    create_eventstream_item(), just missed here originally since it's only
    reproducible without `--force` (Lab 00's documented command has no
    flags at all).
    """
    target = f"{workspace_path}/{item.name}.{item.type}"
    source_path = artifact_root / item.source_py
    if not dry_run and not source_path.exists():
        return False, f"Source path not found: {source_path}"

    content = source_path.read_text(encoding="utf-8") if source_path.exists() else ""

    if item.default_lakehouse:
        lakehouse_target = f"{workspace_path}/{item.default_lakehouse}.Lakehouse"
        ws_result = fab(["get", workspace_path, "-q", "id"], dry_run=dry_run, allow_dry_run_execute=True)
        lh_result = fab(["get", lakehouse_target, "-q", "id"], dry_run=dry_run, allow_dry_run_execute=True)
        workspace_id = ws_result.stdout.strip() if ws_result.returncode == 0 else ""
        lakehouse_id = lh_result.stdout.strip() if lh_result.returncode == 0 else ""
        if not dry_run and (not workspace_id or not lakehouse_id):
            return False, (
                f"Could not resolve IDs to bind default Lakehouse '{item.default_lakehouse}' "
                "(it must be provisioned earlier in manifest.yaml's item order)"
            )
        content = content.replace("__LAKEHOUSE_ID__", lakehouse_id or "__LAKEHOUSE_ID__")
        content = content.replace("__WORKSPACE_ID__", workspace_id or "__WORKSPACE_ID__")

    tmp_dir = Path(tempfile.mkdtemp(prefix="fabric-iq-notebook-"))
    try:
        (tmp_dir / "notebook-content.py").write_text(content, encoding="utf-8")
        cmd = ["import", target, "-i", str(tmp_dir), "--format", ".py", "-f"]
        result = fab(cmd, dry_run=dry_run)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if dry_run:
        return True, "dry-run"
    if result.returncode == 0:
        return True, "imported"
    return False, (result.stderr or result.stdout).strip()


def create_kql_database_item(
    workspace_path: str,
    item: ManifestItem,
    artifact_root: Path,
    *,
    dry_run: bool,
    force: bool,
) -> tuple[bool, str]:
    """Create a `mode: kql_database_source` item: the KQL database attached
    to an Eventhouse.

    WHY THIS EXISTS (all confirmed live against a real tenant): creating an
    Eventhouse via `fab mkdir` auto-provisions exactly one default KQL
    database, and that database's name always matches the Eventhouse's own
    name (e.g. Eventhouse "ColdChainEventhouse" gets a database also named
    "ColdChainEventhouse", not "ColdChainKQLDB"). There is no `fab` command
    to rename it afterward -- `fab mv`/`fab cp` explicitly exclude
    eventhouse/kql_database from their supported item types (see the
    installed `fabric_cli` package's own
    `core/fab_config/command_support.yaml`). `fab export`/`fab get` also do
    not work against a live KQL database item -- both fail with a generic,
    unhelpful "UnexpectedError" -- so a real tenant-verified export of this
    item type isn't obtainable either; see
    artifacts/Eventhouse/HOW-TO-EXPORT.md.

    So this creates a SECOND, correctly-named KQL database via `fab import`
    (which DOES support kql_database, unlike mv/cp/mkdir/get) from a minimal,
    hand-built (not fab-exported) definition folder, with `item.path`'s
    `.platform`/`DatabaseProperties.json` files' `__EVENTHOUSE_ID__`
    placeholder substituted with the real Eventhouse item ID (resolved via
    `item.parent_eventhouse`). It then deletes the auto-created default
    database (`fab rm` IS supported for it), so the Eventhouse ends up with
    exactly one, correctly-named database.

    The `fab import` call here always passes `-f`, regardless of this
    script's own `--force` flag: confirmed live that a plain `fab import`
    of this hand-built definition prompts an interactive "Are you sure?"
    confirmation (unrelated to whether the item already exists) that would
    otherwise hang a non-interactive run forever.
    """
    if not item.parent_eventhouse:
        return False, "manifest.yaml error: kql_database_source item has no parent_eventhouse set"

    source_dir = artifact_root / item.path
    if not dry_run and not source_dir.exists():
        return False, f"Source definition not found: {source_dir}"

    eventhouse_target = f"{workspace_path}/{item.parent_eventhouse}.Eventhouse"
    eh_result = fab(["get", eventhouse_target, "-q", "id"], dry_run=dry_run, allow_dry_run_execute=True)
    eventhouse_id = eh_result.stdout.strip() if eh_result.returncode == 0 else ""
    if not dry_run and not eventhouse_id:
        return False, (
            f"Could not resolve item ID of parent Eventhouse '{item.parent_eventhouse}' "
            "(it must be provisioned earlier in manifest.yaml's item order)"
        )

    target = f"{workspace_path}/{item.name}.{item.type}"
    tmp_dir = Path(tempfile.mkdtemp(prefix="fabric-iq-kqldb-"))
    try:
        for src_file in sorted(source_dir.iterdir()) if source_dir.exists() else []:
            if not src_file.is_file():
                continue
            content = src_file.read_text(encoding="utf-8")
            content = content.replace("__EVENTHOUSE_ID__", eventhouse_id or "__EVENTHOUSE_ID__")
            (tmp_dir / src_file.name).write_text(content, encoding="utf-8")

        result = fab(["import", target, "-i", str(tmp_dir), "-f"], dry_run=dry_run)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if dry_run:
        return True, "dry-run"
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()

    # Best-effort cleanup of the auto-created default database (always named
    # the same as the Eventhouse -- see docstring above). Not fatal if this
    # fails (e.g. it was already removed by a prior run): the
    # correctly-named database above is what matters, and a leftover
    # default-named one is harmless clutter, not broken state.
    default_db_target = f"{workspace_path}/{item.parent_eventhouse}.KQLDatabase"
    fab_c(f'rm "{default_db_target}" -f')

    return True, "imported, default database removed"


def create_eventstream_item(
    workspace_path: str,
    item: ManifestItem,
    artifact_root: Path,
    *,
    dry_run: bool,
    force: bool,
) -> tuple[bool, str]:
    """Create a `mode: eventstream_source` item (the Eventstream) by
    `fab import`-ing the checked-in definition folder, with
    `__WORKSPACE_ID__`/`__KQLDATABASE_ID__` placeholders substituted for the
    real current workspace ID and `item.parent_kql_database`'s real item ID.

    WHY THIS EXISTS: the checked-in `eventstream.json`'s Eventhouse
    destination originally hardcoded a `workspaceId`/`itemId` pointing at the
    presenter's own dev-tenant Eventhouse (wherever it was hand-built).
    Importing it as-is against any other workspace fails live with:
        EventStreamBadWebRequest: "Cross-workspace destination(s) found:
        Eventhouse in the Eventstream. Please ensure all Eventstream
        destinations belong to the current workspace"
    Confirmed live that `itemId` specifically must be the KQL DATABASE's own
    item ID, not the Eventhouse container's -- passing the Eventhouse's ID
    instead fails with a different, more specific error:
        EventStreamBadWebRequest: "Unable to extract cluster URL from the
        Eventhouse KQL database item ID <eventhouse-id>. Please make sure
        the Eventhouse destination is properly configured."
    This substitutes real IDs in at import time, the same pattern
    create_notebook_item() already uses for
    `__LAKEHOUSE_ID__`/`__WORKSPACE_ID__`.

    Also confirmed live that a plain `fab import` of this checked-in
    definition (without `-f`) fails with a generic, unhelpful
    "UnexpectedError" -- the CLI apparently can't render its usual
    interactive confirmation prompt when `--output_format json` is set, and
    falls back to a useless error instead of just proceeding or asking. This
    call always passes `-f`, independent of this script's own `--force`
    flag, to avoid that.
    """
    if not item.parent_kql_database:
        return False, "manifest.yaml error: eventstream_source item has no parent_kql_database set"

    source_dir = artifact_root / item.path
    if not dry_run and not source_dir.exists():
        return False, f"Source definition not found: {source_dir}"

    kqldb_target = f"{workspace_path}/{item.parent_kql_database}.KQLDatabase"
    ws_result = fab(["get", workspace_path, "-q", "id"], dry_run=dry_run, allow_dry_run_execute=True)
    kqldb_result = fab(["get", kqldb_target, "-q", "id"], dry_run=dry_run, allow_dry_run_execute=True)
    workspace_id = ws_result.stdout.strip() if ws_result.returncode == 0 else ""
    kqldb_id = kqldb_result.stdout.strip() if kqldb_result.returncode == 0 else ""
    if not dry_run and (not workspace_id or not kqldb_id):
        return False, (
            f"Could not resolve IDs to bind destination KQL database '{item.parent_kql_database}' "
            "(it must be provisioned earlier in manifest.yaml's item order)"
        )

    target = f"{workspace_path}/{item.name}.{item.type}"
    tmp_dir = Path(tempfile.mkdtemp(prefix="fabric-iq-eventstream-"))
    try:
        for src_file in sorted(source_dir.iterdir()) if source_dir.exists() else []:
            if not src_file.is_file():
                continue
            content = src_file.read_text(encoding="utf-8")
            content = content.replace("__WORKSPACE_ID__", workspace_id or "__WORKSPACE_ID__")
            content = content.replace("__KQLDATABASE_ID__", kqldb_id or "__KQLDATABASE_ID__")
            (tmp_dir / src_file.name).write_text(content, encoding="utf-8")

        result = fab(["import", target, "-i", str(tmp_dir), "-f"], dry_run=dry_run)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if dry_run:
        return True, "dry-run"
    if result.returncode == 0:
        return True, "imported"
    return False, (result.stderr or result.stdout).strip()


def import_items(
    workspace_path: str,
    items: list[ManifestItem],
    artifact_root: Path,
    *,
    dry_run: bool,
    force: bool,
) -> list[tuple[ManifestItem, bool, str]]:
    """Provision each manifest item in manifest order.

    Five modes, per item:
    - `mode: import`: `fab import ... -f` from a pre-captured,
      tenant-verified item-definition folder with no placeholder
      substitution needed. Not currently used by any item in manifest.yaml
      (every item needs either no definition at all, or per-workspace ID
      substitution) -- kept as the generic fallback below for any future
      item type that doesn't need substitution.
    - `mode: create` (Lakehouse, Eventhouse): `fab mkdir` + optional `fab cp`
      -- see create_via_mkdir_item() above.
    - `mode: notebook_source` (Notebook): `fab import` directly from the
      checked-in `.py` source, since a Notebook's git-source format IS
      publicly documented and plain-text -- see create_notebook_item() above.
    - `mode: kql_database_source` (the KQL database inside the Eventhouse):
      `fab import` a minimal, hand-built definition, then delete the
      Eventhouse's auto-created default database -- see
      create_kql_database_item() above.
    - `mode: eventstream_source` (the Eventstream): `fab import` the
      checked-in definition with `__WORKSPACE_ID__`/`__KQLDATABASE_ID__`
      placeholders substituted -- see create_eventstream_item() above.

    Preferred path per BUILD_PLAN.md: try `fab deploy` (manifest-driven,
    wraps fabric-cicd) first for import-mode items, since it could cover
    them in one shot. That substitution is NOT made here -- it needs
    a pre-event dry run to confirm `fab deploy`'s coverage actually matches
    what this manifest expects. Until that's validated, this script uses the
    more verbose but individually verifiable per-item `fab import` loop
    below. If/when `fab deploy` is confirmed to work, that branch can be
    replaced with a single `fab deploy -f manifest.yaml`-style call; the
    other modes are unaffected either way.
    """
    results: list[tuple[ManifestItem, bool, str]] = []
    for item in items:
        if item.mode == "create":
            ok, detail = create_via_mkdir_item(
                workspace_path, item, artifact_root, dry_run=dry_run, force=force
            )
            results.append((item, ok, detail))
            continue

        if item.mode == "notebook_source":
            ok, detail = create_notebook_item(
                workspace_path, item, artifact_root, dry_run=dry_run, force=force
            )
            results.append((item, ok, detail))
            continue

        if item.mode == "kql_database_source":
            ok, detail = create_kql_database_item(
                workspace_path, item, artifact_root, dry_run=dry_run, force=force
            )
            results.append((item, ok, detail))
            continue

        if item.mode == "eventstream_source":
            ok, detail = create_eventstream_item(
                workspace_path, item, artifact_root, dry_run=dry_run, force=force
            )
            results.append((item, ok, detail))
            continue

        source_path = artifact_root / item.path
        if not dry_run and not source_path.exists():
            results.append((item, False, f"Source path not found: {source_path}"))
            continue

        target = f"{workspace_path}/{item.name}.{item.type}"
        # Always -f, independent of this script's own --force flag -- see
        # create_notebook_item()'s docstring for why: a plain `fab import`
        # (even for a brand-new item) can hang or fail with a generic
        # "UnexpectedError", confirmed live for every other `fab import`
        # call site in this file.
        cmd = ["import", target, "-i", str(source_path), "-f"]
        result = fab(cmd, dry_run=dry_run)
        if dry_run:
            results.append((item, True, "dry-run"))
            continue
        if result.returncode == 0:
            results.append((item, True, "imported"))
        else:
            error_text = (result.stderr or result.stdout).strip()
            results.append((item, False, error_text))
    return results


# =============================================================================
# Step 7: Run the KQL schema
# =============================================================================


def run_kql_schema(workspace_path: str, artifact_root: Path, *, dry_run: bool) -> tuple[bool, str]:
    """Run artifacts/Eventhouse/ColdChainKQLDB.kql against the live
    ColdChainKQLDB database, by importing a small throwaway notebook
    (KQL_RUNNER_NOTEBOOK_TEMPLATE) that executes it server-side via Kusto's
    `.execute database script` control command, running it with `fab job
    run`, then deleting that notebook again.

    WHY A NOTEBOOK RATHER THAN CALLING KUSTO DIRECTLY FROM THIS LAPTOP: an
    earlier version of this function used the azure-kusto-data SDK locally,
    which needed its own separate interactive device-code sign-in --
    independent of (and confusing alongside) `fab auth login`'s session.
    Running the same logic FROM a Fabric notebook instead avoids that
    entirely: confirmed live that `notebookutils.credentials.getToken
    ("kusto")` gives the notebook a trusted-execution Kusto-audience token
    for free, no interactive prompt at all -- because the notebook runs
    server-side, inside Fabric, under `fab job run`'s already-established
    `fab auth login` session. This function now only needs `fab import` +
    `fab job run` (both already using that session) -- no local Kusto
    dependency, and no second sign-in.

    Confirmed live end-to-end, via the actual generated notebook: this
    created FreezerTelemetryRaw (with its docstring), StoresDim, FreezersDim
    (seeded), and the FreezerTelemetryEnriched materialized view (empty but
    queryable, as expected before telemetry flows) -- and confirmed
    idempotent-safe on a second run.

    `fab job run` is used WITHOUT `--timeout` -- confirmed live that passing
    it crashes client-side in fab 0.1.10 (`'<' not supported between
    instances of 'int' and 'str'`) even though the job itself runs fine
    server-side; omitting it, `job run` still blocks synchronously and
    reports the real completion status.
    """
    script_path = artifact_root / KQL_SCHEMA_SCRIPT_PATH
    if not dry_run and not script_path.exists():
        return False, f"Script not found: {script_path}"

    kqldb_target = f"{workspace_path}/{KQL_DATABASE_NAME}.KQLDatabase"
    props_result = fab(["get", kqldb_target, "-q", "properties"], dry_run=dry_run, allow_dry_run_execute=True)

    notebook_target = f"{workspace_path}/{KQL_RUNNER_NOTEBOOK_NAME}.Notebook"
    if dry_run:
        print(
            f"  [dry-run] would run: import+run a throwaway notebook to apply "
            f"{KQL_SCHEMA_SCRIPT_PATH} against {KQL_DATABASE_NAME}, then delete it"
        )
        return True, "dry-run"

    try:
        # `fab get <path> -q properties` (no --output_format json) prints the
        # queried value as a bare JSON object directly -- confirmed live --
        # not wrapped in the {"result": {"data": [...]}} envelope that
        # --output_format json adds.
        properties = json.loads(props_result.stdout)
        query_service_uri = properties["queryServiceUri"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return False, f"Could not resolve {KQL_DATABASE_NAME}'s query URI: {exc}"

    script = script_path.read_text(encoding="utf-8")
    content = (
        KQL_RUNNER_NOTEBOOK_TEMPLATE.replace("__CLUSTER_URI__", query_service_uri)
        .replace("__DATABASE_NAME__", KQL_DATABASE_NAME)
        .replace("__KQL_SCRIPT_JSON__", json.dumps(script))
    )

    tmp_dir = Path(tempfile.mkdtemp(prefix="fabric-iq-kqlrunner-"))
    try:
        (tmp_dir / "notebook-content.py").write_text(content, encoding="utf-8")
        import_result = fab(["import", notebook_target, "-i", str(tmp_dir), "--format", ".py", "-f"])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if import_result.returncode != 0:
        return False, (
            f"Could not import KQL runner notebook: "
            f"{(import_result.stderr or import_result.stdout).strip()}"
        )

    run_result = fab(["job", "run", notebook_target])
    # Always clean up the throwaway notebook, whether the run succeeded or
    # not -- best-effort, not fatal if it fails.
    fab_c(f'rm "{notebook_target}" -f')

    if run_result.returncode != 0:
        return False, f"KQL script execution failed: {(run_result.stderr or run_result.stdout).strip()}"

    return True, "schema applied"


# =============================================================================
# Step 8: Verification
# =============================================================================


def verify_items(workspace_path: str, items: list[ManifestItem], dry_run: bool) -> list[tuple[str, bool]]:
    result = fab_c(f'ls "{workspace_path}" -l', dry_run=dry_run, allow_dry_run_execute=True)
    listing = result.stdout if result.returncode == 0 else ""

    checks = []
    for item in items:
        expected = f"{item.name}.{item.type}"
        found = dry_run or (expected in listing)
        checks.append((expected, found))
    return checks


# =============================================================================
# Step 9: Summary + error mapping
# =============================================================================


def print_summary(
    workspace_name: str,
    capacity: Capacity,
    import_results: list[tuple[ManifestItem, bool, str]],
    verify_results: list[tuple[str, bool]],
    kql_result: Optional[tuple[bool, str]],
) -> None:
    print("\n" + "=" * 70)
    print("FABRIC IQ PROVISIONING SUMMARY")
    print("=" * 70)
    print(f"Workspace:  {workspace_name}")
    print(f"Capacity:   {capacity.name}")
    workspace_slug = workspace_name.replace(" ", "%20")
    print(f"Deep link:  https://app.fabric.microsoft.com/groups/me/list?experience=fabric-developer&workspace={workspace_slug}")
    print("  (If that link doesn't resolve, open app.fabric.microsoft.com and select the workspace from the list.)")

    print("\nItems imported:")
    for item, ok, detail in import_results:
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {item.name}.{item.type}  ({detail})")

    if kql_result is not None:
        kql_ok, kql_detail = kql_result
        status = "OK" if kql_ok else "FAILED"
        print(f"\nKQL schema ({KQL_DATABASE_NAME}):")
        print(f"  [{status}] {KQL_SCHEMA_SCRIPT_PATH}  ({kql_detail})")
        if not kql_ok:
            print(
                f"  Re-run this script to retry, or run {KQL_SCHEMA_SCRIPT_PATH} manually "
                f"in a KQL Queryset attached to {KQL_DATABASE_NAME}."
            )

    print("\nPost-import verification (`fab ls <workspace>.Workspace -l`):")
    all_found = True
    for expected, found in verify_results:
        status = "found" if found else "MISSING"
        if not found:
            all_found = False
        print(f"  [{status}] {expected}")

    if not all_found:
        print(
            "\nSome expected items are missing. Re-run this script with --force to retry, or "
            "provision the missing item(s) manually:\n"
            f'    Lakehouse:   fab mkdir "{workspace_name}.Workspace/<Name>.Lakehouse"\n'
            f'                 fab cp artifacts/SampleData/<file>.csv "{workspace_name}.Workspace/<Name>.Lakehouse/Files/SampleData/<file>.csv"\n'
            f'    Everything else: fab import "{workspace_name}.Workspace/<Name>.<Type>" -i artifacts/<Type>/<Name>.<Type> -f'
        )

    print(f"\nNext step: {LAB00_PATH}")
    print("=" * 70)


def explain_error(exc: ProvisioningError) -> None:
    print(f"\nERROR: {exc.message}", file=sys.stderr)
    if exc.hint:
        print(f"HINT:  {exc.hint}", file=sys.stderr)
    print(f"\nSee {PREREQUISITES_PATH} for the full pre-event checklist.", file=sys.stderr)


# =============================================================================
# Main
# =============================================================================


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision the Fabric IQ workshop environment (workspace + plumbing items).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every command that would run, without creating or importing anything.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Never prompt. Requires --capacity and --workspace-name. Intended for presenter testing/CI.",
    )
    parser.add_argument(
        "--capacity",
        default=None,
        help="Exact capacity name to use (skips the interactive picker).",
    )
    parser.add_argument(
        "--workspace-name",
        default=DEFAULT_WORKSPACE_NAME,
        help="Name of the workspace to create/reuse.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reuse an existing workspace without prompting, and override the trial-capacity warning. (Item imports always overwrite -- see setup/README.md.)",
    )
    parser.add_argument(
        "--skip-kql-schema",
        action="store_true",
        help="Don't run ColdChainKQLDB.kql against the KQL database.",
    )
    args = parser.parse_args(argv)

    if args.non_interactive and not args.capacity:
        parser.error("--non-interactive requires --capacity <name>")
    return args


def main(argv: Optional[list[str]] = None) -> int:
    # Windows' legacy console code page (not UTF-8) is still Python's default
    # stdout/stderr encoding as of this writing, unless the PYTHONUTF8=1 env
    # var is set -- confirmed by a tester that without it, this script's own
    # print() calls raise UnicodeEncodeError on output containing characters
    # outside that code page (e.g. from `fab`'s own colored/symbol output).
    # Reconfiguring here removes the need for attendees to set that variable
    # themselves; a no-op on macOS/Linux, which already default to UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args(argv)

    try:
        print("--- Step 1/9: Preflight checks ---")
        check_python_version()
        check_fab_installed(args.dry_run)

        print("\n--- Step 2/9: Authentication ---")
        ensure_authenticated(args.dry_run, args.non_interactive)

        print("\n--- Step 3/9: Capacity selection ---")
        capacities = list_capacities(args.dry_run)
        capacity = pick_capacity(
            capacities,
            non_interactive=args.non_interactive,
            requested_name=args.capacity,
            force=args.force,
        )

        print("\n--- Step 4/9: Workspace creation ---")
        workspace_path = create_or_reuse_workspace(
            args.workspace_name,
            capacity,
            dry_run=args.dry_run,
            non_interactive=args.non_interactive,
            force=args.force,
        )

        print("\n--- Step 5/9: Resolving artifact source ---")
        artifact_root = resolve_artifact_root(args.dry_run)
        items = load_manifest(artifact_root)
        print(f"Loaded {len(items)} item(s) from manifest.yaml: " + ", ".join(f"{i.name}.{i.type}" for i in items))

        print("\n--- Step 6/9: Provisioning items ---")
        import_results = import_items(workspace_path, items, artifact_root, dry_run=args.dry_run, force=args.force)
        for item, ok, detail in import_results:
            if not ok:
                print(f"  WARNING: failed to provision {item.name}.{item.type}: {detail}")
                if "not enabled" in detail.lower() or "preview" in detail.lower() or "tenant setting" in detail.lower():
                    print(f"  HINT: this looks like a tenant preview-setting gap. See {PREREQUISITES_PATH}, section 1.")

        print("\n--- Step 7/9: KQL schema ---")
        kqldb_provisioned = any(
            ok for item, ok, _ in import_results if item.type == "KQLDatabase"
        )
        if args.skip_kql_schema:
            print("  Skipped (--skip-kql-schema).")
            kql_result = None
        elif not kqldb_provisioned:
            print(f"  Skipped: {KQL_DATABASE_NAME} was not provisioned above (see Step 6 warnings).")
            kql_result = None
        else:
            kql_result = run_kql_schema(workspace_path, artifact_root, dry_run=args.dry_run)
            ok, detail = kql_result
            if not ok:
                print(f"  WARNING: failed to run KQL schema: {detail}")

        print("\n--- Step 8/9: Verification ---")
        verify_results = verify_items(workspace_path, items, args.dry_run)

        print("\n--- Step 9/9: Summary ---")
        print_summary(args.workspace_name, capacity, import_results, verify_results, kql_result)

        any_failed = (
            any(not ok for _, ok, _ in import_results)
            or any(not found for _, found in verify_results)
            or (kql_result is not None and not kql_result[0])
        )
        return 1 if (any_failed and not args.dry_run) else 0

    except ProvisioningError as exc:
        explain_error(exc)
        return 1
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
