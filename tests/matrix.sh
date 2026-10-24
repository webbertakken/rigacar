#!/bin/bash
# Runs the end-to-end test on every Blender given, under a virtual display.
# Usage: tests/matrix.sh ~/Applications/blender-*/blender
set -uo pipefail
cd "$(dirname "$0")/.."
status=0
for blender in "$@"; do
  log=$(mktemp -t rigacar-e2e.XXXXXX)
  timeout 300 xvfb-run -a "$blender" --factory-startup --python tests/e2e.py > "$log" 2>&1
  rc=$?
  echo "$(grep -m1 '\[e2e\] Blender' "$log" | cut -c7-): $(grep -c '\[e2e\] PASS' "$log") passed, rc=$rc"
  grep '\[e2e\] FAIL' "$log"
  [ "$rc" -eq 0 ] || { status=1; echo "  log: $log"; continue; }
  rm "$log"
done
exit $status
