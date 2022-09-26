.PHONY: build test package clean

build:
	poetry install
	# if macOS, build swift
	if [ "$(shell uname)" = "Darwin" ]; then \
		make build-swift; \
	fi

build-swift: aw_watcher_window/aw-watcher-window-macos

aw_watcher_window/aw-watcher-window-macos: aw_watcher_window/macos.swift
	swiftc $^ -o $@

test:
	aw-watcher-window --help

typecheck:
	poetry run mypy aw_watcher_window/ --ignore-missing-imports

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

clean:
	rm -rf build dist
	rm -rf aw_watcher_window/__pycache__
