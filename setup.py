#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='aw-watcher-x11',
      version='0.1',
      description='X11 window watcher for ActivityWatch',
      author='Erik Bjäreholt',
      author_email='erik@bjareho.lt',
      url='https://github.com/ActivityWatch/aw-watcher-x11',
      packages=['aw_watcher_x11'],
      install_requires=[
          'aw-client>=0.2',
          'pytz'
      ],
      dependency_links=[
          'https://github.com/ActivityWatch/aw-client/tarball/master#egg=aw-client'
      ],
      entry_points={
          'console_scripts': ['aw-watcher-x11 = aw_watcher_x11:main']
      })
