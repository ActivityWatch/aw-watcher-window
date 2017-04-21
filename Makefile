.PHONY: build

build:
#	- gcc -framework Carbon get_window.c
	- python3 setup.py install

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

