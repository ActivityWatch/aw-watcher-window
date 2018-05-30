#!/usr/bin/env python

from setuptools import setup
import sys
import platform

additional_reqs = []
if sys.platform in ["win32", "cygwin"]:
    additional_reqs.append("wmi")
    additional_reqs.append("pypiwin32")
elif platform.system() == "Linux":
    additional_reqs.append("python-xlib")

setup(name='aw-watcher-window',
      version='0.2',
      description='Cross platform window watcher for ActivityWatch',
      author='Erik Bjäreholt, Måns Magnusson',
      author_email='erik@bjareho.lt, exoji2e@gmail.com',
      url='https://github.com/ActivityWatch/aw-watcher-window',
      packages=['aw_watcher_window'],
      package_data={'aw_watcher_window': ['*.scpt']},
      install_requires=[
          'aw-client>=0.2.0',
      ] + additional_reqs,
      entry_points={
          'console_scripts': ['aw-watcher-window = aw_watcher_window:main']
      },
      classifiers=[
          'Programming Language :: Python :: 3'
      ])
