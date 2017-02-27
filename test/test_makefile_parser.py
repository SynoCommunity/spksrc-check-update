import unittest
from makefile_parser.makefile_parser import MakefileParser

class TestMakefileParser(unittest.TestCase):
    def setUp(self):
        self.parser = MakefileParser()
        self.parser.parse_file('./test/test_makefile_parser_testfile')

    def test_value_simple_var(self):
        self.assertEqual(self.parser.get_var('PKG_NAME'), ['boost'])
        self.assertEqual(self.parser.get_var('PKG_VERS'), ['1.63.0'])

    def test_value_multiple_vars(self):
        self.assertEqual(self.parser.get_var('DEPENDS'), ['cross/bzip2 cross/zlib', 'cross/python'])

    def test_var_replacement(self):
        self.assertEqual(self.parser.get_var('PKG_DIST_SITE'), ['http://sourceforge.net/projects/boost/files/boost/1.63.0'])

    def test_function_subst(self):
        self.assertEqual(self.parser.get_var('PKG_DIR'), ['boost_1_63_0'])

    def test_value_generate(self):
        self.assertEqual(self.parser.get_var('NEW_DIST_NAME'), ['boost_1_5_1.tar.bz2', 'boost_1_6_0.tar.bz2'])

if __name__ == '__main__':
    unittest.main()
