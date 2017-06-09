.PHONY: build

build:
	pip3 install .

test:
	python3 -c "import aw_watcher_window"

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

