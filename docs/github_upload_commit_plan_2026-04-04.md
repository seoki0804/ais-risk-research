# GitHub Upload Commit Plan (2026-04-04)

This plan splits changes into reviewable commits and avoids uploading the 22GB `outputs/` tree.

## Commit 1: Core model pipeline

```bash
git add src/ais_risk/all_models.py
git add src/ais_risk/all_models_cli.py
git add src/ais_risk/all_models_seed_sweep.py
git add src/ais_risk/all_models_seed_sweep_cli.py
git add src/ais_risk/__init__.py
git commit -m "feat: add unified all-model training and seed-sweep evaluation pipeline"
```

## Commit 2: Tests

```bash
git add tests/test_all_models.py
git add tests/test_all_models_cli.py
git add tests/test_all_models_seed_sweep.py
git commit -m "test: cover all-model pipeline, CLI, and seed-sweep aggregation"
```

## Commit 3: Automation scripts

```bash
git add examples/run_all_supported_models_61day.sh
git add examples/run_all_supported_models_multiarea_61day.sh
git add examples/export_github_results_bundle_2026-04-04.sh
git commit -m "chore: add reproducible run/export scripts for GitHub release"
```

## Commit 4: Docs

```bash
git add README.md
git add docs/github_upload_commit_plan_2026-04-04.md
git add docs/results/2026-04-04/README.md
git commit -m "docs: document model pipeline usage and GitHub upload workflow"
```

## Commit 5: Curated results bundle (optional but recommended)

```bash
git add docs/results/2026-04-04
git commit -m "data: add curated lightweight model evaluation bundle (2026-04-04)"
```

## Final push

```bash
git push origin <branch>
```

## One-command runner

If you want to apply this exact commit sequence automatically:

```bash
examples/commit_github_upload_2026-04-04.sh
```

## Notes

- `.gitignore` now blocks `outputs/**` and `output/` by default.
- Only curated files under `docs/results/**` should be versioned for results.
