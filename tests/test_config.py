import pathlib
import re
import sys

import tomlkit

from aw_watcher_window import config as config_module


def test_first_run_config_has_no_research_keys(tmp_path, monkeypatch):
    """Research/dev options must never be authored into a fresh user's config.

    load_config_toml() writes the default_config template to disk on first run.
    It comments out keys but leaves table headers uncommented, so a research
    table in the template lands verbatim in every new user's config file.
    Verified by symptom: run against an empty config dir and read what was written.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config_module.load_config()

    written = next(tmp_path.rglob("aw-watcher-window.toml")).read_text()
    assert "research" not in written

    # The file must still be valid TOML, and parse to nothing but comments.
    assert dict(tomlkit.parse(written)["aw-watcher-window"]) == {}


def test_research_options_are_read_when_user_sets_them(tmp_path, monkeypatch):
    """Absent from the template, but honoured when a Research Edition user opts in."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "activitywatch" / "aw-watcher-window"
    config_path.mkdir(parents=True)
    (config_path / "aw-watcher-window.toml").write_text(
        "[aw-watcher-window]\n"
        "research_enabled = true\n"
        "\n"
        "[aw-watcher-window.research_category_map]\n"
        'youtube = "Entertainment"\n'
        "\n"
        "[aw-watcher-window.research_app_category_map]\n"
        '"Microsoft Outlook" = "Communication"\n'
    )
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window"])

    args = config_module.parse_args()

    assert args.research_enabled is True
    assert args.research_category_map == {"youtube": "Entertainment"}
    assert args.research_app_category_map == {"Microsoft Outlook": "Communication"}


def test_research_edition_sed_target_is_intact():
    """The Research Edition release build patches this file with sed.

    ActivityWatch/activitywatch .github/workflows/release.yml runs
    ``sed -i 's/^research_enabled = false$/research_enabled = true/'`` against
    this module. That target lives in another repo, so pin it here — otherwise
    reformatting research_defaults silently breaks the Research Edition build.
    """
    # Check the source FILE, not the evaluated string. sed anchors on ^...$ in
    # the file, so an indented `    research_enabled = false` inside the literal
    # still strips to the same value — the string-level check would stay green
    # while the release build broke.
    source = pathlib.Path(config_module.__file__).read_text()
    assert re.search(
        r"^research_enabled = false$", source, re.MULTILINE
    ), "Research Edition sed target moved or got indented; see release.yml"

    # Simulate what release.yml sed actually does: apply the replacement to the
    # source FILE and confirm the patched line appears at column 0.  Checking the
    # runtime string (research_defaults) alone is insufficient — .strip() would
    # return the same value even if the source line is indented, keeping this
    # assertion green while the real sed-on-source would silently fail to match.
    patched_source = re.sub(
        r"^research_enabled = false$",
        "research_enabled = true",
        source,
        flags=re.MULTILINE,
    )
    assert re.search(r"^research_enabled = true$", patched_source, re.MULTILINE), (
        "sed patch did not produce 'research_enabled = true' in source"
    )
    # Also verify the patched value is structurally valid TOML with the flag set.
    # The triple-quoted literal's runtime value is equivalent to the source content
    # (both are stripped of surrounding whitespace), so we can reuse it here.
    patched_defaults = re.sub(
        r"^research_enabled = false$",
        "research_enabled = true",
        config_module.research_defaults,
        flags=re.MULTILINE,
    )
    assert tomlkit.parse(patched_defaults)["research_enabled"] is True


def test_parse_args_defaults_research_off_without_config(tmp_path, monkeypatch):
    """No research keys anywhere => disabled, with empty maps."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window"])

    args = config_module.parse_args()

    assert args.research_enabled is False
    assert args.research_category_map == {}
    assert args.research_app_category_map == {}


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


def test_no_research_overrides_config_enabled(monkeypatch):
    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: {
            "exclude_title": False,
            "exclude_titles": [],
            "poll_time": 1.0,
            "strategy_macos": "swift",
            "research_enabled": True,
            "research_category_map": {},
        },
    )
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window", "--no-research"])

    args = config_module.parse_args()

    assert args.research_enabled is False
