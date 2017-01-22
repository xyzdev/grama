from nose.tools import assert_equal
from grama.grama import Machine, Instruction, Address


class Test(object):
    @staticmethod
    def build():
        inp = []
        out = []

        def pr(x):
            out.append(x)

        def rd():
            return inp.pop(0)

        ma = Machine()
        ma.concepts['stdout'].stream = pr
        ma.concepts['stdin'].stream = rd

        return ma, inp, out

    @staticmethod
    def assert_value(ma, path, expected):
        actual = ma.find(Address(*path))
        assert_equal(expected, actual.name, '%s:%s != %s' % (path, actual.name, expected))

    @staticmethod
    def assert_concepts(ma, expected):
        expected.update({'write', 'read', 'stdin', 'stdout', 'stddbg', 'break', 'eof',
                         ma.find(Address('stdin', ['eof'])).name})
        assert_equal(expected, set(ma.concepts.keys()))

    def test_create(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))

        ma.do()
        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_concepts(ma, {'foo'})

    def test_create_duplicate(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))

        ma.do()
        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_concepts(ma, {'foo'})

    def test_link(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('baz')))

        ma.do()

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')

        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('baz')).links)

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address('baz'), Address('foo')))

        ma.do()

        self.assert_value(ma, ('foo', {}), 'foo')
        self.assert_value(ma, ('bar', {}), 'bar')
        self.assert_value(ma, ('baz', {}), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('baz')).links)

        ma.instructions.append(Instruction(Instruction.LINK,
                                           Address('bar', ['foo']),
                                           Address('bar', ['foo']),
                                           Address('bar', ['foo'])))

        ma.do()

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')
        self.assert_value(ma, ('bar', ['foo', 'baz']), 'baz')
        self.assert_value(ma, ('baz', ['baz', 'baz', 'baz', 'baz']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({'baz': 'baz'}, ma.find(Address('baz')).links)

        ma.instructions.append(Instruction(Instruction.LINK,
                                           Address('bar', ['foo', 'baz']),
                                           Address('bar'),
                                           Address('foo')))

        ma.do()

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({'baz': 'baz', 'foo': 'bar'}, ma.find(Address('baz')).links)

    def test_link_new(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('baz')))

        ma.do()

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')

        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('baz')).links)

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address(Address.NEW), Address('foo')))

        ma.do()

        new = ma.find(Address('bar', ['foo']))

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), new.name)
        self.assert_value(ma, (new.name, []), new.name)

        assert_equal({'foo': new.name}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('baz')).links)
        assert_equal({}, ma.find(Address(new.name)).links)
        self.assert_concepts(ma, {'foo', 'bar', 'baz', new.name})

    def test_match_pass(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('baz')))

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address('baz'), Address('foo')))

        # Concepts differ
        ma.instructions.append(Instruction(Instruction.MATCH, Address('bar'), Address('baz'), offset=100))
        # Concepts differ
        ma.instructions.append(Instruction(Instruction.MATCH, Address('bar', ['foo']), Address('bar'), offset=200))
        # Link doesn't exist
        ma.instructions.append(Instruction(Instruction.MATCH, Address('bar', ['bar']), Address('bar'), offset=300))
        # Neither link exists
        ma.instructions.append(Instruction(Instruction.MATCH, Address('bar', ['baz']), Address('bar', ['baz']),
                                           offset=400))
        # Neither concept exists
        ma.instructions.append(Instruction(Instruction.MATCH, Address('fooz'), Address('fooz'), offset=500))

        ma.do()

        assert_equal(len(ma.instructions), ma.ip)

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('baz')).links)

    def test_match_a(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('baz')))

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address('baz'), Address('foo')))

        ma.instructions.append(Instruction(Instruction.MATCH, Address('bar', ['foo']), Address('baz'), offset=100))

        ma.do()

        assert_equal(len(ma.instructions) + 99, ma.ip)

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('baz')).links)

    def test_match_b(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('baz')))

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address('baz'), Address('foo')))

        ma.instructions.append(Instruction(Instruction.MATCH, Address('baz'), Address('bar', ['foo']), offset=100))

        ma.do()

        assert_equal(len(ma.instructions) + 99, ma.ip)

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('baz')).links)

    def test_match_same_path(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('baz')))

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address('baz'), Address('foo')))

        ma.instructions.append(Instruction(Instruction.MATCH, Address('bar', ['foo']), Address('bar', ['foo']),
                                           offset=100))

        ma.do()

        assert_equal(len(ma.instructions) + 99, ma.ip)

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('baz')).links)

    def test_match_same_concept(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('baz')))

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address('baz'), Address('foo')))

        ma.instructions.append(Instruction(Instruction.MATCH, Address('bar'), Address('bar'), offset=100))

        ma.do()

        assert_equal(len(ma.instructions) + 99, ma.ip)

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')
        self.assert_value(ma, ('baz', []), 'baz')
        self.assert_value(ma, ('bar', ['foo']), 'baz')

        assert_equal({'foo': 'baz'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('baz')).links)

    def test_stdin(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))

        ma.do()

        self.assert_value(ma, ('foo', []), 'foo')
        self.assert_value(ma, ('bar', []), 'bar')

        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('bar')).links)

        ma.instructions.append(Instruction(Instruction.LINK, Address('bar'), Address('stdin', ['read']),
                                           Address('foo')))

        inp.append('new_concept')
        ma.do()

        self.assert_value(ma, ('foo', {}), 'foo')
        self.assert_value(ma, ('bar', {}), 'bar')
        self.assert_value(ma, ('new_concept', {}), 'new_concept')
        self.assert_value(ma, ('bar', ['foo']), 'new_concept')

        assert_equal({'foo': 'new_concept'}, ma.find(Address('bar')).links)
        assert_equal({}, ma.find(Address('foo')).links)
        assert_equal({}, ma.find(Address('new_concept')).links)

    def test_stdout(self):
        ma, inp, out = self.build()
        ma.instructions.append(Instruction(Instruction.CREATE, Address('foo')))
        ma.instructions.append(Instruction(Instruction.CREATE, Address('bar')))

        ma.do()

        self.assert_value(ma, ('foo', []), 'foo')

        assert_equal({}, ma.find(Address('foo')).links)

        ma.instructions.append(Instruction(Instruction.LINK, Address('stdout'), Address('foo'), Address('write')))

        ma.do()

        assert_equal(['foo'], out)
        self.assert_value(ma, ('foo', {}), 'foo')
        assert_equal({}, ma.find(Address('write')).links)

        assert_equal({}, ma.find(Address('foo')).links)

        ma.instructions.append(Instruction(Instruction.LINK, Address('stdout'), Address('bar'), Address('write')))

        ma.do()

        assert_equal(['foo', 'bar'], out)
        self.assert_value(ma, ('foo', {}), 'foo')
        assert_equal({}, ma.find(Address('write')).links)

        assert_equal({}, ma.find(Address('foo')).links)
