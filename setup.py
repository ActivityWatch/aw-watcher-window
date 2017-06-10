#!/usr/bin/env python

from setuptools import setup
import sys

additional_reqs = []
if sys.platform in ["win32", "cygwin"]:
    additional_reqs.append("wmi")
    additional_reqs.append("pypiwin32")

setup(name='aw-watcher-window',
      version='0.1',
      description='Cross platform window watcher for ActivityWatch',
      author='Erik Bjäreholt, Måns Magnusson',
      author_email='erik@bjareho.lt, exoji2e@gmail.com',
      url='https://github.com/ActivityWatch/aw-watcher-window',
      packages=['aw_watcher_window'],
      package_data={'aw_watcher_window': ['*.scpt']},
      install_requires=[
          'aw-client>=0.2.0',
      ] + additional_reqs,
      dependency_links=[
          'https://github.com/ActivityWatch/aw-core/tarball/master#egg=aw-core-0.2.0',
          'https://github.com/ActivityWatch/aw-client/tarball/master#egg=aw-client-0.2.0'
      ],
      entry_points={
          'console_scripts': ['aw-watcher-window = aw_watcher_window:main']
      })
