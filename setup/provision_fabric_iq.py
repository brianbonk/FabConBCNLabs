#!/usr/bin/env python3
"""
provision_fabric_iq.py -- Fabric IQ workshop environment provisioner.

Creates a "Fabric IQ" Fabric workspace pinned to a non-trial capacity, and
imports the four pre-built items (Lakehouse, Eventhouse, Eventstream,
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
    6. Provisions the Lakehouse, Eventhouse, Eventstream, and Notebook items,
       in that dependency order, from manifest.yaml. The Lakehouse is
       created via `fab mkdir` + `fab cp` (the sample CSVs); the other three
       are `fab import`'d from a pre-captured item-definition folder --
       `fab export`/`fab import` do not support the Lakehouse item type at
       all, see artifacts/Lakehouse/HOW-TO-EXPORT.md.
    7. Verifies the workspace now contains all four expected items.
    8. Prints a summary with a deep link into the workspace and a pointer to
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
      the item.
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

See setup/README.md for the full flag reference and troubleshooting guide.
"""

from __future__ import annotations

import argparse
import json
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

# Derived from this repo's actual `git remote -v` at authoring time. Used
# only as a fallback when this script is run standalone (not from within a
# checkout that already has artifacts/ next to it).
DEFAULT_REPO_URL = "https://github.com/SQLClause/FabConBCNRTI-workshop.git"
REPO_SUBDIR_TO_FABRICIQ = "FabricIQ"  # FabricIQ/ lives at this path inside the repo

PREREQUISITES_PATH = "prerequisites/PREREQUISITES.md"
LAB00_PATH = "modules/module-00-welcome-and-setup/lab-00-environment-setup-and-verify.md"

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
    # "import" (fab import -i <path>), "create" (fab mkdir + fab cp), or
    # "notebook_source" (fab import -i <source_py, placeholder-substituted>)
    mode: str = "import"
    path: Optional[str] = None  # mode: import only
    sample_data_dir: Optional[str] = None  # mode: create only
    sample_data_dest: Optional[str] = None  # mode: create only
    source_py: Optional[str] = None  # mode: notebook_source only
    default_lakehouse: Optional[str] = None  # mode: notebook_source only


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
        result = subprocess.run(cmd, capture_output=True, text=True)
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
                "Install it with:  pip install ms-fabric-cli\n"
                f"    Then confirm with `fab --version`. See {PREREQUISITES_PATH}, section 4."
            ),
        )
    version = result.stdout.strip()
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
        )
        for i in items
    ]


def create_lakehouse_item(
    workspace_path: str,
    item: ManifestItem,
    artifact_root: Path,
    *,
    dry_run: bool,
    force: bool,
) -> tuple[bool, str]:
    """Create a `mode: create` item (currently just the Lakehouse) via
    `fab mkdir`, then seed it with local files via `fab cp` -- one call per
    file, since local-to-OneLake `cp` doesn't support directories.

    This exists because `fab export`/`fab import` do not support the
    Lakehouse item type at all (it's a container object, not a
    definition-based item) -- see artifacts/Lakehouse/HOW-TO-EXPORT.md.
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
        cmd = ["import", target, "-i", str(tmp_dir), "--format", ".py"]
        if force:
            cmd.append("-f")
        result = fab(cmd, dry_run=dry_run)
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

    Three modes, per item:
    - `mode: import` (Eventhouse, Eventstream): `fab import ... -f` from a
      pre-captured, tenant-verified item-definition folder -- these item
      types' definition JSON shape isn't publicly documented, so it can only
      come from a real `fab export` against a dev tenant.
    - `mode: create` (Lakehouse): `fab mkdir` + `fab cp`, since
      `fab export`/`fab import` don't support the Lakehouse item type at all
      -- see create_lakehouse_item() above.
    - `mode: notebook_source` (Notebook): `fab import` directly from the
      checked-in `.py` source, since a Notebook's git-source format IS
      publicly documented and plain-text -- see create_notebook_item() above.

    Preferred path per BUILD_PLAN.md: try `fab deploy` (manifest-driven,
    wraps fabric-cicd) first for the import-mode items, since it could cover
    both of them in one shot. That substitution is NOT made here -- it needs
    a pre-event dry run to confirm `fab deploy`'s coverage of
    Eventhouse/Eventstream actually matches what this manifest expects.
    Until that's validated, this script uses the more verbose but
    individually verifiable per-item `fab import` loop below. If/when
    `fab deploy` is confirmed to work, that branch can be replaced with a
    single `fab deploy -f manifest.yaml`-style call; the Lakehouse's
    `mode: create` and the Notebook's `mode: notebook_source` branches are
    unaffected either way.
    """
    results: list[tuple[ManifestItem, bool, str]] = []
    for item in items:
        if item.mode == "create":
            ok, detail = create_lakehouse_item(
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

        source_path = artifact_root / item.path
        if not dry_run and not source_path.exists():
            results.append((item, False, f"Source path not found: {source_path}"))
            continue

        target = f"{workspace_path}/{item.name}.{item.type}"
        cmd = ["import", target, "-i", str(source_path)]
        if force:
            cmd.append("-f")
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
# Step 7: Verification
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
# Step 8: Summary + error mapping
# =============================================================================


def print_summary(
    workspace_name: str,
    capacity: Capacity,
    import_results: list[tuple[ManifestItem, bool, str]],
    verify_results: list[tuple[str, bool]],
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
    print(
        "Reminder -- this script does NOT create the Ontology, Data Agent, or Operations Agent "
        "items, and does NOT run the 00_LoadReferenceData notebook for you. Both are explicit, "
        "hands-on lab steps -- see the lab guides under modules/."
    )
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
        help="Reuse an existing workspace without prompting, override the trial-capacity warning, and force-overwrite items on import.",
    )
    args = parser.parse_args(argv)

    if args.non_interactive and not args.capacity:
        parser.error("--non-interactive requires --capacity <name>")
    return args


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    try:
        print("--- Step 1/7: Preflight checks ---")
        check_python_version()
        check_fab_installed(args.dry_run)

        print("\n--- Step 2/7: Authentication ---")
        ensure_authenticated(args.dry_run, args.non_interactive)

        print("\n--- Step 3/7: Capacity selection ---")
        capacities = list_capacities(args.dry_run)
        capacity = pick_capacity(
            capacities,
            non_interactive=args.non_interactive,
            requested_name=args.capacity,
            force=args.force,
        )

        print("\n--- Step 4/7: Workspace creation ---")
        workspace_path = create_or_reuse_workspace(
            args.workspace_name,
            capacity,
            dry_run=args.dry_run,
            non_interactive=args.non_interactive,
            force=args.force,
        )

        print("\n--- Step 5/7: Resolving artifact source ---")
        artifact_root = resolve_artifact_root(args.dry_run)
        items = load_manifest(artifact_root)
        print(f"Loaded {len(items)} item(s) from manifest.yaml: " + ", ".join(f"{i.name}.{i.type}" for i in items))

        print("\n--- Step 6/7: Provisioning items ---")
        import_results = import_items(workspace_path, items, artifact_root, dry_run=args.dry_run, force=args.force)
        for item, ok, detail in import_results:
            if not ok:
                print(f"  WARNING: failed to provision {item.name}.{item.type}: {detail}")
                if "not enabled" in detail.lower() or "preview" in detail.lower() or "tenant setting" in detail.lower():
                    print(f"  HINT: this looks like a tenant preview-setting gap. See {PREREQUISITES_PATH}, section 1.")

        print("\n--- Step 7/7: Verification ---")
        verify_results = verify_items(workspace_path, items, args.dry_run)

        print_summary(args.workspace_name, capacity, import_results, verify_results)

        any_failed = any(not ok for _, ok, _ in import_results) or any(not found for _, found in verify_results)
        return 1 if (any_failed and not args.dry_run) else 0

    except ProvisioningError as exc:
        explain_error(exc)
        return 1
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
