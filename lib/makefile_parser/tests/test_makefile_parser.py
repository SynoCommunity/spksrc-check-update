# -*- coding: utf-8 -*-

import unittest
from makefile_parser.makefile_parser import MakefileParser


class TestMakefileParser(unittest.TestCase):
    def setUp(self):
        self.parser = MakefileParser()
        self.parser.parse_file(
            './lib/makefile_parser/tests/test_makefile_parser_testfile')

    def test_parse_text(self):
        text = """TEST=10
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileParser()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10'])
        self.assertEqual(tmp_parser.get_var_values('VALUE'), ['56_10_11'])
        tmp_parser.del_vars_values()
        self.assertEqual(tmp_parser.get_var_values('TEST'), None)
        self.assertEqual(tmp_parser.get_var_values('VALUE'), None)

    def test_is_parsed(self):
        text = """TEST=10
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileParser()
        self.assertEqual(tmp_parser.is_parsed(), False)
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.is_parsed(), True)

    def test_default_value(self):
        self.assertEqual(self.parser.get_var_values('UNKNOW_VAR', ['DEFAULT_VALUE']), ['DEFAULT_VALUE'])

    def test_value_simple_var(self):
        self.assertEqual(self.parser.get_var_values('PKG_NAME'), ['boost'])
        self.assertEqual(self.parser.get_var_values('PKG_VERS'), ['1.63.0'])

    def test_value_multiple_vars(self):
        self.assertEqual(self.parser.get_var_values('DEPENDS'), [
                         'cross/bzip2 cross/zlib', 'cross/python'])

    def test_var_replacement(self):
        self.assertEqual(self.parser.get_var_values('PKG_DIST_SITE'), [
                         'http://sourceforge.net/projects/boost/files/boost/1.63.0'])

    def test_var_replacement_with_value_command(self):
        self.assertEqual(self.parser.get_var_values('PKG_DIST_SITE_VALUE'), [
                         'http://sourceforge.net/projects/boost/files/boost/1.63.0'])

    def test_value_generate(self):
        self.assertEqual(self.parser.get_var_values('NEW_DIST_NAME'), [
                         'boost_1_5_1.tar.bz2', 'boost_1_6_0.tar.bz2'])

    def test_call_value(self):
        self.assertEqual(self.parser.get_var_values(
            'TEST_CALL_VALUE'), ['AA 10'])

    def test_call_subst(self):
        self.assertEqual(self.parser.get_var_values(
            'PKG_DIR'), ['boost_1_63_0'])

    def test_call_empty(self):
        self.assertEqual(self.parser.get_var_values(
            'EMPTY_CALL'), ['11  33'])

    def test_call_empty2(self):
        self.assertEqual(self.parser.get_var_values(
            'EMPTY_CALL2'), ['11  33'])

    def test_call_unkonw(self):
        self.assertEqual(self.parser.get_var_values(
            'UNKNOW_CALL'), ['11  33'])

    def test_assigns(self):
        self.assertEqual(self.parser.get_var_values('ASSIGN1'), ['1'])
        self.assertEqual(self.parser.get_var_values('ASSIGN2'), ['2'])
        self.assertEqual(self.parser.get_var_values('ASSIGN3'), ['3'])
        self.assertEqual(self.parser.get_var_values('ASSIGN4'), ['4'])
        self.assertEqual(self.parser.get_var_values('ASSIGN5'), ['5'])

    def test_delete_var(self):
        self.parser.del_var_values('PKG_VERS')
        self.assertEqual(self.parser.get_var_values('PKG_VERS'), None)

    def test_reevaluate_var(self):
        self.parser.set_var_values('PKG_VERS', ['1.71.0'])
        self.parser.evaluate_var('PKG_DIST_NAME')
        self.assertEqual(self.parser.get_var_values(
            'PKG_DIST_NAME'), ['boost_1_71_0.tar.bz2'])

    def test_reevaluate_var_with_value_command(self):
        self.parser.set_var_values('PKG_VERS', ['1.71.0'])
        self.parser.evaluate_var('PKG_DIST_SITE_VALUE')
        self.assertEqual(self.parser.get_var_values(
            'PKG_DIST_SITE_VALUE'), ['http://sourceforge.net/projects/boost/files/boost/1.71.0'])

    def test_value_with_comment(self):
        self.assertEqual(self.parser.get_var_values(
            'VALUE_WITH_COMMENT'), ['10 11 '])

    def test_is_containing_call(self):
        self.assertEqual(self.parser.is_containing_call(
            'UNKNOW_VAR'), None)
        self.assertEqual(self.parser.is_containing_call(
            'VALUE'), False)
        self.assertEqual(self.parser.is_containing_call(
            'TEST_CALL_VALUE'), True)
        self.assertEqual(self.parser.is_containing_call(
            'VALUE_WITH_COMMENT'), False)


if __name__ == '__main__':
    unittest.main()
