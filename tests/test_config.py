import os
import pathlib
import re
import sys

import aw_core.dirs
import pytest
import tomlkit

from aw_watcher_window import config as config_module

# The Research Edition release build (release.yml) patches config.py with
# scripts/patch_research_edition_config.py before running `make test`, which
# flips research_enabled's default to true. The guards below assert the
# pristine (non-research) defaults and must not fire on that build.
RESEARCH_BUILD = os.environ.get("AW_RESEARCH_EDITION") == "true"


def _patch_config_dir(monkeypatch, tmp_path):
    """Point aw_core's config dir at tmp_path on all platforms.

    XDG_CONFIG_HOME is Linux-only; appdirs ignores it on macOS/Windows.
    Patching get_config_dir directly is cross-platform.
    """
    def _mock(module_name=None):
        base = tmp_path / "activitywatch"
        result = base / module_name if module_name else base
        result.mkdir(parents=True, exist_ok=True)
        return str(result)
    monkeypatch.setattr(aw_core.dirs, "get_config_dir", _mock)


def test_first_run_config_has_no_research_keys(tmp_path, monkeypatch):
    """Research/dev options must never be authored into a fresh user's config.

    load_config_toml() writes the default_config template to disk on first run.
    It comments out keys but leaves table headers uncommented, so a research
    table in the template lands verbatim in every new user's config file.
    Verified by symptom: run against an empty config dir and read what was written.
    """
    _patch_config_dir(monkeypatch, tmp_path)

    config_module.load_config()

    written = next(tmp_path.rglob("aw-watcher-window.toml")).read_text()
    assert "research" not in written

    # The file must still be valid TOML, and parse to nothing but comments.
    assert dict(tomlkit.parse(written)["aw-watcher-window"]) == {}


def test_research_options_are_read_when_user_sets_them(tmp_path, monkeypatch):
    """Absent from the template, but honoured when a Research Edition user opts in."""
    _patch_config_dir(monkeypatch, tmp_path)
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


@pytest.mark.skipif(
    RESEARCH_BUILD,
    reason="research edition build patches this default on purpose (release.yml)",
)
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


@pytest.mark.skipif(
    RESEARCH_BUILD,
    reason="research edition build patches this default on purpose (release.yml)",
)
def test_parse_args_defaults_research_off_without_config(tmp_path, monkeypatch):
    """No research keys anywhere => disabled, with empty maps."""
    _patch_config_dir(monkeypatch, tmp_path)
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


@pytest.mark.parametrize(
    "value,expected",
    [
        ('"1Password"', ["1Password"]),
        ('["1Password", "Secret.*"]', ["1Password", "Secret.*"]),
        ("[]", []),
        ('""', [""]),
    ],
)
def test_exclude_titles_toml_values(tmp_path, monkeypatch, value, expected):
    _patch_config_dir(monkeypatch, tmp_path)
    config_dir = tmp_path / "activitywatch" / "aw-watcher-window"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "aw-watcher-window.toml").write_text(
        f"[aw-watcher-window]\nexclude_titles = {value}\n"
    )
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window"])

    args = config_module.parse_args()

    assert args.exclude_titles == expected
    if expected == ["1Password"]:
        from aw_watcher_window.main import transform_window, try_compile_regex

        patterns = [try_compile_regex(title) for title in args.exclude_titles]
        assert len(patterns) == 1
        for title in ["1Password vault", "Project notes", "Terminal"]:
            expected_title = "excluded" if title == "1Password vault" else title
            assert transform_window(
                {"app": "Test", "title": title}, exclude_titles=patterns
            )["title"] == expected_title
    if expected == [""]:
        assert re.compile(args.exclude_titles[0]).search("any title") is not None


@pytest.mark.parametrize("value", ["17", "true", "{pattern = 'Secret'}", '["Secret", 17]'])
def test_invalid_exclude_titles_config_errors(tmp_path, monkeypatch, capsys, value):
    _patch_config_dir(monkeypatch, tmp_path)
    config_dir = tmp_path / "activitywatch" / "aw-watcher-window"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "aw-watcher-window.toml").write_text(
        f"[aw-watcher-window]\nexclude_titles = {value}\n"
    )
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window"])

    with pytest.raises(SystemExit) as exc:
        config_module.parse_args()

    assert exc.value.code == 2
    assert "exclude_titles must be a string or a list of strings" in capsys.readouterr().err


def test_cli_exclude_titles_overrides_invalid_config(tmp_path, monkeypatch):
    _patch_config_dir(monkeypatch, tmp_path)
    config_dir = tmp_path / "activitywatch" / "aw-watcher-window"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "aw-watcher-window.toml").write_text(
        "[aw-watcher-window]\nexclude_titles = 17\n"
    )
    monkeypatch.setattr(
        sys, "argv", ["aw-watcher-window", "--exclude-titles", "Secret.*", "Private"]
    )

    assert config_module.parse_args().exclude_titles == ["Secret.*", "Private"]


def test_exclude_apps_string_in_config_is_coerced_to_single_pattern(monkeypatch):
    """A bare string in config must not be iterated character-by-character.

    ``exclude_apps = "1Password"`` is natural TOML for one app. argparse's
    ``nargs='+'`` hands a string default through unchanged, and main.py would
    then compile each *character* as a pattern — silently excluding far more
    than the user asked for.
    """
    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: {
            "exclude_title": False,
            "exclude_titles": [],
            "exclude_apps": "1Password",
            "poll_time": 1.0,
            "strategy_macos": "swift",
        },
    )
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window"])

    args = config_module.parse_args()

    assert args.exclude_apps == ["1Password"]


def test_exclude_apps_list_in_config_is_preserved(monkeypatch):
    """The list form is the documented shape and must be untouched."""
    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: {
            "exclude_title": False,
            "exclude_titles": [],
            "exclude_apps": ["1Password", "KeePassXC"],
            "poll_time": 1.0,
            "strategy_macos": "swift",
        },
    )
    monkeypatch.setattr(sys, "argv", ["aw-watcher-window"])

    args = config_module.parse_args()

    assert args.exclude_apps == ["1Password", "KeePassXC"]
