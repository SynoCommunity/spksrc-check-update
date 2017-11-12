# -*- coding: utf-8 -*-

import copy
import logging
import pyparsing as pp

_LOGGER = logging.getLogger(__name__)


class MakefileParser(object):

    def __init__(self):
        """ Initialize the Makefile parser and private variables
        """
        self._parser = self._get_parser()
        self._vars_not_evaluate = {}
        self._vars = {}
        self._is_parsed = False

    def _get_parser(self):
        """ Initialize the pyparsing parser for Makefile 
        """
        assign = pp.oneOf(['=', '?=', ':=', '::=', '+='])('assign')
        var_name = pp.Word(pp.alphas + '_', pp.alphanums + '_')('var')

        enclosed = pp.Forward()
        nested_parents = pp.nestedExpr('$(', ')', content=enclosed)
        nested_brackets = pp.nestedExpr('${', '}', content=enclosed)
        enclosed <<= (nested_parents | nested_brackets |
                      pp.CharsNotIn('$(){}#\n')).leaveWhitespace()

        return pp.lineStart + var_name + assign + pp.ZeroOrMore(pp.White()) + pp.ZeroOrMore(enclosed)('value') + pp.Optional(pp.pythonStyleComment)('comment')

    def _generate_str_possibility(self, arr):
        str_arr = []
        str_arr.append('')

        for s_arr in arr:
            new_arr = []
            for curr_str in str_arr:
                for k, v in enumerate(s_arr):
                    new_arr.append(curr_str + v)
            str_arr = new_arr

        return str_arr

    def _call_value(self, arguments, re_evaluate_values):
        """ Execute the call $(value VAR) from Makefile
        """
        if re_evaluate_values:
            self.evaluate_var(arguments)

        return self._vars[arguments]

    def _call_subst(self, arguments, re_evaluate_values):
        """ Execute the call $(subst b,a,a b c d) from Makefile
        """
        args = arguments.split(',')

        return args[2].replace(args[0], args[1])

    def parse_call(self, arguments, re_evaluate_values=False):
        """ Parse the calls $(VAR) or $(xxx yyy zzz) and execute it
        """
        arguments = arguments.strip()

        args = arguments.split(' ')
        if not args:
            return ['']

        first_arg = args.pop(0)

        if args:
            func_name = '_call_' + first_arg
            func_args = ' '.join(args)
            _LOGGER.debug("parse_call: '%s' with args: %s",
                          first_arg, func_args)
            try:
                func = getattr(self, func_name)
                value = func(func_args, re_evaluate_values)
                _LOGGER.debug("parse_call: return %s", value)
                if type(value) is list:
                    return value

                return [value]
            except:
                return ['']
        else:
            if first_arg in self._vars:
                if re_evaluate_values:
                    self.evaluate_var(first_arg)

                return self._vars[first_arg]

        return ['']

    def evaluate_result(self, parse_result, re_evaluate_values=False, to_parse=False):
        str_ret = []
        for res in parse_result:

            if isinstance(res, pp.ParseResults):
                str_to_add = self.evaluate_result(
                    res, re_evaluate_values, True)
                str_ret.append(str_to_add)
            else:
                str_ret.append([res])

        str_gen = self._generate_str_possibility(str_ret)
        if to_parse is True:

            new_arr = []
            for s in str_gen:
                new_arr += self.parse_call(s, re_evaluate_values)
            str_ret = new_arr
        else:
            str_ret = str_gen

        return str_ret

    def _parse_line(self, line):
        """ Parse one line of Makefile content
        """
        result = self._parser.searchString(line)

        if result:
            if result[0]['var'] not in self._vars:
                self._vars_not_evaluate[result[0]['var']] = []
                self._vars_not_evaluate[result[0]['var']].append('')
                self._vars[result[0]['var']] = []
                self._vars[result[0]['var']].append('')

            if 'value' in result[0]:
                if self._vars[result[0]['var']] and self._vars[result[0]['var']][0] == '':
                    self._vars_not_evaluate[result[0]['var']].pop(0)
                    self._vars[result[0]['var']].pop(0)

                _LOGGER.debug("_parse_line: evalute var: %s",
                              result[0]['var'])
                self._vars_not_evaluate[result[0]
                                        ['var']].append(result[0]['value'])
                self._vars[result[0]['var']
                           ] += self.evaluate_result(result[0]['value'])

    def parse_file(self, file):
        """ Parse a Makefile file
        """
        _LOGGER.debug("parse_file: file: %s", file)
        file = open(file, "r")
        for line in file:
            self._parse_line(line)
        file.close()
        self._is_parsed = True

    def parse_text(self, text):
        """ Parse a Makefile content
        """
        _LOGGER.debug("parse_text: text: %s", text)
        lines = text.split('\n')
        for line in lines:
            self._parse_line(line)
        self._is_parsed = True

    def del_vars_values(self):
        """ Delete all variables parsed from the Makefile
        """
        self._vars = {}

    def del_var_values(self, var):
        """ Delete one variable parsed from the Makefile
        """
        if var in self._vars:
            del self._vars[var]

    def get_vars_values(self):
        """ Get the values of all variables from the parsed Makefile
        """
        return copy.copy(self._vars)

    def get_var_values(self, var, default=None):
        """ Get the values of a variable from the parsed Makefile
        """
        if var in self._vars:
            return copy.copy(self._vars[var])

        return default

    def set_var_values(self, var, value, value_not_evaluate=None):
        """ Set a value for a variable
        """
        _LOGGER.debug("set_var_values: var: %s, value: %s", var, value)
        if not value_not_evaluate:
            value_not_evaluate = value

        if not isinstance(value, list):
            value = [value]

        if not isinstance(value_not_evaluate, list):
            value_not_evaluate = [value_not_evaluate]

        self._vars_not_evaluate[var] = value_not_evaluate
        self._vars[var] = value

    def evaluate_var(self, var):
        """ Ask to re-evaluate the values of a variable by using the values of the others variables 
        """
        _LOGGER.debug("evaluate_var: var: %s", var)
        if var in self._vars_not_evaluate:
            self._vars[var] = []
            for v in self._vars_not_evaluate[var]:
                self._vars[var] += self.evaluate_result(v, True)

    def is_parsed(self):
        """ Return if parse_file or parse_text was called
        """
        return self._is_parsed
