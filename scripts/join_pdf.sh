#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pdfunite source/MS408_part1_pages001-107.pdf source/MS408_part2_pages108-214.pdf source/MS408_full.pdf
echo "Wrote source/MS408_full.pdf"
