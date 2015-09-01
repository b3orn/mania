# -*- coding: utf-8 -*-

'''
   mania.scanner
   ~~~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging
import re
import operator
import mania.types as types


logger = logging.getLogger(__name__)


def token(function):
    function._token = True

    return function


def priority(level):
    def decorator(function):
        function._priority = level
        
        return function

    return decorator


class MetaScanner(type):
    
    def __new__(mcs, name, bases, dct):
        cls = type.__new__(mcs, name, bases, dct)

        tokens = []

        for name in dir(cls):
            element = getattr(cls, name)

            if getattr(element, '_token', False) == True:
                tokens.append((name, getattr(element, '_priority', 0)))

        tokens.sort(key=operator.itemgetter(1))

        if tokens:
            cls._tokens = list(zip(*tokens)[0])

        else:
            cls._tokens = []

        return cls


class BaseScanner(object):

    __metaclass__ = MetaScanner

    def __init__(self, source, flags=None):
        self.source = source
        self.flags = (flags or re.UNICODE | re.DOTALL) | re.MULTILINE
        self.iterator = re.finditer(self.regexp, self.source, self.flags)
        self.stopped = False

    @classmethod
    def from_file(cls, stream):
        return cls(stream.read())

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self.stopped:
            raise StopIteration

        try:
            match = next(self.iterator)

        except StopIteration:
            self.stopped = True

            return None, None

        group = match.group(match.lastgroup)

        return match.lastgroup, getattr(self, match.lastgroup)(group)

    @property
    def regexp(self):
        regexp = []

        for name in self._tokens:
            element = getattr(self, name)

            regexp.append('(?P<{0}>{1})'.format(name, element.__doc__))

        return '|'.join(regexp)


class Scanner(BaseScanner):

    @token
    def name(self, value):
        r'[\w\:\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~]+'


        old = (
            r'(?:[^\W0-9]|[\:\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
            r'(?:'
                r'(?:'
                    r'(?<=[\:\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
                    r'(?:[^\W0-9]|[\:\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
                    r'[\w\:\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~]*'
                r')'
                r'|'
                r'(?:'
                    r'(?<![\:\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
                    r'[\w\:\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~]*'
                r')'
            r')?'
        )

        return types.Symbol(value)

    @token
    def integer(self, value):
        r'[+-]?(?:0[xX][0-9a-fA-F]+|0[0-7]+|[0-9][0-9]*)'

        if value[-2:] in ('0x', '0X'):
            base = 16

        elif value.startswith('0'):
            base = 8

        else:
            base = 10

        return types.Integer(int(value, base=base))

    @token
    def float(self, value):
        r'[+-]?(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?'

        return types.Float(float(value))

    @token
    def fraction(self, value):
        r'[+-]?\d+/[+-]?\d+'

        (numerator, denominator) = re.match(
            r'^([+-]?\d+)/([+-]?\d+)$',
            value
        ).group(1, 2)

        return types.Fraction(int(numerator), int(denominator))

    @token
    def string(self, value):
        r'"[^"\\]*(?:\\.[^"\\]*)*"'

        return types.String(value[1:-1])

    @token
    def singleton(self, value):
        r'#'

        return value

    @token
    def dot(self, value):
        r'\.{1}(?!\.+)'

        return value
    
    @token
    def ellipsis(self, value):
        r'\.{3}(?!\.+)'

        return types.Ellipsis()

    @token
    def quote(self, value):
        r"'"

        return value

    @token
    def quasiquote(self, value):
        r'`'

        return value

    @token
    def unquote(self, value):
        r','

        return value

    @token
    def opening_parentheses(self, value):
        r'\('

        return value
    
    @token
    def closing_parentheses(self, value):
        r'\)'

        return value

    @token
    def opening_brackets(self, value):
        r'\['

        return value

    @token
    def closing_brackets(self, value):
        r'\]'

        return value

    @token
    def opening_braces(self, value):
        r'\{'

        return value

    @token
    def closing_braces(self, value):
        r'\}'

        return value

    @token
    def newline(self, value):
        r'\n'

        return value

    @token
    def whitespace(self, value):
        r'[^\S\n]+'

        return value

    @token
    def comment(self, value):
        r';.*?$'

        return value

    @token
    @priority(1)
    def unknown(self, value):
        r'.'

        return value
