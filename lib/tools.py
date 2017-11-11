# -*- coding: utf-8 -*-

import os
import pickle
import time
import logging

_LOGGER = logging.getLogger(__name__)


class Tools:

    @staticmethod
    def cache_save(filename, data):
        """ Save cache in a file
        """

        parent_dir = os.path.dirname(filename)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        with open(filename, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
        _LOGGER.debug("cache_save: path: %s" % (filename,))

    @staticmethod
    def cache_check(filename, duration=3600):
        """ Check cache from a file
        """
        if os.path.exists(filename):
            mtime = os.path.getmtime(filename)
            if (mtime + duration) > time.time():
                _LOGGER.debug("cache_check: valid cache for: %s" % (filename,))
                return True
        return False

    @staticmethod
    def cache_load(filename, duration=None):
        """ Load cache from a file
        """
        if not duration and os.path.exists(filename) or duration and Tools.cache_check(filename, duration):
            with open(filename, 'rb') as f:
                return pickle.load(f)

        return None
