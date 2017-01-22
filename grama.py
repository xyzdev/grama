#!/usr/bin/python
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

import sys
import argparse
from grama.grama import Machine, Parser


def main():
    argparser = argparse.ArgumentParser(description="Gra'Ma' Lang - virtual graph machine interpreter")
    argparser.add_argument('-i', dest='interactive', action='store_true', default=False,
                           help='open interactive mode after executing a program file')
    argparser.add_argument('-d', dest='debug', action='store_true', default=False,
                           help='open debugger after loading program but before executing')
    argparser.add_argument('-v', dest='verbose', action='store_true', default=False,
                           help='enable extra debug output')
    argparser.add_argument('-e', dest='execute', default='', type=str,
                           help='execute command')
    argparser.add_argument('filename', type=str, default=None, nargs=argparse.REMAINDER, help='program file to execute')

    args = argparser.parse_args()
    if len(args.filename) > 1:
        argparser.error('extra arguments after filename')

    if args.execute and args.filename:
        argparser.error('filename and -e arguments are mutually exclusive')

    interactive = args.interactive if (args.filename or args.execute) else sys.stdin.isatty()

    ma = Machine()
    parser = Parser()

    if args.filename:
        with open(args.filename[0], 'r') as f:
            source = f.read()
        ma.instructions.extend(parser.parse(source))
    elif args.execute:
        ma.instructions.extend(parser.parse(args.execute))
    elif not interactive:
        source = ''
        while True:
            inp = sys.stdin.readline()
            if not inp or inp.strip() == ';':
                break
            source += inp

        ma.instructions.extend(parser.parse(source))

    if args.verbose:
        print [str(i) for i in ma.instructions]

    if ma.instructions and not args.debug:
        ma.do(verbose=args.verbose)

    if interactive or args.debug:
        ma.debugger.attach = True
        ma.debugger.debug = args.debug
        ma.debugger.verbose = args.verbose
        ma.do(verbose=args.verbose)

if __name__ == "__main__":
    sys.exit(main())
