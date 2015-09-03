# -*- coding: utf-8 -*-

'''
   mania.builtins.mania_io
   ~~~~~~~~~~~~~~~~~~~~~~~

   :copyright: (c) 2015 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import, division
import logging
import sys
import mania.types as types


logger = logging.getLogger(__name__)


class IO(types.NativeModule):

    def __init__(self):
        types.NativeModule.__init__(self, types.Symbol('mania:io'))

        self.register('stdin', types.Stream(sys.stdin))
        self.register('stdout', types.Stream(sys.stdout))
        self.register('stderr', types.Stream(sys.stderr))

    @types.export
    def read(self, stream, number):
        return types.String(stream.stream.read(number))

    @types.export
    def write(self, stream, data):
        stream.stream.write(data.value)

        return types.Integer(len(data.value))
