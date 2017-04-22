.PHONY: build

build:
	python3 setup.py install

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

