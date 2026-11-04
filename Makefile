.PHONY: build test package clean

MACOSX_DEPLOYMENT_TARGET ?= 12.0

build:
	poetry install
	# if macOS, build swift
	if [ "$(shell uname)" = "Darwin" ]; then \
		make build-swift; \
	fi

build-swift: aw_watcher_window/aw-watcher-window-macos

# NOTE: macos.swift is the sole Swift source and is compiled explicitly in
# the rule below (not via $^). Keep UPX/strip off the helper
# (aw-watcher-window.spec COLLECT): packing or stripping the Mach-O can
# destroy the __TEXT,__info_plist section the permission entry depends on.
aw_watcher_window/aw-watcher-window-macos: aw_watcher_window/macos.swift aw_watcher_window/Helper-Info.plist
	swiftc -target "$(shell uname -m)-apple-macosx$(MACOSX_DEPLOYMENT_TARGET)" \
		-Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker aw_watcher_window/Helper-Info.plist \
		aw_watcher_window/macos.swift -o $@

test:
	poetry run aw-watcher-window --help  # Ensures that it at least starts
	poetry run python -m pytest tests/
	make typecheck

typecheck:
	poetry run mypy aw_watcher_window/ --ignore-missing-imports

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

clean:
	rm -rf build dist
	rm -rf aw_watcher_window/__pycache__
	rm aw_watcher_window/aw-watcher-window-macos
