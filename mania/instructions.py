# -*- coding: utf-8 -*-

'''
   mania.instructions
   ~~~~~~~~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging
import struct
import mania.consts as consts
import mania.node as node
import mania.compiler
import mania.types
import mania.frame


logger = logging.getLogger(__name__)


opcodes = {}

def opcode(opcode):
    def _inner(cls):
        opcodes[opcode] = cls

        cls.opcode = opcode

        return cls

    return _inner


class Instruction(object):

    @property
    def size(self):
        return struct.calcsize('<B')

    @classmethod
    def load(cls, stream):
        return cls()

    def dump(self, stream):
        stream.write(struct.pack('<B', self.opcode))

    def eval(self, vm):
        raise NotImplementedError('"eval" needs to be implemented in subclasses')


@opcode(consts.NOP)
class Nop(Instruction):

    def eval(self, vm):
        pass


class StackOperation(Instruction):

    def __init__(self, count):
        self.count = count

    @property
    def size(self):
        return super(StackOperation, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (index,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(index)

    def dump(self, stream):
        super(StackOperation, self).dump(stream)

        stream.write(struct.pack('<I', self.index))


@opcode(consts.DUPLICATE)
class Duplicate(StackOperation):

    def eval(self, vm):
        vm.frame.stack.extend(vm.frame.stack[-self.count:])


@opcode(consts.ROTATE)
class Rotate(StackOperation):

    def eval(self, vm):
        vm.frame.stack[-self.number:] = vm.frame.stack[-self.count:][::-1]


@opcode(consts.POP)
class Pop(StackOperation):

    def eval(self, vm):
        for _ in xrange(self.count):
            vm.frame.pop()


class LoadStoreOperation(Instruction):

    def __init__(self, index):
        self.index = index

    @property
    def size(self):
        return super(LoadStoreOperation, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (index,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(index)

    def dump(self, stream):
        super(LoadStoreOperation, self).dump(stream)

        stream.write(struct.pack('<I', self.index))


@opcode(consts.STORE)
class Store(LoadStoreOperation):

    def eval(self, vm):
        vm.frame.define(vm.frame.constant(self.index), vm.frame.pop())


@opcode(consts.LOAD)
class Load(LoadStoreOperation):

    def eval(self, vm):
        name = vm.frame.constant(self.index)

        try:
            vm.frame.push(vm.frame.lookup(name))

        except NameError:
            name = name.value
            scope = vm.frame

            while name:
                if ':' in name and all(c == ':' for c in name):
                    vm.frame.push(scope.lookup(mania.types.Symbol(name)))

                elif ':' in name:
                    head, name = name.split(':')

                    scope = scope.lookup(mania.types.Symbol(head))

                else:
                    vm.frame.push(scope.lookup(mania.types.Symbol(name)))


@opcode(consts.LOAD_FIELD)
class LoadField(LoadStoreOperation):

    def eval(self, vm):
        vm.frame.push(vm.frame.pop().lookup(vm.frame.constant(self.index)))


@opcode(consts.LOAD_CONSTANT)
class LoadConstant(LoadStoreOperation):

    def eval(self, vm):
        vm.frame.push(vm.frame.constant(self.index))


@opcode(consts.LOAD_CODE)
class LoadCode(Instruction):

    def __init__(self, entry_point, size):
        self.entry_point = entry_point
        self._size = size

    @property
    def size(self):
        return super(LoadCode, self).size + struct.calcsize('<II')

    @classmethod
    def load(cls, stream):
        (entry, size) = struct.unpack('<II', stream.read(struct.calcsize('<II')))

        return cls(entry, size)

    def dump(self, stream):
        super(LoadCode, self).dump(stream)

        stream.write(struct.pack('<II', self.entry_point, self._size))

    def eval(self, vm):
        vm.frame.push(vm.frame.code.module.code(self.entry_point, self._size))


@opcode(consts.LOAD_MODULE)
class LoadModule(LoadStoreOperation):

    def eval(self, vm):
        name = vm.frame.constants(self.index)

        try:
            module = vm.process.scheduler.node.load_module(name)

            vm.frame.define(name, module)

            vm.frame.push(module)

        except LoadingDeferred:
            vm.process.status = node.WAITING_FOR_MODULE
            vm.process.waiting_for = name
            vm.frame.position -= 1

            raise node.Schedule()


@opcode(consts.ADD)
class Add(Instruction):

    def eval(self, vm):
        y = vm.frame.pop()
        x = vm.frame.pop()

        vm.frame.push(x.add(y))


@opcode(consts.SUB)
class Sub(Instruction):

    def eval(self, vm):
        y = vm.frame.pop()
        x = vm.frame.pop()

        vm.frame.push(x.sub(y))


@opcode(consts.MUL)
class Mul(Instruction):

    def eval(self, vm):
        y = vm.frame.pop()
        x = vm.frame.pop()

        vm.frame.push(x.mul(y))


@opcode(consts.BUILD_QUOTED)
class BuildQuoted(Instruction):

    def eval(self, vm):
        vm.frame.push(mania.types.Quoted(vm.frame.pop()))


@opcode(consts.BUILD_QUASIQUOTED)
class BuildQuasiquoted(Instruction):

    def eval(self, vm):
        vm.frame.push(mania.types.Quasiquoted(vm.frame.pop()))


@opcode(consts.BUILD_UNQUOTED)
class BuildUnquoted(Instruction):

    def eval(self, vm):
        vm.frame.push(mania.types.Unquoted(vm.frame.pop()))


@opcode(consts.BUILD_PAIR)
class BuildPair(Instruction):

    def eval(self, vm):
        tail = vm.frame.pop()
        head = vm.frame.pop()

        vm.frame.push(mania.types.Pair(head, tail))


@opcode(consts.BUILD_FUNCTION)
class BuildFunction(Instruction):

    def eval(self, vm):
        code = vm.frame.pop()

        vm.frame.push(mania.types.Function(code, vm.frame.scope))


@opcode(consts.BUILD_MACRO)
class BuildMacro(Instruction):

    def __init__(self, count):
        self.count = count

    @property
    def size(self):
        return super(BuildMacro, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (count,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(count)

    def eval(self, vm):
        rules = [vm.frame.pop() for _ in xrange(self.count)][::-1]

        vm.frame.push(mania.types.Macro(rules))


@opcode(consts.BUILD_RULE)
class BuildRule(Instruction):

    def eval(self, vm):
        templates = vm.frame.pop()
        pattern = vm.frame.pop()

        vm.frame.push(mania.types.Rule(pattern, templates))


@opcode(consts.BUILD_PATTERN)
class BuildPattern(Instruction):

    def eval(self, vm):
        vm.frame.push(mania.types.Pattern(vm.frame.pop()))


@opcode(consts.BUILD_TEMPLATE)
class BuildTemplate(Instruction):

    def __init__(self, count):
        self.count = count

    @property
    def size(self):
        return super(BuildTemplate, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (count,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(count)

    def eval(self, vm):
        templates = [vm.frame.pop() for _ in xrange(self.count)][::-1]

        vm.frame.push([
            mania.types.Template(template) for template in templates
        ])


@opcode(consts.EXIT)
class Exit(Instruction):

    def eval(self, vm):
        vm.process.status = node.EXITING

        raise node.Schedule()


@opcode(consts.JUMP)
class Jump(Instruction):

    def __init__(self, position):
        self.position = position

    @property
    def size(self):
        return super(Jump, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (position,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(position)

    def dump(self, stream):
        super(Jump, self).dump(stream)

        stream.write(struct.pack('<I', self.number))

    def eval(self, vm):
        vm.frame.position = self.position


@opcode(consts.JUMP_IF_NIL)
class JumpIfNil(Jump):

    def eval(self, vm):
        if vm.frame.pop() == mania.types.Nil():
            vm.frame.position = self.position


@opcode(consts.JUMP_IF_TRUE)
class JumpIfTrue(Jump):

    def eval(self, vm):
        if vm.frame.pop() == mania.types.Bool(True):
            vm.frame.position = self.position


@opcode(consts.JUMP_IF_FALSE)
class JumpIfFalse(Jump):

    def eval(self, vm):
        if vm.frame.pop() == mania.types.Bool(False):
            vm.frame.position = self.position


@opcode(consts.JUMP_IF_EMPTY)
class JumpIfEmpty(Jump):

    def eval(self, vm):
        if len(vm.frame.stack) == 0:
            vm.frame.position = self.position


@opcode(consts.JUMP_IF_NOT_EMPTY)
class JumpIfNotEmpty(Jump):

    def eval(self, vm):
        if len(vm.frame.stack) != 0:
            vm.frame.position = self.position


@opcode(consts.JUMP_IF_SIZE)
class JumpIfSize(Jump):

    def __init__(self, size, position):
        self.size_ = size
        self.position = position

    @property
    def size(self):
        return super(JumpIfSize, self).size + struct.calcsize('<II')

    @classmethod
    def load(cls, stream):
        (size, position) = struct.unpack('<II', stream.read(struct.calcsize('<II')))

        return cls(size, position)

    def dump(self, stream):
        super(JumpIfSize, self).dump(stream)

        stream.write(struct.pack('<II', self.number))

    def eval(self, vm):
        if len(vm.frame.stack) == self.size_:
            vm.frame.position = self.position


@opcode(consts.CALL)
class Call(Instruction):

    def __init__(self, number):
        self.number = number

    @property
    def size(self):
        return super(Call, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (number,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(number)

    def dump(self, stream):
        super(Call, self).dump(stream)

        stream.write(struct.pack('<I', self.number))

    def eval(self, vm):
        args = [vm.frame.pop() for _ in xrange(self.number)]

        callable = vm.frame.pop()

        if isinstance(callable, mania.types.NativeFunction):
            result = callable(*args[::-1])

            if result is None:
                result = mania.types.Undefined()

            vm.frame.push(result)

        else:
            vm.frame = mania.frame.Frame(
                parent=vm.frame,
                scope=mania.frame.Scope(parent=callable.scope),
                code=callable.code,
                stack=mania.frame.Stack(args)
            )


@opcode(consts.APPLY)
class Apply(Call):

    def eval(self, vm):
        list = (vm.frame.pop() or [])[::-1]
        args = list + [vm.frame.pop() for _ in xrange(self.number)]

        callable = vm.frame.pop()

        if isinstance(callable, mania.types.NativeFunction):
            result = callable(*args[::-1])

            if result is None:
                result = mania.types.Undefined()

            vm.frame.push(result)

        else:
            vm.frame = mania.frame.Frame(
                parent=vm.frame,
                scope=mania.frame.Scope(parent=callable.scope),
                code=callable.code,
                stack=mania.frame.Stack(args)
            )


@opcode(consts.RETURN)
class Return(Instruction):

    def eval(self, vm):
        value = vm.frame.stack.pop()

        vm.restore()

        vm.frame.stack.push(value)


@opcode(consts.RESTORE)
class Restore(Instruction):

    def eval(self, vm):
        vm.restore()


@opcode(consts.REVERSE)
class Reverse(Instruction):

    def eval(self, vm):
        if isinstance(vm.frame.peek(), mania.types.Pair):
            vm.frame.push(mania.types.Pair.from_sequence(vm.frame.pop()[::-1]))


@opcode(consts.EVAL)
class Eval(Instruction):

    def compile_call(self, vm, expression):
        compiler = mania.compiler.SimpleCompiler(None)

        n = -1
        call = True

        while expression != mania.types.Nil():
            if expression.head == mania.types.Ellipsis():
                if expression.tail != mania.types.Nil():
                    raise mania.types.ExpandError()

                call = False
                n -= 1

                break

            compiler.compile_any(expression.head)

            compiler.builder.add(Eval())

            expression = expression.tail
            n += 1

        if call:
            compiler.builder.add(Call(n))

        else:
            compiler.builder.add(Apply(n))

        module = compiler.builder.module

        vm.frame = mania.frame.Frame(
            parent=vm.frame,
            scope=vm.frame.scope,
            stack=vm.frame.stack,
            code=module.code(
                module.entry_point,
                len(module) - module.entry_point
            )
        )

    def eval(self, vm):
        expression = vm.frame.pop()

        if isinstance(expression, mania.types.Pair):
            if isinstance(expression.head, mania.types.Pair):
                self.compile_call(vm, expression)

            elif isinstance(expression.head, mania.types.Symbol):
                evalable = vm.frame.lookup(expression.head)

                if isinstance(evalable, mania.types.Macro):
                    result = (evalable.expand(vm, expression) or [])[::-1]

                    if result:
                        for code in result:
                            vm.frame = mania.frame.Frame(
                                parent=vm.frame,
                                scope=vm.frame.scope,
                                stack=vm.frame.stack,
                                code=code
                            )

                    else:
                        vm.frame.push(mania.types.Undefined())

                elif isinstance(evalable, mania.types.Function):
                    self.compile_call(vm, expression)

                else:
                    raise SyntaxError('{0} is not callable'.format(
                        evalable
                    ))

            else:
                raise SyntaxError('type {0} is not callable'.format(
                    type(expression.head)
                ))

        elif isinstance(expression, mania.types.Symbol):
            try:
                evalable = vm.frame.lookup(expression)

            except NameError:
                name = expression.value
                scope = vm.frame

                while name:
                    if ':' in name and all(c == ':' for c in name):
                        vm.frame.push(scope.lookup(mania.types.Symbol(name)))

                    elif ':' in name:
                        head, name = name.split(':')

                        scope = scope.lookup(mania.types.Symbol(head))

                    else:
                        vm.frame.push(scope.lookup(mania.types.Symbol(name)))

            if isinstance(evalable, mania.types.Macro):
                try:
                    result = (evalable.expand(vm, expression) or [])[::-1]

                    if result:
                        for code in result:
                            vm.frame = mania.frame.Frame(
                                parent=vm.frame,
                                scope=vm.frame.scope,
                                stack=vm.frame.stack,
                                code=code
                            )

                    else:
                        vm.frame.push(mania.types.Undefined())

                except mania.types.MatchError:
                    vm.frame.push(evalable)

            else:
                vm.frame.push(evalable)

        elif isinstance(expression, mania.types.Quoted):
            vm.frame.push(expression.value)

        elif isinstance(expression, mania.types.Quasiquoted):
            pass

        elif isinstance(expression, mania.types.Unquoted):
            raise SyntaxError('Unquote is only allowed inside a quasiquote')

        else:
            vm.frame.push(expression)


@opcode(consts.BUILD_MODULE)
class BuildModule(Instruction):

    def eval(self, vm):
        exports = vm.frame.pop()
        name = vm.frame.pop()

        locals = {}

        for export in exports:
            locals[export] = vm.frame.lookup(export)

        scope = mania.frame.Scope(locals=locals)

        module = mania.types.Module(
            name=name,
            entry_point=0,
            constants=[],
            instructions=[],
            scope=scope
        )

        vm.process.scheduler.node.loaded_modules[name] = module


class Receive(Instruction):

    def eval(self, vm):
        if vm.process.queue.empty():
            vm.process.status = WAITING_FOR_MESSAGE
            vm.frame.position -= 1

            raise Schedule()

        else:
            vm.frame.push(vm.process.queue.get())
