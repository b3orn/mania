#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import sys
import logging
import mania
import mania.types as types
import mania.instructions as instructions
from mania.scanner import Scanner
from mania.parser import Parser
from mania.compiler import SimpleCompiler
from mania.node import Node, LoadingDeferred
from mania.frame import Scope
import mania.builtins


logger = logging.getLogger(__name__)


def main():
    root = logging.getLogger()

    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root.addHandler(handler)

    source = '''(author "Björn Schulz <bjoern@fac3.org>")
(copyright "2015 Björn Schulz")
(license "MIT")
(version "0.1.0" "dev")
(description "A simple hello world program in mania.")

(define-module test (main)
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

    filename = 'test.bam'

    with open(filename, 'wb') as stream:
        module.dump(stream)

    with open(filename, 'rb') as stream:
        loaded = types.Module.load(stream)

    node = Node(1024, 1, [])

    process = node.spawn_process(
        code=module.code(
            module.entry_point,
            len(module) - module.entry_point
        ),
        scope=Scope(parent=mania.builtins.register_scope)
    )

    node.start()

    try:
        node.load_module(module.name)

    except LoadingDeferred:
        pass

    node.start()

    module = node.load_module(module.name)

    function = module.lookup(types.Symbol('main'))

    process = node.spawn_process(
        code=function.code,
        scope=Scope(parent=function.scope)
    )

    node.start()


if __name__ == '__main__':
    main()
