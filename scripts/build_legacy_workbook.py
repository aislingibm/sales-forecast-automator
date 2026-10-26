#!/usr/bin/env python3
"""
Legacy Workbook Generator for Sales Forecast Automator.
Creates a realistic synthetic "legacy" Excel workbook replicating the manual daily process:
1. RawExtract sheet (10-column schema from snapshot)
2. Pivot sheet (live Excel SUMIFS & COUNTIFS formulas, summary cards, and manual adjustment quirk)
3. Notes sheet (daily manual SOP runbook and documented hidden quirks)
Hard constraint: ONLY synthetic data.
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd

def build_legacy_workbook(
    csv_path: str = None,
    output_path: str = "legacy/Daily_Forecast_LEGACY.xlsx"
) -> str:
    from scripts.generate_synthetic_data import get_as_of_date, snapshot_filename
    if csv_path is None:
        csv_path = os.path.join("data", "snapshots", snapshot_filename(get_as_of_date()))
    # Resolve paths relative to forecast-automator root if needed
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(base_dir, csv_path)
    if not os.path.isabs(output_path):
        output_path = os.path.join(base_dir, output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if not os.path.exists(csv_path):
        from scripts.generate_synthetic_data import create_snapshots
        create_snapshots(count=2000, output_dir=os.path.dirname(csv_path))

    df = pd.read_csv(csv_path)

    wb = openpyxl.Workbook()

    # Styling definitions (classic Excel analyst corporate palette)
    font_title = Font(name="Calibri", size=14, bold=True, color="1F497D")
    font_section = Font(name="Calibri", size=11, bold=True, color="1F497D")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_regular = Font(name="Calibri", size=11)
    font_italic = Font(name="Calibri", size=10, italic=True, color="595959")
    font_warning = Font(name="Calibri", size=10, italic=True, color="C00000")

    fill_navy = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    fill_subtotal = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    fill_quirk = PatternFill(start_color="FDE9D9", end_color="FDE9D9", fill_type="solid") # light orange for manual adjustment
    fill_filter_box = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    border_thin = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )
    border_total = Border(
        top=Side(style="thin", color="000000"),
        bottom=Side(style="double", color="000000")
    )

    # ==========================================
    # SHEET 1: RawExtract
    # ==========================================
    ws_raw = wb.active
    ws_raw.title = "RawExtract"

    raw_columns = [
        "ut_level_30_dscr", "ut_level_15_dscr", "coverage_id", "signing_date",
        "sales_order_num", "customer_name", "saas_acv_usd_at_plan", "country",
        "client_sub_type", "signing_category"
    ]

    for col_idx, col_name in enumerate(raw_columns, start=1):
        cell = ws_raw.cell(row=1, column=col_idx, value=col_name)
        cell.fill = fill_navy
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_idx, row in enumerate(df.to_dict(orient="records"), start=2):
        ws_raw.cell(row=row_idx, column=1, value=str(row.get("ut_level_30_dscr") or ""))
        ws_raw.cell(row=row_idx, column=2, value=str(row.get("ut_level_15_dscr") or ""))
        ws_raw.cell(row=row_idx, column=3, value=str(row.get("coverage_id") or ""))
        ws_raw.cell(row=row_idx, column=4, value=str(row.get("signing_date") or ""))
        ws_raw.cell(row=row_idx, column=5, value=str(row.get("sales_order_num") or ""))
        ws_raw.cell(row=row_idx, column=6, value=str(row.get("customer_name") or ""))

        acv_raw = row.get("saas_acv_usd_at_plan", 0.0)
        try:
            acv_num = float(acv_raw)
        except (ValueError, TypeError):
            acv_num = 0.0
        
        c_acv = ws_raw.cell(row=row_idx, column=7, value=acv_num)
        c_acv.number_format = "$#,##0.00"
        c_acv.alignment = Alignment(horizontal="right")

        ws_raw.cell(row=row_idx, column=8, value=str(row.get("country") or ""))
        ws_raw.cell(row=row_idx, column=9, value=str(row.get("client_sub_type") or ""))
        ws_raw.cell(row=row_idx, column=10, value=str(row.get("signing_category") or ""))

        for col_idx in range(1, 11):
            ws_raw.cell(row=row_idx, column=col_idx).font = font_regular
            ws_raw.cell(row=row_idx, column=col_idx).border = border_thin

    max_raw_row = len(df) + 1

    # ==========================================
    # SHEET 2: Pivot (Formulas & Filter Header)
    # ==========================================
    ws_pivot = wb.create_sheet(title="Pivot")
    ws_pivot.views.sheetView[0].showGridLines = True

    # Title Banner
    ws_pivot.cell(row=2, column=2, value="DAILY NEW SIGNINGS FORECAST - DATA PLATFORM").font = font_title
    ws_pivot.cell(row=3, column=2, value="Legacy Manual Workbook (Formulas Linked to RawExtract)").font = font_italic

    # Active Pivot Filter Box
    ws_pivot.cell(row=5, column=2, value="Active Pivot Filter Rules:").font = font_section
    filter_specs = [
        ("Country:", "United States", 6),
        ("Client Sub-Type:", "Select T Activate", 7),
        ("Signing Category:", "New Signings", 8),
        ("Product Area (UT15):", "Data Platform", 9)
    ]
    for lbl, val, r in filter_specs:
        ws_pivot.cell(row=r, column=2, value=lbl).font = font_bold
        c_val = ws_pivot.cell(row=r, column=3, value=val)
        c_val.font = font_regular
        c_val.fill = fill_filter_box

    # Pivot Table Headers
    ws_pivot.cell(row=11, column=2, value="Product Offering (UT Level 30)").font = font_header
    ws_pivot.cell(row=11, column=2).fill = fill_navy
    ws_pivot.cell(row=11, column=3, value="Deal Count").font = font_header
    ws_pivot.cell(row=11, column=3).fill = fill_navy
    ws_pivot.cell(row=11, column=3).alignment = Alignment(horizontal="right")
    ws_pivot.cell(row=11, column=4, value="Total SaaS ACV (USD)").font = font_header
    ws_pivot.cell(row=11, column=4).fill = fill_navy
    ws_pivot.cell(row=11, column=4).alignment = Alignment(horizontal="right")
    ws_pivot.cell(row=11, column=5, value="Avg Deal Size (USD)").font = font_header
    ws_pivot.cell(row=11, column=5).fill = fill_navy
    ws_pivot.cell(row=11, column=5).alignment = Alignment(horizontal="right")

    ut30_products = [
        "Analytics Engine Serverless",
        "Data Product Hub Enterprise",
        "DataStage Modernized",
        "Db2 Warehouse SaaS",
        "watsonx.data Core",
        "watsonx.governance Cloud"
    ]

    # Quirk #1 note: We exclude test sandbox account "Acme Test Enterprise 999" from the formula
    for idx, prod in enumerate(ut30_products, start=12):
        ws_pivot.cell(row=idx, column=2, value=prod).font = font_regular
        ws_pivot.cell(row=idx, column=2).border = border_thin

        # COUNTIFS formula (excluding manual exclusion account)
        count_formula = (
            f'=COUNTIFS(RawExtract!A$2:A${max_raw_row}, B{idx}, '
            f'RawExtract!H$2:H${max_raw_row}, $C$6, '
            f'RawExtract!I$2:I${max_raw_row}, $C$7, '
            f'RawExtract!J$2:J${max_raw_row}, $C$8, '
            f'RawExtract!B$2:B${max_raw_row}, $C$9, '
            f'RawExtract!F$2:F${max_raw_row}, "<>Acme Test Enterprise 999")'
        )
        c_count = ws_pivot.cell(row=idx, column=3, value=count_formula)
        c_count.font = font_regular
        c_count.number_format = "#,##0"
        c_count.alignment = Alignment(horizontal="right")
        c_count.border = border_thin

        # SUMIFS formula
        sum_formula = (
            f'=SUMIFS(RawExtract!G$2:G${max_raw_row}, '
            f'RawExtract!A$2:A${max_raw_row}, B{idx}, '
            f'RawExtract!H$2:H${max_raw_row}, $C$6, '
            f'RawExtract!I$2:I${max_raw_row}, $C$7, '
            f'RawExtract!J$2:J${max_raw_row}, $C$8, '
            f'RawExtract!B$2:B${max_raw_row}, $C$9, '
            f'RawExtract!F$2:F${max_raw_row}, "<>Acme Test Enterprise 999")'
        )
        c_sum = ws_pivot.cell(row=idx, column=4, value=sum_formula)
        c_sum.font = font_regular
        c_sum.number_format = "$#,##0.00"
        c_sum.alignment = Alignment(horizontal="right")
        c_sum.border = border_thin

        # Average Formula = SUM / COUNT
        avg_formula = f'=IF(C{idx}>0, D{idx}/C{idx}, 0)'
        c_avg = ws_pivot.cell(row=idx, column=5, value=avg_formula)
        c_avg.font = font_regular
        c_avg.number_format = "$#,##0.00"
        c_avg.alignment = Alignment(horizontal="right")
        c_avg.border = border_thin

    # Quirk #2: Manual Offline Adjustment Row
    adj_row = 18
    ws_pivot.cell(row=adj_row, column=2, value="[Manual Adjustment] Q2 Executive Plan Catch-up (Off-book)").font = font_warning
    ws_pivot.cell(row=adj_row, column=2).fill = fill_quirk
    ws_pivot.cell(row=adj_row, column=2).border = border_thin

    c_adj_count = ws_pivot.cell(row=adj_row, column=3, value=1)
    c_adj_count.font = font_warning
    c_adj_count.fill = fill_quirk
    c_adj_count.number_format = "#,##0"
    c_adj_count.alignment = Alignment(horizontal="right")
    c_adj_count.border = border_thin

    c_adj_val = ws_pivot.cell(row=adj_row, column=4, value=150000.00)
    c_adj_val.font = font_warning
    c_adj_val.fill = fill_quirk
    c_adj_val.number_format = "$#,##0.00"
    c_adj_val.alignment = Alignment(horizontal="right")
    c_adj_val.border = border_thin

    c_adj_avg = ws_pivot.cell(row=adj_row, column=5, value=150000.00)
    c_adj_avg.font = font_warning
    c_adj_avg.fill = fill_quirk
    c_adj_avg.number_format = "$#,##0.00"
    c_adj_avg.alignment = Alignment(horizontal="right")
    c_adj_avg.border = border_thin

    # Subtotal (System Calculated)
    sub_row = 19
    ws_pivot.cell(row=sub_row, column=2, value="Subtotal (Extract Only)").font = font_bold
    ws_pivot.cell(row=sub_row, column=2).fill = fill_subtotal
    ws_pivot.cell(row=sub_row, column=2).border = border_thin

    c_sub_cnt = ws_pivot.cell(row=sub_row, column=3, value="=SUM(C12:C17)")
    c_sub_cnt.font = font_bold
    c_sub_cnt.fill = fill_subtotal
    c_sub_cnt.number_format = "#,##0"
    c_sub_cnt.alignment = Alignment(horizontal="right")
    c_sub_cnt.border = border_thin

    c_sub_sum = ws_pivot.cell(row=sub_row, column=4, value="=SUM(D12:D17)")
    c_sub_sum.font = font_bold
    c_sub_sum.fill = fill_subtotal
    c_sub_sum.number_format = "$#,##0.00"
    c_sub_sum.alignment = Alignment(horizontal="right")
    c_sub_sum.border = border_thin

    c_sub_avg = ws_pivot.cell(row=sub_row, column=5, value="=IF(C19>0, D19/C19, 0)")
    c_sub_avg.font = font_bold
    c_sub_avg.fill = fill_subtotal
    c_sub_avg.number_format = "$#,##0.00"
    c_sub_avg.alignment = Alignment(horizontal="right")
    c_sub_avg.border = border_thin

    # Grand Total (Including manual adjustment)
    tot_row = 20
    ws_pivot.cell(row=tot_row, column=2, value="Grand Total (Reported to Leadership)").font = font_bold
    ws_pivot.cell(row=tot_row, column=2).border = border_total

    c_tot_cnt = ws_pivot.cell(row=tot_row, column=3, value="=SUM(C12:C18)")
    c_tot_cnt.font = font_bold
    c_tot_cnt.number_format = "#,##0"
    c_tot_cnt.alignment = Alignment(horizontal="right")
    c_tot_cnt.border = border_total

    c_tot_sum = ws_pivot.cell(row=tot_row, column=4, value="=SUM(D12:D18)")
    c_tot_sum.font = font_bold
    c_tot_sum.number_format = "$#,##0.00"
    c_tot_sum.alignment = Alignment(horizontal="right")
    c_tot_sum.border = border_total

    c_tot_avg = ws_pivot.cell(row=tot_row, column=5, value="=IF(C20>0, D20/C20, 0)")
    c_tot_avg.font = font_bold
    c_tot_avg.number_format = "$#,##0.00"
    c_tot_avg.alignment = Alignment(horizontal="right")
    c_tot_avg.border = border_total

    # ==========================================
    # SHEET 3: Notes (SOP & Documented Quirks)
    # ==========================================
    ws_notes = wb.create_sheet(title="Notes")
    ws_notes.views.sheetView[0].showGridLines = True

    ws_notes.cell(row=2, column=2, value="SALES FORECAST WORKBOOK - STANDARD OPERATING PROCEDURE (SOP)").font = font_title
    ws_notes.cell(row=3, column=2, value="Owner: Senior Sales Ops Analyst (Legacy Manual Process)").font = font_italic

    sop_steps = [
        ("Step 1: Morning Extract Refresh", "Download the daily raw CSV extract from the sales data portal. Open this workbook and paste the entire extract into the 'RawExtract' sheet starting at cell A2. Overwrite previous day's extract."),
        ("Step 2: Pivot Table & Formula Check", "Go to the 'Pivot' sheet. Confirm that the 4 filter cells (C6:C9) are set to 'United States', 'Select T Activate', 'New Signings', and 'Data Platform'. Hit Ctrl+Alt+F9 to force a full workbook calculation."),
        ("Step 3: Quality Review & Problem Row Triage", "Scan RawExtract for negative ACV or duplicate order numbers. If a rogue deal is found, manually delete or override the row in RawExtract before sending."),
        ("Step 4: Management Adjustments & Quirks (See Below)", "Verify any offline adjustments for the current quarter with the sales VP. Check row 18 on Pivot sheet."),
        ("Step 5: Copy & Email Distribution", "Copy cells B11:E20 from the Pivot sheet. Paste as an image/table into the daily 8:30 AM forecast update email to Sales Leadership.")
    ]

    r_sop = 5
    for title, text in sop_steps:
        ws_notes.cell(row=r_sop, column=2, value=title).font = font_section
        ws_notes.cell(row=r_sop+1, column=2, value=text).font = font_regular
        r_sop += 3

    ws_notes.cell(row=r_sop, column=2, value="DOCUMENTED WORKBOOK QUIRKS & UNWRITTEN RULES:").font = font_section
    r_sop += 1

    quirks = [
        ("Quirk #1: Hardcoded Customer Exclusion in Formulas",
         "The analyst manually excludes 'Acme Test Enterprise 999' directly in the SUMIFS and COUNTIFS formulas because it represents an internal sandbox/partner test account that was polluting revenue numbers. This exclusion was never formalized in the data portal extract."),
        ("Quirk #2: Off-book Manual Adjustment Row (Row 18)",
         "Row 18 on the Pivot sheet contains a manual +$150,000.00 'Q2 Executive Plan Catch-up' credit instructed verbally by sales leadership to account for a timing delay in booking a strategic multi-year agreement. This value is hardcoded and has no corresponding record in RawExtract or Sales Cloud.")
    ]

    for title, text in quirks:
        ws_notes.cell(row=r_sop, column=2, value=title).font = font_bold
        ws_notes.cell(row=r_sop, column=2).fill = fill_quirk
        ws_notes.cell(row=r_sop+1, column=2, value=text).font = font_regular
        r_sop += 3

    # Adjust column widths
    for ws in [ws_raw, ws_pivot, ws_notes]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        val_str = str(cell.value)
                        if not val_str.startswith("="):
                            max_len = max(max_len, len(val_str))
                except:
                    pass
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    ws_notes.column_dimensions["B"].width = 110

    wb.save(output_path)
    print(f"Legacy workbook created successfully at: {output_path}")
    return output_path

if __name__ == "__main__":
    build_legacy_workbook()
