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
    pass


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
    name = bindings[mania.types.Symbol('name')]
    parameters = bindings[mania.types.Symbol('parameters')] or []
    body = bindings[mania.types.Symbol('body')] or []

    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    for i, parameter in enumerate(parameters):
        compiler.builder.add(mania.instructions.Store(
            compiler.builder.constant(parameter)
        ))

    for node in body:
        compiler.compile_any(node)
        compiler.builder.add(mania.instructions.Eval())

    compiler.builder.add(mania.instructions.Return())

    entry_point = compiler.builder.index()

    compiler.builder.add(mania.instructions.LoadCode(0, entry_point))
    compiler.builder.add(mania.instructions.BuildFunction())
    compiler.builder.add(mania.instructions.Store(
        compiler.builder.constant(name)
    ))
    compiler.builder.add(mania.instructions.Load(
        compiler.builder.constant(name)
    ))

    module = compiler.builder.module

    module.entry_point = entry_point

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
    compiler.builder.add(mania.instructions.Load(compiler.builder.constant(
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


def lambda_(vm, bindings):
    parameters = bindings[mania.types.Symbol('parameters')] or []
    body = bindings[mania.types.Symbol('body')] or []

    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    for i, parameter in enumerate(parameters):
        compiler.builder.add(mania.instructions.Store(
            compiler.builder.constant(parameter)
        ))

    for node in body:
        compiler.compile_any(node)
        compiler.builder.add(mania.instructions.Eval())

    compiler.builder.add(mania.instructions.Return())

    entry_point = compiler.builder.index()

    compiler.builder.add(mania.instructions.LoadCode(0, entry_point))
    compiler.builder.add(mania.instructions.BuildFunction())

    module = compiler.builder.module

    module.entry_point = entry_point

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


lambda_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Pair.from_sequence([
                mania.types.Symbol('parameters'),
                mania.types.Ellipsis()
            ]),
            mania.types.Symbol('body'),
            mania.types.Ellipsis()
        ])),
        lambda_
    )
])


def import_(vm, bindings):
    pass


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


def add(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    compiler.compile_any(bindings[mania.types.Symbol('x')])
    compiler.builder.add(mania.instructions.Eval())
    compiler.compile_any(bindings[mania.types.Symbol('y')])
    compiler.builder.add(mania.instructions.Eval())
    compiler.builder.add(mania.instructions.Add())

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


add_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('x'),
            mania.types.Symbol('y')
        ])),
        add
    )
])


def add(x, y):
    return [x.add(y)]


add_macro = mania.types.NativeFunction(add)


def sub(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    compiler.compile_any(bindings[mania.types.Symbol('x')])
    compiler.builder.add(mania.instructions.Eval())
    compiler.compile_any(bindings[mania.types.Symbol('y')])
    compiler.builder.add(mania.instructions.Eval())
    compiler.builder.add(mania.instructions.Sub())

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


sub_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('x'),
            mania.types.Symbol('y')
        ])),
        sub
    )
])


def sub(x, y):
    return [x.sub(y)]


sub_macro = mania.types.NativeFunction(sub)


def mul(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    compiler.compile_any(bindings[mania.types.Symbol('x')])
    compiler.builder.add(mania.instructions.Eval())
    compiler.compile_any(bindings[mania.types.Symbol('y')])
    compiler.builder.add(mania.instructions.Eval())
    compiler.builder.add(mania.instructions.Mul())

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


mul_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('x'),
            mania.types.Symbol('y')
        ])),
        mul
    )
])


def mul(x, y):
    return [x.mul(y)]


mul_macro = mania.types.NativeFunction(mul)


def let(vm, bindings):
    variables = list(bindings[mania.types.Symbol('variables')] or [])
    values = list(bindings[mania.types.Symbol('values')] or [])

    if len(values) != len(variables):
        raise SyntaxError('let bindings need a value')

    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    for name in variables:
        compiler.builder.add(mania.instructions.Store(
            compiler.builder.constant(name)
        ))

    for node in bindings[mania.types.Symbol('body')]:
        compiler.compile_any(node)
        compiler.builder.add(mania.instructions.Eval())

    compiler.builder.add(mania.instructions.Return())

    size = compiler.builder.index()

    compiler.builder.add(mania.instructions.LoadCode(0, size))
    compiler.builder.add(mania.instructions.BuildFunction())

    if mania.types.Symbol('name') in bindings:
        name = bindings[mania.types.Symbol('name')]

        compiler.builder.add(mania.instructions.Store(
            compiler.builder.constant(name)
        ))
        compiler.builder.add(mania.instructions.Load(
            compiler.builder.constant(name)
        ))

    for value in values:
        compiler.compile_any(value)
        compiler.builder.add(mania.instructions.Eval())

    compiler.builder.add(mania.instructions.Call(len(values)))
    compiler.builder.add(mania.instructions.Return())

    entry_point = compiler.builder.index()

    compiler.builder.add(mania.instructions.LoadCode(size, entry_point - size))
    compiler.builder.add(mania.instructions.BuildFunction())
    compiler.builder.add(mania.instructions.Call(0))

    module = compiler.builder.module

    module.entry_point = entry_point

    return [module.code(
        module.entry_point,
        len(module) - module.entry_point
    )]


let_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Pair.from_sequence([
                mania.types.Pair.from_sequence([
                    mania.types.Symbol('variables'),
                    mania.types.Symbol('values')
                ]),
                mania.types.Ellipsis()
            ]),
            mania.types.Symbol('body'),
            mania.types.Ellipsis()
        ])),
        let
    ),
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('name'),
            mania.types.Pair.from_sequence([
                mania.types.Pair.from_sequence([
                    mania.types.Symbol('variables'),
                    mania.types.Symbol('values')
                ]),
                mania.types.Ellipsis()
            ]),
            mania.types.Symbol('body'),
            mania.types.Ellipsis()
        ])),
        let
    )
])


def if_(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    compiler.compile_any(bindings[mania.types.Symbol('condition')])
    compiler.builder.add(mania.instructions.Eval())

    negative_jump = compiler.builder.add(None)

    compiler.compile_any(bindings[mania.types.Symbol('positive')])
    compiler.builder.add(mania.instructions.Eval())

    end_jump = compiler.builder.add(None)

    compiler.builder.replace(
        negative_jump,
        mania.instructions.JumpIfFalse(compiler.builder.index())
    )

    if mania.types.Symbol('negative') in bindings:
        compiler.compile_any(bindings[mania.types.Symbol('negative')])
        compiler.builder.add(mania.instructions.Eval())

    else:
        compiler.builder.add(mania.instructions.LoadConstant(
            compiler.builder.constant(mania.types.Undefined())
        ))

    end = compiler.builder.add(mania.instructions.Restore())

    compiler.builder.replace(end_jump, mania.instructions.Jump(end))

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module)
    )]


if_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('condition'),
            mania.types.Symbol('positive')
        ])),
        if_
    ),
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('condition'),
            mania.types.Symbol('positive'),
            mania.types.Symbol('negative')
        ])),
        if_
    )
])


def and_(vm, bindings):
    compiler = mania.compiler.SimpleCompiler(mania.types.Nil())

    compiler.compile_any(bindings[mania.types.Symbol('left')])
    compiler.builder.add(mania.instructions.Eval())

    left_false = compiler.builder.add(None)

    compiler.compile_any(bindings[mania.types.Symbol('right')])
    compiler.builder.add(mania.instructions.Eval())

    right_false = compiler.builder.add(None)

    compiler.builder.add(mania.instructions.LoadConstant(
        compiler.builder.constant(mania.types.Bool(True))
    ))

    compiler.builder.add(mania.instructions.Restore())

    false_position = compiler.builder.add(mania.instructions.LoadConstant(
        compiler.builder.constant(mania.types.Bool(False))
    ))

    compiler.builder.replace(
        left_false,
        mania.instructions.JumpIfFalse(false_position)
    )

    compiler.builder.replace(
        right_false,
        mania.instructions.JumpIfFalse(false_position)
    )

    module = compiler.builder.module

    return [module.code(
        module.entry_point,
        len(module)
    )]


and_macro = mania.types.NativeMacro([
    mania.types.NativeRule(
        mania.types.Pattern(mania.types.Pair.from_sequence([
            mania.types.Symbol('_'),
            mania.types.Symbol('left'),
            mania.types.Symbol('right')
        ])),
        and_
    )
])


def println(*args):
    print ' '.join(map(str, args))

    return mania.types.Undefined()


def equal(x, y):
    return [mania.types.Bool(x == y)]


def not_equal(x, y):
    return [mania.types.Bool(x != y)]


def greater(x, y):
    return [mania.types.Bool(x > y)]


default_scope = mania.frame.Scope(locals={
    mania.types.Symbol('define-module'): define_module_macro,
    mania.types.Symbol('define'): define_macro,
    mania.types.Symbol('lambda'): lambda_macro,
    mania.types.Symbol('import'): import_macro,
    mania.types.Symbol('+'): add_macro,
    mania.types.Symbol('-'): sub_macro,
    mania.types.Symbol('*'): mul_macro,
    mania.types.Symbol('println'): mania.types.NativeFunction(println, name='println'),
    mania.types.Symbol('=='): mania.types.NativeFunction(equal),
    mania.types.Symbol('/='): mania.types.NativeFunction(not_equal),
    mania.types.Symbol('>'): mania.types.NativeFunction(greater),
    mania.types.Symbol('let'): let_macro,
    mania.types.Symbol('if'): if_macro,
    mania.types.Symbol('and'): and_macro
})
