# 🛤️ Development Track: Big Data Engines Benchmark

The original build predates this portfolio workspace (`billion_challenge`, first commit 2025-06-04).
This track covers incorporating it into the portfolio: renaming to the ID convention, reproducing the
challenge at full scale on new hardware, and publishing with fresh, artifact-sourced evidence.

**Status:** Complete and published. Repo renamed and cloned in; 1B-row challenge re-run on this
machine; dashboard rebuilt from the new run; README updated with real numbers; site page live.

---

## Phase 0: Incorporation

- [x] Confirmed the source repo (`andrematiello/billion_challenge`) is public, has a real README, tests,
      and an MIT license, so no rebuild from scratch was needed, unlike AE-05's source material
- [x] Decided placement with the user: **TRANS-04** (transversal_skills), not a 7th Data Engineer slot.
      None of the existing 6 DE projects (Airflow/ETL, Spark/Databricks, Kafka, Terraform, LLM FinOps,
      Postgres DW) cover engine selection by data volume, and it reads more like a cross-stack skill
      than one track's specialty
- [x] Renamed the GitHub repo to `TRANS-04-big-data-engines-benchmark` (ID convention, D-013); GitHub
      redirects the old name automatically
- [x] Cloned into `transversal_skills/trans_04_big_data_engines_benchmark/` as its own git repo (D-014)

## Phase 1: Environment

- [x] `.python-version` pins 3.11. Used `uv python install 3.11 && uv venv --python 3.11` (no Poetry
      available in this environment, so `uv pip install -e .` filled in against the same `pyproject.toml`)
- [x] `pytest -q`: 12 passed, confirming the pipeline logic before committing to an hour-plus full-scale
      run

**Checkpoint:** ✅ tests green before touching the 1B-row dataset.

## Phase 2: Full-scale reproduction

- [x] Scope decided with the user: full 1,000,000,000-row input, but only the fast implementations
      (DuckDB, PyArrow, Polars lazy) re-run at scale. The slow stdlib/pandas paths already have
      historical numbers (12-24 min each), and reproducing them wouldn't have changed the conclusion.
- [x] `python create_measurements.py 1_000_000_000`: 14.8 GiB file, 324 s
- [x] `python -m src.etl_duckdb`: **22.73 s**, 41,343 stations (`logs/log_duckdb.csv`)
- [x] `python -m src.etl_python_pyarrow`: **1,185.02 s**, 41,343 stations (`logs/log_pyarrow.csv`)
- [x] `python -m src.etl_python_polars_lazy`: **OOM-killed** by the kernel at 12.51 GiB resident
      (`journalctl -k`). This reproduces the historical README's own note that Polars didn't complete
      in a 16 GiB environment, now with the kernel's OOM log as evidence instead of an assumption.
- [x] `python -m src.create_station_metrics_mart`: built from the DuckDB output, the only implementation
      whose CSV the mart script reads, giving **41,343 rows**

**Checkpoint:** ✅ 2 of the 3 fast implementations completed at full scale. The third failed exactly as
the historical record predicted, and that's itself the evidence worth keeping, not a run to hide or
retry.

## Phase 3: Evidence and documentation

- [x] `docs/evidence/run_results.json`: every number above traced to its source (a log CSV or the
      kernel log), never typed from memory (D-017 discipline, inherited from the rest of this portfolio)
- [x] Ran the Streamlit dashboard locally against the new mart, screenshotted with Playwright
      (`docs/screenshots/dashboard-local.png`)
- [x] README rewritten, with a new "Reproduced in this portfolio session" section ahead of the original
      "Historical benchmark" table. That table was kept and clearly labeled as the original hardware's
      numbers rather than deleted or silently overwritten.
- [x] Site page (`site/projects/trans-04-big-data-engines-benchmark.html`) plus a card in `index.html`,
      status **Live**

## Concepts to master

- **Out-of-core vs. in-memory aggregation at scale.** DuckDB's streaming execution model finishes a
  1B-row group-by in 23 seconds on a 15 GiB machine. Polars's lazy engine is designed to stream too, and
  it still got OOM-killed. Worth being able to explain why "lazy" doesn't automatically mean "bounded
  memory" for every operation.
- **Reading a kernel OOM log.** `journalctl -k` and `dmesg` surface `anon-rss` at the moment of the kill,
  which is real peak-memory evidence for a process that never got the chance to log its own metrics.

## Common pitfalls

- **Treating an OOM kill as a failed run to hide.** It's the same finding the original historical
  benchmark already reported. Re-discovering it independently, with kernel-log evidence, is stronger
  proof than the historical table's prose claim on its own.
- **`set -e` in the driver script stops the whole batch on any non-zero exit**, including a `Killed`
  (exit 137). The mart-building step had to be run manually after the Polars OOM instead of assuming the
  script's `create_station_metrics_mart` call at the end had already run.
