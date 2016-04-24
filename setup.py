#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='actwa-watcher-x11',
      version='0.1',
      description='X11 window watcher for ActivityWatch',
      author='Erik Bjäreholt',
      author_email='erik@bjareho.lt',
      url='https://github.com/ActivityWatch/actwa-watcher-x11',
      namespace_packages=['actwa', 'actwa.watchers'],
      packages=['actwa.watchers.x11'],
      install_requires=['actwa-client'],
      entry_points={
          'console_scripts': ['actwa-watcher-x11 = actwa.watchers.x11:main']
      }
)
