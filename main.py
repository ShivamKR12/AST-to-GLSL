from ursina import *

import ast
import inspect
import textwrap
import typing

app = Ursina(size=(800, 600))

class VertIn(typing.Generic[typing.TypeVar('T')]):
    pass
class FragIn(typing.Generic[typing.TypeVar('T')]):
    pass
class VertOut(typing.Generic[typing.TypeVar('T')]):
    pass
class FragOut(typing.Generic[typing.TypeVar('T')]):
    pass
class VertUni(typing.Generic[typing.TypeVar('T')]):
    pass
class FragUni(typing.Generic[typing.TypeVar('T')]):
    pass

py_to_glsl_precedence_dict = {
    ast.Add: 0,
    ast.Sub: 0,
    ast.Mult: 1,
    ast.Div: 1,
}

glsl_builtin_vars = {
    'gl_Position',
    'gl_FragCoord',
    'gl_FragColor',
}

def py_to_glsl_err(cls, node, error_msg, line_msg='here', indent=0):
    min_lineno = max(node.lineno - 1 - 3, 0)
    max_lineno = min(node.lineno - 1 + 3, len(cls.file_lines) - 1)
    msg = ''
    max_line_length = 50
    for lineno in range(min_lineno, max_lineno + 1):
        line = cls.file_lines[lineno]
        max_line_length = max(len(line), max_line_length)
        msg +=  line
        if lineno == node.lineno - 1:
            msg += '  <--------- ' + line_msg
        msg += '\n'
    sep = '-' * (max_line_length + 2)
    raise Exception(
        'Shader error ({}:{}): {}\n{}\n{}\n{}'.format(
            cls.__name__, node.lineno, error_msg,
            sep, msg, sep
        )
    )

def glsl_has_higher_precedence(a, b):
    return py_to_glsl_precedence_dict[type(a)] > py_to_glsl_precedence_dict[type(b)]

def py_constant_to_glsl(cls, node, indent=0):
    return '{}'.format(node.value)

def py_name_to_glsl(cls, node, indent=0):
    return '{}'.format(node.id)

def py_op_to_glsl(cls, node, indent=0):
    op_str = None

    if isinstance(node, ast.Add):
        op_str = '+'
    elif isinstance(node, ast.Sub):
        op_str = '-'
    elif isinstance(node, ast.Mult):
        op_str = '*'
    elif isinstance(node, ast.Div):
        op_str = '*'
    elif isinstance(node, ast.Eq):
        op_str = '=='
    elif isinstance(node, ast.Gt):
        op_str = '>'
    elif isinstance(node, ast.Lt):
        op_str = '<'

    return '{}'.format(op_str)

def py_binop_to_glsl(cls, node, indent=0):
    op_str = py_op_to_glsl(cls, node.op);
    left_str = py_to_glsl(cls, node.left)
    right_str = py_to_glsl(cls, node.right)

    left_str_form = '{}'
    right_str_form = '{}'
    if isinstance(node.left, ast.BinOp) and glsl_has_higher_precedence(node.op, node.left.op):
        left_str_form = '({})'
    if isinstance(node.right, ast.BinOp) and glsl_has_higher_precedence(node.op, node.right.op):
        right_str_form = '({})'
    left_str = left_str_form.format(left_str)
    right_str = right_str_form.format(right_str)

    return '{} {} {}'.format(left_str, op_str, right_str)


def py_ann_assign_to_glsl(cls, node, indent=0, is_global=False):
    var_name = py_to_glsl(cls, node.target)
    var_type = py_to_glsl(cls, node.annotation)
    var_value = None

    if hasattr(node, 'value') and node.value is not None:
        var_value = py_to_glsl(cls, node.value)

    prefix_str = ''
    if is_global:
        prefix_str = 'const'
        if isinstance(node.annotation, ast.Subscript):
            if node.annotation.value.id == 'VertIn' or node.annotation.value.id == 'FragIn':
                prefix_str = 'in'
            elif node.annotation.value.id == 'VertOut' or node.annotation.value.id == 'FragOut':
                prefix_str = 'out'
            elif node.annotation.value.id == 'VertUni' or node.annotation.value.id == 'FragUni':
                prefix_str = 'uniform'

    if var_value is None:
        if prefix_str != '':
            return '{}{} {} {};'.format(' ' * indent, prefix_str, var_type, var_name)
        else:
            return '{}{} {};'.format(' ' * indent, var_type, var_name)

    if prefix_str != '':
        return '{}{} {} {} = {};'.format(' ' * indent, prefix_str, var_type, var_name, var_value)

    return '{}{} {} = {};'.format(' ' * indent, var_type, var_name, var_value)

def py_subscript_to_glsl(cls, node, indent=0):
    value_str = py_to_glsl(cls, node.slice)

    return '{}'.format(value_str)

def py_aug_assign_to_glsl(cls, node, indent=0):
    var_str = py_to_glsl(cls, node.target)
    op_str = py_op_to_glsl(cls, node.op)
    value_str = py_to_glsl(cls, node.value)

    return '{}{} {}= {};'.format(' ' * indent, var_str, op_str, value_str)

def py_assign_to_glsl(cls, node, indent=0):
    var_name = py_to_glsl(cls, node.targets[0])
    var_value = py_to_glsl(cls, node.value)

    return '{}{} = {};'.format(' ' * indent, var_name, var_value);

def py_compare_to_glsl(cls, node, indent=0):
    comp_str = py_op_to_glsl(cls, node.ops[0])

    left_str = py_to_glsl(cls, node.left)

    right_str = ''
    for c in node.comparators:
        right_str += py_to_glsl(cls, c)

    return '{} {} {}'.format(left_str, comp_str, right_str)

def py_if_to_glsl(cls, node, indent=0):
    test_str = py_to_glsl(cls, node.test, indent=indent)

    body_str = ''
    for statement_node in node.body:
        body_str += py_to_glsl(cls, statement_node, indent=indent + 4) + '\n'

    return '{}if ({}) {{\n{}{}}}'.format(' ' * indent, test_str, body_str, ' ' * indent)

def py_return_to_glsl(cls, node, indent=0):
    return_str = py_to_glsl(cls, node.value)

    return '{}return {};'.format(' ' * indent, return_str)

def py_call_to_glsl(cls, node, indent=0):
    name_str = py_to_glsl(cls, node.func)

    args_str = ''
    for i, arg in enumerate(node.args):
        args_str += py_to_glsl(cls, arg)
        if i < len(node.args) - 1:
            args_str += ', '

    return '{}{}({})'.format(' ' * indent, name_str, args_str)

def py_atrribute_to_glsl(cls, node, indent=0):
    var_name_str = py_to_glsl(cls, node.value)

    return '{}{}.{}'.format(' ' * indent, var_name_str, node.attr)

def py_pass_to_glsl(cls, node, indent=0):
    return ''

def py_to_glsl(cls, node, indent=0):
    conversion_func = py_to_glsl_dict.get(type(node))
    if conversion_func is None:
        py_to_glsl_err(
            cls,
            node,
            'Invalid Python AST for shader code in {} on line {}.'.format(cls.file_path, node.lineno),
            line_msg='{}'.format(type(node)),
            indent=indent
        )
    return conversion_func(cls, node, indent=indent)

py_to_glsl_dict = {
    ast.Constant: py_constant_to_glsl,
    ast.Name: py_name_to_glsl,
    ast.BinOp: py_binop_to_glsl,
    ast.AnnAssign: py_ann_assign_to_glsl,
    ast.Subscript: py_subscript_to_glsl,
    ast.AugAssign: py_aug_assign_to_glsl,
    ast.Assign: py_assign_to_glsl,
    ast.Compare: py_compare_to_glsl,
    ast.If: py_if_to_glsl,
    ast.Return: py_return_to_glsl,
    ast.Call: py_call_to_glsl,
    ast.Attribute: py_atrribute_to_glsl,
    ast.Add: py_op_to_glsl,
    ast.Sub: py_op_to_glsl,
    ast.Mult: py_op_to_glsl,
    ast.Div: py_op_to_glsl,
    ast.Eq: py_op_to_glsl,
    ast.Gt: py_op_to_glsl,
    ast.Lt: py_op_to_glsl,
    ast.Pass: py_pass_to_glsl,
}

def pyshader(cls, glsl_version_number=150):
    class_file_string = ''
    class_file_path = inspect.getfile(cls)
    with open(class_file_path, 'r') as f:
        class_file_string = f.read()


    class_file_ast = ast.parse(class_file_string)

    glsl_vertex_source = '#version {} // Vertex Shader\n\n'.format(glsl_version_number)
    glsl_fragment_source = '#version {} // Fragment Shader\n\n'.format(glsl_version_number)

    has_vertex_shader = False
    has_fragment_shader = False

    cls.file_path = class_file_path
    cls.file_string = class_file_string
    cls.file_lines = cls.file_string.split('\n')
    for node in ast.walk(class_file_ast):
        if isinstance(node, ast.ClassDef) and node.name == cls.__name__:
            cls.lineno = node.lineno
            for class_child in ast.iter_child_nodes(node):
                if isinstance(class_child, ast.FunctionDef):
                    if class_child.name == 'vertex':
                        glsl_vertex_source += '\nvoid main() {\n'
                        has_vertex_shader = True
                        for statement in ast.iter_child_nodes(class_child):
                            if isinstance(statement, ast.arguments):
                                continue
                            glsl_string = py_to_glsl(cls, statement, indent=4)
                            glsl_vertex_source += glsl_string + '\n'
                        glsl_vertex_source += '}\n'
                    elif class_child.name == 'fragment':
                        glsl_fragment_source += '\nvoid main() {\n'
                        has_fragment_shader = True
                        for statement in ast.iter_child_nodes(class_child):
                            if isinstance(statement, ast.arguments):
                                continue
                            glsl_string = py_to_glsl(cls, statement, indent=4)
                            glsl_fragment_source += glsl_string + '\n'
                        glsl_fragment_source += '}\n'
                elif isinstance(class_child, ast.AnnAssign):
                    for_vert = False
                    for_frag = False
                    if isinstance(class_child.annotation, ast.Subscript):
                        if class_child.annotation.value.id.startswith('Vert'):
                            for_vert = True
                            for_frag = False
                        elif class_child.annotation.value.id.startswith('Frag'):
                            for_vert = False
                            for_frag = True
                    glsl_string = py_ann_assign_to_glsl(cls, class_child, is_global=True)
                    if for_vert:
                        glsl_vertex_source += glsl_string + '\n'
                    elif for_frag:
                        glsl_fragment_source += glsl_string + '\n'
                elif isinstance(class_child, ast.Assign):
                    py_assign_to_glsl(cls, class_child)
            del cls.lineno
            break
    del cls.file_lines
    del cls.file_string
    del cls.file_path

    if not has_vertex_shader:
        glsl_vertex_source = textwrap.dedent(
            '''\
            #version {} // Vertex Shader\n
            uniform mat4 p3d_ModelViewProjectionMatrix;\n
            in vec4 p3d_Vertex;
            in vec2 p3d_MultiTexCoord0;\n
            out vec2 uv;\n
            void main() {{
                gl_Position = p3d_ModelViewProjectionMatrix * p3d_vertex;
                uv = p3d_MultiTexCoord0;
            }}
            '''.format(glsl_version_number)
        )

    if not has_fragment_shader:
        glsl_fragment_source = textwrap.dedent(
            '''\
            #version {} // Fragment Shader\n
            uniform sampler2D p3d_Texture0;
            uniform vec4 p3d_ColorScale;\n
            in vec2 uv;\n
            void main() {{
                gl_FragColor = texture(p3d_Texture0, uv) * p3d_ColorScale;
            }}
            '''.format(glsl_version_number)
        )

    cls.glsl_vertex_source = glsl_vertex_source
    cls.glsl_fragment_source = glsl_fragment_source
    def shader_get_vertex_source():
        return cls.glsl_vertex_source
    def shader_get_fragment_source():
        return cls.glsl_fragment_source
    def shader_get_source():
        return cls.glsl_vertex_source + '\n//--------------------------\n\n' + cls.glsl_fragment_source
    cls.get_vertex_source = shader_get_vertex_source
    cls.get_fragment_source = shader_get_fragment_source
    cls.get_source = shader_get_source

    return cls


@pyshader
class MyShader:
    p3d_ModelViewProjectionMatrix: VertUni['mat4']
    p3d_Vertex: VertIn['vec4']
    p3d_MultiTexCoord0: VertIn['vec2']
    uv: VertOut['vec2']

    def vertex():
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex
        uv = p3d_MultiTexCoord0;

    p3d_Texture0: FragUni['sampler2D']
    uv: FragIn['vec2']
    
    def fragment():
        gl_FragColor = texture(p3d_Texture0, uv) * vec4(uv.x, uv.y, uv.x * uv.y, 1.0)

#print(MyShader.get_source())
print(MyShader.get_vertex_source())
print(MyShader.get_fragment_source())

my_shader = Shader(vertex=MyShader.get_vertex_source(), fragment=MyShader.get_fragment_source())

box = Entity(model='cube', texture='brick', shader=my_shader)

ed = EditorCamera()

app.run()
