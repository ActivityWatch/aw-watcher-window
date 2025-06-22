aw-watcher-virtualdesktop
=======================

Window watcher with virtual desktop tracking for Windows.

[![Build Status](https://travis-ci.org/ActivityWatch/aw-watcher-window.svg?branch=master)](https://travis-ci.org/ActivityWatch/aw-watcher-window)

## How to install

To install the pre-built application, go to https://activitywatch.net/downloads/

To build your own packaged application, run `make package`

To install the latest git version directly from github without cloning, run
`pip install git+https://github.com/ActivityWatch/aw-watcher-virtualdesktop.git`

To install from a cloned version, cd into the directory and run
`poetry install` to install inside an virtualenv. You can run the binary via `aw-watcher-virtualdesktop`.

If you want to install it system-wide it can be installed with `pip install .`, but that has the issue
that it might not get the exact version of the dependencies due to not reading the poetry.lock file.

## Usage

In order for this watcher to be available in the UI, you'll need to have a Away From Computer (afk) watcher running alongside it.

Every heartbeat now includes a `virtual_desktop` field indicating the current workspace index (or desktop name on Windows). This information is best-effort and may not be available on all desktop environments.

Window titles can contain sensitive data. Use the `--exclude-title` option or set `exclude_title = true` in the configuration to omit the `title` field entirely from the sent events.


