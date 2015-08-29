# -*- coding: utf-8 -*-

'''
   mania.compiler
   ~~~~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging
import io
import mania.types
import mania.instructions


logger = logging.getLogger(__name__)


class Placeholder(object):

    def __init__(self, instruction):
        self.instruction = instruction


class Builder(object):

    def __init__(self, name):
        self.name = name
        self.constants = [name]
        self.instructions = []

    @property
    def module(self):
        return mania.types.Module(
            name=self.name,
            entry_point=0,
            constants=self.constants,
            instructions=self.instructions
        )

    def constant(self, value):
        if value in self.constants:
            return self.constants.index(value)

        self.constants.append(value)

        return len(self.constants) - 1

    def index(self):
        return len(self.instructions)

    def add(self, instruction):
        index = self.index()

        self.instructions.append(instruction)

        return index

    def replace(self, index, instruction):
        self.instructions[index] = instruction


class Compiler(object):

    def __init__(self, name):
        self.name = name
        self.builder = Builder(self.name)

    def compile(self, code):
        raise NotImplementedError('"eval" needs to be implemented in subclasses')


class SimpleCompiler(Compiler):

    def compile(self, module):
        for element in module:
            self.compile_any(element)

            self.builder.add(mania.instructions.Eval())

        self.builder.add(mania.instructions.Exit())

        return self.builder.module

    def compile_any(self, code):
        if isinstance(code, mania.types.Pair):
            self.compile_pair(code)

        elif isinstance(code, mania.types.Quoted):
            self.compile_quoted(code)

        elif isinstance(code, mania.types.Quasiquoted):
            self.compile_quasiquoted(code)

        elif isinstance(code, mania.types.Unquoted):
            self.compile_unquoted(code)

        else:
            self.compile_constant(code)

    def compile_pair(self, code):
        self.compile_any(code.head)
        self.compile_any(code.tail)

        self.builder.add(mania.instructions.BuildPair())

    def compile_quoted(self, code):
        self.compile_any(code.value)

        self.builder.add(mania.instructions.BuildQuoted())

    def compile_quasiquoted(self, code):
        self.compile_any(code.value)

        self.builder.add(mania.instructions.BuildQuasiquoted())

    def compile_unquoted(self, code):
        self.compile_any(code.value)

        self.builder.add(mania.instructions.BuildUnquoted())

    def compile_constant(self, code):
        index = self.builder.constant(code)

        self.builder.add(mania.instructions.LoadConstant(index))


class CallCompiler(Compiler):

    def compile(self, expression):
        n = -1

        while expression != mania.types.Nil():
            self.compile_any(expression.head)

            if isinstance(expression.head, mania.types.Pair):
                self.builder.add(mania.instructions.Eval())

            expression = expression.tail
            n += 1

        self.builder.add(mania.instructions.Call(n))

        return self.builder.module

    def compile_any(self, code):
        if isinstance(code, mania.types.Symbol):
            self.compile_symbol(code)

        elif isinstance(code, mania.types.Quasiquoted):
            pass

        elif isinstance(code, mania.types.Quoted):
            pass

        elif isinstance(code, mania.types.Unquoted):
            pass

        elif isinstance(code, mania.types.Pair):
            self.compile_pair(code)

        else:
            self.compile_constant(code)

    def compile_symbol(self, code):
        index = self.builder.constant(code)

        self.builder.add(mania.instructions.LoadConstant(index))
        self.builder.add(mania.instructions.Eval())

    def compile_pair(self, code):
        self.compile_any(code.head)
        self.compile_any(code.tail)

        self.builder.add(mania.instructions.BuildPair())

    def compile_constant(self, code):
        index = self.builder.constant(code)

        self.builder.add(mania.instructions.LoadConstant(index))
