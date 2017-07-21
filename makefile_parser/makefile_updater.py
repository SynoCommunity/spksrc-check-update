
import sys
import json
import copy
import logging
import pyparsing as pp

_LOGGER = logging.getLogger(__name__)

class MakefileUpdater(object):

    def __init__(self, makefile, method, version):
        

        """ Initialize the Makefile parser and private variables
        """
        self._parser = self._get_parser()
        self._vars_not_evaluate = {}
        self._vars = {}


    def _get_parser(self):
        """ Initialize the pyparsing parser for Makefile 
        """
        assign = pp.oneOf(['=', '?=', ':=', '::=', '+='])('assign')
        var_name = pp.Word(pp.alphas+'_', pp.alphanums+'_')('var')

        enclosed = pp.Forward()
        nestedParens = pp.nestedExpr('$(', ')', content=enclosed)
        nestedBrackets = pp.nestedExpr('${', '}', content=enclosed)
        enclosed <<= (nestedParens | nestedBrackets | pp.CharsNotIn('$(){}\n')).leaveWhitespace()

        return pp.lineStart + var_name + assign + pp.ZeroOrMore(pp.White()) + pp.ZeroOrMore(enclosed)('value')
