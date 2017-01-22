import os

from nose.tools import assert_equal
from grama.grama import Machine, Address, Parser


class Test(object):
    def __init__(self):
        pass

    @staticmethod
    def assert_value(ma, path, expected):
        actual = ma.find(Address(*path))
        assert_equal(expected, actual.name, '%s:%s != %s' % (path, actual.name, expected))

    @staticmethod
    def subleq():
        inp = []
        out = []

        def pr(x):
            out.append(x)

        def rd():
            return inp.pop(0) + '\n'

        ma = Machine()
        ma.concepts['stdout'].stream = pr
        ma.concepts['stdin'].stream = rd
        program = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'programs', 'subleq.grama')
        with open(program, 'r') as f:
            source = f.read()

        ma.instructions.extend(Parser().parse(source))
        return ma, inp, out

    @staticmethod
    def op(inp, a, b, c=None):
        inp.append(str(len(inp) / 2))
        inp.append(str(a))
        inp.append(str(len(inp) / 2))
        inp.append(str(b))
        ip = len(inp) / 2
        inp.append(str(ip))
        inp.append(str(c) if c is not None else str(ip + 1))

    def test_subleq(self):
        ma, inp, out = self.subleq()

        self.op(inp, 9, 11)      # store -[9] at [11]
        self.op(inp, 11, 10)     # add -[9] to [10]
        self.op(inp, 9, 11, -1)  # subtract and terminate
        # Data
        self.op(inp, 2, 4, 0)
        inp.append('')

        ma.do()

        self.assert_value(ma, ('program', ['ip']), '-1')
        self.assert_value(ma, ('0', ['value']), '9')
        self.assert_value(ma, ('1', ['value']), '11')
        self.assert_value(ma, ('2', ['value']), '3')
        self.assert_value(ma, ('3', ['value']), '11')
        self.assert_value(ma, ('4', ['value']), '10')
        self.assert_value(ma, ('5', ['value']), '6')
        self.assert_value(ma, ('6', ['value']), '9')
        self.assert_value(ma, ('7', ['value']), '11')
        self.assert_value(ma, ('8', ['value']), '-1')
        self.assert_value(ma, ('9', ['value']), '2')
        self.assert_value(ma, ('10', ['value']), '6')  # [9] + [10] (2 + 4)
        self.assert_value(ma, ('11', ['value'] + ['next'] * 4), '0')

        assert_equal([], inp)
        assert_equal(['ip', 'value'] * 12 + ['ip'], out)

    def test_subleq_unknown_numbers(self):
        ma, inp, out = self.subleq()

        self.op(inp, 0, 2, -3)  # Terminate
        # Data
        self.op(inp, 8, 5, 9)
        inp.append('')

        inp.append('-1')  # -3/sign
        inp.append('-2')  # -3/next
        inp.append('-1')  # -3/next/next

        inp.append('1')  # 8/sign
        inp.append('7')  # 8/prev
        inp.append('6')  # 8/prev/prev
        inp.append('5')  # 8/prev/prev/prev

        inp.append('1')  # 9/sign
        inp.append('8')  # 9/prev

        ma.do()

        assert_equal([], inp)
        assert_equal(['ip', 'value'] * 6 + ['ip'] +
                     ['-3', 'sign', 'next', '-2', 'next',
                      '8', 'sign', 'prev', '7', 'prev', '6', 'prev', '9', 'sign', 'prev'],
                     out)

        self.assert_value(ma, ('9', ['sign']), '1')
        self.assert_value(ma, ('8', ['sign']), '1')
        self.assert_value(ma, ('7', ['sign']), '1')
        self.assert_value(ma, ('6', ['sign']), '1')
        self.assert_value(ma, ('5', ['sign']), '1')
        self.assert_value(ma, ('4', ['sign']), '1')
        self.assert_value(ma, ('3', ['sign']), '1')
        self.assert_value(ma, ('2', ['sign']), '1')
        self.assert_value(ma, ('1', ['sign']), '1')
        self.assert_value(ma, ('0', ['sign']), '0')
        self.assert_value(ma, ('-1', ['sign']), '-1')
        self.assert_value(ma, ('-2', ['sign']), '-1')
        self.assert_value(ma, ('-3', ['sign']), '-1')

        self.assert_value(ma, ('-3', ['next']), '-2')
        self.assert_value(ma, ('-2', ['next']), '-1')
        self.assert_value(ma, ('-1', ['next']), '0')
        self.assert_value(ma, ('0', ['next']), '1')
        self.assert_value(ma, ('1', ['next']), '2')
        self.assert_value(ma, ('2', ['next']), '3')
        self.assert_value(ma, ('3', ['next']), '4')
        self.assert_value(ma, ('4', ['next']), '5')
        self.assert_value(ma, ('5', ['next']), '6')
        self.assert_value(ma, ('6', ['next']), '7')
        self.assert_value(ma, ('7', ['next']), '8')
        self.assert_value(ma, ('8', ['next']), '9')
        assert_equal(ma.find(Address('9', ['next'])), None)

        self.assert_value(ma, ('program', ['ip']), '-3')
        self.assert_value(ma, ('0', ['value']), '0')
        self.assert_value(ma, ('1', ['value']), '2')
        self.assert_value(ma, ('2', ['value']), '-3')
        self.assert_value(ma, ('3', ['value']), '8')
        self.assert_value(ma, ('4', ['value']), '5')
        self.assert_value(ma, ('5', ['value']), '9')
        self.assert_value(ma, ('6', ['value']), '0')
        self.assert_value(ma, ('7', ['value']), '0')
        self.assert_value(ma, ('8', ['value']), '0')
        self.assert_value(ma, ('9', ['value']), '0')
