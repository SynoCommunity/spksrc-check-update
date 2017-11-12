# -*- coding: utf-8 -*-

import os
import logging
import copy
import pprint

from multiprocessing import Pool

from .config import Config
from .cache import Cache
from .makefile_parser.makefile_parser import MakefileParser
from .package_search_update import PackageSearchUpdate
from .package_builder import PackageBuilder

_LOGGER = logging.getLogger(__name__)


class PackagesManager(object):

    def __init__(self):
        self._packages = {}
        self._packages_build = []
        self._cache = Cache(duration=Config.get(
            "cache_duration_packages_manager"))
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
        return os.path.join(Config.get('spksrc_git_dir'), package, 'Makefile')

    def generate_package_informations(self, package):
        if not package in self._packages:
            makefile_path = self.get_makefile_path(package)

            if not os.path.exists(makefile_path):
                _LOGGER.warning("Package %s doesn't exist !", package)
                return

            parser = MakefileParser()
            search_update = PackageSearchUpdate(package, makefile_path)
            search_update.set_parser(parser)

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
        cache_filename = 'packages.pkl'
        self._packages = self._cache.load(cache_filename)

        if not self._packages:
            packages = self._find_packages(Config.get('spksrc_git_dir') + 'cross') + self._find_packages(
                Config.get('spksrc_git_dir') + 'native') + self._find_packages(Config.get('spksrc_git_dir') + 'spk')

            self._packages = {}
            for package in packages:
                self.generate_package_informations(package)

            self._cache.save(cache_filename, self._packages)

    def package_search_update(self, package):

        search_update = self._packages[package]['search_update']

        search_update.search_updates()

        self._packages[package]['informations'] = search_update.get_informations()

    def check_update_packages(self):
        """ Print all dependencies
        """
        pool = Pool(processes=Config.get('nb_jobs'))

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

        # builder = PackageBuilder(packages, update_deps=Config.get('update_deps'),
        #                          allow_major_release=Config.get('allow_major_release'), allow_prerelease=Config.get('allow_prerelease'))
        # builder.set_spksrc_dir(os.path.join(
        #     Config.get('work_dir'), PackageBuilder.default_spksrc_dir))
        # if Config.get('verbose'):
        #     builder.set_verbose(True)

        # builder.build()
        # pprint.pprint(packages)
