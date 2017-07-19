.PHONY: build test package clean

build:
	pip3 install . --process-dependency-links

test:
	python3 -c "import aw_watcher_window"
	python3 -m mypy -m aw_watcher_window --ignore-missing-imports

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

clean:
	rm -rf build dist
	rm -rf aw_watcher_window/__pycache__
