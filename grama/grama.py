# Copyright (c) 2017 xyzdev
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from functools import partial
import sys
import uuid
import re
import signal


class Concept(object):
    def __init__(self, name=None, links=None):
        self.name = name if name is not None else str(uuid.uuid4())
        self.links = links if links is not None else {}

    def get(self, ma, link):
        return ma.concepts.get(self.links.get(link))

    def link(self, name, target):
        self.links[name] = target

    def target_by_link(self, typ):
        if isinstance(typ, Concept):
            typ = typ.name
        return self.links.get(typ)

    def __str__(self):
        return "%s [%s]" % (Parser.encode_name(self.name),
                            ','.join('%s->%s' % (Parser.encode_name(typ), Parser.encode_name(tgt))
                                     for typ, tgt in self.links.iteritems()))


class Address(object):
    NEW = object()

    def __init__(self, name=None, path=None):
        self.name = name
        self.path = [] if path is None else path

    def __str__(self):
        return '/'.join([Parser.encode_name(self.name) if self.name is not self.NEW else '+'] +
                        [Parser.encode_name(seg) for seg in self.path])


class Machine(object):
    def __init__(self, attach=False):
        self.concepts = {}
        self.instructions = []
        self.ip = 0
        self.stdin = InputConcept(self)
        self.stdout = OutputConcept(self)
        self.debugger = DebugConcept(self, attach=attach)
        self.concepts[self.stdin.name] = self.stdin
        self.concepts[self.stdout.name] = self.stdout
        self.concepts[self.debugger.name] = self.debugger

    def find(self, addr):
        if addr.name is Address.NEW:
            return self.create()

        c = self.concepts.get(addr.name)

        for seg in addr.path:
            if c is None:
                return None
            c = c.get(self, seg)

        return c

    def create(self, name=None):
        concept = name if isinstance(name, Concept) else Concept(name)
        if concept.name in self.concepts:
            return concept
        self.concepts[concept.name] = concept
        return concept

    def tick(self):
        if self.ip >= len(self.instructions) or self.ip < 0:
            return False
        self.ip += self.instructions[self.ip].execute(self)
        return True

    def do(self, verbose=False):
        with DebugSignalTrap(self.debugger):
            while True:
                if self.debugger.attach:
                    self.debugger.do(self)

                if not self.tick() and not self.debugger.attach:
                    break

                if verbose:
                    sys.stdout.write('.')


class Instruction(object):
    CREATE, LINK, MATCH = range(3)

    def __init__(self, action, source, target=None, link=None, offset=1):
        self.action = action
        self.source = source
        self.target = target
        self.link = link
        self.offset = offset

    def execute(self, ma):
        link = ma.find(self.link) if isinstance(self.link, Address) else ma.concepts.get(self.link)
        if self.action == self.CREATE:
            ma.create(self.source.name)
            return 1
        if self.action == self.LINK:
            s = ma.find(self.source)
            t = ma.find(self.target)
            if not s:
                raise ValueError('Failed to link (%s)/%s to %s' % (self.source, self.link, self.target))
            if not t:
                raise ValueError('Failed to link %s/%s to (%s)' % (self.source, self.link, self.target))
            if not link:
                raise ValueError('Failed to link %s/(%s) to %s' % (self.source, self.link, self.target))
            s.link(link.name, t.name)
            return 1
        if self.action == self.MATCH:
            s = ma.find(self.source)
            t = ma.find(self.target)
            if s and t and s.name == t.name:
                return self.offset
            return 1
        raise Exception("Programmer error.")

    def __str__(self):
        if self.action == self.CREATE:
            return str(self.source)
        if self.action == self.LINK:
            return '%s/%s>%s' % (self.source, self.link, self.target)
        if self.action == self.MATCH:
            return '%s?%s:%d' % (self.source, self.target, self.offset)

        return "{%s %s, %s, %s, %s}" %\
               (['C', 'L', 'M'][self.action], self.source, self.target, self.link, self.offset)


class InputConcept(Concept):
    def __init__(self, ma, stream=None):
        super(InputConcept, self).__init__(name='stdin')
        self.ma = ma
        self.stream = stream if stream else lambda: sys.stdin.readline()
        ma.create('read')
        ma.create('eof')
        eof = ma.create()
        self.link('eof', eof.name)

    def get(self, ma, link):
        if link != 'read':
            return super(InputConcept, self).get(ma, link)

        name = self.stream()
        name = name.strip('\n') if name else self.links.get('eof')

        c = self.ma.concepts.get(name)
        if c is not None:
            return c
        return self.ma.create(name)


class OutputConcept(Concept):
    def __init__(self, ma, stream=None):
        super(OutputConcept, self).__init__(name='stdout')
        self.ma = ma
        self.stream = stream if stream else self._print
        ma.create('write')

    @staticmethod
    def _print(x):
        print x

    def link(self, name, target):
        if name != 'write':
            return super(OutputConcept, self).link(name, target)
        c = self.ma.concepts.get(target)
        if c is None:
            return None
        self.stream(target)


class DebugSignalTrap(object):
    def __init__(self, debugger):
        self.debugger = debugger
        self.trapped = False

    def __enter__(self):
        self.old_signal = signal.getsignal(signal.SIGUSR1)
        if self.old_signal is None or self.old_signal is signal.SIG_DFL or self.old_signal is signal.SIG_IGN:
            self.trapped = True
            signal.signal(signal.SIGUSR1, self.handle_attach)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.trapped:
            signal.signal(signal.SIGUSR1, self.old_signal)

        return False

    def handle_attach(self, sig, stack_num):
        self.debugger.attach = True
        self.debugger.debug = True


class DebugReadline(object):
    def __init__(self, debugger, ma):
        self.debugger = debugger
        self.ma = ma
        self.readline = None
        self.cache = []

    def __enter__(self):
        try:
            import readline
            self.readline = readline
        except ImportError:
            return
        else:
            readline.parse_and_bind('tab: complete')
            readline.set_completer_delims('')
            readline.set_completer(partial(self.complete, self.ma))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.readline:
            self.readline.set_completer(None)
        return False

    ops_pattern = re.compile('[/>?:; ]')

    def split_input(self, text):
        quoted = text.split("'")
        if len(quoted) % 2 == 0:
            token = "'" + quoted[-1]
        else:
            token = self.ops_pattern.split(quoted[-1])[-1]
        return text[:-len(token)], token

    def compare(self, a, b):
        if not a or not b:
            return False

        if a[0] == "'" and a[-1] != "'":
            a += "'"

        a_enc = self.debugger.parser.encode_name(self.debugger.parser.decode(a))
        a_enc = a_enc.replace('\'', '')
        a = a.replace('\'', '')
        b = b.replace('\'', '')

        return b.startswith(a_enc) or b.startswith(a)

    def complete(self, ma, text, state):
        if not state:
            self.cache = []

        if not text or not self.readline:
            return None

        lb = self.readline.get_line_buffer()
        prefix, text = self.split_input(text)

        if lb.startswith('/' + text) and ' ' not in lb:
            matches = [cmd for cmd in self.debugger.commands.keys() if cmd.startswith(text)]
            return len(matches) > state and '/' + matches[state] + ' '
        else:
            if self.cache:
                matches = self.cache
            else:
                concepts = [self.debugger.parser.encode_name(c.name) for c in ma.concepts.values()]
                matches = [c for c in concepts if self.compare(text, c)]
                self.cache = matches

            return len(matches) > state and prefix + matches[state]


class DebugConcept(Concept):
    def __init__(self, ma, parser=None, istream=None, ostream=None, verbose=False, debug=True, attach=False):
        super(DebugConcept, self).__init__('stddbg')

        self.parser = parser if parser else Parser()
        self.istream = istream if istream else self._read
        self.ostream = ostream if ostream else self._print
        self.verbose = verbose
        self.debug = debug
        self.attach = attach
        self.breakpoints = set()
        self.commands = {
            'help': ' - show this text',
            'dump': '[c] [ip] [i]  - print concepts, ip, instructions',
            'show': 'NAME[/PATH]  - print concept',
            'verbose': '[0|1]  - toggle verbose flag',
            'debug': '[0|1]  - toggle between debug mode and interactive mode',
            'step': '[IP]  - execute statement at ip or IP',
            'break': '[IP] [0|1]  - list breakpoints or toggle breakpoint at IP',
            'continue': ' - continue execution from ip',
        }

        ma.create('break')

    @staticmethod
    def _print(x):
        print x

    def _read(self):
        try:
            return raw_input('dbg> ' if self.debug else '> ') + '\n'
        except EOFError:
            self.ostream('')
            return ''

    def link(self, name, target):
        if name != 'break' or not target:
            return super(DebugConcept, self).link(name, target)

        self.attach = True
        self.debug = True
        return None

    def _ip_str(self, ma, ip=None):
        if ip is None:
            ip = ma.ip
        sep = '%s%s' % ('b' if ip in self.breakpoints else ' ',
                        '*' if ip == ma.ip else ' ')
        s = ma.instructions[ip] if 0 <= ip < len(ma.instructions) else '[END]'
        return '%d:%s%s' % (ip, sep, s)

    def _conv_int(self, args, default=None):
        if not args:
            return default
        try:
            if len(args) != 1:
                raise ValueError()
            return int(args[0])
        except ValueError:
            if default is not None:
                self.ostream('Expected a single integer argument.')
            return default

    def do(self, ma):
        with DebugReadline(self, ma):
            return self._do(ma)

    def _do(self, ma):
        if self.debug:
            self.ostream(self._ip_str(ma))
        else:
            self.ostream("Gra'Ma' - Copyright 2017 xyzdev. Type '/help' for list of commands.")

        while True:
            if self.istream != self._read:
                self.ostream('dbg>' if self.debug else '>')
            line = self.istream()

            if not line:
                self.attach = False
                if self.debug:
                    self.ostream('<detached>')
                break

            line = line.strip()
            words = line.split(' ')
            cmd, args = words[0], words[1:]

            if not cmd:
                continue

            if cmd == '/help':
                for cmd, h in self.commands.iteritems():
                    self.ostream('/%s %s' % (cmd, h))

                self.ostream('STMT [; STMT] ...  - execute one or more statements')

            elif cmd == '/verbose':
                self.verbose = not self.verbose if not args else bool(self._conv_int(args, self.verbose))

            elif cmd == '/debug':
                self.debug = not self.debug if not args else bool(self._conv_int(args, self.debug))

            elif cmd == '/py':
                try:
                    self.ostream(eval(' '.join(args)))
                except Exception, e:
                    self.ostream(e)

            elif cmd == '/show':
                if not args:
                    self.ostream('ADDRESS REQUIRED')
                else:
                    seg = [self.parser.decode(s) for s in args[0].split('/')]
                    self.ostream(ma.find(Address(seg[0], seg[1:])))

            elif cmd == '/dump':
                if not args or 'c' in args:
                    self.ostream('CONCEPTS:')
                    for c in ma.concepts.values():
                        self.ostream(' %s' % c)

                if not args or 'ip' in args:
                    self.ostream('INSTRUCTION POINTER: %s' % self._ip_str(ma))

                if not args or 'i' in args:
                    self.ostream('INSTRUCTIONS:')
                    for idx, i in enumerate(ma.instructions):
                        self.ostream('%d:%s%s%s' % (idx,
                                                    'b' if idx in self.breakpoints else ' ',
                                                    '*' if idx == ma.ip else ' ', i))

            elif cmd == '/break':
                if not args:
                    for ip in sorted(self.breakpoints):
                        self.ostream(self._ip_str(ma, ip))
                    continue

                bp = self._conv_int(args[:1], -1)
                if bp < 0:
                    self.ostream('Expected non-negative instruction address')
                else:
                    current = bp in self.breakpoints
                    state = self._conv_int(args[1:], not current)
                    if state:
                        self.breakpoints.add(bp)
                    else:
                        self.breakpoints.discard(bp)
                    self.ostream(self._ip_str(ma, bp))

            elif cmd in ('/step', '/s'):
                if args:
                    ma.ip = int(args[0])
                    self.ostream(self._ip_str(ma))

                self.debug = True
                try:
                    ma.tick()
                except (Exception, KeyboardInterrupt), e:
                    self.ostream(e)

                self.ostream(self._ip_str(ma))

            elif cmd in ('/continue', '/c'):
                self.attach = False
                if self.debug:
                    self.ostream('<resuming execution>')
                try:
                    self.attach = False
                    while not self.attach and ma.tick():
                        self.attach = self.attach or ma.ip in self.breakpoints

                    if self.attach:
                        self.ostream('<interrupted>')
                    elif not self.debug:
                        break
                except (Exception, KeyboardInterrupt), e:
                    self.ostream(e)

                self.ostream(self._ip_str(ma))

            elif cmd and cmd[0] == '/':
                self.ostream('Invalid command. See "/help" for list of commands.')

            else:
                try:
                    instructions = self.parser.parse(line)
                except ValueError, e:
                    self.ostream(e)
                    continue

                debugging = self.debug
                if debugging:
                    old_ip = ma.ip
                    old_len = len(ma.instructions)

                    # End program after executing the last instruction.
                    ma.instructions.append(Instruction(Instruction.MATCH, Address('stddbg'), Address('stddbg'),
                                                       offset=-(old_len + 1)))

                ma.ip = len(ma.instructions)
                ma.instructions.extend(instructions)

                try:
                    self.attach = False
                    while not self.attach and ma.tick():
                        pass
                except (Exception, KeyboardInterrupt), e:
                    self.ostream(e)
                    self.ostream(self._ip_str(ma))

                if self.attach:
                    self.ostream('<interrupted>')
                    self.ostream(self._ip_str(ma))

                if debugging:
                    ma.instructions = ma.instructions[:old_len]
                    ma.ip = old_ip

                self.debug = debugging or self.debug

        return None


class Parser(object):

    name_re = r'(?:[^/>+:?;\'\s]+|\'[^\t\n\r\']*\')'
    name_pattern = re.compile('^%s$' % name_re)
    escape_pattern = re.compile(r'\\[0-9a-f][0-9a-f]')

    @classmethod
    def encode_name(cls, name):
        esc = ''.join((c if c not in ("'", '\\') and 31 < ord(c) < 127 else '\\' + c.encode('hex') for c in name))
        return "'%s'" % esc if not cls.name_pattern.match(esc) else esc

    @classmethod
    def decode(cls, name):
        if not name:
            return ''
        if name[0] == "'":
            name = name[1:-1]
        return re.sub(cls.escape_pattern, lambda m: m.group(0)[1:].decode('hex'), name)

    def __init__(self):
        decode = self.decode

        node_pattern = re.compile(r'^(%s)$' % self.name_re)
        link_pattern = re.compile(r'^(%s)((?:/%s)*)/(%s)>(%s|\+)((?:/%s)*)$' % tuple([self.name_re] * 5))
        match_pattern = re.compile(r'^(%s)((?:/%s)*)\?(%s)((?:/%s)*):(-?\d+)$' % tuple([self.name_re] * 4))

        def split_path(path):
            # Split and decode possibly quoted names separated by '/'. Expects and removes leading '/'.
            return [decode(p) for p in re.split(r"(/|'[^']*')", path[1:]) if p not in ('/', '')]

        def link(m):
            dst = decode(m.group(1))
            link = decode(m.group(3))
            src = Address.NEW if m.group(4) == '+' else decode(m.group(4))
            dst_path = split_path(m.group(2))
            src_path = split_path(m.group(5))

            return Instruction(Instruction.LINK, Address(dst, dst_path), Address(src, src_path), Address(link))

        def match(m):
            dst = decode(m.group(1))
            src = decode(m.group(3))
            dst_path = split_path(m.group(2))
            src_path = split_path(m.group(4))

            return Instruction(Instruction.MATCH, Address(dst, dst_path), Address(src, src_path),
                               offset=int(m.group(5)))

        self.stmts = {
            node_pattern: lambda m: Instruction(Instruction.CREATE, Address(decode(m.group(1)))),
            link_pattern: link,
            match_pattern: match,
        }

    @staticmethod
    def _split_statements(line):
        # Split line on semicolon, respecting quotes and comments, yielding trimmed, non-empty lines.
        stmt = ''
        quoted = False
        for c in line:
            if c == "'":
                quoted = not quoted

            if not quoted and c == '#':
                break

            if not quoted and c == ';':
                if stmt.strip():
                    yield stmt.strip()
                stmt = ''
            else:
                stmt += c

        if stmt.strip():
            yield stmt.strip()

    def parse(self, string):
        instr = []
        for lineno, line in enumerate(string.split('\n')):
            for stmt in self._split_statements(line):
                for p, f in self.stmts.items():
                    m = p.match(stmt)
                    if m:
                        instr.append(f(m))
                        break
                else:
                    raise ValueError('Syntax error in statement on line %d: "%s"' % (lineno + 1, stmt))

        return instr
