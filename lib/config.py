# -*- coding: utf-8 -*-

import re
import logging
import multiprocessing
from datetime import datetime
import parsedatetime


def convert_duration(value):
    """ Convert an input duration in seconds
    """
    if type(value) is int:
        return value

    cal = parsedatetime.Calendar()
    date_now = datetime.now().replace(microsecond=0)
    date, _ = cal.parseDT(value, sourceTime=date_now)
    return (date - date_now).total_seconds()


configs = {
    'debug_level': {'default': 'INFO', 'type': int, 'convert': logging.getLevelName},

    'nb_jobs': {'default': multiprocessing.cpu_count(), 'type': int},

    'work_dir': {'default': 'work', 'type': str},

    'spksrc_git_dir': {'default': '%work_dir%/spksrc-git', 'type': str},
    'spksrc_git_uri': {'default': 'https://github.com/SynoCommunity/spksrc.git', 'type': str},
    'spksrc_git_branch': {'default': 'master', 'type': str},

    'cache_enabled': {'default': True, 'type': bool},
    'cache_dir': {'default': '%work_dir%/cache', 'type': str},
    'cache_duration': {'default': '7d', 'type': int, 'convert': convert_duration},
    'cache_duration_packages_manager': {'default': '%cache_duration%', 'type': int, 'convert': convert_duration},
    'cache_duration_search_update_download': {'default': '%cache_duration%', 'type': int, 'convert': convert_duration},

    'build_update_deps': {'default': False, 'type': bool},
    'build_major_release_allowed': {'default': False, 'type': bool},
    'build_prerelease_allowed': {'default': False, 'type': bool},

    'packages': {'default': [], 'type': list}
}


class Config:

    configs_cached = {}
    regex_config_replace = re.compile('%\w+%')

    @staticmethod
    def get_default(property_name, default=None):
        """ Get default property value
        """
        prop = configs.get(property_name)
        if prop:
            return prop['default']
        return default

    @staticmethod
    def get(property_name, default=None):
        """ Get property value
        """
        if property_name in Config.configs_cached:
            return Config.configs_cached[property_name]

        prop = configs.get(property_name)
        if not prop:
            return default

        value = prop.get('value') or prop.get('default')
        if type(value) is str:
            for match in Config.regex_config_replace.findall(value):
                replace_value = Config.get(match[1:-1])
                if replace_value:
                    if type(replace_value) is not str and value == match:
                        value = replace_value
                        break
                    else:
                        value = value.replace(match, str(replace_value))
                else:
                    value = value.replace(match, "")

        value = Config.convert(prop, value)
        Config.configs_cached[property_name] = value

        return value

    @staticmethod
    def set(property_name, value):
        """ Set new property value
        """
        Config.clear_cache(property_name)

        if not property_name in configs:
            configs[property_name] = {'default': value, 'type': str}
        configs[property_name]['value'] = value

    @staticmethod
    def clear_cache(property_name):
        """ Clear cache for property
        """
        if property_name in Config.configs_cached:
            del Config.configs_cached[property_name]

        prop_var = '%' + property_name + '%'
        for (key, prop) in configs.items():
            if key in Config.configs_cached:
                prop_value = prop.get('value') or prop.get('default')
                if prop_var in prop_value:
                    Config.clear_cache(key)

    @staticmethod
    def convert(prop, value):
        """ Convert value to property type
        """
        if 'convert' in prop and callable(prop['convert']):
            value = prop['convert'](value)

        type_ = prop['type']
        return type_(value)
