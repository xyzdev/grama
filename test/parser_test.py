from nose.tools import assert_equal, assert_raises_regexp
from grama.grama import Instruction, Address, Parser


class Test(object):
    @staticmethod
    def assert_instruction(expected_action, expected_addr1, expected_addr2, expected_addr3, expected_ofs, actual):
        assert_equal(expected_action, actual.action)
        assert_equal(str(expected_addr1), str(actual.source))
        assert_equal(str(expected_addr2), str(actual.target))
        assert_equal(str(expected_addr3), str(actual.link))
        assert_equal(expected_ofs, actual.offset)

    def test_multiple_complex_statements_on_one_line(self):
        parser = Parser()
        instr = parser.parse("\\21;' '#';\\7d\n\\21/' '>' ';\\21/' '?' ':-1")
        assert_equal(4, len(instr))
        self.assert_instruction(Instruction.CREATE, Address('!'), None, None, 1, instr[0])
        self.assert_instruction(Instruction.CREATE, Address(' '), None, None, 1, instr[1])

        self.assert_instruction(Instruction.LINK, Address('!'), Address(' '), Address(' '), 1, instr[2])
        self.assert_instruction(Instruction.MATCH, Address('!', [' ']), Address(' '), None, -1, instr[3])

    def test_comment(self):
        parser = Parser()

        instr = parser.parse(" # Comment")
        assert_equal(0, len(instr))

        instr = parser.parse("# Comment with no leading space")
        assert_equal(0, len(instr))

        instr = parser.parse("a# Comment")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.CREATE, Address('a'), None, None, 1, instr[0])

        instr = parser.parse("a# Comment\nb # Comment")
        assert_equal(2, len(instr))
        self.assert_instruction(Instruction.CREATE, Address('a'), None, None, 1, instr[0])
        self.assert_instruction(Instruction.CREATE, Address('b'), None, None, 1, instr[1])

    def test_create(self):
        parser = Parser()
        instr = parser.parse("uncomplicated_concept_name")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.CREATE, Address('uncomplicated_concept_name'), None, None, 1, instr[0])

    def test_create_quoted(self):
        parser = Parser()
        instr = parser.parse("'uncomplicated_concept_name'")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.CREATE, Address('uncomplicated_concept_name'), None, None, 1, instr[0])

    def test_create_missing_end_quote(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'uncomplicated_concept_name")

    def test_create_quoted_complex(self):
        parser = Parser()
        instr = parser.parse("'\\27 />?:-;#\\41'#Comment'")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.CREATE, Address("' />?:-;#A"), None, None, 1, instr[0])

    def test_create_complex(self):
        parser = Parser()
        instr = parser.parse("\\27\\20\\2f\\3e\\3f\\3a-\\3b\\41#Comment'\n")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.CREATE, Address("' />?:-;A"), None, None, 1, instr[0])

    def test_create_path(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1:'):
            parser.parse("/a")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1:'):
            parser.parse("a/")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1:'):
            parser.parse("a/b")

    def test_link(self):
        parser = Parser()
        instr = parser.parse("uncomplicated_concept_name/uncompl_link>other_uncompl_name")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.LINK,
                                Address('uncomplicated_concept_name'),
                                Address('other_uncompl_name'),
                                Address('uncompl_link'), 1, instr[0])

    def test_link_target_link(self):
        parser = Parser()
        instr = parser.parse("uncomplicated_concept_name/uncompl_link>other_uncompl_name/other_link")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.LINK,
                                Address('uncomplicated_concept_name'),
                                Address('other_uncompl_name', ['other_link']),
                                Address('uncompl_link'), 1, instr[0])

    def test_link_source_link(self):
        parser = Parser()
        instr = parser.parse("uncomplicated_concept_name/other_src_link/uncompl_link>other_uncompl_name/other_link")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.LINK,
                                Address('uncomplicated_concept_name', ['other_src_link']),
                                Address('other_uncompl_name', ['other_link']),
                                Address('uncompl_link'), 1, instr[0])

    def test_link_quoted(self):
        parser = Parser()
        instr = parser.parse("'uncomplicated_concept_name'/'other_src_link'/'uncompl_link'>"
                             "'other_uncompl_name'/'other_link'")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.LINK,
                                Address('uncomplicated_concept_name', ['other_src_link']),
                                Address('other_uncompl_name', ['other_link']),
                                Address('uncompl_link'), 1, instr[0])

    def test_link_complex(self):
        parser = Parser()
        instr = parser.parse("\\27\\20\\2f\\3e\\3f\\3a-\\3b\\41/\\27\\20\\2f\\3e\\3f\\3a-\\3b\\42/"
                             "\\27\\20\\2f\\3e\\3f\\3a-\\3b\\43>"
                             "\\27\\20\\2f\\3e\\3f\\3a-\\3b\\44/\\27\\20\\2f\\3e\\3f\\3a-\\3b\\45 #Comment")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.LINK,
                                Address("' />?:-;A", ["' />?:-;B"]),
                                Address("' />?:-;D", ["' />?:-;E"]),
                                Address("' />?:-;C"), 1, instr[0])

    def test_link_quoted_complex(self):
        parser = Parser()
        instr = parser.parse("'\\27 />?:-;#\\41'/'\\27 />?:-;#\\42'/'\\27 />?:-;#\\43'>"
                             "'\\27 />?:-;#\\44'/'\\27 />?:-;#\\45'")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.LINK,
                                Address("' />?:-;#A", ["' />?:-;#B"]),
                                Address("' />?:-;#D", ["' />?:-;#E"]),
                                Address("' />?:-;#C"), 1, instr[0])

    def test_link_to_new(self):
        parser = Parser()
        instr = parser.parse("'\\27 />?:-;#\\41'/'\\27 />?:-;#\\42'/'\\27 />?:-;#\\43'>+")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.LINK,
                                Address("' />?:-;#A", ["' />?:-;#B"]),
                                Address(Address.NEW),
                                Address("' />?:-;#C"), 1, instr[0])

    def test_link_missing_quote(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a/'b'/'c'>'d'/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/'b/'c'>'d'/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/'b'/'c>'d'/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/'b'/'c'>'d/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/'b'/'c'>'d'/'e")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a'/'b'/'c'>'d'/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/b'/'c'>'d'/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/'b'/c'>'d'/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/'b'/'c'>d'/'e'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'/'b'/'c'>'d'/e'")

    def test_link_missing_link(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a>b/c")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/>b/c")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse(">b")

    def test_link_missing_target(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b/c")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>")

    def test_link_extra_slash(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("/a>b/c")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b/>c/d")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>/c/d")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>c/d/")

    def test_link_extra_link(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>c/c>d/e")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a>b>c")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>c/d>e")

    def test_link_unexpected_token(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>c?")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>c:")

    def test_match_simple(self):
        parser = Parser()
        instr = parser.parse("uncomplicated_concept_name?uncomplicated_concept_name2:2")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address('uncomplicated_concept_name'),
                                Address('uncomplicated_concept_name2'), None, 2, instr[0])

        instr = parser.parse("uncomplicated_concept_name?uncomplicated_concept_name2:-1")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address('uncomplicated_concept_name'),
                                Address('uncomplicated_concept_name2'), None, -1, instr[0])

        instr = parser.parse("uncomplicated_concept_name?uncomplicated_concept_name2:10")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address('uncomplicated_concept_name'),
                                Address('uncomplicated_concept_name2'), None, 10, instr[0])

    def test_match_simple_quoted(self):
        parser = Parser()
        instr = parser.parse("'uncomplicated_concept_name'?'uncomplicated_concept_name2':2")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address('uncomplicated_concept_name'),
                                Address('uncomplicated_concept_name2'), None, 2, instr[0])

    def test_match_complex(self):
        parser = Parser()
        instr = parser.parse("\\27\\20\\2f\\3e\\3f\\3a-\\3b\\41?\\27\\20\\2f\\3e\\3f\\3a-\\3b\\42:2")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address("' />?:-;A"),
                                Address("' />?:-;B"), None, 2, instr[0])

    def test_match_complex_quoted(self):
        parser = Parser()
        instr = parser.parse("'\\27 />?:-;#\\41'?'\\27 />?:-;#\\42':2")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address("' />?:-;#A"),
                                Address("' />?:-;#B"), None, 2, instr[0])

    def test_match_path(self):
        parser = Parser()
        instr = parser.parse("a/b/c?d/e/f:2")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address('a', ['b', 'c']),
                                Address('d', ['e', 'f']), None, 2, instr[0])

    def test_match_complex_path(self):
        parser = Parser()
        instr = parser.parse("'\\27 />?:-;#\\41'/'\\27 />?:-;#\\42'?"
                             "\\27\\20\\2f\\3e\\3f\\3a-\\3b\\43/\\27\\20\\2f\\3e\\3f\\3a-\\3b\\43:2")
        assert_equal(1, len(instr))
        self.assert_instruction(Instruction.MATCH,
                                Address("' />?:-;#A", ["' />?:-;#B"]),
                                Address("' />?:-;C", ["' />?:-;C"]), None, 2, instr[0])

    def test_illegal_match(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("?b:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?b:")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?:")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("?a:")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/?b:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b/?c:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?/b:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?b/:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?b/c/:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?b:c")

    def test_double_slahes(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a//b>c')

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a/b//c>d')

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a/b>c//d')

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a/b>c/d//e')

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a//b?c:1')

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a/b//c?d:1')

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a?b//c:1')

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse('a?b/c//d:1')

    def test_illegal_syntax(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("?")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse(":")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("/")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse(">")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("/")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a>b?:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?b>c:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a/b'>c")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/'b>c'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'b'")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("'a'b'?c:1")

    def test_illegal_new(self):
        parser = Parser()
        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("+")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/+")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("+/a")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("+/+")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("+/a>b")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/+>b")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>b/+")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b>+/+")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("+?b:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a?+:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/+?b:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b?+:1")

        with assert_raises_regexp(ValueError, 'Syntax error in statement on line 1'):
            parser.parse("a/b?c/+:1")
