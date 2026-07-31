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

Rule fields:
  pattern     -- Python ``re`` regex applied to the target field value.
  field       -- Window-event field to match against (default: ``"title"``).
  action      -- ``"drop"`` (discard the event) or ``"redact"`` (replace the value).
  replacement -- Replacement string for ``"redact"`` action (default: ``"excluded"``).

macOS note: the default ``swift`` strategy bypasses this Python transform.
Use ``--strategy jxa`` or ``--strategy applescript`` if watcher-side privacy
filtering is required on macOS.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_VALID_ACTIONS = frozenset({"drop", "redact"})


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
                "privacy_filter: unknown action %r (expected 'drop' or 'redact') — rule skipped",
                action,
            )
            continue

        compiled.append(
            {
                "pattern": pattern,
                "field": raw.get("field", "title"),
                "action": action,
                "replacement": raw.get("replacement", "excluded"),
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
