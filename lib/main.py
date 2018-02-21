# -*- coding: utf-8 -*-

import sys
import os
import getopt
import logging
import multiprocessing
from datetime import datetime
import parsedatetime
from .config import Config
from .packages_manager import PackagesManager

_LOGGER = logging.getLogger(__name__)

# logging_format = "[%(levelname)s][%(filename)s:%(lineno)s:%(funcName)s()] %(message)s"
logging_format = "[%(levelname)s]%(message)s"

class Main(object):

    def __init__(self):
        self._packages = []
        pass

    def version(self):
        import imp
        version = imp.load_source('version', 'lib/version.py')
        print(version.SPKSRC_UPDATER_VERSION)

    def help(self):
        from .config import configs
        str_options = ""
        for (key, prop) in configs.items():
            str_options += "  - {:<40} {} (Default: {})\n".format(key, prop.get('description', ''), Config.get_default(key),)

        print("""
Script to gather search update for spksrc package in cross/ and native/.

Usage:
  spksrc-updater.py [options] [action]

Action:
  - search                                  Search for new updates
  - search_all                              Search for new updates and print all new versions
  - build                                   Launch build for the new packages
  - print_deps                              Prints all dependancies
  - print_parent_deps                       Prints all parent dependancies

Parameters:
  - Global:
    -h --help                               Show this screen.
    -v --version                            Print version
    -d --debug=<level>                      Debug level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    -w --work-dir=<directory>               Work directory (Default: {})
    -r --root=<root>                        Root directory of spksrc
    -p --packages=<package,package>         Packages to check for update
    -j --jobs                               Number of jobs (Default: max CPU core)
    -o --option "<key>=<value>"             Set an option

  - Cache:
    -c --disable-cache                      Disable cache
    -e --cache-duration=<duration>          Cache duration in seconds (Default: {})

  - Build:
    -m --allow-major-release                Allow to update to next major version (Default: False)
    -a --allow-prerelease                   Allow prerelease version (Default: False)
    -u --update-deps                        Update deps before build the current package (Default: False)

Available options:
{}

Examples:

  - Search news version for ALL packages:
        python spksrc-updater.py -r ../spksrc search

  - Launch build for the new release of ffmpeg:
        python spksrc-updater.py -r ../spksrc -p cross/ffmpeg build

  - Launch build for the new release of zlib and ffmpeg:
        python spksrc-updater.py -r ../spksrc -p cross/zlib,cross/ffmpeg build

  - Launch build for the new major release of ffmpeg:
        python spksrc-updater.py -r ../spksrc -p cross/ffmpeg --allow-major-release build

  - Launch build for the new release of ffmpeg and all its dependencies:
        python spksrc-updater.py -r ../spksrc -p cross/ffmpeg --allow-prerelease build

""".format(Config.get_default('work_dir'), Config.get_default('cache_duration'), str_options))

    def read_args(self):
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hcvmaur:p:d:w:j:o:e:", [
                "jobs="
                "debug=",
                "work-dir=",
                "root=",
                "packages=",
                "cache-duration=",
                "otpion=",
                "version",
                "disable-cache",
                "update-deps",
                "allow-major-release",
                "allow-prerelease",
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
                Config.set('spksrc_git_dir', arg.rstrip(os.path.sep) + os.path.sep)
            elif opt in ("-p", "--packages"):
                self._packages = arg.strip(os.path.sep).split(',')
            elif opt in ("-d", "--debug"):
                Config.set('debug_level', arg)
            elif opt in ("-e", "--cache-duration"):
                Config.set('cache_duration', arg)
            elif opt in ("-w", "--work-dir"):
                Config.set('work_dir', arg.rstrip(os.path.sep))
            elif opt in ("-m", "--allow-major-release"):
                Config.set('build_major_release_allowed', True)
            elif opt in ("-a", "--allow-prerelease"):
                Config.set('build_prerelease_allowed', True)
            elif opt in ("-u", "--update-deps"):
                Config.set('build_update_deps', True)
            elif opt in ("-j", "--jobs"):
                Config.set('nb_jobs', max(int(arg), 1))
            elif opt in ("-o", "--option"):
                option = arg.split('=')
                if len(option) > 1:
                    if not Config.set(option[0], option[1]):
                        self.help()
                        _LOGGER.error("Option %s is unknown", option[0])
                        sys.exit(2)
                else:
                    self.help()
                    _LOGGER.error("Invalid option format: %s", arg)
                    sys.exit(2)

        return args

    def check_spksc_dir(self):
        check = os.path.exists(Config.get('spksrc_git_dir'))
        check = check & os.path.isdir(Config.get('spksrc_git_dir'))
        check = check & os.path.isdir(Config.get('spksrc_git_dir') + 'cross')
        check = check & os.path.isdir(Config.get('spksrc_git_dir') + 'native')
        check = check & os.path.isdir(Config.get('spksrc_git_dir') + 'spk')
        check = check & os.path.isdir(
            Config.get('spksrc_git_dir') + 'toolchains')

        if not check:
            self.help()
            print("<root> have to be a root directory of spksrc")
            sys.exit(2)

    def check_packages_list(self):
        if self._packages:
            for package in self._packages:
                if not os.path.exists(Config.get('spksrc_git_dir') + package + os.path.sep + 'Makefile'):
                    self.help()
                    print("<package> " + package + " doesn't exist or it is not a valid spksrc package")
                    sys.exit(2)

    def _command_search(self):
        self._spksrc_manager.check_update_packages()
        self._spksrc_manager.pprint_next_version()

    def _command_search_all(self):
        self._spksrc_manager.check_update_packages()
        self._spksrc_manager.pprint_new_versions()

    def _command_build(self):
        pass

    def _command_print_deps(self):
        print('Package dependencies:')

        if not self._packages:
            self.help()
            print("-p <package> is required for this command")
            sys.exit(2)

        for package in self._packages:
            self._spksrc_manager.pprint_deps(package)

    def _command_print_parent_deps(self):
        print('Package parents dependencies:')

        if not self._packages:
            self.help()
            print("-p <package> is required for this command")
            sys.exit(2)

        for package in self._packages:
            self._spksrc_manager.pprint_parent_deps(package)

    def main(self):
        """
        main
        """

        args = self.read_args()

        logging.basicConfig(format=logging_format,level=Config.get('debug_level'))

        command = 'search'
        if args:
            command = args[0]

        if not Config.get('spksrc_git_dir'):
            self.help()
            print("<root> is required")
            sys.exit(2)

        self.check_spksc_dir()

        self.check_packages_list()

        self._spksrc_manager = PackagesManager(self._packages)

        try:
            func = getattr(self, '_command_' + command)
        except AttributeError as e:
            _LOGGER.warning('Command "%s" was not found or during call: %s', command, e)
            return None

        self._versions = func()

def main():
    app = Main()
    ret = app.main()
    sys.exit(ret)
