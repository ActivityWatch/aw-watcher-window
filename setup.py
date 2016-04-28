#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='aw-watcher-x11',
      version='0.1',
      description='X11 window watcher for ActivityWatch',
      author='Erik Bjäreholt',
      author_email='erik@bjareho.lt',
      url='https://github.com/ActivityWatch/aw-watcher-x11',
      namespace_packages=['aw', 'aw.watchers'],
      packages=['aw.watchers.x11'],
      install_requires=['aw-client'],
      entry_points={
          'console_scripts': ['aw-watcher-x11 = aw.watchers.x11:main']
      }
)
