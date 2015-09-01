# -*- coding: utf-8 -*-

'''
   mania.parser
   ~~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging
import mania.types as types


logger = logging.getLogger(__name__)


NORMAL = 0


class Module(object):

    def __init__(self, body, lineno=None):
        self.body = body
        self.lineno = lineno


class Parser(object):

    def __init__(self, scanner, flags=NORMAL):
        self.scanner = scanner
        self.flags = flags or NORMAL
        self.token = None
        self.value = None
        self.lineno = 1

        self.tokens = {
            'name': self.parse_constant,
            'ellipsis': self.parse_constant,
            'integer': self.parse_constant,
            'float': self.parse_constant,
            'fraction': self.parse_constant,
            'string': self.parse_constant,
            'quote': self.parse_quoted,
            'quasiquote': self.parse_quasiquoted,
            'unquote': self.parse_unquoted,
            'singleton': self.parse_singleton,
            'opening_parentheses': self.parse_list
        }

    def advance(self):
        try:
            self.token, self.value = self.scanner.next()

            while self.token in ('newline', 'comment', 'whitespace'):
                if self.token == 'newline':
                    self.lineno += 1

                self.token, self.value = self.scanner.next()

        except StopIteration:
            self.token, self.value = None, None

    def expect(self, token):
        if self.token != token:
            self.syntax_error('Expected token "{0}", got token "{1}"'.format(
                token,
                self.token
            ))

        value = self.value

        self.advance()

        return value

    def syntax_error(self, message, lineno=None):
        raise SyntaxError('{0}, in line {1}'.format(
            message,
            lineno or self.lineno
        ))

    def parse(self):
        self.advance()

        while self.token is not None:
            yield self.parse_any()

    def parse_any(self):
        if not self.token:
            self.syntax_error('Reached end of file, was expecting tokens')

        elif self.token not in self.tokens:
            self.syntax_error('Unexpected/unknown token "{0}":"{1}"'.format(
                self.token,
                self.value
            ))

        return self.tokens[self.token]()

    def parse_constant(self):
        value = self.value

        self.advance()

        return value

    def parse_quoted(self):
        self.expect('quote')

        return types.Quoted(self.parse_any())

    def parse_quasiquoted(self):
        self.expect('quasiquote')

        return types.Quasiquoted(self.parse_any())

    def parse_unquoted(self):
        self.expect('unquote')

        return types.Unquoted(self.parse_any())

    def parse_singleton(self):
        self.expect('singleton')

        return {
            'u': types.Undefined(),
            'undefined': types.Undefined(),
            'n': types.Nil(),
            'nil': types.Nil(),
            't': types.Bool(True),
            'true': types.Bool(True),
            'f': types.Bool(False),
            'false': types.Bool(False)
        }[self.expect('name').value]

    def parse_list(self):
        self.expect('opening_parentheses')

        if self.token == 'closing_parentheses':
            self.advance()

            return types.Nil()

        head = self.parse_any()

        if self.token == 'dot':
            self.advance()

            tail = self.parse_any()

            self.expect('closing_parentheses')

            return types.Pair(head, tail)

        result = [head]

        while self.token != 'closing_parentheses':
            result.append(self.parse_any())

        self.expect('closing_parentheses')

        return types.Pair.from_sequence(result)
