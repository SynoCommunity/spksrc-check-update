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

import git as git

from makefile_parser.makefile_parser import MakefileParser

_LOGGER = logging.getLogger(__name__)

class PackageBuilder(object):

    # Gir repository of spksrc
    spksrc_git_uri = 'https://github.com/SynoCommunity/spksrc.git'

    # Default cache dir to save
    default_spksrc_dir = 'spksrc-git'

    def __init__(self, packages):
        self._verbose = False
        self._packages = packages
        self._spksrc_dir = PackageBuilder.default_spksrc_dir
        self._packags_build = []

    def log(self, message):
        """ Print a message with a prefix
        """
        if self._verbose:
            print("Builder: " + message)

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
                git.Repo.clone_from(PackageBuilder.spksrc_git_uri, self._spksrc_dir)
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


    def create_deps_tree(self):
        for package_name, package in self._packages.items():
            for dep in package['depends']:
                if dep not in self._packages:
                    self.log("Package " + dep + " is not found")
                    break

                if 'parents' not in self._packages[dep]:
                    self._packages[dep]['parents'] = []
                self._packages[dep]['parents'].append(package_name)

    def build(self):
        # Prepare spksrc directory by cloning the repository, reset hard and checkout master
        self.prepare_spskrc_dir()

        # Loop on packages to the tree of dependances
        self.create_deps_tree()


        if 'cross/x265' in self._packages:
            pprint.pprint(self._packages['cross/x265'])
        else:
            pprint.pprint(self._packages)

