# -*- coding: utf-8 -*-

import os
import pickle
import time
import logging
import inspect
from pkg_resources import parse_version

_LOGGER = logging.getLogger(__name__)


class Tools:

    @staticmethod
    def get_next_major_version(version):
        """
        Given a parsed version from pkg_resources.parse_version, returns a new
        version string with the major minor version.

        Examples
        ========
        >>> _next_major_version(pkg_resources.parse_version('1.2.3'))
        '2.0.0'
        """

        if hasattr(version, 'base_version'):
            # New version parsing from setuptools >= 8.0
            if version.base_version:
                parts = version.base_version.split('.')
            else:
                parts = []
        else:
            parts = []
            for part in version:
                if part.startswith('*'):
                    break
                parts.append(part)

        parts = [p for p in parts]

        if len(parts) < 3:
            parts += [0] * (3 - len(parts))

        major, minor, micro = parts[:3]

        try:
            major = int(major)
        except:
            return None

        return parse_version('{0}.{1}.{2}'.format(major + 1, 0, 0))

    @staticmethod
    def get_next_major_version_prerelease(version):
        """
        Given a parsed version from pkg_resources.parse_version, returns a new
        version string with the next major version included '-dev0' to ignore new pre-release.

        Examples
        ========
        >>> _next_major_version(pkg_resources.parse_version('1.2.3'))
        '2.0.0-r0'
        """
        return parse_version('{0}-dev0'.format(Tools.get_next_major_version(version)))
