#!/bin/bash
# Re-run everything downstream of the gold labels (use after any change to rules/features).
# Usage:  bash scripts/run_all_eval.sh          # uses whatever `python` is on PATH
#         PY=/path/to/python bash scripts/...   # or point it at a specific interpreter
set -e
cd "$(dirname "$0")/.."
PY="${PY:-python}"
command -v "$PY" >/dev/null || { echo "no interpreter: $PY (set PY=...)" >&2; exit 1; }
echo "using $("$PY" --version 2>&1) at $(command -v "$PY")"

"$PY" scripts/02_features.py
"$PY" scripts/06_benchmark.py
"$PY" scripts/08_analyse.py
"$PY" scripts/10_train_final.py
"$PY" scripts/09_scale_cost.py
for t in type audience; do "$PY" scripts/07_learning_curve.py "$t" > "results/lc_$t.log" 2>&1 & done; wait
"$PY" scripts/08_analyse.py > results/analyse_final.log 2>&1
echo ALL DONE
