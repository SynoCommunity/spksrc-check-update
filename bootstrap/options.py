import multiprocessing

""" Store all defaults values
"""
DEFAULTS = {
    'spksrc_git_uri': 'https://github.com/SynoCommunity/spksrc.git',
    'spksrc_dir': 'spksrc-git'
}

""" Store all options
"""
OPTIONS = {
    'root': None,
    'packages': None,
    'verbose': False,
    'use_cache': True,
    'update_deps': False,
    'allow_major_release': False,
    'allow_prerelease': False,
    'build': False,
    'cache_dir': 'cache',
    'cache_duration_search_update_download': 24 * 3600 * 7,
    'cache_duration_search_update_versions': 24 * 3600 * 7,
    'cache_duration_spksrc_manager_packages': 24 * 3600 * 7,
    'cache_duration': 24 * 3600 * 7,
    'work_dir': 'work',
    'nb_jobs': multiprocessing.cpu_count()
}
