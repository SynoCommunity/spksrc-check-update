# -*- coding: utf-8 -*-

import sys
import os
import getopt
import pprint
import logging
from datetime import datetime

import parsedatetime
import multiprocessing
from .config import Config
from .packages_manager import PackagesManager

_LOGGER = logging.getLogger(__name__)

class Main(object):

    def __init__(self):
        pass

    def version(self):
        import imp
        version = imp.load_source('version', 'lib/version.py')
        print(version.SPKSRC_UPDATER_VERSION)

    def help(self):
        print("""
Script to gather search update for spksrc package in cross/ and native/.

Usage:
  main.py [options] [action]

Action:
  - search: Search for new updates
  - build: Launch build for the new packages
  - print_deps: Prints all dependancies
  - print_parent_deps: Prints all parent dependancies

Parameters:
  -h --help                        Show this screen.
  -v --version                     Print version
  -r --root=<root>                 Root directory of spksrc
  -p --packages=<package,package>  Packages to check for update (Optional)
  -c --disable-cache               Disable cache
  -d --cache-duration=<duration>   Cache duration in seconds (Default: 3 days)
  -d --debug=<level>               Debug level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  -w --work-dir=<directory>        Work directory (Default: work)
  -m --allow-major-release         Allow to update to next major version (Default: False)
  -a --allow-prerelease            Allow prerelease version (Default: False)
  -u --update-deps                 Update deps before build the current package (Default: False)
  -j --jobs                        Number of jobs (Default: max CPU core)
  -o --option "<key>=<value>"      Set an option

Available options:
  - packages
  - verbose
  - cache_enabled
  - update_deps
  - allow_major_release
  - allow_prerelease
  - cache_duration
  - work_dir
  - nb_jobs

Examples:

  - Search news version for ALL packages:
        python main.py -r ../spksrc search

  - Launch build for the new release of ffmpeg:
        python main.py -r ../spksrc -p cross/ffmpeg build

  - Launch build for the new release of zlib and ffmpeg:
        python main.py -r ../spksrc -p cross/zlib,cross/ffmpeg build

  - Launch build for the new major release of ffmpeg:
        python main.py -r ../spksrc -p cross/ffmpeg --allow-major-release build

  - Launch build for the new release of ffmpeg and all its dependencies:
        python main.py -r ../spksrc -p cross/ffmpeg --allow-prerelease build

""")

    def read_args(self):
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hcvmaur:p:d:w:j:", [
                "jobs="
                "root=",
                "packages=",
                "debug=",
                "work-dir=",
                "version",
                "disable-cache",
                "allow-prerelease",
                "update-deps",
            ])
        except getopt.GetoptError as error:
            self.help()
            _LOGGER.error(error)
            sys.exit(2)

        for opt, arg in opts:
            if opt == '-h':
                self.help()
                sys.exit()
            elif opt in ("-v", "--version"):
                self.version()
                sys.exit()
            elif opt in ("-c", "--disable-cache"):
                Config.set('cache_enabled', False)
            elif opt in ("-r", "--root"):
                Config.set('root', arg.rstrip(os.path.sep) + os.path.sep)
            elif opt in ("-p", "--packages"):
                Config.set('packages', arg.strip(os.path.sep).split(','))
            elif opt in ("-d", "--debug"):
                Config.set('debug_level', arg)
            elif opt in ("-e", "--cache-duration"):
                cal = parsedatetime.Calendar()
                date_now = datetime.now().replace(microsecond=0)
                date, _ = cal.parseDT(arg, sourceTime=date_now)
                Config.set('cache_duration', (
                    date - date_now).total_seconds())
            elif opt in ("-w", "--work-dir"):
                Config.set('work_dir', arg.rstrip(os.path.sep))
            elif opt in ("-m", "--allow-major-release"):
                Config.set('allow_major_release', True)
            elif opt in ("-a", "--allow-prerelease"):
                Config.set('allow_prerelease', True)
            elif opt in ("-u", "--update-deps"):
                Config.set('update_deps', True)
            elif opt in ("-j", "--jobs"):
                Config.set('nb_jobs', max(int(arg), 1))

        return args

    def check_spksc_dir(self):
        check = os.path.exists(Config.get('root'))
        check = check & os.path.isdir(Config.get('root'))
        check = check & os.path.isdir(Config.get('root') + 'cross')
        check = check & os.path.isdir(Config.get('root') + 'native')
        check = check & os.path.isdir(Config.get('root') + 'spk')
        check = check & os.path.isdir(Config.get('root') + 'toolchains')

        if not check:
            self.help()
            print("<root> have to be a root directory of spksrc")
            sys.exit(2)

    def check_packages_list(self):
        if Config.get('packages'):
            for package in Config.get('packages'):
                if not os.path.exists(Config.get('root') + package + os.path.sep + 'Makefile'):
                    self.help()
                    print("<package> " + package +
                          " doesn't exist or it is not a valid spksrc package")
                    sys.exit(2)

    def _command_search(self):
        self._spksrc_manager.check_update_packages()
        pass

    def _command_build(self):
        pass

    def _command_print_deps(self):
        print('Package dependencies:')

        if not Config.get('packages'):
            self.help()
            print("-p <package> is required for this command")
            sys.exit(2)

        for package in Config.get('packages'):
            self._spksrc_manager.pprint_deps(package)

    def _command_print_parent_deps(self):
        print('Package parents dependencies:')

        if not Config.get('packages'):
            self.help()
            print("-p <package> is required for this command")
            sys.exit(2)

        for package in Config.get('packages'):
            self._spksrc_manager.pprint_parent_deps(package)

    def main(self):
        """
        main
        """

        args = self.read_args()

        logging.basicConfig(level=logging.getLevelName(Config.get('debug_level')))

        command = 'search'
        if args:
            command = args[0]

        if not Config.get('root'):
            self.help()
            print("<root> is required")
            sys.exit(2)

        self.check_spksc_dir()

        self.check_packages_list()

        self._spksrc_manager = PackagesManager()

        try:
            func = getattr(self, '_command_' + command)
            self._versions = func()
        except Exception as e:
            _LOGGER.warning('Command "%s" was not found or during call: %s' % (command, e,))
            return None


def main():
    logging_format = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()] %(message)s"
    logging.basicConfig(format=logging_format)
    app = Main()
    ret = app.main()
    sys.exit(ret)
