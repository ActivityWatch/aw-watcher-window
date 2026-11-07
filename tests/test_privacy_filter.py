"""Tests for the watcher-side privacy filter."""

import pytest

from aw_watcher_window.privacy_filter import apply_privacy_filters, compile_privacy_rules


# ---------------------------------------------------------------------------
# compile_privacy_rules
# ---------------------------------------------------------------------------


def test_compile_empty_rules():
    assert compile_privacy_rules([]) == []


def test_compile_valid_drop_rule():
    rules = compile_privacy_rules(
        [{"pattern": "(?i)incognito", "action": "drop"}]
    )
    assert len(rules) == 1
    assert rules[0]["action"] == "drop"
    assert rules[0]["field"] == "title"
    assert rules[0]["replacement"] == "excluded"


def test_compile_valid_redact_rule():
    rules = compile_privacy_rules(
        [{"pattern": "bank", "action": "redact", "replacement": "REDACTED", "field": "title"}]
    )
    assert len(rules) == 1
    assert rules[0]["replacement"] == "REDACTED"


def test_compile_defaults_to_redact():
    rules = compile_privacy_rules([{"pattern": "secret"}])
    assert rules[0]["action"] == "redact"


def test_compile_invalid_regex_skipped():
    rules = compile_privacy_rules([{"pattern": "[invalid(", "action": "drop"}])
    assert rules == []


def test_compile_non_string_pattern_skipped():
    rules = compile_privacy_rules([{"pattern": 123, "action": "drop"}])
    assert rules == []


def test_compile_unknown_action_skipped():
    rules = compile_privacy_rules([{"pattern": "foo", "action": "transform"}])
    assert rules == []


def test_compile_missing_pattern_skipped():
    rules = compile_privacy_rules([{"action": "drop"}])
    assert rules == []


def test_compile_non_dict_skipped():
    rules = compile_privacy_rules(["not a dict"])
    assert rules == []


def test_compile_non_string_field_skipped():
    rules = compile_privacy_rules(
        [{"pattern": "bank", "action": "redact", "field": 123}]
    )
    assert rules == []


def test_compile_non_string_replacement_skipped():
    rules = compile_privacy_rules(
        [{"pattern": "bank", "action": "redact", "replacement": 123}]
    )
    assert rules == []


def test_compile_multiple_rules():
    raw = [
        {"pattern": "incognito", "action": "drop"},
        {"pattern": "bank", "action": "redact"},
    ]
    compiled = compile_privacy_rules(raw)
    assert len(compiled) == 2


# ---------------------------------------------------------------------------
# apply_privacy_filters
# ---------------------------------------------------------------------------


@pytest.fixture
def drop_rule():
    return compile_privacy_rules(
        [{"pattern": "(?i)private browsing|incognito", "action": "drop"}]
    )


@pytest.fixture
def redact_rule():
    return compile_privacy_rules(
        [{"pattern": "(?i)bank", "action": "redact", "replacement": "REDACTED"}]
    )


def test_no_rules_passes_through():
    window = {"app": "Firefox", "title": "Incognito Window"}
    assert apply_privacy_filters(window, []) == window


def test_drop_matching_event(drop_rule):
    window = {"app": "Firefox", "title": "Private Browsing - Mozilla Firefox"}
    result = apply_privacy_filters(window, drop_rule)
    assert result is None


def test_drop_case_insensitive(drop_rule):
    window = {"app": "Chrome", "title": "incognito"}
    result = apply_privacy_filters(window, drop_rule)
    assert result is None


def test_drop_non_matching_passes_through(drop_rule):
    window = {"app": "Firefox", "title": "Hacker News"}
    result = apply_privacy_filters(window, drop_rule)
    assert result == window


def test_redact_matching_title(redact_rule):
    window = {"app": "Chrome", "title": "My Bank - Dashboard"}
    result = apply_privacy_filters(window, redact_rule)
    assert result is not None
    assert result["title"] == "REDACTED"
    assert result["app"] == "Chrome"


def test_redact_default_replacement():
    rules = compile_privacy_rules([{"pattern": "secret", "action": "redact"}])
    window = {"app": "Terminal", "title": "secret notes"}
    result = apply_privacy_filters(window, rules)
    assert result["title"] == "excluded"


def test_redact_does_not_mutate_input(redact_rule):
    window = {"app": "Chrome", "title": "bankofamerica.com"}
    original_title = window["title"]
    apply_privacy_filters(window, redact_rule)
    assert window["title"] == original_title


def test_drop_does_not_mutate_input(drop_rule):
    window = {"app": "Firefox", "title": "Private Browsing"}
    original = dict(window)
    apply_privacy_filters(window, drop_rule)
    assert window == original


def test_field_not_present_skips_rule(redact_rule):
    window = {"app": "Terminal"}  # no 'title' field
    result = apply_privacy_filters(window, redact_rule)
    assert result == window


def test_non_string_field_skipped():
    rules = compile_privacy_rules([{"pattern": "123", "action": "drop", "field": "count"}])
    window = {"app": "Foo", "title": "bar", "count": 123}
    result = apply_privacy_filters(window, rules)
    assert result is not None  # non-string field value: rule skipped


def test_multiple_rules_first_drop_wins():
    rules = compile_privacy_rules(
        [
            {"pattern": "drop_me", "action": "drop"},
            {"pattern": "drop_me", "action": "redact"},
        ]
    )
    window = {"app": "App", "title": "drop_me now"}
    assert apply_privacy_filters(window, rules) is None


def test_multiple_rules_redact_then_drop():
    rules = compile_privacy_rules(
        [
            {"pattern": "bank", "action": "redact", "replacement": "REDACTED"},
            {"pattern": "REDACTED", "action": "drop"},
        ]
    )
    window = {"app": "Chrome", "title": "my bank account"}
    # First rule redacts "bank" → "REDACTED"; second drops "REDACTED"
    assert apply_privacy_filters(window, rules) is None


def test_custom_field():
    rules = compile_privacy_rules(
        [{"pattern": "(?i)messenger", "action": "drop", "field": "app"}]
    )
    window = {"app": "Facebook Messenger", "title": "Chat"}
    assert apply_privacy_filters(window, rules) is None


def test_custom_field_does_not_affect_title():
    rules = compile_privacy_rules(
        [{"pattern": "(?i)messenger", "action": "drop", "field": "app"}]
    )
    window = {"app": "Terminal", "title": "messenger in title"}
    # app doesn't match; rule scoped to 'app' field
    assert apply_privacy_filters(window, rules) == window


# ---------------------------------------------------------------------------
# rewrite action (alternative to redact, for partial title cleanup)
# ---------------------------------------------------------------------------


@pytest.fixture
def rewrite_rule():
    return compile_privacy_rules(
        [
            {
                "pattern": r" - Mozilla Firefox$",
                "action": "rewrite",
                "replacement": "",
                "app": "Firefox",
            }
        ]
    )


def test_compile_rewrite_rule():
    rules = compile_privacy_rules(
        [{"pattern": r"\(\d+\)\s*", "action": "rewrite", "replacement": ""}]
    )
    assert len(rules) == 1
    assert rules[0]["action"] == "rewrite"
    assert rules[0]["replacement"] == ""
    assert rules[0]["app"] is None


def test_compile_rewrite_requires_replacement():
    # "excluded" would delete the matched text instead of substituting it, so a
    # rewrite with no explicit replacement is rejected rather than defaulted.
    assert compile_privacy_rules([{"pattern": "x", "action": "rewrite"}]) == []


def test_compile_rewrite_rejects_bad_app():
    assert (
        compile_privacy_rules(
            [{"pattern": "x", "action": "rewrite", "replacement": "", "app": 3}]
        )
        == []
    )


def test_rewrite_replaces_only_the_match(rewrite_rule):
    window = {"app": "Firefox", "title": "GitHub - Mozilla Firefox"}
    result = apply_privacy_filters(window, rewrite_rule)
    assert result is not None
    assert result["title"] == "GitHub"
    assert result["app"] == "Firefox"


def test_rewrite_strips_unread_counter():
    rules = compile_privacy_rules(
        [{"pattern": r"^\(\d+\+?\)\s*", "action": "rewrite", "replacement": ""}]
    )
    window = {"app": "Thunderbird", "title": "(3) Inbox - work"}
    result = apply_privacy_filters(window, rules)
    assert result is not None
    assert result["title"] == "Inbox - work"


def test_rewrite_respects_app_scope(rewrite_rule):
    window = {"app": "Chromium", "title": "GitHub - Mozilla Firefox"}
    result = apply_privacy_filters(window, rewrite_rule)
    assert result == window


def test_rewrite_app_scope_is_case_insensitive(rewrite_rule):
    window = {"app": "firefox", "title": "Docs - Mozilla Firefox"}
    result = apply_privacy_filters(window, rewrite_rule)
    assert result is not None
    assert result["title"] == "Docs"


def test_rewrite_without_app_scope_applies_everywhere():
    rules = compile_privacy_rules(
        [{"pattern": r" - Mozilla Firefox$", "action": "rewrite", "replacement": ""}]
    )
    window = {"app": "Chromium", "title": "Docs - Mozilla Firefox"}
    result = apply_privacy_filters(window, rules)
    assert result is not None
    assert result["title"] == "Docs"


def test_rewrite_non_matching_passes_through(rewrite_rule):
    window = {"app": "Firefox", "title": "Hacker News"}
    assert apply_privacy_filters(window, rewrite_rule) == window


def test_rewrite_never_drops_or_redacts():
    rules = compile_privacy_rules(
        [{"pattern": "bank", "action": "rewrite", "replacement": "BANK"}]
    )
    window = {"app": "Chrome", "title": "bank statement"}
    result = apply_privacy_filters(window, rules)
    assert result is not None
    assert result["title"] == "BANK statement"


def test_rewrite_input_not_mutated(rewrite_rule):
    window = {"app": "Firefox", "title": "GitHub - Mozilla Firefox"}
    apply_privacy_filters(window, rewrite_rule)
    assert window["title"] == "GitHub - Mozilla Firefox"
