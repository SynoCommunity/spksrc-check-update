# -*- coding: utf-8 -*-

import sys
import json
import copy
import logging
import pyparsing as pp
from .makefile_parser import MakefileParser

_LOGGER = logging.getLogger(__name__)


class MakefileUpdater(MakefileParser):

    def __init__(self):
        """ Initialize the Makefile parser
        """
        super().__init__()
        self._original_content = []
        self._updated_content = []

    def parse_file(self, file):
        """ Parse a Makefile file
        """
        _LOGGER.debug("parse_file: file: %s", file)
        file = open(file, "r")
        for line in file:
            self._original_content.append(line.rstrip('\n'))
            self._parse_line(line)
        file.close()
        self._updated_content = self._original_content
        self._is_parsed = True

    def parse_text(self, text):
        """ Parse a Makefile content
        """
        self._original_content = text.split('\n')
        self._updated_content = self._original_content
        super().parse_text(text)


    def _get_parser_updater(self, func):
        """ Return a parser which will replace value field by the function in parameter
        """
        parser = copy.copy(self._parser)

        def pp_look_for_field(x, field):
            if x.resultsName == field:
                return x
            try:
                for v in x:
                    res = pp_look_for_field(v, field)
                    if res:
                        return res
            except:
                return None
            return None

        value_field = pp_look_for_field(parser, 'value')
        value_field.setParseAction(func)

        return parser

    def update_content(self, var, idx=None):
        """ Update a var with his current value
        """
        if var not in self._vars:
            return False

        if self.is_containing_call(var):
            # TODO
            return False

        if idx is None:
            idx = []
        if not isinstance(idx, list):
            idx = [idx]

        i_var_values = 0
        for i, line in enumerate(self._updated_content):
            result = self._parser.searchString(line)
            if result:
                if result[0]['var'] == var:
                    if not idx or i_var_values in idx:
                        parser_updater = self._get_parser_updater(lambda toks: self._vars[var][i_var_values])
                        self._updated_content[i] = parser_updater.transformString(line)
                    i_var_values += 1

        return True

    def write_output(self):
        """ Return content with update fields
        """
        return '\n'.join(self._updated_content)

    def write_file(self, path):
        """ Write content with update fields in a file
        """
        file = open(path, 'w')
        file.write(self.write_output())
        file.close
