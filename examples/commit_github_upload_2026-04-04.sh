#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

git add src/ais_risk/all_models.py
git add src/ais_risk/all_models_cli.py
git add src/ais_risk/all_models_seed_sweep.py
git add src/ais_risk/all_models_seed_sweep_cli.py
git add src/ais_risk/__init__.py
git commit -m "feat: add unified all-model training and seed-sweep evaluation pipeline"

git add tests/test_all_models.py
git add tests/test_all_models_cli.py
git add tests/test_all_models_seed_sweep.py
git commit -m "test: cover all-model pipeline, CLI, and seed-sweep aggregation"

git add examples/run_all_supported_models_61day.sh
git add examples/run_all_supported_models_multiarea_61day.sh
git add examples/export_github_results_bundle_2026-04-04.sh
git add examples/commit_github_upload_2026-04-04.sh
git commit -m "chore: add reproducible run/export/commit scripts for GitHub release"

git add README.md
git add .gitignore
git add docs/github_upload_commit_plan_2026-04-04.md
git add docs/results/2026-04-04/README.md
git commit -m "docs: document model pipeline usage and GitHub upload workflow"

git add docs/results/2026-04-04
git commit -m "data: add curated lightweight model evaluation bundle (2026-04-04)"

echo "done: commits created on branch $(git symbolic-ref --short HEAD)"
