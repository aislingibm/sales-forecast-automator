#!/usr/bin/env python3
"""
Deterministic Synthetic Data Generator for Sales Forecast Automator.
Generates snapshot CSVs and mock Sales Cloud datasets with planted quality anomalies and variances.
Hard constraint: ONLY synthetic data.
"""

import os
import csv
import random
import argparse
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple

DEFAULT_SEED = 42

UT_LEVEL_15_LIST = [
    ("Data Platform", 0.65),
    ("Automation", 0.15),
    ("Security", 0.12),
    ("Sustainability", 0.08)
]

UT_LEVEL_30_MAP = {
    "Data Platform": [
        "watsonx.data Core",
        "watsonx.governance Cloud",
        "Db2 Warehouse SaaS",
        "DataStage Modernized",
        "Data Product Hub Enterprise",
        "Analytics Engine Serverless"
    ],
    "Automation": [
        "AppConnect Enterprise Cloud",
        "MQ Managed SaaS",
        "API Connect Enterprise"
    ],
    "Security": [
        "QRadar Log Insights",
        "Guardium Data Security",
        "Verify SaaS Identity"
    ],
    "Sustainability": [
        "Envizi ESG Suite",
        "Maximo Cloud APM"
    ]
}

COUNTRIES = [
    ("United States", 0.70),
    ("Canada", 0.10),
    ("United Kingdom", 0.08),
    ("Germany", 0.06),
    ("Japan", 0.06)
]

CLIENT_SUB_TYPES = [
    ("Select T Activate", 0.60),
    ("Commercial Growth", 0.20),
    ("Enterprise Strategic", 0.15),
    ("Midmarket Pilot", 0.05)
]

SIGNING_CATEGORIES = [
    ("New Signings", 0.65),
    ("Renewals", 0.20),
    ("Expansions", 0.15)
]

def _weighted_choice(choices_with_weights: List[Tuple[Any, float]], rng: random.Random) -> Any:
    choices, weights = zip(*choices_with_weights)
    return rng.choices(choices, weights=weights, k=1)[0]

def generate_base_records(
    count: int = 2000,
    base_date: date = date(2025, 5, 15),
    seed: int = DEFAULT_SEED
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    records = []

    for i in range(1, count + 1):
        ut_15 = _weighted_choice(UT_LEVEL_15_LIST, rng)
        ut_30_options = UT_LEVEL_30_MAP[ut_15]
        ut_30 = rng.choice(ut_30_options)
        
        days_offset = rng.randint(0, 89)
        signing_dt = base_date - timedelta(days=days_offset)
        
        cov_num = rng.randint(1, 450)
        coverage_id = f"COV-{cov_num:05d}"
        
        sales_order_num = f"SO-{i:06d}"
        cust_id = rng.randint(100, 999)
        customer_name = f"Acme Test Enterprise {cust_id}"
        
        # ACV rounded to 2 decimal places ($10,000 to $450,000)
        acv = round(rng.uniform(10000.0, 450000.0), 2)
        country = _weighted_choice(COUNTRIES, rng)
        client_sub = _weighted_choice(CLIENT_SUB_TYPES, rng)
        sign_cat = _weighted_choice(SIGNING_CATEGORIES, rng)

        record = {
            "ut_level_30_dscr": ut_30,
            "ut_level_15_dscr": ut_15,
            "coverage_id": coverage_id,
            "signing_date": signing_dt.isoformat(),
            "sales_order_num": sales_order_num,
            "customer_name": customer_name,
            "saas_acv_usd_at_plan": f"{acv:.2f}",
            "country": country,
            "client_sub_type": client_sub,
            "signing_category": sign_cat,
        }
        records.append(record)

    return records

def inject_quality_anomalies(records: List[Dict[str, Any]], rng: random.Random) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Injects deterministic quality issues:
    1. Duplicated sales_order_num (5 orders duplicated)
    2. Missing coverage_id (10 records set to empty string)
    3. Negative or zero ACV (4 negative, 2 zero ACV records)
    """
    anomalies_log = {
        "duplicates": [],
        "missing_coverage_ids": [],
        "invalid_acv": []
    }

    # 1. Duplicates: Clone 5 existing records with modified ACVs or exact duplicates
    dup_indices = [15, 42, 88, 120, 205]
    for idx in dup_indices:
        if idx < len(records):
            dup_rec = dict(records[idx])
            records.append(dup_rec)
            anomalies_log["duplicates"].append(dup_rec["sales_order_num"])

    # 2. Missing coverage IDs
    missing_cov_indices = [7, 23, 64, 102, 145, 189, 230, 275, 310, 360]
    for idx in missing_cov_indices:
        if idx < len(records):
            records[idx]["coverage_id"] = ""
            anomalies_log["missing_coverage_ids"].append(records[idx]["sales_order_num"])

    # 3. Invalid ACV
    invalid_acv_indices = [
        (33, "-15000.00"),
        (77, "-4200.50"),
        (111, "-8900.00"),
        (190, "-25000.00"),
        (250, "0.00"),
        (320, "0.00")
    ]
    for idx, val in invalid_acv_indices:
        if idx < len(records):
            records[idx]["saas_acv_usd_at_plan"] = val
            anomalies_log["invalid_acv"].append((records[idx]["sales_order_num"], val))

    return records, anomalies_log

def create_snapshots(
    count: int = 2000,
    seed: int = DEFAULT_SEED,
    output_dir: str = "data/snapshots"
) -> Dict[str, str]:
    """
    Creates snapshot_yesterday.csv (2025-05-14) and snapshot_today.csv (2025-05-15)
    with intentional day-over-day changes:
    - Added deals in today's snapshot
    - Dropped deals from yesterday's snapshot
    - Modified ACVs
    """
    os.makedirs(output_dir, exist_ok=True)
    rng = random.Random(seed)

    # Base snapshot for today (2025-05-15)
    records_today = generate_base_records(count=count, base_date=date(2025, 5, 15), seed=seed)
    
    # Yesterday's snapshot (2025-05-14) - derived with slight changes
    records_yesterday = [dict(r) for r in records_today[: count - 20]]  # 20 deals added today
    
    # Add 10 deals that were only in yesterday (dropped today)
    for i in range(1, 11):
        dropped_deal = {
            "ut_level_30_dscr": "watsonx.data Core",
            "ut_level_15_dscr": "Data Platform",
            "coverage_id": f"COV-008{i:02d}",
            "signing_date": "2025-05-13",
            "sales_order_num": f"SO-YEST-{i:04d}",
            "customer_name": f"Dropped Acme Client {i}",
            "saas_acv_usd_at_plan": f"{55000.0 + i*1000:.2f}",
            "country": "United States",
            "client_sub_type": "Select T Activate",
            "signing_category": "New Signings",
        }
        records_yesterday.append(dropped_deal)

    # Modify ACV on 5 deals between yesterday and today
    for idx in [5, 12, 30, 45, 60]:
        if idx < len(records_yesterday):
            old_acv = float(records_yesterday[idx]["saas_acv_usd_at_plan"])
            records_yesterday[idx]["saas_acv_usd_at_plan"] = f"{old_acv * 0.85:.2f}"

    # Inject data quality anomalies into today's snapshot
    records_today, anomalies_log = inject_quality_anomalies(records_today, rng)

    fieldnames = [
        "ut_level_30_dscr", "ut_level_15_dscr", "coverage_id", "signing_date",
        "sales_order_num", "customer_name", "saas_acv_usd_at_plan", "country",
        "client_sub_type", "signing_category"
    ]

    path_yesterday = os.path.join(output_dir, "snapshot_2025-05-14.csv")
    path_today = os.path.join(output_dir, "snapshot_2025-05-15.csv")

    with open(path_yesterday, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records_yesterday)

    with open(path_today, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records_today)

    return {
        "yesterday": path_yesterday,
        "today": path_today,
        "anomalies": anomalies_log
    }

def generate_mock_sales_cloud_dataset(
    forecast_records: List[Dict[str, Any]],
    seed: int = DEFAULT_SEED
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Generates a mock Sales Cloud dataset with deterministic planted variances:
    1. Deals only in Forecast (omitted in Sales Cloud)
    2. Deals only in Sales Cloud (omitted in Forecast)
    3. Deals with ACV discrepancy
    4. Deals with Attribute mismatch (customer name, signing date, coverage ID)
    """
    rng = random.Random(seed + 100)
    sc_records = []
    
    # Identify golden deals
    golden_deals = [
        dict(r) for r in forecast_records
        if r["country"] == "United States"
        and r["client_sub_type"] == "Select T Activate"
        and r["signing_category"] == "New Signings"
        and r["ut_level_15_dscr"] == "Data Platform"
    ]

    planted_variances = {
        "only_in_forecast": [],
        "only_in_sales_cloud": [],
        "acv_mismatch": [],
        "attribute_mismatch": []
    }

    # Filter out duplicate order keys to build base map
    unique_golden = {}
    for r in golden_deals:
        if r["sales_order_num"] not in unique_golden:
            unique_golden[r["sales_order_num"]] = r

    all_golden_orders = list(unique_golden.keys())

    # 1. Only in forecast (omit 3 orders from Sales Cloud)
    omit_orders = set(all_golden_orders[:3])
    planted_variances["only_in_forecast"] = list(omit_orders)

    # 2. ACV mismatch on 3 orders
    acv_mismatch_orders = set(all_golden_orders[3:6])
    
    # 3. Attribute mismatch on 3 orders
    attr_mismatch_orders = set(all_golden_orders[6:9])

    for so_num, record in unique_golden.items():
        if so_num in omit_orders:
            continue
        sc_rec = dict(record)
        
        if so_num in acv_mismatch_orders:
            curr_acv = float(sc_rec["saas_acv_usd_at_plan"])
            new_acv = round(curr_acv + 15000.0, 2)
            sc_rec["saas_acv_usd_at_plan"] = f"{new_acv:.2f}"
            planted_variances["acv_mismatch"].append({
                "sales_order_num": so_num,
                "forecast_acv": record["saas_acv_usd_at_plan"],
                "sales_cloud_acv": sc_rec["saas_acv_usd_at_plan"],
                "delta": 15000.0
            })
            
        elif so_num in attr_mismatch_orders:
            sc_rec["customer_name"] = sc_rec["customer_name"] + " (Legal Entity Changed)"
            planted_variances["attribute_mismatch"].append({
                "sales_order_num": so_num,
                "forecast_customer": record["customer_name"],
                "sales_cloud_customer": sc_rec["customer_name"]
            })
            
        sc_records.append(sc_rec)

    # 4. Only in Sales Cloud (add 2 orders that do not exist in forecast)
    for i in range(1, 3):
        extra_order = {
            "ut_level_30_dscr": "watsonx.data Core",
            "ut_level_15_dscr": "Data Platform",
            "coverage_id": f"COV-0099{i}",
            "signing_date": "2025-05-10",
            "sales_order_num": f"SO-SC-EXTRA-{i:03d}",
            "customer_name": f"Direct Sales Cloud Client {i}",
            "saas_acv_usd_at_plan": f"{75000.0 * i:.2f}",
            "country": "United States",
            "client_sub_type": "Select T Activate",
            "signing_category": "New Signings",
        }
        sc_records.append(extra_order)
        planted_variances["only_in_sales_cloud"].append(extra_order["sales_order_num"])

    return sc_records, planted_variances

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic sales forecast data.")
    parser.add_argument("--rows", type=int, default=2000, help="Row count for base snapshot")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic random seed")
    parser.add_argument("--outdir", type=str, default="data/snapshots", help="Output directory")
    args = parser.parse_args()

    result = create_snapshots(count=args.rows, seed=args.seed, output_dir=args.outdir)
    print(f"Generated snapshots successfully in {args.outdir}:")
    print(f" - Yesterday: {result['yesterday']}")
    print(f" - Today:     {result['today']}")
    print(f" - Planted anomalies: {result['anomalies']}")
