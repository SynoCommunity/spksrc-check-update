#!/usr/bin/env python3
"""Script to gather search update for spksrc package in cross/ and native/."""
import sys
from makefile_parser.makefile_parser import MakefileParser

def main():
    """Main entry point for the script."""
    p = MakefileParser()
    p.parse_file('./test/test_makefile_parser_testfile')

    print(p.get_var('PKG_NAME'))
    p.pprint_vars()
    
if __name__ == '__main__':
    sys.exit(main())
