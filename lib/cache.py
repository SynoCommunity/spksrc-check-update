# -*- coding: utf-8 -*-

import os
import pickle
import time
import logging

from .config import Config

_LOGGER = logging.getLogger(__name__)


class Cache:

    def __init__(self, **kwargs):
        self._duration = kwargs.get('duration', Config.get("cache_duration"))
        self._dir = kwargs.get('dir', Config.get("cache_dir"))

    def save(self, filename, data):
        """ Save cache in a file
        """
        path = os.path.join(self._dir, filename)
        parent_dir = os.path.dirname(path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        with open(path, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
        _LOGGER.debug("Save in %s", path)

    def check(self, filename, duration=None):
        """ Check cache from a file
        """
        path = os.path.join(self._dir, filename)
        if not Config.get('cache_enabled'):
            return False

        c_duration = duration or self._duration
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if (mtime + c_duration) > time.time():
                _LOGGER.debug("Valid cache for: %s", path)
                return True
        return False

    def load(self, filename, duration=None):
        """ Load cache from a file
        """
        path = os.path.join(self._dir, filename)
        if not Config.get('cache_enabled'):
            return None

        path = os.path.join(self._dir, filename)
        if not duration and os.path.exists(path) or duration and self.check(filename, duration):
            with open(path, 'rb') as f:
                return pickle.load(f)

        return None

    def clear(self, filename):
        """ Delete file
        """
        path = os.path.join(self._dir, filename)
        if os.path.exists(path):
            os.remove(path)
