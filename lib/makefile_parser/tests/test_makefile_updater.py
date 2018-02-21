# -*- coding: utf-8 -*-

import unittest
from makefile_parser.makefile_updater import MakefileUpdater


class TestMakefileUpdater(unittest.TestCase):
    def setUp(self):
        pass

    def test_update_var_value(self):
        text = """TEST=10
VALUE=56_$(TEST)_11"""
        text_excepted = """TEST=9876
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10'])
        self.assertEqual(tmp_parser.get_var_values('VALUE'), ['56_10_11'])

        tmp_parser.set_var_values('TEST', '9876')
        tmp_parser.set_var_values('VALUE', '99_88_77')

        self.assertEqual(tmp_parser.get_var_values('TEST'), ['9876'])
        self.assertEqual(tmp_parser.get_var_values('VALUE'), ['99_88_77'])

        self.assertEqual(tmp_parser.update_content('TEST'), True)
        self.assertEqual(tmp_parser.write_output(), text_excepted)

    def test_update_unkown_var_value(self):
        text = """TEST=10
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.update_content('UNKONW_VAR'), False)

    def test_update_var_value_with_call(self):
        text = """TEST=10
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.update_content('VALUE'), False)

    def test_update_var_multiple_values_keep_same(self):
        text = """AAAA=1000
TEST=10
TEST=21
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('AAAA'), ['1000'])
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10', '21'])
        self.assertEqual(tmp_parser.get_var_values('VALUE'), ['56_10_11', '56_21_11'])
        self.assertEqual(tmp_parser.update_content('TEST'), True)
        self.assertEqual(tmp_parser.write_output(), text)

    def test_update_var_multiple_values_update(self):
        text = """AAAA=1000
TEST=10
TEST=66
TEST=21
VALUE=56_$(TEST)_11"""
        text_excepted = """AAAA=1000
TEST=9876
TEST=66
TEST=21
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10', '66', '21'])

        tmp_parser.set_var_values('TEST', '9876')

        self.assertEqual(tmp_parser.get_var_values('TEST'), ['9876'])

        self.assertEqual(tmp_parser.update_content('TEST'), True)
        self.assertEqual(tmp_parser.write_output(), text_excepted)

    def test_update_var_multiple_values_update_all(self):
        text = """AAAA=1000
TEST=10
TEST=66
TEST=21
VALUE=56_$(TEST)_11"""
        text_excepted = """AAAA=1000
TEST=9876
TEST=6543
TEST=1234
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10', '66', '21'])

        tmp_parser.set_var_values('TEST', ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.get_var_values('TEST'), ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.update_content('TEST'), True)
        self.assertEqual(tmp_parser.write_output(), text_excepted)

    def test_update_var_multiple_values_update_first(self):
        text = """AAAA=1000
TEST=10
TEST=66
TEST=21
VALUE=56_$(TEST)_11"""
        text_excepted = """AAAA=1000
TEST=9876
TEST=66
TEST=21
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10', '66', '21'])

        tmp_parser.set_var_values('TEST', ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.get_var_values('TEST'), ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.update_content('TEST', idx=0), True)
        self.assertEqual(tmp_parser.write_output(), text_excepted)

    def test_update_var_multiple_values_update_last(self):
        text = """AAAA=1000
TEST=10
TEST=66
TEST=21
VALUE=56_$(TEST)_11"""
        text_excepted = """AAAA=1000
TEST=10
TEST=66
TEST=1234
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10', '66', '21'])

        tmp_parser.set_var_values('TEST', ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.get_var_values('TEST'), ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.update_content('TEST', idx=2), True)
        self.assertEqual(tmp_parser.write_output(), text_excepted)

    def test_update_var_multiple_values_update_multiple(self):
        text = """AAAA=1000
TEST=10
TEST=66
TEST=21
VALUE=56_$(TEST)_11"""
        text_excepted = """AAAA=1000
TEST=10
TEST=6543
TEST=1234
VALUE=56_$(TEST)_11"""
        tmp_parser = MakefileUpdater()
        tmp_parser.parse_text(text)
        self.assertEqual(tmp_parser.get_var_values('TEST'), ['10', '66', '21'])

        tmp_parser.set_var_values('TEST', ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.get_var_values('TEST'), ['9876', '6543', '1234'])

        self.assertEqual(tmp_parser.update_content('TEST', idx=[1,2]), True)
        self.assertEqual(tmp_parser.write_output(), text_excepted)

if __name__ == '__main__':
    unittest.main()
