#!/usr/bin/env bash
# Thin launcher for provision_fabric_iq.py on macOS/Linux.
#
# Usage:
#   ./run-setup.sh                 # interactive
#   ./run-setup.sh --dry-run
#   ./run-setup.sh --non-interactive --capacity "My Capacity" --workspace-name "Fabric IQ"
#
# All arguments are passed straight through to provision_fabric_iq.py --
# see setup/README.md for the full flag reference.

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 was not found on your PATH." >&2
    echo "Install Python 3.10-3.13 (see ../prerequisites/PREREQUISITES.md, section 1) and re-run." >&2
    exit 1
fi

if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "NOTE: no virtual environment detected. If 'fab' isn't found below, run" >&2
    echo "      python3 check_environment.py --install-deps  first." >&2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/provision_fabric_iq.py" "$@"
