from setuptools import setup, find_packages
import sys, os
curdir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(curdir, 'README.rst')) as fd:
    long_description = fd.read()

version = '0.1.0'

setup(name='cmdbot-evented',
      version=version,
      description="An IRC Bot with a `cmd` attitude",
      long_description=long_description,
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      url='https://github.com/kyleterry/cmdbot-evented/',
      author="Bruno Bord modified by Kyle Terry",
      author_email='bruno@jehaisleprintemps.net',
      license="Public Domain (WTFPL)",
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'argparse',
          'nose',
          'ipdb',
          'gevent',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
