#!/usr/bin/env python3
"""
check_environment.py -- Fabric IQ workshop preflight environment checker.

Run this BEFORE `provision_fabric_iq.py` (or right after cloning, per
Lab 00 Part A). It checks the tools this workshop's Python tooling needs
-- Git, Python 3.10+, and a working, isolated pip -- and fixes what it
safely can instead of just failing.

WHAT THIS SCRIPT DOES:
    1. Checks Git is installed (needed to clone this repo in the first
       place; checked here mainly so the summary is complete and so
       standalone re-runs catch it).
    2. Checks the Python version running this script is 3.10+.
    3. Checks whether this interpreter is running inside a virtual
       environment. If not, it creates one at the repo root (`.venv`)
       and prints the exact activate command for your OS/shell --
       it does NOT install packages until you activate it and re-run,
       since a script can't change its parent shell's environment.
    4. Once running inside a venv, checks pip works and (with
       --install-deps) installs setup/requirements.txt for you.

WHY THE VENV STEP EXISTS:
    Recent Python installs (Homebrew and python.org on macOS, most current
    Linux distros) refuse `pip install` outside a virtual environment and
    raise "externally-managed-environment" (PEP 668). Using a venv for this
    workshop's tooling sidesteps that entirely and is good practice anyway.

USAGE:
    python3 check_environment.py                  # check only
    python3 check_environment.py --install-deps    # also pip install -r requirements.txt once venv is active
    python3 check_environment.py --dry-run          # print what would happen, change nothing

See setup/README.md and prerequisites/PREREQUISITES.md for the full guide.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Optional

MIN_PYTHON = (3, 10)
# ms-fabric-cli (a hard requirement -- see requirements.txt) does not yet
# publish wheels for Python 3.14; its latest PyPI release (1.7.0) declares
# `Requires-Python >=3.10,<3.14`, so `pip install -r requirements.txt` fails
# outright on 3.14+ even though the standard library itself works fine.
# Bump this once a newer ms-fabric-cli release supports it.
MAX_PYTHON_EXCLUSIVE = (3, 14)
FABRICIQ_ROOT = Path(__file__).resolve().parent.parent
VENV_PATH = FABRICIQ_ROOT / ".venv"
REQUIREMENTS_PATH = Path(__file__).resolve().parent / "requirements.txt"
PREREQUISITES_PATH = "prerequisites/PREREQUISITES.md"


class CheckError(Exception):
    """Raised for a fatal, actionable failure. `hint` is printed alongside
    the message and should point at a concrete next step."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.hint = hint


# =============================================================================
# OS-specific install hints
# =============================================================================


def _os_name() -> str:
    system = platform.system()
    return {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(system, "other")


def git_install_hint() -> str:
    os_name = _os_name()
    if os_name == "macos":
        return (
            "Install Git with:  xcode-select --install\n"
            "    (this installs Apple's Command Line Tools, which include Git)\n"
            "    or, if you use Homebrew:  brew install git"
        )
    if os_name == "windows":
        return (
            "Install Git with:  winget install --id Git.Git -e --source winget\n"
            "    or download the installer from https://git-scm.com/download/win"
        )
    if os_name == "linux":
        return (
            "Install Git with your distro's package manager, e.g.:\n"
            "    Debian/Ubuntu:  sudo apt update && sudo apt install -y git\n"
            "    Fedora/RHEL:    sudo dnf install -y git"
        )
    return "Install Git from https://git-scm.com/downloads"


def python_install_hint() -> str:
    os_name = _os_name()
    range_str = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}-{MAX_PYTHON_EXCLUSIVE[0]}.{MAX_PYTHON_EXCLUSIVE[1] - 1}"
    if os_name == "macos":
        return (
            f"Install Python {range_str} with:  brew install python@3.12\n"
            "    or download an installer from https://www.python.org/downloads/\n"
            f"    (avoid {MAX_PYTHON_EXCLUSIVE[0]}.{MAX_PYTHON_EXCLUSIVE[1]}+ for now -- ms-fabric-cli doesn't support it yet)"
        )
    if os_name == "windows":
        return (
            f"Install Python {range_str} with:  winget install --id Python.Python.3.12 -e\n"
            "    or download an installer from https://www.python.org/downloads/\n"
            "    (tick \"Add python.exe to PATH\" during setup; "
            f"avoid {MAX_PYTHON_EXCLUSIVE[0]}.{MAX_PYTHON_EXCLUSIVE[1]}+ for now -- ms-fabric-cli doesn't support it yet)"
        )
    if os_name == "linux":
        return (
            f"Install Python {range_str} and the venv module with your package manager, e.g.:\n"
            "    Debian/Ubuntu:  sudo apt update && sudo apt install -y python3 python3-venv python3-pip\n"
            "    Fedora/RHEL:    sudo dnf install -y python3 python3-pip"
        )
    return f"Install Python {range_str} from https://www.python.org/downloads/"


def activate_hint() -> str:
    os_name = _os_name()
    rel = "setup" if Path.cwd() == FABRICIQ_ROOT / "setup" else "."
    prefix = "" if rel == "." else "cd ..  # back to the repo root\n    "
    if os_name == "windows":
        return (
            f"{prefix}.\\.venv\\Scripts\\Activate.ps1   (PowerShell)\n"
            "    or:  .venv\\Scripts\\activate.bat        (cmd.exe)"
        )
    return f"{prefix}source .venv/bin/activate"


# =============================================================================
# Checks
# =============================================================================


def check_git() -> str:
    path = shutil.which("git")
    if not path:
        raise CheckError("Git was not found on your PATH.", hint=git_install_hint())
    # encoding="utf-8"/errors="replace": confirmed by a tester that Windows'
    # legacy console code page otherwise raises UnicodeDecodeError decoding
    # subprocess output (see the matching note in provision_fabric_iq.py's
    # run() helper).
    result = subprocess.run(["git", "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    version = result.stdout.strip() or "git (version unknown)"
    print(f"[OK] {version}")
    return version


def check_python_version() -> None:
    current = sys.version_info[:2]
    found = f"{sys.version_info.major}.{sys.version_info.minor}"
    if current < MIN_PYTHON:
        raise CheckError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required (found {found}).",
            hint=python_install_hint(),
        )
    if current >= MAX_PYTHON_EXCLUSIVE:
        raise CheckError(
            f"Python {found} is too new for this workshop's tooling -- ms-fabric-cli does not "
            f"yet support {MAX_PYTHON_EXCLUSIVE[0]}.{MAX_PYTHON_EXCLUSIVE[1]}+ (found {found}).",
            hint=python_install_hint(),
        )
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def in_virtual_env() -> bool:
    return sys.prefix != sys.base_prefix


def check_or_create_venv(dry_run: bool) -> bool:
    """Returns True if the caller is ready to proceed with pip checks right
    now (i.e. already running inside a venv). Returns False if a venv was
    just created (or already existed) but isn't active in this process --
    the caller must activate it and re-run."""
    if in_virtual_env():
        print(f"[OK] Running inside a virtual environment ({sys.prefix})")
        return True

    if VENV_PATH.exists():
        print(f"[ACTION NEEDED] A virtual environment already exists at {VENV_PATH}, but it isn't active.")
    else:
        print(f"No active virtual environment detected. Creating one at {VENV_PATH} ...")
        if dry_run:
            print(f"  [dry-run] would run: python3 -m venv {VENV_PATH}")
        else:
            try:
                venv.create(VENV_PATH, with_pip=True)
            except Exception as exc:  # ensurepip missing, disk full, etc.
                raise CheckError(
                    f"Could not create a virtual environment at {VENV_PATH}: {exc}",
                    hint=python_install_hint(),
                ) from exc
            print(f"[OK] Created virtual environment at {VENV_PATH}")

    print(
        "\n[ACTION NEEDED] Activate the virtual environment, then re-run this script:\n"
        f"    {activate_hint()}\n"
        "    python3 setup/check_environment.py --install-deps"
    )
    return False


def check_pip(dry_run: bool) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise CheckError(
            "pip is not working in this environment.",
            hint=(
                f"Try recreating the venv:  rm -rf {VENV_PATH}  then re-run this script.\n"
                "    " + python_install_hint()
            ),
        )
    print(f"[OK] {result.stdout.strip()}")


def install_requirements(dry_run: bool) -> None:
    if not REQUIREMENTS_PATH.exists():
        raise CheckError(f"requirements.txt not found at {REQUIREMENTS_PATH}")

    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)]
    print(f"\nInstalling dependencies from {REQUIREMENTS_PATH.name} ...")
    if dry_run:
        print(f"  [dry-run] would run: {' '.join(cmd)}")
        return
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise CheckError(
            "pip install failed.",
            hint="Check the pip output above. If you see \"externally-managed-environment\", "
            "confirm the venv is actually active (your shell prompt should show `(.venv)`).",
        )
    print("[OK] Dependencies installed.")


# =============================================================================
# Main
# =============================================================================


def explain_error(exc: CheckError) -> None:
    print(f"\nERROR: {exc.message}", file=sys.stderr)
    if exc.hint:
        print(f"HINT:  {exc.hint}", file=sys.stderr)
    print(f"\nSee {PREREQUISITES_PATH} for the full pre-event checklist.", file=sys.stderr)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check (and where possible, fix) this machine's Fabric IQ workshop prerequisites.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Also run `pip install -r requirements.txt` once a venv is confirmed active.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without creating a venv or installing anything.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    # Windows' legacy console code page (not UTF-8) is still Python's default
    # stdout/stderr encoding as of this writing, unless the PYTHONUTF8=1 env
    # var is set -- confirmed by a tester that without it, print() calls
    # containing non-ASCII characters raise UnicodeEncodeError. Reconfiguring
    # here removes the need for attendees to set that variable themselves; a
    # no-op on macOS/Linux, which already default to UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args(argv)

    try:
        print("--- Step 1/4: Git ---")
        check_git()

        print("\n--- Step 2/4: Python ---")
        check_python_version()

        print("\n--- Step 3/4: Virtual environment ---")
        ready = check_or_create_venv(args.dry_run)
        if not ready:
            print("\n" + "=" * 70)
            print("Git and Python are OK. Activate the venv above and re-run this script to finish.")
            print("=" * 70)
            return 1

        print("\n--- Step 4/4: pip ---")
        check_pip(args.dry_run)

        if args.install_deps:
            install_requirements(args.dry_run)

        print("\n" + "=" * 70)
        print("ENVIRONMENT READY -- proceed to setup/README.md (run-setup.sh / run-setup.ps1).")
        print("=" * 70)
        return 0

    except CheckError as exc:
        explain_error(exc)
        return 1
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
