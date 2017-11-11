# -*- coding: utf-8 -*-

import os
import logging
import copy
import pprint

from multiprocessing import Pool

from .options import DEFAULTS, OPTIONS
from .tools import Tools
from .makefile_parser.makefile_parser import MakefileParser
from .package_search_update import PackageSearchUpdate
from .package_builder import PackageBuilder

_LOGGER = logging.getLogger(__name__)


class PackagesManager(object):

    def __init__(self):
        self._packages = {}
        self._packages_build = []

        self.generate_packages_list()

    def _find_packages(self, path):
        """ Find all packages in a directory and return package name
        """
        result = []
        dirname = os.path.basename(path)
        for filename in os.listdir(path):
            makefile = os.path.join(path, filename, 'Makefile')
            if os.path.exists(makefile):
                result.append(dirname + os.path.sep + filename)

        return result

    def get_makefile_path(self, package):
        """ Return Makefile path of a package
        """
        return os.path.join(OPTIONS['root'], package, 'Makefile')

    def generate_package_informations(self, package):
        if not package in self._packages:
            makefile_path = self.get_makefile_path(package)

            if not os.path.exists(makefile_path):
                _LOGGER.warning("Package %s doesn't exist !" % (package,))
                return

            parser = MakefileParser()
            search_update = PackageSearchUpdate(package, makefile_path)
            search_update.set_parser(parser)

            if not OPTIONS['use_cache']:
                search_update.disable_cache()

            search_update.set_cache_dir(os.path.join(
                OPTIONS['work_dir'], PackageSearchUpdate.default_cache_dir))
            search_update.set_cache_duration(OPTIONS['cache_duration'])

            if OPTIONS['verbose']:
                search_update.set_verbose(True)

            informations = search_update.get_informations()
            self._packages[package] = {
                'makefile_path': makefile_path,
                'parser': parser,
                'search_update': search_update,
                'informations': informations,
                'parents': []
            }

            for dep in informations['all_depends']:
                self.generate_package_informations(dep)
                self._packages[dep]['parents'].append(package)

    def generate_packages_list(self):
        """ XXX
        """
        packages_cache = os.path.join(
            OPTIONS['work_dir'], OPTIONS['cache_dir'], 'packages.pkl')
        self._packages = Tools.cache_load(
            packages_cache, OPTIONS['cache_duration_packages_manager'])

        if not self._packages:
            packages = self._find_packages(OPTIONS['root'] + 'cross') + self._find_packages(
                OPTIONS['root'] + 'native') + self._find_packages(OPTIONS['root'] + 'spk')

            self._packages = {}
            for package in packages:
                self.generate_package_informations(package)

            Tools.cache_save(packages_cache, self._packages)

    def package_search_update(self, package):

        search_update = self._packages[package]['search_update']

        search_update.search_updates()

        self._packages[package]['informations'] = search_update.get_informations()

    def check_update_packages(self):
        """ Print all dependencies
        """
        pool = Pool(processes=OPTIONS['nb_jobs'])

        pool.map(self.package_search_update, self._packages)

    def pprint_deps(self, package, depth=0):
        """ Print all dependencies
        """
        print('  ' * depth + " - " + package)
        for deps in self._packages[package]['informations']['all_depends']:
            self.pprint_deps(deps, depth + 1)

    def pprint_parent_deps(self, package, depth=0):
        """ Print all parent dependencies
        """
        print('  ' * depth + " - " + package)
        for deps in self._packages[package]['parents']:
            self.pprint_parent_deps(deps, depth + 1)

        # packages = self.check_update_packages()

        # builder = PackageBuilder(packages, update_deps=OPTIONS['update_deps'],
        #                          allow_major_release=OPTIONS['allow_major_release'], allow_prerelease=OPTIONS['allow_prerelease'])
        # builder.set_spksrc_dir(os.path.join(
        #     OPTIONS['work_dir'], PackageBuilder.default_spksrc_dir))
        # if OPTIONS['verbose']:
        #     builder.set_verbose(True)

        # builder.build()
        # pprint.pprint(packages)
