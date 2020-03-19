.PHONY: build test package clean

build:
	poetry install

test:
	aw-watcher-window --help
	python -m mypy aw_watcher_window/ --ignore-missing-imports

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

clean:
	rm -rf build dist
	rm -rf aw_watcher_window/__pycache__
