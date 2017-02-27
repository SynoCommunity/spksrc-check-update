
import sys
from makefile_parser.makefile_parser import MakefileParser

class SearchUpdate(object):

    def __init__(self, path):
        self._path = path
        self._parser = MakefileParser()
        self._parser.parse_file(path)
        
        
    def get_version(self):
        version = self._parser.get_var('PKG_VERS')
        if version is None:
            version = self._parser.get_var('PKG_VERS_MAJOR')
            
            if version is not None:
                version_minor = self._parser.get_var('PKG_VERS_MINOR')
                if version_minor is not None:
                    version[0] += '.' + version_minor[0]
                    version_patch = self._parser.get_var('PKG_VERS_PATCH')
                    if version_patch is not None:
                        version[0] += '.' + version_patch[0]
                version = version[0]
        else:
            version = version[0]
        
        return version
        
        
    def search(self):
        
        version = self.get_version()
        
        print(version)
        



