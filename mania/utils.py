# -*- coding: utf-8 -*-

'''
   mania.utils
   ~~~~~~~~~~~

   :copyright: (c) 2015 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import
import logging
import re
import mania.types


logger = logging.getLogger(__name__)


r_name = re.compile((
    r'^((?:[^\W0-9]|[\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
    r'(?:'
        r'(?:'
            r'(?<=[\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
            r'(?:[^\W0-9]|[\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
            r'[\w\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~]*'
        r')'
        r'|'
        r'(?:'
            r'(?<![\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~])'
            r'[\w\!\$\%\&\*\+\-\/\<\=\>\?\@\\\^\_\|\~]*'
        r')'
    r')?):('
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
    r')?)$'
))


def split_name(name):
    name = name.value
    parts = []

    if ':' not in name or all(c == ':' for c in name):
        yield [mania.types.Symbol(name)]

        return

    while True:
        match = r_name.match(name)

        if match:
            parts.append(match.group(1))

            name = match.group(2)

            if not r_name.match(name):
                parts.append(name)

        else:
            break

    module = ''

    for i in xrange(1, len(parts)):
        yield map(
            mania.types.Symbol,
            [':'.join(parts[:len(parts) - i])] + parts[len(parts) - i:]
        )
