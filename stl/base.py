# Copyright 2016 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Base classes, functions, exceptions."""

import logging

# python2 and python3 compatible way for detecting if something is a string.
try:
  basestring  # pylint: disable=pointless-statement

  def IsString(x):
    """Returns if |x| is a string (compatible with python2 and python3)."""
    return isinstance(x, basestring)
except NameError:

  def IsString(x):
    """Returns if |x| is a string (compatible with python2 and python3)."""
    return isinstance(x, str)


def GetCSV(array):
  """Return a comma-separated string."""
  if not array:
    return ''
  return ','.join([str(e) for e in array])


class NamedObject(object):
  """Base class for all objects with a name.

  Attributes:
    name: Name of this object.
  """

  def __init__(self, name):
    self.name = name

  def __repr__(self):
    return str(self)

  def __eq__(self, other):
    return self.name == other.name

  def __ne__(self, other):
    return not self == other

  def Resolve(self, env, resolved_params):
    """Resolve object.

    It resolves any internal attributes with unresolved values, then returns
    the resolved values which can be used for graph.

    Args:
      env: Environment with all information necessary to resolve internal
          attributes.
      resolved_params: Resolved values which will possibly be referenced by
          internal attributes.

    Raises:
      NotImplementedError
    """
    raise NotImplementedError('Resolve() is not implemented: ' + self.name)


class ParameterizedObject(NamedObject):
  """Base class of objects which has parameters.

  A parameterized object can be used to expanded later with actual arguments.

  Attributes:
    params: List of parameters for this object.
  """

  def __init__(self, name):
    NamedObject.__init__(self, name)
    self.params = []

  def __eq__(self, other):
    return NamedObject.__eq__(self, other) and self.params == other.params

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class TypedObject(NamedObject):
  """Base class for all object with a type and name.

  Attributes:
    type_: Type of this object.
  """

  def __init__(self, name, type_):
    NamedObject.__init__(self, name)
    self.type_ = type_

  def __eq__(self, other):
    return NamedObject.__eq__(self, other) and self.type_ == other.type_

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class Const(TypedObject):
  """Constants.

  A constant is defined with "const" keyword. For example,

  const string kStringConstantExample = "string constant example";

  Atrributes:
    value: Value for this constant. Resolve() returns it.
  """

  def __init__(self, name, type_, value=None):
    TypedObject.__init__(self, name, type_)
    self.value = value

  def __str__(self):
    return 'CONST %s(%s): %s' % (self.name, self.type_, repr(self.value))

  def __eq__(self, other):
    return TypedObject.__eq__(self, other) and self.value == other.value

  def Resolve(self, env, resolved_params):
    logging.log(1, 'Resolving ' + self.name)
    if isinstance(self.value, NamedObject):
      return self.value.Resolve(env, resolved_params)
    return self.value


class Value(NamedObject):
  """Values.

  A value is either integer, string, array, or dictionary. self.name can be None
  which means the value doesn't have a name.

  Attributes:
    value: Actual value.
  """

  def __init__(self, value):
    NamedObject.__init__(self, value)
    self.value = value
    self.name = None  # Clear name by default

  def __eq__(self, other):
    return NamedObject.__eq__(self, other) and self.value == other.value

  def __str__(self):
    if self.name is None:
      return repr(self.value)
    return 'VALUE: %s(%s)' % (self.name, repr(self.value))

  def Resolve(self, env, resolved_params):
    logging.log(1, 'Resolving ' + str(self))
    if isinstance(self.value, NamedObject):
      return self.value.Resolve(env, resolved_params)

    # Expand (struct or array)
    if isinstance(self.value, list):
      if self.value and self.value[0].name:  # dict
        dict_ = {}
        for v in self.value:
          dict_[v.name] = v.Resolve(env, resolved_params)
        return dict_
      # list
      return [v.Resolve(env, resolved_params) for v in self.value]

    if isinstance(self.value, int) or self.value is None:
      return self.value

    if not IsString(self.value):
      raise TypeError('Wrong value: ' + self.value)

    # Get reference
    if self.value.startswith('$'):
      var = self.value[1:]
      fields = var.split('.')
      # Role field or not?
      if len(fields) > 1:  # Role field
        assert len(fields) == 2
        role = Role.FindStatic(fields[0], env, resolved_params)
        return FuncGetField(role, fields[1])

      logging.log(1, '** RESOLVEDPARAMS **: ' + str(resolved_params))
      # Params or local vars?
      if var in resolved_params:
        v = resolved_params[var]
        if isinstance(v, FuncSet):
          if isinstance(v.obj, LocalVar):
            return v.obj
          else:  # if isinstance(v.obj, Role):
            return FuncGetField(v.obj, v.field)
        return v
      # Const?
      consts = env['_current_module'].consts
      if var in consts:
        return consts[var].Resolve(env, {})
      # Roles?
      roles = env['_current_module'].roles
      if var in roles:
        return roles[var]
      raise NameError('Cannot find a const, role or local var: ' + var)

    # Set reference
    if self.value.startswith('&'):
      var = self.value[1:]
      fields = var.split('.')
      # Role field or not?
      if len(fields) > 1:  # Role field
        assert len(fields) == 2
        role = Role.FindStatic(fields[0], env, resolved_params)
        return FuncSet(role, fields[1])

      # Local vars?
      if var in resolved_params:
        local = resolved_params[var]
        if isinstance(local, FuncSet):
          return local
        if isinstance(local, LocalVar):
          return FuncSet(local)
      # Roles?
      roles = env['_current_module'].roles
      if var in roles:
        return roles[var]
      raise NameError('Cannot find a local var or role: ' + var)

    # Literal value (integer, boolean, or string)
    return self.value


class QualifierValue(Value):
  """Value from a Qualifier.

  This is an instance of a Qualifier in a MessageValue. The external Qualifier
  can be used to generate values, or validate the value of a message field.

  Attributes:
    qualifier: qualifier.Qualifier instance.
    params: List of parameters for this qualifier.
    out_ref: Output variable for this qualifier. Qualifiers can be used to
        assign values to local variables in a Transition.
  """

  class Resolved(Value):
    """Resolved value from a QualifierValue.

    This is resolved instance of a QualifierValue; it is used directly by the
    test driver to validate and generate field values. This class accepts a
    list of resolved arguments which can be python primitives, STL local
    variables, or runnable STL functions.

    Attributes:
      qualifier: qualifier.Qualifier instance.
      qual_type: The field type to be qualified (int, bool, string, message).
      args: List of concrete arguments to be run in
          self.qualifier.Validate()/Generate().
      func_set: Output FuncSet for this qualifier. Qualifiers can be used to
          assign values to local variables in a Transition or to fields in a
          Role via func_set.
    """

    def __init__(self, qualifier, args, func_set=None):
      Value.__init__(self, None)
      self.qualifier = qualifier
      self.qual_type = qualifier.qual_type
      self.args = args
      self.func_set = func_set

    def __eq__(self, other):
      return Value.__eq__(self, other) and self.qualifier == other.qualifier

    def __str__(self):
      return 'QUALIFIER-RESOLVED: %s(%s) -> %s' % (self.qualifier.name,
                                                   self.args, self.func_set)

    def ValidateAndSet(self, value):
      if self.func_set:
        self.func_set.SetValue(value)
      return self.qualifier.external.Validate(value, *self._EvalArgs())

    def Generate(self):
      self.value = self.qualifier.external.Generate(*self._EvalArgs())
      if self.func_set:
        self.func_set.SetValue(self.value)
      return self.value

    def _EvalArgs(self):
      args = []
      for a in self.args:
        if isinstance(a, LocalVar):
          args.append(a.value)
        elif isinstance(a, Func):
          args.append(a.Run())
        else:
          args.append(a)
      return args

  def __init__(self, qualifier, params, out_ref=None):
    Value.__init__(self, None)
    self.qualifier = qualifier
    self.params = params
    self.out_ref = out_ref

  def __eq__(self, other):
    return NamedObject.__eq__(self, other) and self.name == other.name

  def __str__(self):
    return 'QUALIFIER-VALUE: %s(%s) -> %s' % (self.qualifier.name, self.params,
                                              self.out_ref)

  def Resolve(self, env, resolved_params):
    args = []
    for v in self.params:
      args.append(v.Resolve(env, resolved_params))
    func_set = None
    if self.out_ref:
      func_set = self.out_ref.Resolve(env, resolved_params)
    return QualifierValue.Resolved(self.qualifier, args, func_set)


class Param(TypedObject):
  """Parameters for ParameterizedObject."""

  def __init__(self, name, type_):
    TypedObject.__init__(self, name, type_)

  def __str__(self):
    return 'PARAM %s(%s)' % (self.name, self.type_)

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class LocalVar(TypedObject):
  """Local variables.

  Local variables can be defined with types in transition spec. In most case,
  transitions define local variables to store values temporarily which don't
  change state transition results, but need to proceed and complete transitions.

  Attributes:
    value: Current value of this local variable.
  """

  def __init__(self, name, type_):
    TypedObject.__init__(self, name, type_)
    self.value = None

  def __str__(self):
    return 'LOCAL %s(%s)' % (self.name, self.type_)

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class Field(TypedObject):
  """Fields in messages or in roles.

  Attributes:
    optional: Whether or not this field is optional in the given message.
        Meanless for roles.
    repeated: Whether or not this field is repeated in the given message.
        Meanless for roles.
    encoding_props: Dictionary of miscellaneous property values, used for
        custom encoding schemes.
  """

  def __init__(self, name, type_, optional=False, repeated=False):
    TypedObject.__init__(self, name, type_)
    self.optional = optional
    self.repeated = repeated
    self.encoding_props = {}
    if self.repeated:
      self.optional = True

  def __eq__(self, other):
    return (TypedObject.__eq__(self, other) and
            self.optional == other.optional and self.repeated == other.repeated)

  def __str__(self):
    if self.repeated:
      return 'FIELD-REPEATED %s(%s)' % (self.name, self.type_)
    if self.optional:
      return 'FIELD-OPTIONAL %s(%s)' % (self.name, self.type_)
    return 'FIELD %s(%s)' % (self.name, self.type_)

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class Role(NamedObject):
  """Roles.

  A role represents an endpoint of events which triggers events, i,e becomes
  the source of events, or becomes the target of events. It has fields to
  store values necessary to execute events, for example, address for a protocol.

  Attributes:
    fields: Map of fields and their names. A field is used to store values
        necessary to execute events.
    field_values: Map of field names and current values.
  """

  def __init__(self, name):
    NamedObject.__init__(self, name)
    self.fields = {}
    self.field_values = {}

  def __eq__(self, other):
    return (NamedObject.__eq__(self, other) and self.fields == other.fields and
            self.field_values == other.field_values)

  def __str__(self):
    return 'ROLE ' + self.name

  def __getitem__(self, key):
    if key not in self.fields:
      raise AttributeError("No field exists in role '%s': %s" % (self.name,
                                                                 key))
    if key in self.field_values:
      return self.field_values[key]
    return None

  def __setitem__(self, key, value):
    if key not in self.fields:
      raise AttributeError("No field exists in role '%s': %s" % (self.name,
                                                                 key))
    # TODO(byungchul): Type checking.
    self.field_values[key] = value

  def Resolve(self, env, resolved_params):
    logging.log(1, 'Resolving ' + self.name)
    return self

  @staticmethod
  def FindStatic(name, env, resolved_params):
    """Find a role from |resolved_params| or |env|."""
    # Find role in params
    if name in resolved_params:
      resolved_role = resolved_params[name]
      if not isinstance(resolved_role, Role):
        raise NameError('Not a role: ' + name)
      return resolved_role
    # Find role in current module
    roles = env['_current_module'].roles
    if name not in roles:
      raise NameError('Cannot find a role: ' + name)
    return roles[name]


class Expand(NamedObject):
  """Expressions to expand to other objects.

  Messages, events, states, transitions can be parameterized. A parameterized
  object can be expanded with values.
  Note that Resolve() is only used to expand parameterized messages. Other
  parameterized objects are expanded differently.

  Attributes:
    values: List of values to be used when expanding to other object.
  """

  def __init__(self, name):
    NamedObject.__init__(self, name)
    self.values = []

  def __eq__(self, other):
    return NamedObject.__eq__(self, other) and self.values == other.values

  def __str__(self):
    return 'EXPAND %s: v(%s)' % (self.name, GetCSV(self.values))

  def Resolve(self, env, resolved_params):
    # This function is called only for messages. Other expand is handled
    # separately, for example, by Transition or Event.
    messages = env['_current_module'].messages
    if self.name not in messages:
      raise NameError('Cannot find a message: ' + self.name)
    msg = messages[self.name]

    if msg.is_array:
      assert len(self.values) == 1
      msg_array = self.values[0]
      assert isinstance(msg_array.value, list)
      new_resolved_fields = []
      for msg_element in msg_array.value:
        new_resolved_fields.append({
            v.name: v.Resolve(env, resolved_params)
            for v in msg_element.value
        })
    else:
      new_resolved_fields = {
          v.name: v.Resolve(env, resolved_params)
          for v in self.values
      }

    return msg.Resolve(env, new_resolved_fields)


class Func(NamedObject):
  """External function call.

  Attributes:
    func: The callable function this wraps and runs.
    args: List of arguments for given function with |name|.
  """

  def __init__(self, name, func=None):
    NamedObject.__init__(self, name)
    self.func = func
    self.args = []

  def __str__(self):
    return 'FUNC %s(%s)' % (self.name, GetCSV(self.args))

  def Run(self):
    """Execute the function with |args|.

    Returns:
      Whether the function succeeded to execute.
    Raises:
      RuntimeError: If self.func is None.
    """
    if not self.func:
      raise RuntimeError('Func does not contain a runnable function.')
    return self.func(*self.args)

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class FuncNoOp(Func):
  """External function doing nothing."""

  def __init__(self, name):
    Func.__init__(self, name)

  def Run(self):
    return True

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class FuncGetField(Func):
  """External function to get the value of a field either of Role or dictionary.

  Attributes:
    obj: Object which has the field of |field|. It can be either Role or
        dictionary.
    field: Field name to get the value of.
  """

  def __init__(self, obj, field):
    Func.__init__(self, 'GetField')
    self.obj = obj
    self.field = field

  def __str__(self):
    if isinstance(self.obj, Role):
      return 'GET %s.%s' % (self.obj.name, self.field)
    return 'GET %s.%s' % (self.obj, self.field)

  def Run(self):
    return self.obj[self.field]

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class FuncSet(Func):
  """External function to set a value to a field of Role or to a LocalVar.

  Attributes:
    obj: Object which has the field of |field|. It can be either Role or
        LocalVar.
    field: Field name to set a value to. |obj| must be a Role.
  """

  def __init__(self, obj, field=None):
    Func.__init__(self, 'Set')
    self.obj = obj
    self.field = field
    if isinstance(self.obj, LocalVar):
      if field:
        raise TypeError("Local var '%s' cannot set a field: %s" %
                        (self.obj.name, field))
    elif isinstance(self.obj, Role):
      if not field:
        raise TypeError('Cannot set role: ' + self.obj.name)
    else:
      raise TypeError('Cannot set ' + self.obj)

  def __str__(self):
    if isinstance(self.obj, LocalVar):
      return 'SET ' + self.obj.name
    # if isinstance(self.obj, Role):
    return 'SET %s.%s' % (self.obj.name, self.field)

  def Run(self):
    """Get the value to a field of Role or to a LocalVar."""
    if isinstance(self.obj, LocalVar):
      return self.obj.value
    elif isinstance(self.obj, Role):
      return self.obj[self.field]
    else:
      raise TypeError('Cannot GetValue on type %s' % type(self.obj))

  def SetValue(self, value):
    """Set a value to a field of Role or to a LocalVar."""
    if isinstance(self.obj, LocalVar):
      self.obj.value = value
    elif isinstance(self.obj, Role):
      self.obj[self.field] = value
    else:
      raise TypeError('Cannot SetValue on type %s' % type(self.obj))

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)


class FuncWithContext(Func):
  """External event function with context.

  An event has a context consisting of source Role, target Role, and a flag
  indication if this function is called to test source Role.

  Attributes:
    context: Context to run this event function.
  """

  class Context(object):
    """Context to run a function as an event in state transition spec.

    Attributes:
      source: Source role of this event function.
      target: Target role of this event function.
      test_source: Whether or not this function call is to test source Role.
          If not, this function call is to test target Role.
    """

    def __init__(self):
      self.source = None
      self.target = None
      self.test_source = False

    def __str__(self):
      return ('CONTEXT: s(%s)%s, t(%s)%s' % (self.source,
                                             '*' if self.test_source else '',
                                             self.target,
                                             '' if self.test_source else '*'))

  def __init__(self, name, event):
    Func.__init__(self, name)
    self.event = event
    self.context = FuncWithContext.Context()

  def __str__(self):
    return ('FUNC %s: s(%s), t(%s), a(%s)' % (
        self.name, self.context.source, self.context.target, GetCSV(self.args)))

  def Run(self):
    logging.log(2, 'Running ' + str(self))
    new_args = [self.context]
    new_args.extend(self.args)
    if self.context.test_source:
      return self.event.Wait(*new_args)
    return self.event.Fire(*new_args)

  def Resolve(self, env, resolved_params):
      raise NotImplementedError('Resolved() is not needed: ' + self.name)
