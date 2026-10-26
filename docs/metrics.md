# Metrics: Before vs. After

Every number below was measured from this repository on 2026-10-26 (macOS arm64, Python 3.9.6, synthetic data, seed 42, 2,005-row snapshot). Anything that could not be measured here is marked **not measured**. No estimates are used.

## Demo table

| Metric | Before (legacy workbook) | After (Sales Forecast Automator) | Source |
| :--- | :--- | :--- | :--- |
| Manual steps in the daily process | **5** SOP steps, plus **2** undocumented quirks that live in people's heads | **0** required per run; the scheduled job performs **6** automated steps | `legacy/Daily_Forecast_LEGACY.xlsx` Notes sheet; `run_daily_pipeline()` in `app/scheduler/runner.py` |
| Automated data checks | **0** (no conditional formatting, no data validation; SOP step 3 is a manual eyeball scan) | **4** quality checks + **3** reconciliation levels with **4** variance classes | `app/quality/checker.py`; `app/reconciliation/matcher.py` |
| Hardcoded business rules | **2** buried in the workbook (a customer exclusion inside 12 formulas; a $150,000 off-book row) | **2** moved to `config/rules.yaml`, version-controlled and test-covered | `config/rules.yaml`; Notes sheet |
| Time to generate the daily report | **not measured** (manual, no timing data in the repo) | **0.20 s** median end to end, range 0.19 to 0.21 s over 8 runs | measured, see below |
| Automated tests | **0** | **21** | `pytest` |
| Test coverage of `app/` | **n/a** (no tests) | **92%** (737 statements, 58 missed) | `pytest --cov=app` |
| Rows processed per second | **not measured** | **~2.87 million rows/s** median (50,000 rows in 0.0174 s) | measured, see below |
| API endpoints | **0** | **7** | live OpenAPI schema |

## What each number means

### Manual vs. automated steps
- **Legacy, 5 manual steps** (Notes sheet): morning extract refresh, pivot and formula check, quality review and problem-row triage, management adjustments and quirks, copy and email distribution.
- **Legacy, 2 quirks** (Notes sheet): a hardcoded exclusion of `Acme Test Enterprise 999` in every SUMIFS/COUNTIFS formula, and a manual +$150,000.00 row 18.
- **Automated, 6 steps** (`run_daily_pipeline` docstring): ensure and ingest the snapshot, run quality checks, reconcile against Sales Cloud, evaluate the `block_on_mismatch` policy, export the Excel report to `outbox/`, log an audit recap.
- "0 manual steps required" means the scheduled job needs no human action to produce the report. A person still decides what to do when a report is flagged `WARNING` or `CHECK`. The report itself shows that status.

### Automated checks added
- **Quality, 4:** duplicate `sales_order_num`; missing `coverage_id`; zero or negative ACV; day-over-day total swing above the 25% threshold.
- **Reconciliation, 3 levels:** grand total; date and UT30 grain; order-level join on `sales_order_num`.
- **Variance classes, 4:** `ONLY_IN_FORECAST`, `ONLY_IN_SALES_CLOUD`, `ACV_MISMATCH`, `ATTRIBUTE_MISMATCH`.
- On the current synthetic snapshot the quality engine reports `WARNING` and reconciliation reports `MISMATCH` / `CHECK`. These are the planted anomalies and variances doing their job.

### Time to generate the report
- Measured by calling `run_daily_pipeline()` eight times with a fresh database on the first run, with nothing else running. It covers ingest of 2,005 rows into SQLite, quality checks, reconciliation, forecast and Excel export.
- Run times: 0.207, 0.198, 0.200, 0.203, 0.189, 0.203, 0.201, 0.196 s. Output: `daily_forecast_2026-10-26_CHECK.xlsx`, 20,286 bytes.
- This is a warm local run on one machine. Cold-start time, container time, and the legacy manual time were **not measured**.

### Rows per second
- Uses the call from `tests/test_performance.py::test_performance_50k_rows`: `compute_forecast_from_df` on 50,000 synthetic rows (seed 123).
- Nine timed runs: 0.0166 to 0.0192 s, median 0.0174 s, so 50,000 / 0.0174 = about 2.87 million rows/s. The test itself printed 0.0190 s on its run.
- Scope matters: this times the forecast engine only. It excludes generating the rows (0.32 s) and database ingest. The end-to-end pipeline rate for a 2,005-row snapshot is about 10,000 rows/s (2,005 rows / 0.20 s), which is the fairer figure for "rows per second through the whole report".
- 8,844 of the 50,000 rows pass the filters.

### Test count and coverage
- 21 tests across 10 files: `test_generator` 6, `test_quality` 2, `test_legacy_parity` 3, `test_reconciliation` 4, and 1 each in `test_api`, `test_changes`, `test_exporter`, `test_performance`, `test_reference_parity`, `test_scheduler`.
- Coverage is 92% (737 statements, 58 missed) on four clean full runs, each from a fresh database. Lowest modules: `app/ingestion/loader.py` 77%, `app/reconciliation/base.py` 78%, `app/reconciliation/mock_client.py` 84%.

### Size of the codebase
| Area | Files | Physical lines | Code lines (non-blank, non-comment) |
| :--- | ---: | ---: | ---: |
| `app/` (Python) | 20 (14 modules plus 6 `__init__.py`) | 1,512 | 1,260 |
| `scripts/` (Python) | 3 | 805 | 641 |
| `tests/` (Python) | 11 (10 test modules plus `__init__.py`) | 656 | 517 |
| `static/` (own HTML, JS, CSS; excludes vendored `chart.umd.js`) | 3 | 1,024 | not measured |

- **Packages in `app/`:** 6 (`api`, `engine`, `ingestion`, `quality`, `reconciliation`, `scheduler`).
- **Endpoints, 7, all GET:** `/health`, `/forecast`, `/forecast/export`, `/quality`, `/changes`, `/reconciliation`, `/reconciliation/details`. The static dashboard is also served at `/`.

## Not measured
- Legacy time to produce the daily report (manual process, no timing data).
- Legacy rows per second (Excel, not run here).
- Cold-start, container, and multi-machine timings.
- Number of past silent errors in the legacy process (no history available).
- Code lines for the frontend files.

## Caveats
- **One flaky test run during measurement.** In the first coverage run, `test_api_endpoints` failed once. I could not reproduce it in 8 further runs, including runs under deliberate load. The likely cause is that my own timing script and that pytest run shared `data/forecast.db` at the same time. The test uses a shared on-disk database, so running two things against it in parallel can break it. The figures above come from clean sequential runs.
- **Dates move with the clock.** Tests and the app use today's date unless `AS_OF_DATE` is set, so row counts and totals can change from day to day. Timings and test counts do not depend on the date.

## Reproduce
```bash
# Tests + coverage (remove the local DB first so runs do not share state)
rm -f data/forecast.db
PYTHONPATH=. pytest -q --cov=app --cov-report=term tests/

# 50,000-row timing
PYTHONPATH=. pytest -q -s tests/test_performance.py

# Endpoints
python -c "from app.main import app; print([(m.upper(), p) for p, v in app.openapi()['paths'].items() for m in v])"
```
