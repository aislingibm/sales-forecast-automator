# Sales Leader & Analyst User Guide

Welcome to the **Sales Forecast Automator** — your automated, self-serve solution for tracking new signings and monitoring revenue variances.

---

## 1. Navigating the Dashboard

### KPI Metrics
At the top of the screen, you will find 4 real-time KPI cards:
- **Total New Signings ACV**: Aggregated Annual Contract Value (USD) for currently filtered deals.
- **Deal Count**: Total number of booked contracts.
- **Average Deal Size**: Mean ACV per transaction.
- **Change vs. Yesterday**: Day-over-over net change in new signings ACV and percentage movement.

### Status Indicators
- **Sales Cloud Badge**: Shows `MATCH` (clean reconciliation), `CHECK` (itemized variances detected), or `Not Verified` (service offline).
- **Data Quality Badge**: Shows `PASS` or `WARNING` if anomalies (duplicate orders, missing coverage IDs, non-positive ACV) are discovered.

---

## 2. Dynamic Filtering & Slicing
You can customize the view without asking for a new workbook cut:
- **Country**: Focus on United States, Canada, UK, Germany, Japan, or All.
- **Client Sub-Type**: Filter by `Select T Activate`, `Commercial Growth`, etc.
- **Signing Category**: Toggle between `New Signings`, `Renewals`, and `Expansions`.
- **Product Area (UT15)**: Filter by `Data Platform`, `Automation`, `Security`, or `Sustainability`.
- **Time Grain**: View daily timeline, weekly totals, monthly summaries, or product details.

---

## 3. Interactive Drill-Down
1. Click any bar on the **Forecast Trajectory** chart.
2. The Deals table below automatically filters to only show contracts belonging to that specific date or product.
3. Click **✕ Clear** on the drill-down banner to reset the table.

---

## 4. Exporting Reports
- Click **Export Excel (.xlsx)** in the top navigation bar to download a styled workbook matching the legacy pivot layout.
- Use the API `/forecast/export?format=csv` to extract raw CSV data for downstream BI tools.
