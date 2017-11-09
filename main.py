#!/usr/bin/env python3

import sys
import os
import getopt
import pprint
from datetime import datetime

import parsedatetime
import multiprocessing
from bootstrap.options import OPTIONS
from spksrc.spksrc_manager import SpksrcManager


class MainApp(object):

    def __init__(self):
        pass

    def help(self):
        print("""
Script to gather search update for spksrc package in cross/ and native/.

Usage:
  main.py [options] -r <root>

Parameters:
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
  -j --jobs                        Number of jobs (Default: max CPU core)
  -o --option "<key>=<value>"      Set an option

Available options:
  - packages
  - verbose
  - use_cache
  - update_deps
  - allow_major_release
  - allow_prerelease
  - cache_duration
  - work_dir
  - nb_jobs

""")

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
                OPTIONS['verbose'] = True
            elif opt in ("-c", "--disable-cache"):
                OPTIONS['use_cache'] = False
            elif opt in ("-r", "--root"):
                OPTIONS['root'] = arg.rstrip(os.path.sep) + os.path.sep
            elif opt in ("-p", "--packages"):
                OPTIONS['packages'] = arg.strip(os.path.sep).split(',')
            elif opt in ("-d", "--cache-duration"):
                cal = parsedatetime.Calendar()
                date_now = datetime.now().replace(microsecond=0)
                date, _ = cal.parseDT(arg, sourceTime=date_now)
                OPTIONS['cache_duration'] = (
                    date - date_now).total_seconds()
            elif opt in ("-w", "--work-dir"):
                OPTIONS['work_dir'] = arg.rstrip(os.path.sep)
            elif opt in ("-m", "--allow-major-release"):
                OPTIONS['allow_major_release'] = True
            elif opt in ("-a", "--allow-prerelease"):
                OPTIONS['allow_prerelease'] = True
            elif opt in ("-u", "--update-deps"):
                OPTIONS['update_deps'] = True
            elif opt in ("-j", "--jobs"):
                OPTIONS['nb_jobs'] = max(int(arg), 1)

    def check_spksc_dir(self):
        check = os.path.exists(OPTIONS['root'])
        check = check & os.path.isdir(OPTIONS['root'])
        check = check & os.path.isdir(OPTIONS['root'] + 'cross')
        check = check & os.path.isdir(OPTIONS['root'] + 'native')
        check = check & os.path.isdir(OPTIONS['root'] + 'spk')
        check = check & os.path.isdir(OPTIONS['root'] + 'toolchains')

        if not check:
            self.help()
            print("<root> have to be a root directory of spksrc")
            sys.exit(2)

    def check_packages_list(self):
        if OPTIONS['packages']:
            for package in OPTIONS['packages']:
                if not os.path.exists(OPTIONS['root'] + package + os.path.sep + 'Makefile'):
                    self.help()
                    print("<package> " + package +
                          " doesn't exist or it is not a valid spksrc package")
                    sys.exit(2)

    def main(self):
        """
        main
        """

        self.read_args()
        pass

        if not OPTIONS['root']:
            self.help()
            print("<root> is required")
            sys.exit(2)

        self.check_spksc_dir()

        self.check_packages_list()

        spksrc_manager = SpksrcManager()

        print('Package dependencies:')
        spksrc_manager.pprint_deps('spk/ffmpeg')

        print('Package parents dependencies:')
        spksrc_manager.pprint_parent_deps('cross/libogg')

        # spksrc_manager.pprint_deps(OPTIONS['packages'][0])

        spksrc_manager.check_update_packages()


if __name__ == '__main__':
    app = MainApp()
    sys.exit(app.main())
