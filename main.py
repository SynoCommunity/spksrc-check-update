#!/usr/bin/env python3

import sys
import os
import getopt
import pprint
from spksrc.search_update import SearchUpdate



class MainApp(object):

    def __init__(self):
        self._root = None
        self._package = None
        self._verbose = False
        self._use_cache = True

    def help(self):
        print("""
Script to gather search update for spksrc package in cross/ and native/.

Usage:
  main.py [options] -r <root>

Options:
  -h --help                     Show this screen.
  -r --root=<root>              Root directory of spksrc
  -p --package=<package>        Package to check update (Optional)
  -c --verbose                  Verbose mode
  -v --disable-cache            Disable cache
""")

    def check_spksc_dir(self):
        check = os.path.exists(self._root)
        check = check & os.path.isdir(self._root)
        check = check & os.path.isdir(self._root + 'cross')
        check = check & os.path.isdir(self._root + 'native')
        check = check & os.path.isdir(self._root + 'spk')
        check = check & os.path.isdir(self._root + 'toolchains')

        return check;


    def read_args(self):
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hcr:p:", ["root=", "package="])
        except getopt.GetoptError as e:
            self.help()
            print(e)
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
            elif opt in ("-p", "--package"):
                self._package = arg.strip(os.path.sep)


    def find_makefile(self, path):
        result = []
        dirname = os.path.basename(path)
        for file in os.listdir(path):
            makefile = os.path.join(path, file, 'Makefile')
            if os.path.exists(makefile):
                result.append([dirname + os.path.sep + file, makefile])

        result.sort()

        return result


    def check_update_makefile(self, package, path):
        search_update = SearchUpdate(package, path)

        if self._use_cache == False:
            search_update.disable_cache()

        new_versions = search_update.search_updates()

        if not new_versions or len(new_versions) == 0:
            print("Error to find version for : "+package)
        else:
            pprint.pprint(new_versions)


    def main(self):
        """
        main
        """

        self.read_args()

        if self._root is None or len(self._root) == 0:
            self.help()
            print("<root> is required")
            sys.exit(2)

        if self.check_spksc_dir() == False:
            self.help()
            print("<root> have to be a root directory of spksrc")
            sys.exit(2)


        makefiles = None
        if self._package is not None:
            if not os.path.exists(self._root + self._package + os.path.sep + 'Makefile'):
                self.help()
                print("<package> " + self._package + " doesn't exist or it is not a valid spksrc package")
                sys.exit(2)

            makefiles = [[self._package, os.path.join(self._root, self._package, 'Makefile')]]
        else:
            makefiles = self.find_makefile(self._root + 'cross') + self.find_makefile(self._root + 'native')


        for makefile in makefiles:
            self.check_update_makefile(makefile[0], makefile[1])

if __name__ == '__main__':
    app = MainApp()
    sys.exit(app.main())
