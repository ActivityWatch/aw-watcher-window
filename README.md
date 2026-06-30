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

## Title Cleaning Rules

You can configure regex-based title cleaning rules to modify window titles before they are sent to the server. This is useful for removing application-specific suffixes, file paths, or other unwanted information from window titles.

### Configuration

Add title cleaning rules to your `~/.config/activitywatch/aw-watcher-window.toml` file:

```toml
# Title cleaning rules - apply regex replacements to window titles for specific apps
[[title_cleaning_rules.rules]]
app = "firefox"
pattern = "( - Mozilla Firefox)$"
replacement = ""

[[title_cleaning_rules.rules]]
app = "code"
pattern = " - Visual Studio Code$"
replacement = ""
```

Each rule consists of:
- `app`: The application name (case-insensitive match)
- `pattern`: Regular expression pattern to match in the window title
- `replacement`: String to replace matches with (can be empty to remove)

See `example-config.toml` for more examples.

### Note to macOS users

To log current window title the terminal needs access to macOS accessibility API.
This can be enabled in `System Preferences > Security & Privacy > Accessibility`, then add the Terminal to this list. If this is not enabled the watcher can only log current application, and not window title.

