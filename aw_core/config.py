from typing import Dict

def load_config_toml(name: str, default=None) -> Dict[str, Dict]:
    return {
        name: {
            "exclude_title": False,
            "exclude_titles": [],
            "poll_time": 1.0,
        }
    }
