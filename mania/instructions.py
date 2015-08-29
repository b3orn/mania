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


@opcode(consts.STORE)
class Store(Instruction):

    def __init__(self, index):
        self.index = index

    @property
    def size(self):
        return super(Store, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (index,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(index)

    def dump(self, stream):
        super(Store, self).dump(stream)

        stream.write(struct.pack('<I', self.index))

    def eval(self, vm):
        vm.frame.define(vm.frame.constant(self.index), vm.frame.pop())


@opcode(consts.LOAD)
class Load(Instruction):

    def __init__(self, index):
        self.index = index

    @property
    def size(self):
        return super(Load, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (index,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(index)

    def dump(self, stream):
        super(Load, self).dump(stream)

        stream.write(struct.pack('<I', self.index))

    def eval(self, vm):
        vm.frame.push(vm.frame.lookup(vm.frame.constant(self.index)))


@opcode(consts.LOAD_CONSTANT)
class LoadConstant(Instruction):

    def __init__(self, index):
        self.index = index

    @property
    def size(self):
        return super(LoadConstant, self).size + struct.calcsize('<I')

    @classmethod
    def load(cls, stream):
        (index,) = struct.unpack('<I', stream.read(struct.calcsize('<I')))

        return cls(index)

    def dump(self, stream):
        super(LoadConstant, self).dump(stream)

        stream.write(struct.pack('<I', self.index))

    def eval(self, vm):
        vm.frame.push(vm.frame.constant(self.index))


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


@opcode(consts.EXIT)
class Exit(Instruction):

    def eval(self, vm):
        vm.process.status = node.EXITING

        raise node.Schedule()


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
        args = [vm.frame.pop() for _ in xrange(self.number)][::-1]

        callable = vm.frame.pop()

        if isinstance(callable, mania.types.NativeFunction):
            for item in callable(*args):
                vm.frame.push(item)

        else:
            vm.frame = mania.frame.Frame(
                parent=vm.frame,
                scope=mania.frame.Scope(parent=callable.scope),
                code=callable.code,
                stack=vm.frame.Stack(args)
            )


@opcode(consts.EVAL)
class Eval(Instruction):

    def eval(self, vm):
        expression = vm.frame.pop()

        if isinstance(expression, mania.types.Pair):
            if isinstance(expression.head, mania.types.Pair):
                compiler = mania.compiler.SimpleCompiler(None)

                n = -1

                while expression != mania.types.Nil():
                    compiler.compile_any(expression.head)

                    compiler.builder.add(Eval())

                    expression = expression.tail
                    n += 1

                compiler.builder.add(Call(n))

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

            elif isinstance(expression.head, mania.types.Symbol):
                evalable = vm.frame.lookup(expression.head)

                if isinstance(evalable, mania.types.Macro):
                    for code in reversed(evalable.expand(vm, expression)):
                        vm.frame = mania.frame.Frame(
                            parent=vm.frame,
                            scope=vm.frame.scope,
                            stack=vm.frame.stack,
                            code=code
                        )

                elif isinstance(evalable, mania.types.Function):
                    compiler = mania.compiler.SimpleCompiler(None)

                    n = -1

                    while expression != mania.types.Nil():
                        compiler.compile_any(expression.head)

                        compiler.builder.add(Eval())

                        expression = expression.tail
                        n += 1

                    compiler.builder.add(Call(n))

                    module = compiler.builder.module

                    vm.frame = mania.frame.Frame(
                        parent=vm.frame,
                        scope=vm.frame.scope,
                        stack=vm.frame.stack,
                        code=module.code(module.entry_point, len(module))
                    )

                else:
                    raise SyntaxError('{0} is not callable'.format(
                        evalable
                    ))

            else:
                raise SyntaxError('type {0} is not callable'.format(
                    type(expression.head)
                ))

        elif isinstance(expression, mania.types.Symbol):
            evalable = vm.frame.lookup(expression)

            if isinstance(evalable, mania.types.Macro):
                pass

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


class LoadModule(Instruction):

    def __init__(self, index):
        self.index = index

    def eval(self, vm):
        name = vm.frame.constants(self.index)

        try:
            module = vm.process.scheduler.node.load_module(name)

            vm.frame.push(module)

        except LoadingDeferred:
            vm.process.status = WAITING_FOR_MODULE
            vm.process.waiting_for = name
            vm.frame.position -= 1

            raise Schedule()

        except LoadError as e:
            vm.throw(e)


class Receive(Instruction):

    def eval(self, vm):
        if vm.process.queue.empty():
            vm.process.status = WAITING_FOR_MESSAGE
            vm.frame.position -= 1

            raise Schedule()

        else:
            vm.frame.push(vm.process.queue.get())
