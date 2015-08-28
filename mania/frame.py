# -*- coding: utf-8 -*-

'''
   mania.frame
   ~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging
import mania.types as types


logger = logging.getLogger(__name__)


class Stack(list):

    def push(self, value):
        list.append(self, value)

        return value

    def peek(self):
        return self[-1]


class Scope(object):

    def __init__(self, parent=None, locals=None):
        self.parent = parent
        self.locals = locals or {}

    def define(self, name, value):
        if name in self.locals:
            if isinstance(self.locals[name], types.Annotation):
                value.annotation = self.locals[name]
                self.locals[name] = value

                return value

            raise NameError('name {0!r} already defined'.format(name))

        self.locals[name] = value

        return value

    def lookup(self, name):
        if name in self.locals:
            if isinstance(self.locals[name], types.Annotation):
                raise NameError('name {0!r} not defined'.format(name))

            return self.locals[name]

        elif self.parent:
            return self.parent.lookup(name)

        raise NameError('name {0!r} not defined'.format(name))


class Frame(object):

    def __init__(self, code, scope=None, parent=None):
        self.code = code
        self.scope = scope or Scope(parent.scope if parent else None)
        self.parent = parent
        self.position = code.entry_point
        self.stack = Stack()

    def define(self, name, value):
        return self.scope.define(value)

    def lookup(self, name):
        return self.scope.lookup(name)

    def push(self, value):
        return self.stack.push(value)

    def pop(self):
        return self.stack.pop()

    def peek(self):
        return self.stack.peek()

    def constant(self, index):
        return self.code.module.constants[index]
