import pytest
from datetime import timedelta
from starlette.testclient import TestClient
from scripts.generate_synthetic_data import get_as_of_date

def test_api_endpoints():
    from app.main import app
    # Context manager runs the startup lifespan, which seeds and ingests today's snapshot
    with TestClient(app) as client:
        _exercise_api(client)

def _exercise_api(client):
    date_to = get_as_of_date()
    date_from = date_to - timedelta(days=90)

    # 1. Health
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # 2. Forecast default & custom filters + group_by + date ranges
    res_forecast = client.get(f"/forecast?country=United%20States&client_sub_type=Select%20T%20Activate&signing_category=New%20Signings&ut_level_15=Data%20Platform&group_by=week&date_from={date_from.isoformat()}&date_to={date_to.isoformat()}")
    assert res_forecast.status_code == 200
    data = res_forecast.json()
    assert "summary" in data
    assert "deals" in data
    assert "ut30_breakdown" in data
    assert len(data["grouped_data"]) > 0

    # Test other group_by branches
    for grp in ["month", "quarter", "ut_level_30", "customer"]:
        res_g = client.get(f"/forecast?group_by={grp}")
        assert res_g.status_code == 200

    # 3. Forecast export csv
    res_export_csv = client.get("/forecast/export?format=csv")
    assert res_export_csv.status_code == 200
    assert "text/csv" in res_export_csv.headers["content-type"]

    # 4. Forecast export xlsx
    res_export_xlsx = client.get("/forecast/export?format=xlsx")
    assert res_export_xlsx.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_export_xlsx.headers["content-type"]

    # 5. Quality
    res_quality = client.get("/quality")
    assert res_quality.status_code == 200
    q_data = res_quality.json()
    assert "status" in q_data
    assert "duplicates_count" in q_data

    # 6. Changes
    res_changes = client.get("/changes?since=yesterday")
    assert res_changes.status_code == 200
    c_data = res_changes.json()
    assert "added_deals" in c_data
    assert "removed_deals" in c_data

    # 7. Reconciliation
    res_rec = client.get("/reconciliation")
    assert res_rec.status_code == 200
    r_data = res_rec.json()
    assert "status" in r_data

    # 8. Reconciliation details
    res_rec_det = client.get("/reconciliation/details")
    assert res_rec_det.status_code == 200
    rd_data = res_rec_det.json()
    assert "variances" in rd_data
