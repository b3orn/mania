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
import mania.types


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
class BuildQuoted(Instruction):

    def eval(self, vm):
        vm.frame.push(mania.types.Quasiquoted(vm.frame.pop()))


@opcode(consts.BUILD_UNQUOTED)
class BuildQuoted(Instruction):

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
        pass


@opcode(consts.EVAL)
class Eval(Instruction):

    def eval(self, vm):
        pass


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
