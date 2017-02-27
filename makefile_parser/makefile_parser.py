
import sys
import pprint
import json
import pyparsing as pp

class MakefileParser(object):

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


    def _generate_str_possibility(self, arr):
        str_arr = []
        str_arr.append('')
        
        for s_arr in arr:
            new_arr = []
            for curr_str in str_arr:
                for k,v in enumerate(s_arr):
                    new_arr.append(curr_str + v)
            str_arr = new_arr
        
        return str_arr
        

    def _evaluate_result(self, parse_result, to_parse = False):
        str_ret = []
        for res in parse_result:
            
            if type(res) is pp.ParseResults:
                str_to_add = self._evaluate_result(res, True)
                str_ret.append(str_to_add)
            else:
                str_ret.append([res])
                
        str_gen = self._generate_str_possibility(str_ret)
        if to_parse is True:
            
            new_arr = []
            for s in str_gen:
                new_arr += self.parse_call(s)
            str_ret = new_arr
        else:
            str_ret = str_gen

        return str_ret


    def _call_subst(self, arguments):
        args = arguments.split(',')

        return args[2].replace(args[0], args[1])


    def parse_call(self, arguments):
        arguments = arguments.strip()

        args = arguments.split(' ')
        if len(args) == 0:
            return ['']

        first_arg = args.pop(0)

        if len(args) > 0:
            func_name = '_call_' + first_arg
            try:
                func = getattr(self, func_name)
                return [ func(' '.join(args)) ]
            except:
                return ['']
        else:
            if first_arg in self._vars:
                return self._vars[ first_arg ]

        return ['']


    def _parse_line(self, line):
        result = self._parser.searchString(line)
           
        if len(result) > 0:
            if result[0]['var'] not in self._vars:
                self._vars[ result[0]['var'] ] = []
                self._vars[ result[0]['var'] ].append('')
            
            if 'value' in result[0]:
                if len(self._vars[ result[0]['var'] ]) > 0 and self._vars[ result[0]['var'] ][0] == '':
                    self._vars[ result[0]['var'] ].pop(0)
                    
                self._vars[ result[0]['var'] ] += self._evaluate_result(result[0]['value'])
                

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
    
    
    def get_var(self, var):
        if var in self._vars:
            return self._vars[ var ]

        return None


    def pprint_vars(self):
        print("VARS = ")
        for k,l in self._vars.items():
            print("\t" + k + " = ")
            for v in l:
                print("\t\t" + v)
        
