#!/usr/bin/env bash
# Thin launcher for check_environment.py on macOS/Linux.
#
# Usage:
#   ./check-environment.sh
#   ./check-environment.sh --install-deps
#
# All arguments are passed straight through to check_environment.py --
# see setup/README.md for details.

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 was not found on your PATH." >&2
    echo "Install Python 3.10-3.13 (see ../prerequisites/PREREQUISITES.md, section 1) and re-run." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/check_environment.py" "$@"
