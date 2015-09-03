# -*- coding: utf-8 -*-

'''
   mania.builtins.mania
   ~~~~~~~~~~~~~~~~~~~~

   :copyright: (c) 2015 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import, division
import logging
import mania.compiler
import mania.instructions as instructions
import mania.types as types
from mania.types import Symbol, Pair, NativeMacro, NativeRule, Pattern, Ellipsis


logger = logging.getLogger(__name__)


class Mania(types.NativeModule):

    def __init__(self):
        types.NativeModule.__init__(self, Symbol('mania'))

        self.register('define-module', NativeMacro([NativeRule(
            Pattern(Pair.from_sequence([
                Symbol('_'),
                Symbol('name'),
                Pair.from_sequence([Symbol('exports'), Ellipsis()]),
                Symbol('body'),
                Ellipsis()
            ])),
            self.define_module
        )]))

        self.register('import', NativeMacro([
            NativeRule(
                Pattern(Pair.from_sequence([Symbol('_'), Symbol('name')])),
                self.import_
            ),
            NativeRule(
                Pattern(Pair.from_sequence([
                    Symbol('_'),
                    Symbol('name'),
                    Pair.from_sequence([Symbol('imports'), Ellipsis()])
                ])),
                self.import_
            )
        ]))

        self.register('define', NativeMacro([
            NativeRule(
                Pattern(Pair.from_sequence([
                    Symbol('_'),
                    Pair.from_sequence([
                        Symbol('name'), Symbol('parameters'), Ellipsis()
                    ]),
                    Symbol('body'),
                    Ellipsis()
                ])),
                self.define_function
            ),
            NativeRule(
                Pattern(Pair.from_sequence([
                    Symbol('_'), Symbol('name'), Symbol('value')
                ])),
                self.define_value
            )
        ]))

        self.register('lambda', NativeMacro([NativeRule(
            Pattern(Pair.from_sequence([
                Symbol('_'),
                Pair.from_sequence([Symbol('parameters'), Ellipsis()]),
                Symbol('body'),
                Ellipsis()
            ])),
            self.lambda_
        )]))

        self.register('define-syntax', NativeMacro([NativeRule(
            Pattern(Pair.from_sequence([
                Symbol('_'),
                Symbol('name'),
                Pair.from_sequence([
                    Symbol('pattern'), Symbol('template'), Ellipsis()
                ]),
                Ellipsis()
            ])),
            self.define_syntax
        )]))

        self.register('let', NativeMacro([
            NativeRule(
                Pattern(Pair.from_sequence([
                    Symbol('_'),
                    Pair.from_sequence([
                        Pair.from_sequence([
                            Symbol('variables'), Symbol('values')
                        ]),
                        Ellipsis()
                    ]),
                    Symbol('body'),
                    Ellipsis()
                ])),
                self.let
            ),
            NativeRule(
                Pattern(Pair.from_sequence([
                    Symbol('_'),
                    Symbol('name'),
                    Pair.from_sequence([
                        Pair.from_sequence([
                            Symbol('variables'), Symbol('values')
                        ]),
                        Ellipsis()
                    ]),
                    Symbol('body'),
                    Ellipsis()
                ])),
                self.let
            )
        ]))

        self.register('if', NativeMacro([
            NativeRule(
                Pattern(Pair.from_sequence([
                    Symbol('_'), Symbol('condition'), Symbol('positive')
                ])),
                self.if_
            ),
            NativeRule(
                Pattern(Pair.from_sequence([
                    Symbol('_'),
                    Symbol('condition'),
                    Symbol('positive'),
                    Symbol('negative')
                ])),
                self.if_
            )
        ]))

        self.register('and', NativeMacro([NativeRule(
            Pattern(Pair.from_sequence([
                Symbol('_'), Symbol('left'), Symbol('right')
            ])),
            self.and_
        )]))

    @types.export
    def format(self, format, *args):
        return types.String(format.value.format(*args))

    @types.export('==')
    def equal(self, x, y):
        return types.Bool(x == y)

    @types.export('/=')
    def not_equal(self, x, y):
        return types.Bool(x != y)

    @types.export('>')
    def greater(self, x, y):
        return types.Bool(x > y)

    @types.export
    def head(self, list):
        return list.head

    @types.export('+')
    def add(self, x, y):
        return x.add(y)

    @types.export('-')
    def sub(self, x, y):
        return x.sub(y)

    @types.export('*')
    def mul(self, x, y):
        return x.mul(y)

    @types.export
    def tail(self, list):
        return list.tail

    def define_module(self, vm, bindings):
        name = bindings[Symbol('name')]

        if ':' in name.value and '' in name.value.split(':'):
            raise types.ExpandError()

        compiler = mania.compiler.SimpleCompiler(name)

        for element in bindings[Symbol('body')]:
            compiler.compile_any(element)
            compiler.builder.add(instructions.Eval())

        compiler.compile_any(name)
        compiler.compile_any(bindings[Symbol('exports')])
    
        compiler.builder.add(instructions.BuildModule())
        compiler.builder.add(instructions.Exit())

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module) - module.entry_point
        )]

    def import_(self, vm, bindings):
        compiler = mania.compiler.SimpleCompiler(types.Nil())

        compiler.compile_any(bindings[Symbol('name')])
        compiler.builder.add(instructions.Eval())
        compiler.builder.add(instructions.LoadModule())

        if Symbol('imports') in bindings:
            for name in bindings[Symbol('imports')]:
                compiler.builder.add(instructions.LoadField(
                    compiler.builder.constant(name)
                ))
                compiler.builder.add(instructions.Store(
                    compiler.builder.constant(name)
                ))

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module) - module.entry_point
        )]

    def compile_function(self, bindings):
        parameters = bindings[Symbol('parameters')] or []
        body = bindings[Symbol('body')] or []

        compiler = mania.compiler.SimpleCompiler(types.Nil())

        empty_check = None

        for i, parameter in enumerate(parameters):
            if ':' in parameter.value and any(c != ':' for c in parameter.value):
                raise types.ExpandError()

            if i + 1 < len(parameters) and isinstance(parameters[i + 1], Ellipsis):
                if i + 2 < len(parameters):
                    raise mania.types.ExpandError()

                empty_check = compiler.builder.add(None)

                compiler.compile_any(types.Nil())

                loop = compiler.builder.add(instructions.BuildPair())

                end = compiler.builder.add(None)

                compiler.builder.add(instructions.Jump(loop))

                index = compiler.builder.index()

                compiler.compile_any(types.Nil())

            store = compiler.builder.add(instructions.Reverse())

            compiler.builder.add(instructions.Store(
                compiler.builder.constant(parameter)
            ))

            if empty_check is not None:
                compiler.builder.replace(
                    end,
                    instructions.JumpIfSize(1, store)
                )
                compiler.builder.replace(
                    empty_check,
                    instructions.JumpIfEmpty(index)
                )

                break

        for node in body:
            compiler.compile_any(node)
            compiler.builder.add(instructions.Eval())

        compiler.builder.add(instructions.Return())

        compiler.builder.entry_point = compiler.builder.index()

        compiler.builder.add(instructions.LoadCode(0, compiler.builder.entry_point))
        compiler.builder.add(instructions.BuildFunction())

        return compiler

    def define_function(self, vm, bindings):
        name = bindings[Symbol('name')]

        if ':' in name.value and any(c != ':' for c in name.value):
            raise mania.types.ExpandError()

        compiler = self.compile_function(bindings)

        compiler.builder.add(instructions.Duplicate(1))
        compiler.builder.add(instructions.Store(
            compiler.builder.constant(name)
        ))

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module) - module.entry_point
        )]

    def define_value(vm, bindings):
        name = bindings[Symbol('name')]

        if ':' in name.value and any(c != ':' for c in name.value):
            raise types.ExpandError()

        compiler = mania.compiler.SimpleCompiler(types.Nil())

        compiler.compile_any(bindings[Symbol('value')])
        compiler.builder.add(instructions.Eval())
        compiler.builder.add(instructions.Duplicate(1))
        compiler.builder.add(instructions.Store(
            compiler.builder.constant(name)
        ))

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module) - module.entry_point
        )]

    def lambda_(self, vm, bindings):
        compiler = self.compile_function(bindings)

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module) - module.entry_point
        )]

    def define_syntax(self, vm, bindings):
        rules = zip(bindings[Symbol('pattern')], bindings[Symbol('template')])

        compiler = mania.compiler.SimpleCompiler(types.Nil())

        for pattern, templates in rules:
            compiler.compile_any(pattern)
            compiler.builder.add(instructions.BuildPattern())

            for template in templates:
                compiler.compile_any(template)

            compiler.builder.add(instructions.BuildTemplate(len(templates)))
            compiler.builder.add(instructions.BuildRule())

        compiler.builder.add(instructions.BuildMacro(len(rules)))
        compiler.builder.add(instructions.Duplicate(1))
        compiler.builder.add(instructions.Store(
            compiler.builder.constant(bindings[Symbol('name')])
        ))

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module) - module.entry_point
        )]

    def let(self, vm, bindings):
        variables = list(bindings[Symbol('variables')] or [])
        values = list(bindings[Symbol('values')] or [])

        if len(values) != len(variables):
            raise SyntaxError('let bindings need a value')

        compiler = mania.compiler.SimpleCompiler(types.Nil())

        for name in variables:
            if ':' in name.value and any(c != ':' for c in name.value):
                raise types.ExpandError()

            compiler.builder.add(instructions.Store(
                compiler.builder.constant(name)
            ))

        for node in bindings[Symbol('body')]:
            compiler.compile_any(node)
            compiler.builder.add(instructions.Eval())

        compiler.builder.add(instructions.Return())

        size = compiler.builder.index()

        compiler.builder.add(instructions.LoadCode(0, size))
        compiler.builder.add(instructions.BuildFunction())

        if Symbol('name') in bindings:
            name = bindings[Symbol('name')]

            if ':' in name.value and any(c != ':' for c in name.value):
                raise types.ExpandError()

            compiler.builder.add(instructions.Store(
                compiler.builder.constant(name)
            ))
            compiler.builder.add(instructions.Load(
                compiler.builder.constant(name)
            ))

        for value in values:
            compiler.compile_any(value)
            compiler.builder.add(instructions.Eval())

        compiler.builder.add(instructions.Call(len(values)))
        compiler.builder.add(instructions.Return())

        entry_point = compiler.builder.index()

        compiler.builder.add(instructions.LoadCode(size, entry_point - size))
        compiler.builder.add(instructions.BuildFunction())
        compiler.builder.add(instructions.Call(0))

        module = compiler.builder.module

        module.entry_point = entry_point

        return [module.code(
            module.entry_point,
            len(module) - module.entry_point
        )]

    def if_(self, vm, bindings):
        compiler = mania.compiler.SimpleCompiler(types.Nil())

        compiler.compile_any(bindings[Symbol('condition')])
        compiler.builder.add(instructions.Eval())

        negative_jump = compiler.builder.add(None)

        compiler.compile_any(bindings[Symbol('positive')])
        compiler.builder.add(instructions.Eval())

        end_jump = compiler.builder.add(None)

        compiler.builder.replace(
            negative_jump,
            instructions.JumpIfFalse(compiler.builder.index())
        )

        if Symbol('negative') in bindings:
            compiler.compile_any(bindings[Symbol('negative')])
            compiler.builder.add(instructions.Eval())

        else:
            compiler.builder.add(instructions.LoadConstant(
                compiler.builder.constant(types.Undefined())
            ))

        end = compiler.builder.add(instructions.Restore())

        compiler.builder.replace(end_jump, instructions.Jump(end))

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module)
        )]

    def and_(self, vm, bindings):
        compiler = mania.compiler.SimpleCompiler(types.Nil())

        compiler.compile_any(bindings[Symbol('left')])
        compiler.builder.add(instructions.Eval())
        compiler.builder.add(instructions.Duplicate(1))

        left_false = compiler.builder.add(None)

        compiler.builder.add(instructions.Pop(1))
        compiler.compile_any(bindings[Symbol('right')])
        compiler.builder.add(instructions.Eval())

        end = compiler.builder.add(instructions.Restore())

        compiler.builder.replace(
            left_false,
            instructions.JumpIfFalse(end)
        )

        module = compiler.builder.module

        return [module.code(
            module.entry_point,
            len(module)
        )]
