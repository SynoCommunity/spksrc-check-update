
import sys
import pprint
import json
import copy
import pyparsing as pp

class MakefileParserSimple(object):

    def __init__(self):
        self._parser = self._get_parser()
        self._vars = {}


    def _get_parser(self):
        assign = pp.oneOf(['=', '?=', ':=', '::=', '+='])('assign')
        var_name = pp.Word(pp.alphas+'_', pp.alphanums+'_')('var')

        enclosed = pp.Forward()
        nestedParens = pp.nestedExpr('$(', ')', content=enclosed)
        nestedBrackets = pp.nestedExpr('${', '}', content=enclosed)
        enclosed <<= (nestedParens | nestedBrackets | pp.CharsNotIn('$(){}\n')).leaveWhitespace()

        return pp.lineStart + var_name + assign + pp.ZeroOrMore(pp.White()) + pp.ZeroOrMore(enclosed)('value')


    def _call_subst(self, arguments):
        args = arguments.split(',')

        return args[2].replace(args[0], args[1])


    def parse_call(self, arguments):
        arguments = arguments.strip()

        args = arguments.split(' ')
        if len(args) == 0:
            return ''

        first_arg = args.pop(0)

        if len(args) > 0:
            func_name = '_call_' + first_arg
            try:
                func = getattr(self, func_name)
                return func(' '.join(args))
            except:
                return ''
        else:
            if first_arg in self._vars:
                return self._vars[ first_arg ]

        return ''


    def _evaluate_result(self, parse_result, to_parse = False):
        str_ret = ''
        for res in parse_result:

            if type(res) is pp.ParseResults:
                str_ret += evaluate(res, True)
            else:
                str_ret += res

        if to_parse is True:
            str_ret = self.parse_call(str_ret)

        return str_ret


    def _parse_line(self, line):
        result = self._parser.searchString(line)

        if len(result) > 0:
            self._vars[ result[0]['var'] ] = ''
            if 'value' in result[0]:
                self._vars[ result[0]['var'] ] = self._evaluate_result(result[0]['value'])


    def reset_vars(self):
        self._vars = {}


    def parse_file(self, file):
        file = open(file, "r")
        for line in file:
            self._parse_line(line)
        file.close()


    def parse_text(self, text):
        lines = text.split('\n')
        for line in lines:
            self._parse_line(line)


    def get_var(self, var, default = None):
        if var in self._vars:
            return copy.copy(self._vars[ var ])

        return default


    def pprint_vars(self):
        print("VARS = ")
        for k,v in self._vars.items():
            print("\t" + k + " = " + v)

