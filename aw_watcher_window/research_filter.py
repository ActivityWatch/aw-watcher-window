"""
Research Edition: privacy-sensitive window-title → category transform.

Replicates the approach used by AW research forks:
- Browser apps: window titles get classified into study categories.
  Unmatched titles → 'excluded'.
- Non-browser apps: title is dropped entirely (only app name recorded).

Enable via config (``research_enabled = true``) and optionally supply a category
map in ``[aw-watcher-window.research_category_map]``.  If the map is empty,
browser titles are classified as ``excluded`` and non-browser titles are still
dropped.

macOS note: on macOS the default ``swift`` strategy captures browser URLs via
accessibility APIs and includes them in the window dict.  This filter uses those
URLs for more reliable category classification (``classify_title`` prefers URL
over title) and strips them from the output before the event is recorded.
"""

from typing import Optional

# Known browser applications (lowercase, for case-insensitive matching)
BROWSER_APPS = frozenset(
    {
        "chrome",
        "google chrome",
        "google chrome canary",
        "google-chrome",
        "google-chrome-beta",
        "google-chrome-unstable",
        "chromium",
        "chromium-browser",
        "brave browser",
        "brave",
        "brave-browser",
        "firefox",
        "firefox developer edition",
        "firefox-esr",
        "safari",
        "edge",
        "microsoft edge",
        "microsoft-edge",
        "microsoft-edge-beta",
        "microsoft-edge-dev",
        "opera",
        "chrome.exe",
        "brave.exe",
        "firefox.exe",
        "msedge.exe",
        "opera.exe",
    }
)


def is_browser(app: str) -> bool:
    """Return True if *app* is a known browser (case-insensitive)."""
    return app.strip().lower() in BROWSER_APPS


def classify_title(title: str, category_map: dict, url: str = "") -> str:
    """
    Classify a browser window into a study category via substring matching.

    Tries *url* first when provided (more reliable than page titles, which can
    change mid-load), then falls back to *title*.
    *category_map*: ``{substring: category_name}`` — first matching substring wins.
    Returns the category name, or ``"excluded"`` if nothing matched.
    """
    if url:
        url_lower = url.lower()
        for pattern, category in category_map.items():
            if pattern.lower() in url_lower:
                return category
    title_lower = title.lower()
    for pattern, category in category_map.items():
        if pattern.lower() in title_lower:
            return category
    return "excluded"


def transform(window: dict, category_map: Optional[dict]) -> dict:
    """
    Apply Research Edition transforms to a window-data dict.

    *window*: ``{"app": str, "title": str}`` (may also carry *url*,
    *incognito* on macOS JXA — URLs are stripped and incognito is preserved).
    *category_map*: study-specific mapping dict, or ``None`` to no-op.

    Returns the transformed window dict (never mutates the input).
    """
    if category_map is None:
        return window

    app = window.get("app", "")

    if is_browser(app):
        # Browser: replace title with a study category
        title = window.get("title", "")
        url = window.get("url", "")
        category = classify_title(title, category_map, url=url)
        # Don't spread window dict — URLs must not be exposed for privacy
        result = {"app": app, "title": category}
        # Preserve incognito flag if present (metadata, not a privacy concern)
        if "incognito" in window:
            result["incognito"] = window["incognito"]
        return result
    else:
        # Non-browser: drop the title entirely (only app name recorded)
        result = {"app": app}
        # Preserve incognito flag if present (metadata, not a privacy concern)
        # Note: URL is NOT preserved for non-browser apps — on macOS JXA,
        # apps like Mail or file managers can expose sensitive URLs (mailbox://, file://)
        if "incognito" in window:
            result["incognito"] = window["incognito"]
        return result
