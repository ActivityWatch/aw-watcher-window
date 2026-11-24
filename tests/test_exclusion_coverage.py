"""Exclusions must cover every field that identifies what they exclude."""

import re

from aw_watcher_window.main import transform_window
from aw_watcher_window.privacy_filter import compile_privacy_rules


def chrome_window():
    # Shape returned by printAppStatus.jxa for a browser window.
    return {
        "app": "Google Chrome",
        "title": "MyBank - Account 1234",
        "url": "https://mybank.example/accounts/1234",
        "incognito": False,
    }


def test_exclude_titles_also_drops_url():
    result = transform_window(
        chrome_window(), exclude_titles=[re.compile("mybank", re.IGNORECASE)]
    )
    assert result["title"] == "excluded"
    # The URL names the page at least as precisely as the title, and the
    # macOS swift helper already clears it for an excluded title.
    assert "url" not in result


def test_exclude_title_flag_also_drops_url():
    result = transform_window(chrome_window(), exclude_title=True)
    assert result["title"] == "excluded"
    assert "url" not in result


def test_non_matching_exclude_titles_keeps_url():
    result = transform_window(
        chrome_window(), exclude_titles=[re.compile("unrelated", re.IGNORECASE)]
    )
    assert result["url"] == "https://mybank.example/accounts/1234"


def test_exclude_apps_matches_app_before_privacy_redaction():
    rules = compile_privacy_rules(
        [
            {
                "pattern": "1Password",
                "field": "app",
                "action": "redact",
                "replacement": "secret",
            }
        ]
    )
    window = {"app": "1Password", "title": "Vault: bank login"}
    result = transform_window(
        window,
        exclude_apps=[re.compile("1Password", re.IGNORECASE)],
        privacy_filter_rules=rules,
    )
    # exclude_apps means "never logged"; redacting the app name first must
    # not let the vault title through.
    assert result is None


def test_exclude_apps_still_matches_privacy_replacement():
    rules = compile_privacy_rules(
        [
            {
                "pattern": "1Password",
                "field": "app",
                "action": "redact",
                "replacement": "Password Manager",
            }
        ]
    )
    result = transform_window(
        {"app": "1Password", "title": "Vault: bank login"},
        exclude_apps=[re.compile("^Password Manager$")],
        privacy_filter_rules=rules,
    )
    assert result is None
