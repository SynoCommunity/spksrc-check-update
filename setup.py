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
        'beautifulsoup4>=4.6.0',
        'GitPython>=2.1.9',
        'html5lib>=0.999999999',
        'parsedatetime>=2.4',
        'pyparsing>=2.2.0',
        'python-dateutil>=2.7.2',
        'requests>=2.18.4',
        'svn>=0.3.44',
    ],
    package_dir={'spksrc_updater': 'lib'},
    packages=["spksrc_updater"],
    scripts=['spksrc-updater'],
    author="Guillaume Smaha & SynoCommunity",
    license='GPLv3',
    url="https://github.com/SynoCommunity/spksrc-updater"
)
