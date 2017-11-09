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
    'packages': None,
    'verbose': False,
    'use_cache': True,
    'update_deps': False,
    'allow_major_release': False,
    'allow_prerelease': False,
    'cache_duration': 24 * 3600 * 7,
    'work_dir': 'work',
    'nb_jobs': multiprocessing.cpu_count()
}
