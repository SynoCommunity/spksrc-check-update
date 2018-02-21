#!/usr/bin/env python
# -*- coding: utf-8 -*-


# python setup.py sdist --format=zip,gztar

from setuptools import setup
import imp
import argparse

version = imp.load_source('version', 'lib/version.py')

setup(
    name="Spksrc-Updater",
    version=version.SPKSRC_UPDATER_VERSION,
    description="Updater for spksrc",
    long_description="""Updater for spksrc""",
    install_requires=[
        'appdirs>=1.4.2',
        'astroid>=1.5.3',
        'beautifulsoup4>=4.5.3',
        'future>=0.16.0',
        'gitdb2>=2.0.0',
        'GitPython>=2.1.1',
        'html5lib>=0.999999999',
        'isort>=4.2.15',
        'lazy-object-proxy>=1.3.1',
        'mccabe>=0.6.1',
        'nose>=1.3.7',
        'packaging>=16.8',
        'parsedatetime>=2.4',
        'pylint>=1.7.2',
        'pyparsing>=2.1.10',
        'python-dateutil>=2.6.0',
        'requests>=2.13.0',
        'six>=1.10.0',
        'smmap2>=2.0.1',
        'svn>=0.3.44',
        'webencodings>=0.5',
        'wrapt>=1.10.10'
    ],
    package_dir={'spksrc_updater': 'lib'},
    packages=["spksrc_updater"],
    scripts=['spksrc-updater'],
    author="Guillaume Smaha & SynoCommunity",
    license='GPLv3',
    url="https://github.com/SynoCommunity/spksrc-updater"
)
