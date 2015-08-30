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

    source = '''(define-module test (main)
    ; See https://en.wikipedia.org/wiki/Ackermann_function for more details.
    (define (a m n)
        (if (== m 0)
            (+ n 1)
            (if (and (> m 0) (== n 0))
                (a (- m 1) 1)
                (a (- m 1) (a m (- n 1))))))

    (define (factorial n)
        (if (== n 0)
            1
            (* n (factorial (- n 1)))))

    (define (main)
        (let ((m 3) (n 4))
            (println "ackermann" m n (a m n)))

        (let ((n 30))
            (println "factorial" n (factorial n)))

        (let loop ((n 10))
            (println "Hello world!")
            (if (/= n 0)
                (loop (- n 1))
                (println "Last one")))

        (let ((a 5) (b 2) (c 32))
            (println (+ (* a b) c)))

        (println ((lambda (x) (* x x)) 5))))'''

    parser = Parser(Scanner(source))

    module = SimpleCompiler(types.Symbol('test')).compile(parser.parse())

    filename = 'test.bam'

    with open(filename, 'wb') as stream:
        module.dump(stream)

    with open(filename, 'rb') as stream:
        loaded = types.Module.load(stream)

    node = Node(2**32, 1, [])

    process = node.spawn_process(
        code=module.code(
            module.entry_point,
            len(module) - module.entry_point
        ),
        scope=Scope(parent=mania.builtins.register_scope)
    )

    node.start()

    try:
        module = node.load_module(module.name)

    except LoadingDeferred:
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
