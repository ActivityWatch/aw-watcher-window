"""Tests for aw-watcher-window Research Edition filter."""

import unittest

from aw_watcher_window.research_filter import (
    BROWSER_APPS,
    classify_app,
    classify_title,
    is_browser,
    transform,
)


class TestIsBrowser(unittest.TestCase):
    def test_known_browsers(self):
        for app in BROWSER_APPS:
            self.assertTrue(is_browser(app), f"{app!r} should be a browser")

    def test_case_insensitive(self):
        for app in (
            "Chrome",
            "GOOGLE CHROME",
            "Google-chrome",
            "Firefox",
            "Safari",
            "Edge",
            "Microsoft Edge",
        ):
            self.assertTrue(is_browser(app), f"{app!r} should be a browser")

    def test_linux_wm_class_browser_names(self):
        for app in (
            "Google-chrome",
            "Brave-browser",
            "Chromium-browser",
            "Microsoft-edge",
        ):
            self.assertTrue(is_browser(app), f"{app!r} should be a browser")

    def test_non_browsers(self):
        for app in ("Slack", "Terminal", "iTerm2", "Code", "zoom.us", ""):
            self.assertFalse(is_browser(app), f"{app!r} should not be a browser")


class TestClassifyTitle(unittest.TestCase):
    CATEGORY_MAP = {
        "youtube": "Youtube",
        "facebook": "Facebook",
        "twitter": "Twitter",
        "reddit": "Forums & Blogs",
        "gmail": "Email",
        "outlook": "Email",
    }

    def test_exact_substring_match(self):
        self.assertEqual(
            classify_title("YouTube - Google Chrome", self.CATEGORY_MAP),
            "Youtube",
        )

    def test_case_insensitive_match(self):
        self.assertEqual(
            classify_title("YOUTUBE - Mozilla Firefox", self.CATEGORY_MAP),
            "Youtube",
        )

    def test_title_with_notification_prefix(self):
        self.assertEqual(
            classify_title("Facebook (1) Notification - Brave Browser", self.CATEGORY_MAP),
            "Facebook",
        )

    def test_no_match_returns_excluded(self):
        self.assertEqual(
            classify_title("systemd (SYSTEM) - man", self.CATEGORY_MAP),
            "excluded",
        )

    def test_first_match_wins(self):
        # Both "facebook" and "twitter" present — first pattern in iteration wins
        result = classify_title("Facebook Twitter integration - Chrome", self.CATEGORY_MAP)
        self.assertEqual(result, "Facebook")

    def test_empty_title(self):
        self.assertEqual(classify_title("", self.CATEGORY_MAP), "excluded")

    def test_url_matches_when_title_does_not(self):
        # URL is used for classification when title gives no match
        result = classify_title("New Tab", self.CATEGORY_MAP, url="https://youtube.com/watch?v=abc")
        self.assertEqual(result, "Youtube")

    def test_url_takes_priority_over_title(self):
        # URL match wins even when title would match a different category
        result = classify_title("Gmail - Google", self.CATEGORY_MAP, url="https://youtube.com/")
        self.assertEqual(result, "Youtube")

    def test_url_fallback_to_title(self):
        # If URL doesn't match any pattern, title is used
        result = classify_title("Facebook - Social", self.CATEGORY_MAP, url="https://example.com/unrelated")
        self.assertEqual(result, "Facebook")

    def test_url_case_insensitive(self):
        result = classify_title("", self.CATEGORY_MAP, url="HTTPS://YOUTUBE.COM/WATCH")
        self.assertEqual(result, "Youtube")


class TestTransform(unittest.TestCase):
    CATEGORY_MAP = {
        "youtube": "Youtube",
        "facebook": "Facebook",
    }

    def test_no_category_map_returns_unchanged(self):
        window = {"app": "Chrome", "title": "YouTube - Chrome"}
        self.assertEqual(transform(window, None), window)

    def test_empty_category_map_excludes_browser_title(self):
        window = {"app": "Chrome", "title": "YouTube - Chrome"}
        self.assertEqual(transform(window, {}), {"app": "Chrome", "title": "excluded"})

    def test_empty_category_map_still_drops_non_browser_title(self):
        window = {"app": "Terminal", "title": "bash"}
        self.assertEqual(transform(window, {}), {"app": "Terminal"})

    def test_browser_title_classified(self):
        window = {"app": "Chrome", "title": "YouTube - Chrome"}
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["app"], "Chrome")
        self.assertEqual(result["title"], "Youtube")

    def test_browser_title_excluded_when_no_match(self):
        window = {"app": "Firefox", "title": "Vim documentation"}
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["app"], "Firefox")
        self.assertEqual(result["title"], "excluded")

    def test_non_browser_drops_title(self):
        window = {"app": "iTerm2", "title": "~/projects/foo"}
        result = transform(window, self.CATEGORY_MAP)
        self.assertNotIn("title", result)
        self.assertEqual(result["app"], "iTerm2")

    def test_non_browser_strips_url_but_preserves_incognito(self):
        # Privacy fix: non-browser URLs must be stripped to prevent leaking sensitive
        # file paths or email URLs (file://, mailbox://); incognito flag is non-sensitive
        window = {
            "app": "Finder",
            "title": "Documents",
            "url": "file:///Users/jdoe/sensitive-folder/",
            "incognito": False,
        }
        result = transform(window, self.CATEGORY_MAP)
        self.assertNotIn("title", result)
        self.assertEqual(result["app"], "Finder")
        self.assertNotIn("url", result, "Non-browser URLs must be stripped for privacy")
        self.assertEqual(result["incognito"], False)

    def test_browser_strips_url_but_preserves_incognito(self):
        # Privacy fix: browser URLs must be stripped to prevent leaking search queries
        # and auth tokens; incognito flag is non-sensitive metadata and can be preserved
        window = {
            "app": "Chrome",
            "title": "YouTube - Google Chrome",
            "url": "https://youtube.com/search?q=secret",
            "incognito": False,
        }
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["title"], "Youtube")
        self.assertNotIn("url", result, "Browser URLs must be stripped for privacy")
        self.assertEqual(result["incognito"], False)

    def test_non_browser_minimal(self):
        window = {"app": "Terminal", "title": "bash"}
        self.assertEqual(transform(window, self.CATEGORY_MAP), {"app": "Terminal"})

    def test_browser_with_leading_trailing_spaces_in_app(self):
        window = {"app": "  Brave Browser  ", "title": "Facebook"}
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["title"], "Facebook")

    def test_linux_browser_wm_class_title_classified(self):
        for app in ("Google-chrome", "Brave-browser"):
            with self.subTest(app=app):
                window = {"app": app, "title": "YouTube"}
                result = transform(window, self.CATEGORY_MAP)
                self.assertEqual(result["app"], app)
                self.assertEqual(result["title"], "Youtube")

    def test_input_not_mutated(self):
        window = {"app": "Chrome", "title": "YouTube - Chrome"}
        original = dict(window)
        transform(window, self.CATEGORY_MAP)
        self.assertEqual(window, original)

    def test_browser_url_used_for_classification(self):
        # URL is used for classification when title doesn't match (Swift advantage)
        window = {
            "app": "Safari",
            "title": "New Tab",  # generic title — won't match
            "url": "https://youtube.com/watch?v=abc123",
        }
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["title"], "Youtube")
        self.assertNotIn("url", result)

    def test_browser_url_takes_priority_over_title(self):
        # URL match takes precedence over title match
        window = {
            "app": "Chrome",
            "title": "Facebook - Home",
            "url": "https://youtube.com/",
        }
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["title"], "Youtube")
        self.assertNotIn("url", result)


class TestClassifyApp(unittest.TestCase):
    APP_CATEGORY_MAP = {
        "microsoft outlook": "Email",
        "outlook.exe": "Email",
        "microsoft teams": "Work & Productivity",
        "teams": "Work & Productivity",
        "spotify": "Music & Audio",
        "finder": "Excluded",
        "steam": "Games",
    }

    def test_exact_match(self):
        self.assertEqual(classify_app("Microsoft Outlook", self.APP_CATEGORY_MAP), "Email")

    def test_case_insensitive(self):
        self.assertEqual(classify_app("SPOTIFY", self.APP_CATEGORY_MAP), "Music & Audio")
        self.assertEqual(classify_app("spotify", self.APP_CATEGORY_MAP), "Music & Audio")
        self.assertEqual(classify_app("Spotify", self.APP_CATEGORY_MAP), "Music & Audio")

    def test_exe_suffix(self):
        self.assertEqual(classify_app("outlook.exe", self.APP_CATEGORY_MAP), "Email")

    def test_unmapped_returns_excluded(self):
        self.assertEqual(classify_app("iTerm2", self.APP_CATEGORY_MAP), "Excluded")
        self.assertEqual(classify_app("Terminal", self.APP_CATEGORY_MAP), "Excluded")
        self.assertEqual(classify_app("", self.APP_CATEGORY_MAP), "Excluded")

    def test_leading_trailing_spaces(self):
        self.assertEqual(classify_app("  Spotify  ", self.APP_CATEGORY_MAP), "Music & Audio")

    def test_explicit_excluded_entry(self):
        # "Finder" is explicitly mapped to "Excluded" in Matthias's map
        self.assertEqual(classify_app("Finder", self.APP_CATEGORY_MAP), "Excluded")

    def test_empty_map_returns_excluded(self):
        self.assertEqual(classify_app("Spotify", {}), "Excluded")


class TestTransformWithAppMap(unittest.TestCase):
    CATEGORY_MAP = {
        "youtube": "Video Streaming",
        "facebook": "Social Networking",
    }
    APP_CATEGORY_MAP = {
        "microsoft outlook": "Email",
        "microsoft teams": "Work & Productivity",
        "spotify": "Music & Audio",
        "finder": "Excluded",
    }

    def test_non_browser_mapped_to_category(self):
        window = {"app": "Microsoft Outlook", "title": "Inbox — johndoe@example.com"}
        result = transform(window, self.CATEGORY_MAP, self.APP_CATEGORY_MAP)
        self.assertEqual(result["app"], "Microsoft Outlook")
        self.assertEqual(result["title"], "Email")

    def test_non_browser_unmapped_returns_excluded(self):
        window = {"app": "iTerm2", "title": "~/projects/secret"}
        result = transform(window, self.CATEGORY_MAP, self.APP_CATEGORY_MAP)
        self.assertEqual(result["app"], "iTerm2")
        self.assertEqual(result["title"], "Excluded")

    def test_non_browser_title_and_url_stripped(self):
        # Title is replaced by category; sensitive URL must not leak
        window = {
            "app": "Microsoft Outlook",
            "title": "Private inbox",
            "url": "mailbox://private@corp.example.com/INBOX",
        }
        result = transform(window, self.CATEGORY_MAP, self.APP_CATEGORY_MAP)
        self.assertEqual(result["title"], "Email")
        self.assertNotIn("url", result)

    def test_non_browser_incognito_preserved(self):
        window = {"app": "Spotify", "title": "Now playing: Secret Playlist", "incognito": True}
        result = transform(window, self.CATEGORY_MAP, self.APP_CATEGORY_MAP)
        self.assertEqual(result["title"], "Music & Audio")
        self.assertEqual(result["incognito"], True)

    def test_browser_unaffected_by_app_map(self):
        # Browser classification should not change even when an app map is present
        window = {"app": "Chrome", "title": "YouTube - Chrome"}
        result = transform(window, self.CATEGORY_MAP, self.APP_CATEGORY_MAP)
        self.assertEqual(result["title"], "Video Streaming")

    def test_no_app_map_legacy_behaviour(self):
        # Without app map, non-browser keeps raw app name and drops title (backward compat)
        window = {"app": "Microsoft Outlook", "title": "Inbox"}
        result = transform(window, self.CATEGORY_MAP, None)
        self.assertEqual(result["app"], "Microsoft Outlook")
        self.assertNotIn("title", result)

    def test_explicit_excluded_mapped_app(self):
        # "Finder" → "Excluded" (explicit map entry, not a lookup miss)
        window = {"app": "Finder", "title": "/Users/jdoe/Documents"}
        result = transform(window, self.CATEGORY_MAP, self.APP_CATEGORY_MAP)
        self.assertEqual(result["title"], "Excluded")

    def test_input_not_mutated_with_app_map(self):
        window = {"app": "Spotify", "title": "Now playing"}
        original = dict(window)
        transform(window, self.CATEGORY_MAP, self.APP_CATEGORY_MAP)
        self.assertEqual(window, original)


if __name__ == "__main__":
    unittest.main()
