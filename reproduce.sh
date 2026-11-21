#!/usr/bin/env bash
# Reproduce every published number offline and fail on any mismatch.
# Standard library Python only. No network calls.
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1. recompute and document checks"
python3 -I code/recompute.py

echo "== 2. regenerate the data CSVs and compare byte for byte"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
python3 -I code/recompute.py --out "$tmp" > /dev/null
for f in receipts_summary.csv funding_ladder.csv redemptions.csv fills_vandyke_txs.csv; do
  cmp "data/$f" "$tmp/$f"
  echo "$f: identical"
done

echo "== 3. SHA256SUMS"
if command -v shasum > /dev/null; then
  (cd data && shasum -a 256 -c SHA256SUMS)
else
  (cd data && sha256sum -c SHA256SUMS)
fi

echo "== 4. tests"
python3 -I -m unittest discover -s tests -v

echo "reproduce: all checks passed"
