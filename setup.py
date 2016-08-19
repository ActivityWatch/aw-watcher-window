#!/usr/bin/env python

from setuptools import setup

setup(name='aw-watcher-macos',
      version='0.1',
      description='ActivityWatch windowwatcher for macOS',
      author='Måns Magnusson',
      author_email='exoji2e@gmail.com',
      url='https://github.com/ActivityWatch/aw-watcher-macos',
      packages=['aw_watcher_macos'],
      install_requires=[
          'aw-client'
      ],
      dependency_links=[
          'https://github.com/ActivityWatch/aw-client/tarball/master#egg=aw-client'
      ],
      entry_points={
          'console_scripts': ['aw-watcher-macos = aw_watcher_macos:main']
      })
