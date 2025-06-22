.PHONY: build test package clean

build:
        poetry install

test:
        aw-watcher-virtualdesktop --help

typecheck:
        poetry run mypy aw_watcher_virtualdesktop/ --ignore-missing-imports

package:
        pyinstaller aw-watcher-window.spec --clean --noconfirm

clean:
        rm -rf build dist
        rm -rf aw_watcher_virtualdesktop/__pycache__
