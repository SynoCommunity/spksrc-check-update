#!/usr/bin/env python3

import sys
import os
import getopt
import pprint
from datetime import datetime

import parsedatetime
import multiprocessing
from multiprocessing import Pool
from spksrc.search_update import SearchUpdate
from spksrc.package_builder import PackageBuilder


class MainApp(object):

    def __init__(self):
        self._root = None
        self._packages = None
        self._verbose = False
        self._use_cache = True
        self._update_deps = False
        self._allow_major_release = False
        self._allow_prerelease = False
        self._cache_duration = 24 * 3600 * 7
        self._work_dir = 'work'
        self._nb_jobs = multiprocessing.cpu_count()

    def help(self):
        print("""
Script to gather search update for spksrc package in cross/ and native/.

Usage:
  main.py [options] -r <root>

Options:
  -h --help                        Show this screen.
  -r --root=<root>                 Root directory of spksrc
  -p --packages=<package,package>  Packages to check for update (Optional)
  -v --verbose                     Verbose mode
  -c --disable-cache               Disable cache
  -d --cache-duration=<duration>   Cache duration in seconds (Default: 3 days)
  -w --work-dir=<directory>        Work directory (Default: work)
  -m --allow-major-release         Allow to update to next major version (Default: False)
  -a --allow-prerelease            Allow prerelease version (Default: False)
  -u --update-deps                 Update deps before build the current package (Default: False)
  -j --jobs                        Number of jobs (Default: CPU core)
""")

    def check_spksc_dir(self):
        check = os.path.exists(self._root)
        check = check & os.path.isdir(self._root)
        check = check & os.path.isdir(self._root + 'cross')
        check = check & os.path.isdir(self._root + 'native')
        check = check & os.path.isdir(self._root + 'spk')
        check = check & os.path.isdir(self._root + 'toolchains')

        return check

    def read_args(self):
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hcvmaur:p:d:w:j:", [
                                       "root=", "packages=", "cache-duration=", "work-dir=", "verbose", "disable-cache", "allow-prerelease", "update-deps", "jobs="])
        except getopt.GetoptError as error:
            self.help()
            print(error)
            sys.exit(2)

        for opt, arg in opts:
            if opt == '-h':
                self.help()
                sys.exit()
            elif opt in ("-v", "--verbose"):
                self._verbose = True
            elif opt in ("-c", "--disable-cache"):
                self._use_cache = False
            elif opt in ("-r", "--root"):
                self._root = arg.rstrip(os.path.sep) + os.path.sep
            elif opt in ("-p", "--packages"):
                self._packages = arg.strip(os.path.sep)
            elif opt in ("-d", "--cache-duration"):
                cal = parsedatetime.Calendar()
                date_now = datetime.now().replace(microsecond=0)
                date, _ = cal.parseDT(arg, sourceTime=date_now)
                self._cache_duration = (date - date_now).total_seconds()
            elif opt in ("-w", "--work-dir"):
                self._work_dir = arg.rstrip(os.path.sep)
            elif opt in ("-m", "--allow-major-release"):
                self._allow_major_release = True
            elif opt in ("-a", "--allow-prerelease"):
                self._allow_prerelease = True
            elif opt in ("-u", "--update-deps"):
                self._update_deps = True
            elif opt in ("-j", "--jobs"):
                self._nb_jobs = max(int(arg), 1)

    def find_makefile(self, path):
        result = []
        dirname = os.path.basename(path)
        for filename in os.listdir(path):
            makefile = os.path.join(path, filename, 'Makefile')
            if os.path.exists(makefile):
                result.append([dirname + os.path.sep + filename, makefile])

        result.sort()

        return result

    def check_update_makefile(self, makefile):
        package, path = makefile
        search_update = SearchUpdate(package, path)

        if not self._use_cache:
            search_update.disable_cache()

        search_update.set_cache_dir(os.path.join(
            self._work_dir, SearchUpdate.default_cache_dir))
        search_update.set_cache_duration(self._cache_duration)

        if self._verbose:
            search_update.set_verbose(True)

        return [package, search_update.search_updates()]

    def get_list_packages(self):
        makefiles = []
        if self._packages is not None:
            packages = self._packages.split(',')
            for package in packages:
                if not os.path.exists(self._root + package + os.path.sep + 'Makefile'):
                    self.help()
                    print("<package> " + package +
                          " doesn't exist or it is not a valid spksrc package")
                    sys.exit(2)

                makefiles += [[package, os.path.join(
                    self._root, package, 'Makefile')]]
        else:
            makefiles = self.find_makefile(
                self._root + 'cross') + self.find_makefile(self._root + 'native')

        return makefiles

    def check_update_packages(self):

        makefiles = self.get_list_packages()

        pool = Pool(processes=self._nb_jobs)

        packages_list = pool.map(self.check_update_makefile, makefiles)

        packages = {}
        for package in packages_list:
            packages[package[0]] = package[1]

        return packages

    def main(self):
        """
        main
        """

        self.read_args()

        if self._root is None or len(self._root) == 0:
            self.help()
            print("<root> is required")
            sys.exit(2)

        if not self.check_spksc_dir():
            self.help()
            print("<root> have to be a root directory of spksrc")
            sys.exit(2)

        packages = self.check_update_packages()

        builder = PackageBuilder(packages, update_deps=self._update_deps,
                                 allow_major_release=self._allow_major_release, allow_prerelease=self._allow_prerelease)
        builder.set_spksrc_dir(os.path.join(
            self._work_dir, PackageBuilder.default_spksrc_dir))
        if self._verbose:
            builder.set_verbose(True)

        builder.build()
        # pprint.pprint(packages)


if __name__ == '__main__':
    app = MainApp()
    sys.exit(app.main())
