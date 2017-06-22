.PHONY: build

build:
	pip3 install . --process-dependency-links

test:
	python3 -c "import aw_watcher_window"
	python3 -m mypy -m aw_watcher_window --ignore-missing-imports

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

