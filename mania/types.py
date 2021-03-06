# -*- coding: utf-8 -*-

'''
   mania.types
   ~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging
import io
import struct
import collections
import types
import mania.consts as consts
import mania.instructions
import mania.compiler
import mania.frame


logger = logging.getLogger(__name__)


serializable_types = {}


def serializable(type):
    def _inner(cls):
        serializable_types[type] = cls

        return cls

    return _inner


class MatchError(Exception):
    pass


class ExpandError(Exception):
    pass


class Type(object):

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return self.to_string().value.encode('utf-8')


@serializable(consts.ELLIPSIS)
class Ellipsis(Type):

    def __eq__(self, other):
        return isinstance(other, Ellipsis)

    def __nonzero__(self):
        return False

    @classmethod
    def load(cls, stream):
        return cls()

    def dump(self, stream):
        stream.write(struct.pack('<B', consts.ELLIPSIS))

    def to_bool(self):
        return Bool(False)

    def to_string(self):
        return String(u'...')


@serializable(consts.UNDEFINED)
class Undefined(Type):

    def __eq__(self, other):
        return isinstance(other, Undefined)

    def __nonzero__(self):
        return False

    @classmethod
    def load(cls, stream):
        return cls()

    def dump(self, stream):
        stream.write(struct.pack('<B', consts.UNDEFINED))

    def to_bool(self):
        return Bool(False)

    def to_string(self):
        return String(u'#undefined')


@serializable(consts.NIL)
class Nil(Type):

    def __eq__(self, other):
        return isinstance(other, Nil)

    def __nonzero__(self):
        return False

    @classmethod
    def load(cls, stream):
        return cls()

    def dump(self, stream):
        stream.write(struct.pack('<B', consts.NIL))

    def to_bool(self):
        return Bool(False)

    def to_string(self):
        return String(u'()')


@serializable(consts.BOOLEAN)
class Bool(Type):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Bool) and self.value == other.value

    def __nonzero__(self):
        return self.value

    @classmethod
    def load(cls, stream):
        return cls(False if stream.read(1) == '\x00' else True)

    def dump(self, stream):
        stream.write(struct.pack('<BB', consts.BOOLEAN, 1 if self.value else 0))

    def to_bool(self):
        return self

    def to_string(self):
        return String(u'#true' if self.value else u'#false')


@serializable(consts.INTEGER)
class Integer(Type):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, (Integer, Float)) and self.value == other.value

    def __gt__(self, other):
        return isinstance(other, (Integer, Float)) and self.value > other.value

    def __nonzero__(self):
        return bool(self.value)

    @classmethod
    def load(cls, stream):
        value = [stream.read(1)]

        while value[-1] != '\x00':
            value.append(stream.read(1))

        return cls(int(''.join(value[:-1])))

    def dump(self, stream):
        stream.write(struct.pack('<B', consts.INTEGER))
        stream.write(str(self.value))
        stream.write('\x00')

    def to_bool(self):
        return Bool(self.value != 0)

    def to_string(self):
        return String(unicode(self.value))

    def add(self, other):
        result = self.value + other.value

        return Float(result) if isinstance(result, float) else Integer(result)

    def sub(self, other):
        result = self.value - other.value

        return Float(result) if isinstance(result, float) else Integer(result)

    def mul(self, other):
        result = self.value * other.value

        return Float(result) if isinstance(result, float) else Integer(result)


@serializable(consts.FLOAT)
class Float(Type):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, (Integer, Float)) and self.value == other.value

    def __gt__(self, other):
        return isinstance(other, (Integer, Float)) and self.value > other.value

    def __nonzero__(self):
        return bool(self.value)

    @classmethod
    def load(cls, stream):
        (value,) = struct.unpack('<d', stream.read(struct.calcsize('<d')))
        
        return cls(value)

    def dump(self, stream):
        stream.write(struct.pack('<Bd', consts.FLOAT, self.value))

    def to_bool(self):
        return Bool(self.value != 0)

    def to_string(self):
        return String(unicode(self.value))

    def add(self, other):
        result = self.value + other.value

        return Float(result) if isinstance(result, float) else Integer(result)

    def sub(self, other):
        result = self.value - other.value

        return Float(result) if isinstance(result, float) else Integer(result)

    def mul(self, other):
        result = self.value * other.value

        return Float(result) if isinstance(result, float) else Integer(result)


@serializable(consts.SYMBOL)
class Symbol(Type):

    def __init__(self, value):
        if isinstance(value, str):
            value = value.decode('utf-8')

        self.value = value

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.value == other.value

    def __nonzero__(self):
        return True

    def __hash__(self):
        return hash(self.value)

    @classmethod
    def load(cls, stream):
        value = [stream.read(1)]

        while value[-1] != '\x00':
            value.append(stream.read(1))

        return cls(''.join(value[:-1]).decode('utf-8'))

    def dump(self, stream):
        stream.write(struct.pack('<B', consts.SYMBOL))
        stream.write(self.value.encode('utf-8'))
        stream.write('\x00')

    def to_bool(self):
        return Bool(True)

    def to_string(self):
        return String(self.value)


@serializable(consts.STRING)
class String(Type):

    def __init__(self, value):
        if isinstance(value, str):
            value = value.decode('utf-8')

        self.value = value

    def __eq__(self, other):
        return isinstance(other, String) and self.value == other.value

    def __nonzero__(self):
        return bool(self.value)

    @classmethod
    def load(cls, stream):
        (length,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(stream.read(length).decode('utf-8'))

    def dump(self, stream):
        value = self.value.encode('utf-8')

        stream.write(struct.pack('<BI', consts.STRING, len(value)))
        stream.write(value)

    def to_bool(self):
        return Bool(len(self.value) > 0)

    def to_string(self):
        return self


class Pair(Type):

    def __init__(self, head, tail):
        self.head = head
        self.tail = tail

    @classmethod
    def from_sequence(self, sequence):
        result = Nil()

        for element in reversed(sequence):
            result = Pair(element, result)

        return result

    def concat(self, other):
        list = self

        while list.tail != Nil():
            list = list.tail

        list.tail = other

    def __len__(self):
        return len(list(e for e in self))

    def __iter__(self):
        iterator = self

        while isinstance(iterator, Pair):
            yield iterator.head

            iterator = iterator.tail

    def __getitem__(self, index):
        return list(self)[index]

    def to_string(self):
        if isinstance(self.tail, (Pair, Nil)):
            return String(u'({0})'.format(' '.join(
                repr(e).decode('utf-8') for e in self
            )))

        else:
            return String(u'({0} . {1})'.format(self.head, self.tail))

    def to_bool(self):
        return Bool(True)


class Quoted(Type):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Quoted) and self.value == other.value

    def to_bool(self):
        return Bool(True)

    def to_string(self):
        return String(u'\'{0}'.format(self.value))


class Quasiquoted(Type):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Quasiquoted) and self.value == other.value

    def to_bool(self):
        return Bool(True)

    def to_string(self):
        return String(u'`{0}'.format(self.value))


class Unquoted(Type):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Unquoted) and self.value == other.value

    def to_bool(self):
        return Bool(True)

    def to_string(self):
        return String(u',{0}'.format(self.value))


class Function(Type):

    def __init__(self, code, scope, name=None):
        self.code = code
        self.scope = scope
        self.name = name

    def to_string(self):
        if self.name:
            return String(u'(function {0})'.format(self.name))

        return String(u'(function)')


class NativeFunction(Function):

    def __init__(self, function, name=None):
        self.function = function
        self.name = name

    def __call__(self, *args):
        return self.function(*args)

    def to_string(self):
        if self.name:
            return String(u'(native-function {0})'.format(self.name))

        return String(u'(native-function)')


class Macro(Type):

    def __init__(self, rules):
        self.rules = rules

    def to_string(self):
        return String(u'(syntax)')

    def expand(self, vm, expression):
        for rule in self.rules:
            try:
                return rule.expand(vm, expression)

            except MatchError:
                pass

        raise MatchError()


class Rule(Type):

    def __init__(self, pattern, templates):
        self.pattern = pattern
        self.templates = templates

    def expand(self, vm, expression):
        result = []
        bindings = self.pattern.match(expression)

        for template in self.templates:
            result.append(template.expand(bindings))

        return result


class Pattern(Type):

    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, expression):
        return self.match_pattern(self.pattern, expression)

    def match_pattern(self, pattern, expression):
        if isinstance(pattern, Pair):
            return self.match_pair(pattern, expression)

        elif isinstance(pattern, Symbol):
            return self.match_symbol(pattern, expression)

        elif isinstance(pattern, Quoted):
            return self.match_quoted(pattern, expression)

        elif pattern == expression:
            return {}

        raise MatchError()

    def match_pair(self, pattern, expression):
        result = collections.defaultdict(list)

        if not isinstance(expression, (Pair, Nil)):
            raise MatchError()

        while pattern and (expression or (isinstance(pattern.tail, Pair) and pattern.tail.head == Ellipsis())):
            if isinstance(pattern.tail, Pair) and pattern.tail.head == Ellipsis():
                if pattern.tail.tail != Nil():
                    raise MatchError('ellipsis is greedy')

                values = collections.defaultdict(list)

                if not expression:
                    bindings = self.match_pattern(pattern.head, pattern.head)

                    for key in bindings:
                        values[key] = []

                while expression:
                    bindings = self.match_pattern(pattern.head, expression.head)
                    expression = expression.tail

                    for key, value in bindings.iteritems():
                        values[key].append(value)

                pattern = pattern.tail.tail

                result.update({
                    key: Pair.from_sequence(values[key])
                    for key in values
                })

            elif isinstance(pattern.tail, Pair):
                result.update(self.match_pattern(pattern.head, expression.head))
                pattern = pattern.tail
                expression = expression.tail

            else:
                result.update(self.match_pattern(pattern.head, expression.head))
                result.update(self.match_pattern(pattern.tail, expression.tail))

                pattern = None
                expression = None

        if pattern or expression:
            raise MatchError()

        return result

    def match_symbol(self, pattern, expression):
        if pattern == Symbol('_'):
            return {}

        return {pattern: expression}

    def match_quoted(self, pattern, expression):
        if pattern.value == expression:
            return {}

        raise MatchError()


class Template(object):

    def __init__(self, template):
        self.template = template

    def expand(self, bindings):
        compiler = mania.compiler.SimpleCompiler(Nil())

        if isinstance(self.template, Quasiquoted):
            compiler.compile_any(
                self.expand_template(self.template.value, bindings, None)
            )

        else:
            compiler.compile_any(self.template)

        compiler.builder.add(mania.instructions.Eval())

        module = compiler.builder.module

        return module.code(
            module.entry_point,
            len(module) - module.entry_point
        )

    def expand_template(self, template, bindings, index):
        if isinstance(template, Pair):
            return self.expand_pair(template, bindings, index)

        elif isinstance(template, Unquoted):
            return self.expand_unquoted(template, bindings, index)

        elif isinstance(template, Quoted):
            return Quoted(self.expand_template(template.value, bindings, index))

        elif isinstance(template, Quasiquoted):
            return Quasiquoted(self.expand_template(template.value, bindings, index))

        return template

    def expand_pair(self, template, bindings, index):
        if isinstance(template.tail, Pair) and template.tail.head == Ellipsis():
            result = []
            i = 0

            while True:
                try:
                    result.append(self.expand_template(
                        template.head, bindings, (index or []) + [i]
                    ))

                    i += 1

                except IndexError:
                    if i != 0:
                        result = Pair.from_sequence(result)

                    break

            tail = self.expand_template(
                template.tail.tail, bindings, index
            )

            if not result and not tail:
                raise IndexError()

            if not result:
                return tail

            result.concat(tail)

            return result

        return Pair(
            self.expand_template(template.head, bindings, index),
            self.expand_template(template.tail, bindings, index)
        )

    def expand_unquoted(self, template, bindings, index):
        if not isinstance(template.value, Symbol):
            raise MatchError()

        if index is None:
            return bindings[template.value]

        result = bindings[template.value]

        for i in index:
            result = result[i]

        return result


class NativeMacro(Macro):

    def to_string(self):
        return String(u'(native-syntax)')


class NativeRule(object):

    def __init__(self, pattern, template):
        self.pattern = pattern
        self.template = template

    def expand(self, vm, expression):
        result = []
        bindings = self.pattern.match(expression)

        return self.template(vm, bindings)


class Annotation(Type):
    pass


class Code(Type):

    def __init__(self, module, entry_point, size):
        self.module = module
        self.entry_point = entry_point
        self.size = size

    def to_string(self):
        return String(u'(code)')

    def __eq__(self, other):
        return (
            isinstance(other, Code) and
            self.module == other.module and
            self.entry_point == other.entry_point and
            self.size == other.size
        )

    def __len__(self):
        return self.size

    def __getitem__(self, index):
        if index < self.entry_point:
            raise IndexError('Index below entry point')

        elif index >= self.entry_point + self.size:
            raise IndexError('Index out of bounds')

        else:
            return self.module.instructions[index]

    def __setitem__(self, index, instruction):
        if index < self.entry_point:
            raise IndexError('Index below entry point')

        elif index >= self.entry_point + self.size:
            raise IndexError('Index out of bounds')

        else:
            self.module.instructions[index] = instruction


class Module(Type):

    def __init__(self, name, entry_point, constants, instructions, scope=None):
        self.name = name
        self.entry_point = entry_point
        self.constants = constants
        self.instructions = instructions
        self.scope = scope

    def to_string(self):
        return String(u'(module {0})'.format(self.name))

    def __len__(self):
        return len(self.instructions)

    @classmethod
    def load(cls, stream):
        if isinstance(stream, basestring):
            stream = io.BytesIO(stream)

        (header, flags, version, name, entry, count, size) = struct.unpack(
            '<3sBIIIII',
            stream.read(struct.calcsize('<3sBIIIII'))
        )

        assert header == 'bam'

        constants = []

        for _ in xrange(count):
            (type,) = struct.unpack('<B', stream.read(struct.calcsize('<B')))

            constants.append(serializable_types[type].load(stream))

        code = []

        while size > 0:
            (opcode,) = struct.unpack('<B', stream.read(struct.calcsize('<B')))

            instruction = mania.instructions.opcodes[opcode].load(stream)

            code.append(instruction)

            size -= instruction.size

        return cls(
            name=constants[name],
            entry_point=entry,
            constants=constants,
            instructions=code
        )

    def dumps(self):
        return self.dump().getvalue()

    def dump(self, stream=None):
        if stream is None:
            stream = io.BytesIO()

        code = io.BytesIO()

        for instruction in self.instructions:
            instruction.dump(code)

        stream.write(struct.pack(
            '<3sBIIIII',
            'bam',
            0,
            0,
            self.constants.index(self.name),
            self.entry_point,
            len(self.constants),
            len(code.getvalue())
        ))

        for constant in self.constants:
            constant.dump(stream)

        stream.write(code.getvalue())

        return stream

    def lookup(self, name):
        return self.scope.lookup(name)

    def code(self, entry_point=0, size=0):
        return Code(self, entry_point, size or len(self) - entry_point)


class NativeModule(Module):

    def __init__(self, name, scope=None):
        Module.__init__(self, name, None, None, None, scope or mania.frame.Scope())

        for name in dir(self):
            value = getattr(self, name)

            if isinstance(value, (types.FunctionType, types.MethodType)):
                if getattr(value, '_export', False):
                    name = getattr(value, '_export_name', name)

                    self.register(name, NativeFunction(value, Symbol(name)))

    def to_string(self):
        return String('(native-module {0})'.format(self.name))

    def register(self, name, value):
        self.scope.define(Symbol(name), value)


def export(function):
    if isinstance(function, basestring):
        name = function

        def _inner(function):
            function._export = True
            function._export_name = name

            return function

        return _inner

    function._export = True

    return function


class Stream(Type):

    def __init__(self, stream):
        self.stream = stream

    def to_string(self):
        return String('(stream)')
