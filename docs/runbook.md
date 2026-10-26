# Operations & Maintenance Runbook

## 1. Quick Start

### Local Execution
```bash
cd forecast-automator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the complete test suite
PYTHONPATH=. pytest --cov=app --cov-report=term-missing

# Start the web server & background scheduler
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to view the self-serve dashboard.
Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive OpenAPI documentation.

### Container Execution (Docker Compose)
```bash
docker compose up --build -d
```

---

## 2. Generating & Refreshing Data
To regenerate the synthetic snapshot files and mock System of Record data with new seeds:
```bash
python scripts/generate_synthetic_data.py --rows 2000 --seed 42 --outdir data/snapshots
```

Signing dates are generated in the 90 days ending on the "as-of" date (today by default), and snapshots are named `snapshot_<YYYY-MM-DD>.csv` for the as-of date and the day before. The seed is deterministic, so the same seed produces the same data shifted to the as-of date. To generate data for a specific date, set `AS_OF_DATE`:
```bash
AS_OF_DATE=2026-10-26 python scripts/generate_synthetic_data.py --rows 2000 --seed 42 --outdir data/snapshots
```
The app, scheduler, API, and mock Sales Cloud client honor the same `AS_OF_DATE` variable, so set it consistently when running them against a fixed date.

To run the independent baseline reference pivot script (defaults to today's snapshot when no path is given):
```bash
python scripts/reference_pivot.py data/snapshots/snapshot_2026-10-26.csv
```

---

## 3. Incident Management & Troubleshooting

### Issue 1: Scheduled Job Fails or Output Missing
1. Check scheduler logs in standard output for `[Daily Pipeline]` tag.
2. Verify SQLite file permissions in `data/forecast.db`.
3. Check if delivery was held due to `block_on_mismatch: true` in `config/settings.yaml`.
4. Trigger manual pipeline execution:
   ```bash
   python -c "from app.scheduler.runner import run_daily_pipeline; run_daily_pipeline()"
   ```

### Issue 2: Sales Cloud Reconciliation Flags "CHECK" (Mismatch)
1. Open the dashboard at `http://127.0.0.1:8000` and navigate to the **Sales Cloud Reconciliation** tab.
2. Review the variance breakdown:
   - `ONLY_IN_FORECAST`: Order was dropped or not yet synchronized in Sales Cloud.
   - `ONLY_IN_SALES_CLOUD`: Order was created directly in Sales Cloud but missing in snapshot extract.
   - `ACV_MISMATCH`: Currency discrepancy exceeds tolerance ($0.01).
   - `ATTRIBUTE_MISMATCH`: Customer name or signing date discrepancy.
3. Check `outbox/` for the generated `.xlsx` with `CHECK` badge.

### Issue 3: Sales Cloud Unavailable ("Not verified")
1. The system automatically retries 3 times with exponential backoff (1s, 2s, 4s).
2. If offline, the daily report is exported with the label `Not verified`.
3. Verify network connectivity or check if `sales_cloud.mock_enabled` is active.
