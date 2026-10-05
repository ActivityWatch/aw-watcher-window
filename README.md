aw-watcher-window
=================

Cross-platform window-Watcher for Linux (X11), macOS, Windows.

[![Build Status](https://travis-ci.org/ActivityWatch/aw-watcher-window.svg?branch=master)](https://travis-ci.org/ActivityWatch/aw-watcher-window)

## How to install

To install the pre-built application, go to https://activitywatch.net/downloads/

To build your own packaged application, run `make package`

To install the latest git version directly from github without cloning, run
`pip install git+https://github.com/ActivityWatch/aw-watcher-window.git`

To install from a cloned version, cd into the directory and run
`poetry install` to install inside an virtualenv. You can run the binary via `aw-watcher-window`.

If you want to install it system-wide it can be installed with `pip install .`, but that has the issue
that it might not get the exact version of the dependencies due to not reading the poetry.lock file.

## Usage

In order for this watcher to be available in the UI, you'll need to have a Away From Computer (afk) watcher running alongside it.

### Note to macOS users

To log current window title the terminal needs access to macOS accessibility API.
This can be enabled in `System Preferences > Security & Privacy > Accessibility`, then add the Terminal to this list. If this is not enabled the watcher can only log current application, and not window title.

### Optional Claude and Joplin titles on macOS

The Swift watcher can replace a generic `Claude` or `Joplin` window title with
the open conversation/session or note title. This is **disabled by default**:
these titles can contain sensitive information and are saved in your existing
window-activity bucket. To opt in, add this to your `aw-watcher-window.toml`:

```toml
[aw-watcher-window]
strategy_macos = "swift"
title_enrichment_macos = ["Claude", "Joplin"]
```

Include only the apps you want. Restart the watcher after changing its config.
The CLI equivalent is `aw-watcher-window --title-enrichment-macos Claude Joplin`;
passing `--title-enrichment-macos` with no apps disables configured enrichment
for that run. Other platforms and the JXA/AppleScript strategies ignore this option.

Existing `exclude_title` and `exclude_titles` filters apply to both native and
enriched titles. A native-title match (including `^Claude$` or `^Joplin$`) skips
enrichment and stays excluded. With `exclude_title` or Research Edition enabled,
enrichment is skipped entirely.
No document URLs or message/note bodies are added to events. An informative native
window title is preserved, and unknown apps are never enriched by name alone.

Claude's document title supports arbitrary text. Its Code-session fallback needs
the English rename/menu labels; Joplin needs the English `Note title` field label.
Unknown, localized, missing, or ambiguous controls retain the native window title.
Joplin requires exactly one labelled title field in a complete shallow search.
Titles themselves can be short, Unicode, or emoji. App interface updates can
invalidate these selectors. Switching sessions without changing the native title
is detected by the existing 10-second poll, so very short visits may be missed.

The watcher may enable Electron accessibility for an opted-in app; this can add
CPU/memory cost in that app. Each enrichment lookup has a 250 ms time budget and
limits both visited elements and queued children. Its Accessibility messages,
including the cold-tree enable request, use at most a 50 ms timeout, shortened
to the remaining budget. Timeout or incomplete searches retain the native title;
OS scheduling can still add delay. These bounds apply to enrichment, not to the
watcher's pre-existing window capture paths.
Turning enrichment off stops these lookups; restart the target app if you also
want it to rebuild without accessibility enabled by this watcher.

See [the testing guide](docs/macos-title-enrichment-testing.md) for automated
regressions, live verification, and the limits of fixture-based tests.
