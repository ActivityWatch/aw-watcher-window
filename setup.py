#!/usr/bin/env python

from setuptools import setup

setup(name='aw-watcher-window',
      version='0.1',
      description='Cross platform window watcher for ActivityWatch',
      author='Erik Bjäreholt, Måns Magnusson',
      author_email='erik@bjareho.lt, exoji2e@gmail.com',
      url='https://github.com/ActivityWatch/aw-watcher-window',
      packages=['aw_watcher_window'],
      install_requires=[
          'aw-client',
          'pytz'
      ],
      dependency_links=[
          'https://github.com/ActivityWatch/aw-client/tarball/master#egg=aw-client'
      ],
      entry_points={
          'console_scripts': ['aw-watcher-window = aw_watcher_window:main']
      })
