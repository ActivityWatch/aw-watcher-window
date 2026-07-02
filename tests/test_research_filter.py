"""Tests for aw-watcher-window Research Edition filter."""

import unittest

from aw_watcher_window.research_filter import (
    BROWSER_APPS,
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
            "Firefox",
            "Safari",
            "Edge",
            "Microsoft Edge",
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

    def test_non_browser_preserves_extra_fields(self):
        window = {"app": "Finder", "title": "Documents", "url": "file:///Users/"}
        result = transform(window, self.CATEGORY_MAP)
        self.assertNotIn("title", result)
        self.assertEqual(result["app"], "Finder")
        self.assertEqual(result["url"], "file:///Users/")

    def test_browser_preserves_url_and_incognito(self):
        window = {
            "app": "Chrome",
            "title": "YouTube - Google Chrome",
            "url": "https://youtube.com",
            "incognito": False,
        }
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["title"], "Youtube")
        self.assertEqual(result["url"], "https://youtube.com")
        self.assertEqual(result["incognito"], False)

    def test_non_browser_minimal(self):
        window = {"app": "Terminal", "title": "bash"}
        self.assertEqual(transform(window, self.CATEGORY_MAP), {"app": "Terminal"})

    def test_browser_with_leading_trailing_spaces_in_app(self):
        window = {"app": "  Brave Browser  ", "title": "Facebook"}
        result = transform(window, self.CATEGORY_MAP)
        self.assertEqual(result["title"], "Facebook")

    def test_input_not_mutated(self):
        window = {"app": "Chrome", "title": "YouTube - Chrome"}
        original = dict(window)
        transform(window, self.CATEGORY_MAP)
        self.assertEqual(window, original)


if __name__ == "__main__":
    unittest.main()
