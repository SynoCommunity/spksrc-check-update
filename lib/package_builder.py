import sys
import os
import shutil
import re
import time
import copy
import logging
import collections
import pprint
import pickle
from pkg_resources import parse_version

import git as git

from .makefile_parser.makefile_parser import MakefileParser

_LOGGER = logging.getLogger(__name__)


class PackageBuilder(object):

    # Gir repository of spksrc
    spksrc_git_uri = 'https://github.com/SynoCommunity/spksrc.git'

    # Default cache dir to save
    default_spksrc_dir = 'spksrc-git'

    def __init__(self, packages, update_deps=False, allow_major_release=False, allow_prerelease=False):
        self._verbose = False
        self._packages = packages
        self._spksrc_dir = PackageBuilder.default_spksrc_dir
        self._packages_build = []
        self._update_deps = update_deps
        self._allow_major_release = allow_major_release
        self._allow_prerelease = allow_prerelease

    def log(self, message):
        """ Print a message with a prefix
        """
        _LOGGER.info("Builder: %s", message)

    def set_verbose(self, verbose):
        """ Define if versose mode
        """
        self._verbose = verbose

    def set_spksrc_dir(self, spksrc_dir):
        """ Set spksrc directory
        """
        self._spksrc_dir = spksrc_dir

    def prepare_spskrc_dir(self):
        """ Prepare the spksrc directory to build
        """

        # Clone repo if not exists
        if not os.path.exists(self._spksrc_dir):
            self.log("Clone repository: " + PackageBuilder.spksrc_git_uri)
            try:
                git.Repo.clone_from(
                    PackageBuilder.spksrc_git_uri, self._spksrc_dir)
            except git.GitCommandError as exception:
                self.log("Error to clone git")
                return

        # Fetch and pull
        self.log("Fetch and pull git")
        repo = git.Repo(self._spksrc_dir)

        # Fetch and pull all remotes
        for remote in repo.remotes:
            remote.fetch()
            remote.pull()

        # Reset hard
        self.log("Reset hard")
        repo.head.reset(index=True, working_tree=True)

        # Checkout master
        self.log("Checkout master")
        repo.refs.master.checkout()

    def _next_major_version(self, version):
        """
        Given a parsed version from pkg_resources.parse_version, returns a new
        version string with the next minor version.

        Examples
        ========
        >>> _next_major_version(pkg_resources.parse_version('1.2.3'))
        '2.0.0'
        """

        if hasattr(version, 'base_version'):
            # New version parsing from setuptools >= 8.0
            if version.base_version:
                parts = version.base_version.split('.')
            else:
                parts = []
        else:
            parts = []
            for part in version:
                if part.startswith('*'):
                    break
                parts.append(part)

        parts = [p for p in parts]

        if len(parts) < 3:
            parts += [0] * (3 - len(parts))

        major, minor, micro = parts[:3]

        try:
            major = int(major)
        except:
            return None

        return parse_version('{0}.{1}.{2}'.format(major + 1, 0, 0))

    def check_version_isvalid(self, current, new):

        if not self._allow_prerelease and new['is_prerelease']:
            return False

        current_p = parse_version(current)
        new_p = parse_version(new['version'])
        if self._allow_major_release:
            return new_p > current_p

        major_version = self._next_major_version(current_p)
        if major_version and new_p >= major_version:
            return False

        return new_p > current_p

    def get_new_version(self, package):
        """ Get the version to update using the parameter (allow_major_release, ...) """
        if package not in self._packages:
            return None

        if not self._packages[package]['versions']:
            return None

        current_version = self._packages[package]['version']

        result = None
        if self._packages[package]['method'] == 'common':
            result = None
            for new_version, new in self._packages[package]['versions'].items():
                if self.check_version_isvalid(current_version, new):
                    result = new

        else:
            result = next(iter(reverse(self._packages[package]['versions'])))

        return result

    def build(self):
        # Prepare spksrc directory by cloning the repository, reset hard and checkout master
        self.prepare_spskrc_dir()

        # Loop on packages to the tree of dependances
        # self.create_deps_tree()

        #

        """
        if 'cross/x265' in self._packages:
            pprint.pprint(self._packages['cross/x265'])
        else:
            pprint.pprint(self._packages)
        """

        for package in self._packages:
            if self._packages[package]['version']:
                self.log(package + " " + self._packages[package]['version'])
            else:
                self.log(package)
            pprint.pprint(self._packages[package])
            #version = self.get_new_version(package)
            # if version:
            #    pprint.pprint(version)
