import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd

def export_forecast_to_excel(
    df: pd.DataFrame,
    output_path: str,
    reconciliation_status: str = "MATCH",
    report_label: str = "FINAL"
) -> str:
    """
    Exports forecast dataset to an Excel workbook matching the legacy report layout.
    Applies professional styling, proper currency number formats, and metadata header.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "New Signings Forecast"

    # Define color scheme (IBM Design inspired)
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    
    border_thin = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )

    columns = [
        "ut_level_30_dscr",
        "coverage_id",
        "signing_date",
        "sales_order_num",
        "customer_name",
        "saas_acv_usd_at_plan"
    ]

    # Write column headers at row 1
    for col_idx, col_name in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Write data rows
    row_idx = 2
    for _, row in df.iterrows():
        ws.cell(row=row_idx, column=1, value=str(row.get("ut_level_30_dscr", ""))).font = data_font
        ws.cell(row=row_idx, column=2, value=str(row.get("coverage_id", ""))).font = data_font
        ws.cell(row=row_idx, column=3, value=str(row.get("signing_date", ""))).font = data_font
        ws.cell(row=row_idx, column=4, value=str(row.get("sales_order_num", ""))).font = data_font
        ws.cell(row=row_idx, column=5, value=str(row.get("customer_name", ""))).font = data_font
        
        acv_val = row.get("saas_acv_usd_at_plan", 0.0)
        try:
            acv_num = float(acv_val)
        except (ValueError, TypeError):
            acv_num = 0.0
            
        acv_cell = ws.cell(row=row_idx, column=6, value=acv_num)
        acv_cell.font = data_font
        acv_cell.number_format = "$#,##0.00"
        acv_cell.alignment = Alignment(horizontal="right")

        for col_idx in range(1, 7):
            ws.cell(row=row_idx, column=col_idx).border = border_thin

        row_idx += 1

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

    wb.save(output_path)
    return output_path
