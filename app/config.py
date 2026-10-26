import os
import yaml
from typing import Dict, Any

DEFAULT_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

def get_rules_config(config_path: str = None) -> Dict[str, Any]:
    if not config_path:
        config_path = os.path.join(DEFAULT_CONFIG_DIR, "rules.yaml")
    if not os.path.exists(config_path):
        return {
            "filters": {
                "country": "United States",
                "client_sub_type": "Select T Activate",
                "signing_category": "New Signings",
                "ut_level_15_dscr": "Data Platform"
            },
            "quality": {"swing_threshold_pct": 25.0}
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_settings_config(config_path: str = None) -> Dict[str, Any]:
    if not config_path:
        config_path = os.path.join(DEFAULT_CONFIG_DIR, "settings.yaml")
    if not os.path.exists(config_path):
        return {
            "app": {
                "host": "127.0.0.1",
                "port": 8000,
                "database_url": "sqlite:///./data/forecast.db",
                "outbox_dir": "./outbox",
                "snapshots_dir": "./data/snapshots"
            },
            "scheduler": {
                "enabled": True,
                "interval_seconds": 86400
            },
            "sales_cloud": {
                "enabled": False,
                "mock_enabled": True,
                "per_order_tolerance_usd": 0.01,
                "block_on_mismatch": False,
                "max_retries": 3,
                "retry_backoff_seconds": 1.0,
                "retry_backoff_multiplier": 2.0
            }
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
