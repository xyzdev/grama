import os

from nose.tools import assert_equal
from grama.grama import Machine, Address, Parser


def assert_value(ma, path, expected):
    actual = ma.find(Address(*path))
    if actual.name != expected:
        raise Exception('%s:%s != %s' % (path, actual.name, expected))


class Test(object):
    def __init__(self):
        pass

    def bf(self):
        inp = []
        out = []

        def pr(x):
            out.append(x)

        def rd():
            return inp.pop(0)

        ma = Machine()
        ma.concepts['stdout'].stream = pr
        ma.concepts['stdin'].stream = rd

        program = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'programs', 'bf.grama')
        with open(program, 'r') as f:
            source = f.read()

        ma.instructions.extend(Parser().parse(source))
        return ma, inp, out

    def test_bf(self):
        ma, inp, out = self.bf()
        for instr in ',+++>+<[->+<]>.!A':  # 'A'+5+1 = 'E'
            inp.append(instr + '\n')

        ma.do()
        assert_value(ma, ('program', ['ip', 'value']), '!')

        a1 = ma.find(Address('memory', ['next'])).name
        assert_value(ma, ('ptr', ['cell']), a1)
        assert_value(ma, (a1, ['value']), 'E')
        assert_equal(['E'], out)

    def test_bf2(self):
        ma, inp, out = self.bf()

        for instr in '+++>+<[->>++[-<+>]<<]>.!':  # 1+3*2
            inp.append(instr + '\n')

        ma.do()
        assert_value(ma, ('program', ['ip', 'value']), '!')
        a1 = ma.find(Address('memory', ['next'])).name
        assert_value(ma, ('ptr', ['cell']), a1)
        assert_value(ma, (a1, ['value']), '\7')
        assert_equal(['\x07'], out)
