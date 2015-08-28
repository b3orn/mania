#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from distutils.core import setup


setup(
    name='mania',
    version='0.1-dev',
    description='Compiler and runtime for the Mania programming language',
    license='MIT',
    author='Björn Schulz',
    author_email='bjoern@fac3.org',
    url='http://github.com/b3orn/mania',
    packages=['mania'],
    scripts=[
        'scripts/mania'
    ]
)
