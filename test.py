#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import mania.types as types
from mania.scanner import Scanner
from mania.parser import Parser
from mania.compiler import SimpleCompiler


def main():
    source = '''`(test test:foo 2 ,+ #u) ;this is just a test'''

    source = '''(author "Björn Schulz <bjoern@fac3.org>")
(copyright "2015 Björn Schulz")
(license "MIT")
(version "0.1.0")
(description "A simple hello world program in mania.")

(define-module main (main)
    (import 'mania:io)
    (import 'mania:string)

    (define (print message)
        (mania:io:write mania:io:stdout message))

    (define (println message)
        (print (mania:string:format "{0}{1}" message mania:io:newline)))

    (define (main)
        (println "Hello world!")))
'''

    parser = Parser(Scanner(source))

    module = SimpleCompiler(types.Symbol('test')).compile(parser.parse())

    filename = 'test.maniac'

    with open(filename, 'wb') as stream:
        module.dump(stream)

    with open(filename, 'rb') as stream:
        loaded = types.Module.load(stream)

    print len(module.constants), len(loaded.constants)
    print len(module.instructions), len(loaded.instructions)


if __name__ == '__main__':
    main()
