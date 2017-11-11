#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys

script_dir = os.path.dirname(os.path.realpath(__file__))
is_bundle = getattr(sys, 'frozen', False)
is_local = not is_bundle

if is_local:
    import imp
    imp.load_module('spksrc_updater', *imp.find_module('lib'))

from spksrc_updater.main import main

if __name__ == '__main__':
    main()
