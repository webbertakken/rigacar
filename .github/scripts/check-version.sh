#!/bin/bash
# Fails unless the release tag (v8.2.0) matches bl_info's version ((8, 2)), ignoring trailing zeros.
set -euo pipefail
tag="${1#v}"
version=$(grep -oP '"version":\s*\(\K[0-9, ]+' "$(dirname "$0")/../../__init__.py" | tr -d ' ' | tr ',' '.')
normalise() { sed -E 's/(\.0)+$//' <<< "$1"; }
if [ "$(normalise "$tag")" != "$(normalise "$version")" ]; then
  echo "::error::Tag v$tag does not match bl_info version $version in __init__.py; bump it before releasing."
  exit 1
fi
echo "Tag v$tag matches bl_info version $version"
