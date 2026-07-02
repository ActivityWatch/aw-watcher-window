import sys

from aw_watcher_window import config as config_module


def test_parse_args_attaches_research_category_map(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: {
            "exclude_title": False,
            "exclude_titles": [],
            "poll_time": 1.0,
            "strategy_macos": "swift",
            "research_enabled": True,
            "research_category_map": {"youtube": "Entertainment"},
        },
    )
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window"])

    args = config_module.parse_args()

    assert args.research_category_map == {"youtube": "Entertainment"}
