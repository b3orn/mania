# -*- coding: utf-8 -*-

'''
   mania.builtins.mania_boot
   ~~~~~~~~~~~~~~~~~~~~~~~~~

   :copyright: (c) 2015 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import, division
import logging
import mania.compiler
import mania.types as types
from mania.types import Symbol, Pair, NativeMacro, NativeRule, Pattern, Ellipsis


logger = logging.getLogger(__name__)


class Boot(types.NativeModule):

    def __init__(self):
        types.NativeModule.__init__(self, Symbol('mania:boot'))

        self.register('define-module', NativeMacro([ NativeRule(
            Pattern(Pair.from_sequence([
                Symbol('_'),
                Symbol('name'),
                Pair.from_sequence([Symbol('exports'), Ellipsis()]),
                Symbol('body'),
                Ellipsis()
            ])),
            self.define_module
        )]))

        ignore = NativeMacro([NativeRule(
            Pattern(Pair.from_sequence([
                Symbol('_'), Symbol('body'), Ellipsis()
            ])),
            self.ignore
        )])

        self.register('comment', ignore)
        self.register('author', ignore)
        self.register('copyright', ignore)
        self.register('license', ignore)
        self.register('version', ignore)
        self.register('description', ignore)

    def ignore(self, vm, bindings):
        pass

    def define_module(self, vm, bindings):
        name = bindings[Symbol('name')]

        if ':' in name.value and '' in name.value.split(':'):
            raise types.ExpandError()

        code = Pair.from_sequence([
            Symbol('define-module'),
            name,
            bindings[Symbol('exports')]
        ])

        code.concat(bindings[Symbol('body')])

        compiler = mania.compiler.SimpleCompiler(name)

        compiler.compile_any(code)

        compiler.builder.add(mania.instructions.Eval())
        compiler.builder.add(mania.instructions.Exit())

        module = compiler.builder.module

        vm.process.scheduler.node.registered_modules[name] = module

        return []
