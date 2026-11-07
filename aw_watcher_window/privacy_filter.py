"""
Watcher-side privacy filter: drop or redact sensitive events before sending.

Mirrors the server-side ``privacy_filters`` engine in aw-server-rust so that
sensitive data never leaves the machine in the first place.

Configure rules in ``~/.config/activitywatch/aw-watcher-window/aw-watcher-window.toml``:

.. code-block:: toml

   # Drop events whose title matches a private-browsing pattern
   [[aw-watcher-window.privacy_filter]]
   pattern = "(?i)private browsing|incognito"
   action  = "drop"

   # Redact window titles containing a banking domain
   [[aw-watcher-window.privacy_filter]]
   pattern     = "(?i)bank\\.example\\.com"
   action      = "redact"
   replacement = "REDACTED"   # optional; defaults to "excluded"

   # Rewrite only Firefox titles, stripping the browser suffix and unread counters
   [[aw-watcher-window.privacy_filter]]
   pattern     = "( - Mozilla Firefox|\\(\\d+\\+?\\)\\s*)$"
   action      = "rewrite"
   replacement = ""
   app         = "firefox"

Rule fields:
  pattern     -- Python ``re`` regex applied to the target field value.
  field       -- Window-event field to match against (default: ``"title"``).
  action      -- ``"drop"`` (discard the event), ``"redact"`` (replace the whole
                 value) or ``"rewrite"`` (apply ``pattern.sub(replacement, value)``
                 so the rest of the value survives).
  replacement -- Replacement string for ``"redact"`` (default: ``"excluded"``).
                 Required and may be empty for ``"rewrite"``.
  app         -- Optional application scope: the rule only touches events whose
                 ``app`` field matches exactly (case-insensitive).

macOS note: the default ``swift`` strategy cannot apply these rules (it
sends heartbeats from a separate binary). The watcher refuses to start
under ``--strategy swift`` when any rule is configured, so titles are not
leaked. Use ``--strategy jxa`` or ``--strategy applescript`` on macOS.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_VALID_ACTIONS = frozenset({"drop", "redact", "rewrite"})


def compile_privacy_rules(raw_rules: list) -> list:
    """Validate and compile regex patterns in privacy filter rules.

    Returns a list of compiled rule dicts ready for :func:`apply_privacy_filters`.
    Invalid rules (bad regex or unknown action) are skipped with an error log.
    """
    compiled = []
    for raw in raw_rules:
        if not isinstance(raw, dict):
            logger.error("privacy_filter rule is not a table: %r — skipped", raw)
            continue

        pattern_str = raw.get("pattern", "")
        if not pattern_str:
            logger.error("privacy_filter rule missing 'pattern' — skipped: %r", raw)
            continue

        try:
            pattern = re.compile(pattern_str)
        except (re.error, TypeError) as exc:
            logger.error(
                "privacy_filter: invalid regex %r — %s — rule skipped", pattern_str, exc
            )
            continue

        action = raw.get("action", "redact")
        if action not in _VALID_ACTIONS:
            logger.error(
                "privacy_filter: unknown action %r (expected one of %s) — rule skipped",
                action,
                "/".join(sorted(_VALID_ACTIONS)),
            )
            continue

        app = raw.get("app")
        if app is not None and (not isinstance(app, str) or not app):
            logger.error(
                "privacy_filter: 'app' must be a non-empty string — rule skipped: %r",
                raw,
            )
            continue

        field = raw.get("field", "title")
        if not isinstance(field, str) or not field:
            logger.error(
                "privacy_filter: 'field' must be a non-empty string — rule skipped: %r",
                raw,
            )
            continue

        if action == "rewrite":
            # A rewrite must be explicit: the "excluded" default would delete
            # the matched value instead of substituting it.
            replacement = raw.get("replacement")
            if not isinstance(replacement, str):
                logger.error(
                    "privacy_filter: 'rewrite' action requires a string "
                    "'replacement' (may be empty) — rule skipped: %r",
                    raw,
                )
                continue
        else:
            replacement = raw.get("replacement", "excluded")
            if not isinstance(replacement, str):
                logger.error(
                    "privacy_filter: 'replacement' must be a string — rule skipped: %r",
                    raw,
                )
                continue

        compiled.append(
            {
                "pattern": pattern,
                "field": field,
                "action": action,
                "replacement": replacement,
                "app": app,
            }
        )
    return compiled


def apply_privacy_filters(window: dict, rules: list) -> Optional[dict]:
    """Apply compiled privacy filter rules to a window event.

    Returns ``None`` when the event should be dropped entirely, otherwise a
    (possibly modified) copy of the window dict. Never mutates the input.
    """
    if not rules:
        return window

    result = dict(window)
    for rule in rules:
        field = rule["field"]
        value = result.get(field)
        if not isinstance(value, str):
            continue
        app = rule.get("app")
        if app is not None:
            event_app = result.get("app")
            if not isinstance(event_app, str) or event_app.lower() != app.lower():
                continue
        if rule["action"] == "rewrite":
            if rule["pattern"].search(value):
                logger.debug(
                    "privacy_filter: rewriting field=%r matched %r",
                    field,
                    rule["pattern"].pattern,
                )
                result[field] = rule["pattern"].sub(rule["replacement"], value)
            continue
        if rule["pattern"].search(value):
            if rule["action"] == "drop":
                logger.debug(
                    "privacy_filter: dropping event (field=%r matched %r)",
                    field,
                    rule["pattern"].pattern,
                )
                return None
            else:  # redact
                logger.debug(
                    "privacy_filter: redacting field=%r matched %r",
                    field,
                    rule["pattern"].pattern,
                )
                result[field] = rule["replacement"]
    return result
