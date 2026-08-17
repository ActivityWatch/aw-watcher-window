"""
Research Edition: privacy-sensitive window-title → category transform.

Replicates the approach used by AW research forks:
- Browser apps: window titles get classified into study categories.
  Unmatched titles → 'excluded'.
- Non-browser apps: app name is mapped to a broad study category where
  possible, otherwise replaced with 'Excluded'.  Supply the mapping in
  ``[aw-watcher-window.research_app_category_map]``.  Without a map the
  previous behaviour is preserved (app name kept, title dropped).

Enable via config (``research_enabled = true``) and optionally supply a
category map in ``[aw-watcher-window.research_category_map]``.  If the map
is empty, browser titles are classified as ``excluded`` and non-browser
behaviour falls back to title-drop.

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


def classify_app(app: str, app_category_map: dict) -> str:
    """
    Classify a non-browser application into a study category.

    Performs a case-insensitive exact lookup of *app* in *app_category_map*
    (``{app_name: category_name}``).  Both the lookup key and the configured
    keys are normalized to lowercase, so mixed-case map keys (e.g. ``"Microsoft
    Outlook"``) match their lowercase application names.  Returns the mapped
    category, or ``"Excluded"`` when the app is not in the map.

    Note: uses capital-E ``"Excluded"`` to match Matthias's original classifier
    convention (``EXCLUDED = "Excluded"``), distinct from the lowercase
    ``"excluded"`` used for browser title mismatches.
    """
    app_lower = app.strip().lower()
    for map_app, category in app_category_map.items():
        if map_app.strip().lower() == app_lower:
            return category
    return "Excluded"


def transform(
    window: dict,
    category_map: Optional[dict],
    app_category_map: Optional[dict] = None,
) -> dict:
    """
    Apply Research Edition transforms to a window-data dict.

    *window*: ``{"app": str, "title": str}`` (may also carry *url*,
    *incognito* on macOS JXA — URLs are stripped and incognito is preserved).
    *category_map*: study-specific URL/title mapping dict, or ``None`` to no-op.
    *app_category_map*: optional app-name → category mapping for non-browser
    apps.  When supplied, non-browser apps are replaced with their mapped
    category (or ``"Excluded"`` if unmapped) instead of keeping the raw app name.

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
        # Non-browser: map app to a study category when a map is provided,
        # otherwise keep the raw app name and drop the title.
        # An empty map is treated as "not provided" — so research_enabled with
        # no configured app map falls back to legacy behaviour instead of
        # classifying every non-browser app as "Excluded".
        if app_category_map:
            app_category = classify_app(app, app_category_map)
            # Replace the raw app identity with its category: the app name is
            # the sensitive identifier for non-browser apps (e.g. "Microsoft
            # Outlook", a niche tool, a company-internal app), so it must not
            # be retained. Title/URL are dropped entirely.
            result = {"app": app_category}
        else:
            # Legacy behaviour: title dropped, app name kept as-is.
            result = {"app": app}
        # Preserve incognito flag if present (metadata, not a privacy concern)
        # Note: URL is NOT preserved for non-browser apps — on macOS JXA,
        # apps like Mail or file managers can expose sensitive URLs (mailbox://, file://)
        if "incognito" in window:
            result["incognito"] = window["incognito"]
        return result
