.PHONY: build

build:
	python3 setup.py install

test:
	python3 -c "import aw_watcher_window"

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

