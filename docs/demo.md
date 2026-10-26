# Demo Kit: 5-Minute Script and Slide Outline

All numbers were read from this repo on 2026-10-26 (seed 42, 2,005-row snapshot). They come from the live app, `pytest`, and [`metrics.md`](metrics.md). Totals do not depend on the date you present.

**Run of show (total 5:00)**

| Segment | Start | End | Length | Screen |
| :--- | :--- | :--- | :--- | :--- |
| 1. Before | 0:00 | 0:50 | 50 s | Excel + Slide 1 |
| 2. Bob at each SDLC stage | 0:50 | 1:50 | 60 s | Slide 2 |
| 3. Live demo | 1:50 | 3:50 | 120 s | Browser, Finder |
| 4. Proof | 3:50 | 4:30 | 40 s | Terminal |
| 5. Close | 4:30 | 5:00 | 30 s | Slide 5 |

---

## Setup (before you start, not part of the 5 minutes)

```bash
cd sales-forecast-automator && source .venv/bin/activate
rm -f data/forecast.db outbox/daily_forecast_*.xlsx      # clean state
uvicorn app.main:app --host 127.0.0.1 --port 8000        # ready in about 1 s
```

1. Open `http://127.0.0.1:8000` in a browser tab and let it finish loading. The two header badges must read `Sales Cloud: CHECK (11 Variances)` and `Quality: WARNING (21 issues)`.
2. Open `legacy/Daily_Forecast_LEGACY.xlsx` in Excel on the **Pivot** tab.
3. Open a second terminal at the repo root with the venv active. Do not run it yet.
4. Open Finder at `outbox/`. It should contain `daily_forecast_<today>_CHECK.xlsx`, written at startup.
5. Put the slides from the outline below in a window.

**Don't:** refresh the browser while pytest is running. The tests share `data/forecast.db` with the server. Don't click the **Day-over-Day Changes** tab (see the Q&A).

---

## Script

### 1. Before: the legacy workbook (0:00 to 0:50)

| Time | Do on screen | Say |
| :--- | :--- | :--- |
| 0:00 | Excel, **Pivot** tab visible. | "Every morning an analyst pasted a CSV into this workbook and emailed the pivot." |
| 0:12 | Click the **Notes** tab. | "The Notes tab is the whole process: five manual steps. The quality check in step 3 is 'scan for bad rows by eye'. There are no automated checks." |
| 0:26 | Click the **Pivot** tab, then cell **C12**. Point at the formula bar. | "Look inside the formula: it excludes `Acme Test Enterprise 999` by name. That rule is repeated in 12 formulas and written nowhere else." |
| 0:38 | Click cell **B18**, then **D18**. | "And row 18 is a hardcoded $150,000 that matches no record in the extract or in Sales Cloud. Two hidden rules, in one person's head." |
| 0:50 | Switch to Slide 2. | |

### 2. Bob at each SDLC stage (0:50 to 1:50)

About 7 seconds each. For each stage, read the prompt, then the result, from the slide. **The prompts are suggested wording. Rehearse the ones you'll say.** The results are things you can open in the repo.

| Time | Stage | Prompt to Bob | Result you can point to |
| :--- | :--- | :--- | :--- |
| 0:50 | 1. Understand | "Read the legacy workbook and list every manual step and hidden rule." | 5 SOP steps and 2 hidden quirks, written up in `docs/legacy_analysis.md`. |
| 0:58 | 2. Design | "Design a Sales Cloud reconciliation that works with no live system." | A `SalesSystemClient` interface with a mock and a dormant live client; 5 ADRs in `docs/adr.md`. |
| 1:05 | 3. Test first | "Build a seeded synthetic generator and an independent reference pivot." | `generate_synthetic_data.py` plants 5 duplicates, 10 missing IDs, 6 bad ACVs and 11 Sales Cloud variances. |
| 1:13 | 4. Build | "Build ingestion, engine, quality checks, reconciliation, API, scheduler, dashboard." | 14 modules in `app/`, 1,260 code lines, 7 endpoints. |
| 1:20 | 5. Debug and verify | "Make the engine match the legacy totals and fix whatever fails." | Both hidden rules moved to `config/rules.yaml`; engine matches the legacy pivot to the cent. |
| 1:28 | 6. Document | "Document architecture, operations and the legacy quirks." | README, architecture, ADRs, runbook, user guide, legacy analysis, metrics. |
| 1:35 | 7. Ops | "Containerize it hardened, and add CI with a coverage gate." | Non-root UBI Dockerfile, compose bound to `127.0.0.1`, CI gate at 80% coverage. |
| 1:43 | 8. Review | "Scan the repo for real customer data, secrets and internal hosts; confirm Sales Cloud is off." | 55 files and full history scanned: no real customers or credentials; `enabled: false`. |

Close the segment with: "Same assistant, start to finish." Then switch to the browser at 1:50.

### 3. Live demo (1:50 to 3:50)

**3a. Dashboard (1:50 to 2:20)**

| Time | Click | Say |
| :--- | :--- | :--- |
| 1:50 | Browser tab, already loaded. Point at the header badges, then the first three KPI cards. **Skip the fourth card, "Change vs. Yesterday"** (it shows +$0.00, see Q&A). | "No one ran anything. The scheduler built this at startup. $84.4 million across 355 deals, average $237,762." |
| 2:00 | **Time Grain / Dimension** dropdown, choose **Product Detail (UT30)**, click **Apply Filters**. | "Any leader can re-cut it without a ticket." |
| 2:08 | Click the tallest bar, **DataStage Modernized**. | "Click a bar and the **Deals Explorer** below shows the 72 deals behind it." |
| 2:17 | Click **✕ Clear** on the drill tag. | |

**3b. Quality findings (2:20 to 2:45)**

| Time | Click | Say |
| :--- | :--- | :--- |
| 2:20 | Tab **Data Quality Findings**. | "Four automated checks. 5 duplicate orders, 10 missing coverage IDs, 6 zero or negative ACVs." |
| 2:35 | Point at the **Audit Alerts** box. | "21 issues flagged. We planted every one, and it found every one. The old process relied on someone spotting them." |

**3c. Sales Cloud mismatch drill-down (2:45 to 3:20)**

| Time | Click | Say |
| :--- | :--- | :--- |
| 2:45 | Tab **Sales Cloud Reconciliation**. Point at the summary line. | "Status is MISMATCH, labelled CHECK. Forecast $83.90M against the system of record $83.36M: a $542,394 net variance across 11 orders." |
| 2:58 | Scroll to the row **SO-000031** (`ACV_MISMATCH`). | "Order by order. SO-000031: forecast $432,742.72, Sales Cloud $447,742.72. The details column says why: a $15,000 discrepancy, over a one-cent tolerance." |
| 3:10 | Point at **SO-000053** (`ATTRIBUTE_MISMATCH`), then the `ONLY_IN_FORECAST` rows. | "A customer legal-entity change, and orders present on only one side. Four variance types, all caught." |

**3d. Generated Excel (3:20 to 3:50)**

| Time | Click | Say |
| :--- | :--- | :--- |
| 3:20 | **Export Excel (.xlsx)**, top right. Open the downloaded file. | "One click gives the legacy layout: six columns, 354 deal rows." |
| 3:32 | Finder, `outbox/`. Point at `daily_forecast_<today>_CHECK.xlsx`. | "This one nobody clicked. The scheduler wrote it, and the file name carries CHECK because reconciliation failed. A mismatched report can't go out looking clean." |
| 3:50 | Switch to the terminal. | |

### 4. Proof (3:50 to 4:30)

| Time | Run | Say |
| :--- | :--- | :--- |
| 3:50 | `PYTHONPATH=. pytest tests/test_legacy_parity.py -v` (about 1 s) | "Parity: the engine's grand total, $84,405,455.61, equals the legacy pivot to the cent. Two more tests prove that dropping either hidden rule breaks parity." Expect **3 passed**. |
| 4:05 | `PYTHONPATH=. pytest -q --cov=app --cov-report=term` (about 4 s) | "The whole suite." Expect **21 passed** and `TOTAL ... 92%`. |
| 4:20 | Point at the `TOTAL` line. | "21 tests, 92% coverage, and CI fails below 80%." |

### 5. Close (4:30 to 5:00)

Show Slide 5. Say:

"To be straight about what's real. The pipeline, the checks, the reconciliation logic, the API and the dashboard are real and tested. The data, the Sales Cloud system, and the legacy workbook are synthetic stand-ins. The live Sales Cloud connector is a disabled stub with no URL and no key. Next steps: connect to a real Sales Cloud with approval, wire up the 06:00 schedule, and ingest yesterday's snapshot so the day-over-day view fills in."

---

## Slide outline (one page, 5 slides)

| # | Title | Content (max 3 bullets) | Visual | Time |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Before: a one-person workbook** | 5 manual steps, 0 automated checks • 2 hidden rules (customer exclusion in 12 formulas; $150,000 off-book row) • Process owner is a single analyst | Screenshot of the Pivot tab with C12's formula and row 18 circled | 0:00 to 0:50 |
| 2 | **Bob across the SDLC** | 8-row table: stage, prompt, result (from the Bob table above) | Table only | 0:50 to 1:50 |
| 3 | **Live demo** | Dashboard • Quality findings • Sales Cloud drill-down • Generated Excel | 4 screenshots, one per beat. Use as a backup if the app fails. | 1:50 to 3:50 |
| 4 | **Proof** | Legacy parity to the cent: $84,405,455.61 • 21 tests pass, 92% coverage, CI gate at 80% • 7 endpoints, 14 modules, 1,260 code lines | The pytest output screenshot | 3:50 to 4:30 |
| 5 | **Mock vs. real, and next steps** | See the table below | Two-column table | 4:30 to 5:00 |

**Slide 5 content**

| Real and tested | Mock or stand-in |
| :--- | :--- |
| Pipeline, forecast engine, 4 quality checks, 3-level reconciliation, Excel export, API, dashboard | All data: seeded synthetic records |
| Rules in `config/rules.yaml` | Sales Cloud: `MockSalesCloudClient` with planted variances |
| Scheduler (24-hour interval) | Legacy workbook: a synthetic replica built by `scripts/build_legacy_workbook.py` |
| | Live connector: disabled stub, `enabled: false`, no URL, no key |

**Next steps:** (1) real Sales Cloud connector after approval, (2) wire the 06:00 cron setting, (3) ingest the previous day's snapshot, (4) decide the duplicate-order policy.

**Do not put on any slide:** "45 minutes a day", "8 hours saved", or any legacy runtime. They are **not measured**. `HACKATHON_GUIDE.md` makes the 45-minute claim, but nothing in the repo supports it.

---

## Q&A cheat sheet

| Question | Honest answer |
| :--- | :--- |
| Why is the KPI total ($84,405,455.61) different from the reconciliation "Forecast Total" ($83,897,529.64)? | The KPI includes one order that appears twice in the extract, worth $357,925.97 extra, plus the $150,000 manual adjustment. Reconciliation de-duplicates by order number. The quality tab flags the duplicate. Matching the legacy total meant keeping that behavior, so the duplicate-order policy is a decision still to be made. |
| KPI shows 355 deals, Excel has 354 rows. | 355 includes the one off-book $150,000 adjustment, now a visible rule in `rules.yaml`. The Excel sheet lists the 354 real deal rows. |
| Is that the real legacy workbook? | No. It is a synthetic replica built by a script. Parity is checked against it and against an independent pandas reference. The test evaluates the workbook's formulas in Python, not in Excel. |
| Why is the Day-over-Day tab empty? | Only today's snapshot is loaded into the database, so there is nothing to compare. The tests for that logic pass using generated snapshots. Ingesting yesterday's file is the fix. |
| Does it really run at 06:00? | Not yet. `settings.yaml` has a cron expression, but the scheduler uses a 24-hour interval from startup. |
| How fast is it? | The whole report takes about 0.20 s. The forecast engine alone processes about 2.87 million rows/s on 50,000 rows. Details in `metrics.md`. |
| Does it touch the real Sales Cloud? | No. It is disabled by default, with no endpoint and no key. |

## Backups
- App won't start: use the four screenshots on Slide 3 and run `curl http://127.0.0.1:8000/quality` for the quality numbers.
- Tests are slow or fail: show the saved terminal output from your rehearsal. If a single test fails, re-run it alone. A full run can fail when the server shares the database.
- The Docker image was **not built or run** in this work, so don't demo it.
