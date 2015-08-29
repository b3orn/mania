# -*- coding: utf-8 -*-

'''
   mania.builtins
   ~~~~~~~~~~~~~~

   :copyright: (c) 2014 by Björn Schulz.
   :license: MIT, see LICENSE for more details.
'''

from __future__ import absolute_import, division
import logging
import mania.compiler
import mania.types
import mania.frame
import mania.instructions


logger = logging.getLogger(__name__)


def register_module(vm, bindings):
    name = bindings[mania.types.Symbol('name')]

    code = mania.types.Pair.from_sequence([
        mania.types.Symbol('define-module'),
        name,
        bindings[mania.types.Symbol('exports')]
    ])

    code.concat(bindings[mania.types.Symbol('body')])

    compiler = mania.compiler.SimpleCompiler(name)

    compiler.compile_any(code)

    compiler.builder.add(mania.instructions.Eval())
    compiler.builder.add(mania.instructions.Exit())

    module = compiler.builder.module

    vm.process.scheduler.node.registered_modules[name] = module

    return []


register_module_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('name'),
            mania.types.Pair.from_sequence([
                mania.types.Symbol('exports'),
                mania.types.Ellipsis()
            ]),
            mania.types.Symbol('body'),
            mania.types.Ellipsis()
        ])),
        register_module
    )
])


def ignore(vm, bindings):
    return []


ignore_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('body'),
            mania.types.Ellipsis()
        ])),
        ignore
    )
])


register_scope = mania.frame.Scope(locals={
    mania.types.Symbol('define-module'): register_module_macro,
    mania.types.Symbol('comment'): ignore_macro,
    mania.types.Symbol('author'): ignore_macro,
    mania.types.Symbol('copyright'): ignore_macro,
    mania.types.Symbol('license'): ignore_macro,
    mania.types.Symbol('version'): ignore_macro,
    mania.types.Symbol('description'): ignore_macro
})


def define_module(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    for element in bindings[mania.types.Symbol('body')]:
        compiler.compile_any(element)
        compiler.builder.add(mania.instructions.Eval())

    compiler.compile_any(bindings[mania.types.Symbol('name')])
    compiler.compile_any(bindings[mania.types.Symbol('exports')])
    
    compiler.builder.add(mania.instructions.BuildModule())
    compiler.builder.add(mania.instructions.Exit())

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


define_module_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('name'),
            mania.types.Pair.from_sequence([
                mania.types.Symbol('exports'),
                mania.types.Ellipsis()
            ]),
            mania.types.Symbol('body'),
            mania.types.Ellipsis()
        ])),
        define_module
    )
])


def define_function(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    compiler.compile_any(bindings[mania.types.Symbol('name')])
    compiler.builder.add(mania.instructions.Store(compiler.builder.constant(
        bindings[mania.types.Symbol('name')]
    )))

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


def define_value(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    compiler.compile_any(bindings[mania.types.Symbol('value')])
    compiler.builder.add(mania.instructions.Eval())
    compiler.builder.add(mania.instructions.Store(compiler.builder.constant(
        bindings[mania.types.Symbol('name')]
    )))

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


define_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Pair.from_sequence([
                mania.types.Symbol('name'),
                mania.types.Symbol('parameters'),
                mania.types.Ellipsis()
            ]),
            mania.types.Symbol('body'),
            mania.types.Ellipsis()
        ])),
        define_function
    ),
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('name'),
            mania.types.Symbol('value')
        ])),
        define_value
    )
])


def import_(vm, bindings):
    return []


import_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('name')
        ])),
        import_
    ),
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('name'),
            mania.types.Pair.from_sequence([
                mania.types.Symbol('import'),
                mania.types.Ellipsis()
            ])
        ])),
        import_
    )
])


default_scope = mania.frame.Scope(locals={
    mania.types.Symbol('define-module'): define_module_macro,
    mania.types.Symbol('define'): define_macro,
    mania.types.Symbol('import'): import_macro
})
