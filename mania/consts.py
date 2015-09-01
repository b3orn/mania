# -*- coding: utf-8 -*-

'''
   mania.consts
   ~~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging


logger = logging.getLogger(__name__)


# Types
ELLIPSIS  = 0x00
UNDEFINED = 0x01
NIL       = 0x02
BOOLEAN   = 0x03
INTEGER   = 0x04
FLOAT     = 0x05
SYMBOL    = 0x06
STRING    = 0x07


# Opcodes
NOP                = 0x00
DUPLICATE          = 0x10
ROTATE             = 0x11
POP                = 0x12
STORE              = 0x13
LOAD               = 0x14
LOAD_FIELD         = 0x15
LOAD_CONSTANT      = 0x16
LOAD_CODE          = 0x17
LOAD_MODULE        = 0x18
NEGATE             = 0x20
ADD                = 0x21
SUB                = 0x22
MUL                = 0x23
DIV                = 0x24
POW                = 0x25
MOD                = 0x26
REM                = 0x27
ROUND              = 0x28
FLOOR              = 0x29
CEIL               = 0x2a
BIT_NOT            = 0x30
BIT_AND            = 0x31
BIT_OR             = 0x32
BIT_XOR            = 0x33
BIT_SHIFT_LEFT     = 0x34
BIT_SHIFT_RIGHT    = 0x35
LOGIC_NOT          = 0x40
LOGIC_AND          = 0x41
LOGIC_OR           = 0x42
LOGIC_XOR          = 0x43
TYPE               = 0x44
EQUAL              = 0x45
NOT_EQUAL          = 0x46
GREATER            = 0x47
GREATER_EQUAL      = 0x48
LESS               = 0x49
LESS_EQUAL         = 0x4a
JUMP               = 0x50
JUMP_IF_NIL        = 0x51
JUMP_IF_TRUE       = 0x52
JUMP_IF_FALSE      = 0x53
JUMP_IF_EMPTY      = 0x54
JUMP_IF_NOT_EMPTY  = 0x55
JUMP_IF_SIZE       = 0x56
CALL               = 0x57
APPLY              = 0x58
RETURN             = 0x59
THROW              = 0x5a
SETUP_CATCH        = 0x5b
END_CATCH          = 0x5c
SPAWN              = 0x60
EXIT               = 0x61
SEND               = 0x62
RECEIVE            = 0x63
BLOCK              = 0x64
YIELD              = 0x65
RESTORE            = 0x66
HEAD               = 0x70
TAIL               = 0x71
REVERSE            = 0x72
UNPACK             = 0x73
BUILD_PAIR         = 0x80
BUILD_LIST         = 0x81
BUILD_QUOTED       = 0x82
BUILD_QUASIQUOTED  = 0x83
BUILD_UNQUOTED     = 0x84
BUILD_FUNCTION     = 0x85
BUILD_MACRO        = 0x86
BUILD_RULE         = 0x87
BUILD_PATTERN      = 0x88
BUILD_TEMPLATE     = 0x89
BUILD_CONTINUATION = 0x8a
BUILD_MODULE       = 0x8b
EVAL               = 0x90
