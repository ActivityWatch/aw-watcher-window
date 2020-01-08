.PHONY: build test package clean

ifdef DEV
pip_install_args := poetry install
else
install_cmd := pip3 install .
endif

build:
	$(install_cmd)

test:
	aw-watcher-window --help
	python3 -m mypy aw_watcher_window/ --ignore-missing-imports

package:
	pyinstaller aw-watcher-window.spec --clean --noconfirm

clean:
	rm -rf build dist
	rm -rf aw_watcher_window/__pycache__
