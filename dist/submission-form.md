# Sales Forecast Automator: Submission Summary

## Problem
Every morning, a sales operations analyst refreshed a legacy Excel workbook: paste a CSV extract into one sheet, check a pivot, scan for bad rows by eye, apply an off-book adjustment, and email the result to sales leadership. The process had five manual steps and no automated checks. It also depended on two undocumented rules that lived only in the analyst's head:

- A customer, `Acme Test Enterprise 999`, was excluded by name inside the pivot formulas.
- A hardcoded +$150,000 "plan catch-up" row had no matching record in the extract or in the system of record.

If the analyst was out, no report went out. If the extract had duplicates or bad values, nobody was alerted. The forecast was never cross-checked against IBM Sales Cloud, the system of record.

## Solution
Sales Forecast Automator replaces the manual workflow with a scheduled, tested pipeline and a self-serve dashboard.

- **Automated daily pipeline:** ingests the snapshot, runs quality checks, reconciles against Sales Cloud, and writes a legacy-format Excel report to an outbox. The file name carries a `CHECK` label when reconciliation fails, so a mismatched report cannot go out looking clean.
- **Four quality checks:** duplicate order numbers, missing coverage IDs, zero or negative ACV, and day-over-day swing above 25%.
- **Three-level reconciliation:** grand total, date and product grain, and order-by-order join. It classifies four variance types (only in forecast, only in Sales Cloud, ACV mismatch, attribute mismatch) and retries with backoff if Sales Cloud is unavailable.
- **Hidden rules made explicit:** the customer exclusion and the $150,000 adjustment now live in `config/rules.yaml`, version-controlled and tested.
- **Self-serve dashboard:** filters, drill-down from chart to deals, and one-click Excel or CSV export. It uses 7 REST endpoints, and Chart.js is bundled locally.

## How Bob was used
Bob was used at every SDLC stage: reverse-engineering the legacy workbook, designing a pluggable Sales Cloud interface, building seeded test data and an independent reference calculation before the application, implementing the app, debugging against legacy totals, writing documentation, containerizing, and finally scanning the repository for real data and secrets.

## Results (measured on 2026-10-26)
| Measure | Value |
| :--- | :--- |
| Legacy parity | Engine grand total $84,405,455.61 equals the legacy workbook pivot to the cent (355 deals) |
| Tests | 21 passing; 92% coverage of `app/`; CI gate at 80% |
| Report generation | 0.20 s median, end to end, for a 2,005-row snapshot |
| Forecast engine throughput | about 2.87 million rows/s on 50,000 rows (engine only) |
| Planted problems caught | 5 duplicates, 10 missing coverage IDs, 6 bad ACVs, 11 Sales Cloud variances |
| Size | 14 modules, 1,260 code lines in `app/`, 7 endpoints |

Legacy runtime and hours saved were **not measured**, and we make no such claim.

## What is mock vs. real
- **Real and tested:** the pipeline, forecast engine, quality checks, reconciliation logic, Excel export, API, dashboard, and rules configuration.
- **Synthetic:** all data (seeded generator, fictitious "Acme Test" customers) and the legacy workbook, which is a replica built by script.
- **Mock:** the Sales Cloud system of record, a deterministic client with planted variances.
- **Dormant:** the live Sales Cloud client is a disabled stub (`sales_cloud.enabled: false`) with no URL and no key. A repository-wide scan found no real customer names, credentials, or internal endpoints in the files.

## Known limitations and next steps
- The live Sales Cloud connector is not implemented and needs approval before enabling.
- The scheduler runs on a 24-hour interval; the 06:00 cron setting in the config is not wired up.
- Only the current day's snapshot is loaded into the database, so the day-over-day view is empty in the running app (the logic is tested).
- A duplicate order in the extract is counted in the dashboard total but de-duplicated in reconciliation. That policy needs a decision.
- The Docker image has not been built or run in this environment.
