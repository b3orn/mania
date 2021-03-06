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
import mania.builtins.mania as boot


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
    (import 'mania:io)
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

    (define (greeter name)
        (lambda (f)
            (f (format "Hello {0}!" name))))

    (define (list e ...) e)

    (define-syntax sum
        ((_ x y) `(+ ,x ,y))
        ((sum x rest ...) `(+ ,x (,sum ,rest ...))))

    (define (arity-test l ...)
        (if (== l #n)
            (println "nil")
            (println "not nil")))

    (define (println message ...)
        (mania:io:write mania:io:stdout (format "{0}\n" (join " " message ...))))

    (define (main)
        (println mania:io)
        (arity-test) ; nil
        (arity-test 1 2 3) ; not nil
        (arity-test (list) ...) ; nil
        (arity-test (list 1 2 3) ...) ; not nil

        (println (sum 1 2)) ; 3
        (println (sum 1 2 3)) ; 6
        (println (sum 1 2 3 4)) ; 10

        (println (list 1 2 3 4 5))

        (let ()
            (define-values (a b c) (list 1 2 3))
            (println "a" a "b" b "c" c))

        (let ((world (greeter "world"))
              (foo (greeter "foo")))
            (world (lambda (n) (println n)))
            (foo (lambda (n) (println n))))

        (let ((m 3) (n 2))
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
        scope=Scope(parent=boot.Mania().scope)
    )

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
