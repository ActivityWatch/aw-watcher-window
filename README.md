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

## Privacy Filter

You can configure rules to **drop** or **redact** sensitive window events before they are sent to aw-server. This is a client-side pre-filter: matching events never leave the machine at all.

Add `[[aw-watcher-window.privacy_filter]]` entries to your config file
(`~/.config/activitywatch/aw-watcher-window/aw-watcher-window.toml`):

```toml
# Drop events from private-browsing windows entirely
[[aw-watcher-window.privacy_filter]]
pattern = "(?i)private browsing|incognito"
action  = "drop"

# Redact window titles that contain sensitive account information
[[aw-watcher-window.privacy_filter]]
pattern     = "(?i)bank|my account|password"
action      = "redact"
replacement = "REDACTED"   # optional; defaults to "excluded"

# Drop events from a specific app by matching its name
[[aw-watcher-window.privacy_filter]]
pattern = "(?i)signal|whatsapp"
field   = "app"            # optional; defaults to "title"
action  = "drop"
```

Rule fields:
- `pattern` — Python `re` regex (case-insensitive flag supported via `(?i)`)
- `field` — window-event field to match against (`"title"` by default; use `"app"` to match on application name)
- `action` — `"drop"` (discard the event) or `"redact"` (replace the field value)
- `replacement` — string to use when redacting; defaults to `"excluded"`

Rules are applied in order. A `"drop"` rule exits immediately — subsequent rules are not evaluated for that event.

> **macOS note**: The default `swift` strategy bypasses this Python transform. Use `--strategy jxa` or `--strategy applescript` to enable watcher-side privacy filtering on macOS.

