# 🛤️ Development Track — Big Data Engines Benchmark

Original build predates this portfolio workspace (`billion_challenge`, first commit 2025-06-04) —
this track covers **incorporating it into the portfolio**: renaming to the ID convention, reproducing
the challenge at full scale on new hardware, and publishing with fresh, artifact-sourced evidence.

**Status:** Complete and published. Repo renamed and cloned in; 1B-row challenge re-run on this
machine; dashboard rebuilt from the new run; README updated with real numbers; site page live.

---

## Phase 0 — Incorporation

- [x] Confirm the source repo (`andrematiello/billion_challenge`) is public, has a real README, tests,
      and MIT license — no rebuild-from-scratch needed, unlike AE-05's source material
- [x] Decide placement with the user: **TRANS-04** (transversal_skills), not a 7th Data Engineer slot —
      none of the existing 6 DE projects (Airflow/ETL, Spark/Databricks, Kafka, Terraform, LLM FinOps,
      Postgres DW) cover engine-selection-by-volume, and it reads as a cross-stack skill rather than one
      track's specialty
- [x] Rename the GitHub repo to `TRANS-04-big-data-engines-benchmark` (ID convention, D-013); GitHub
      redirects the old name automatically
- [x] Clone into `transversal_skills/trans_04_big_data_engines_benchmark/` as its own git repo (D-014)

## Phase 1 — Environment

- [x] `.python-version` pins 3.11; `uv python install 3.11 && uv venv --python 3.11` (no Poetry
      available in this environment, `uv pip install -e .` used instead — same `pyproject.toml`)
- [x] `pytest -q` — 12 passed, confirms the pipeline logic before committing to an hour-plus full-scale
      run

**Checkpoint:** ✅ tests green before touching the 1B-row dataset.

## Phase 2 — Full-scale reproduction

- [x] Scope decided with the user: full 1,000,000,000-row input, but only the **fast** implementations
      (DuckDB, PyArrow, Polars lazy) re-run at scale — the slow stdlib/pandas paths already have
      historical numbers (12–24 min each) that reproducing wouldn't change the conclusion of
- [x] `python create_measurements.py 1_000_000_000` — 14.8 GiB file, 324 s
- [x] `python -m src.etl_duckdb` — **22.73 s**, 41,343 stations (`logs/log_duckdb.csv`)
- [x] `python -m src.etl_python_pyarrow` — **1,185.02 s**, 41,343 stations (`logs/log_pyarrow.csv`)
- [x] `python -m src.etl_python_polars_lazy` — **OOM-killed** by the kernel at 12.51 GiB resident
      (`journalctl -k`) — reproduces the historical README's own note that Polars didn't complete in a
      16 GiB environment, now with the kernel's OOM log as evidence instead of an assumption
- [x] `python -m src.create_station_metrics_mart` — built from the DuckDB output (the only implementation
      whose CSV the mart script reads), **41,343 rows**

**Checkpoint:** ✅ 2 of 3 fast implementations completed at full scale; the third failed exactly as the
historical record predicted, which is itself the evidence worth keeping, not a run to hide or retry.

## Phase 3 — Evidence and documentation

- [x] `docs/evidence/run_results.json` — every number above traced to its source (log CSV or kernel log),
      never typed from memory (D-017 discipline, inherited from the rest of this portfolio)
- [x] Ran the Streamlit dashboard locally against the new mart, screenshotted with Playwright
      (`docs/screenshots/dashboard-local.png`)
- [x] README rewritten: new "Reproduced in this portfolio session" section ahead of the original
      "Historical benchmark" table, which is kept and clearly labeled as the original hardware's numbers
      rather than deleted or silently overwritten
- [x] Site page (`site/projects/trans-04-big-data-engines-benchmark.html`) + card in `index.html`,
      status **Live**

## Concepts to master

- **Out-of-core vs. in-memory aggregation at scale.** DuckDB's streaming execution model finishes a
  1B-row group-by in 23 seconds on a 15 GiB machine; Polars's lazy engine — designed to stream too —
  still got OOM-killed. Worth being able to explain why "lazy" doesn't automatically mean "bounded
  memory" for every operation.
- **Reading a kernel OOM log.** `journalctl -k` / `dmesg` surface `anon-rss` at time of kill — real
  peak-memory evidence for a process that never got to log its own metrics.

## Common pitfalls

- **Treating an OOM kill as a failed run to hide.** It's the same finding the original historical
  benchmark already reported — re-discovering it independently, with kernel-log evidence, is stronger
  proof than the historical table's prose claim alone.
- **`set -e` in the driver script stops the whole batch on any non-zero exit** — including a `Killed`
  (exit 137). The mart-building step had to be run manually after the Polars OOM instead of assuming the
  script's `create_station_metrics_mart` call at the end had already run.
