#!/bin/bash
# Single command to deploy any combination of spark.wiki's projects.
#
# Usage:
#   ./deploy.sh frontend backend
#   ./deploy.sh UpdatePhotoMetadata
#
# All the actual work happens in deploy.py; this just forwards arguments so
# the command matches this repo's other root-level scripts (start_local.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$ROOT/deploy.py" "$@"
