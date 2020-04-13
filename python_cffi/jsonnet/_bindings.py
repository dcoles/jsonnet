"""
Python bindings for libjsonnet using CFFI.

Please do not directly import this module. Its API may change at any time.
"""
from __future__ import absolute_import

import inspect

from jsonnet._lib import ffi, lib
from jsonnet.types import JsonnetError, Text, fsencode, str_encode


class VMHandle:
    """Low-level wrapper around a JsonnetVM pointer."""

    @classmethod
    def create(cls):
        """Create a new JsonnetVm and wrap it."""
        vm = lib.jsonnet_make()
        if not vm:
            raise RuntimeError('Failed to create JsonnetVM')

        return cls(vm)

    def __init__(self, vm):
        """Create a VMHandle from a native JsonnetVm pointer."""
        self._vm = vm
        self._handle = ffi.new_handle(self)
        self._import_callback = None
        self._native_callbacks = {}

    def __del__(self):
        # Ensure the JsonnetVm will eventually be freed
        # even if destroy is not explicitly called.
        self.destroy()

    def destroy(self):
        """Destroy this VMHandle."""
        if self._vm:
            lib.jsonnet_destroy(self._vm)
            self._vm = None

        if self._handle:
            self._handle = None

    def set_max_stack(self, n):
        """Set the maximum stack depth."""
        lib.jsonnet_max_stack(self._vm, n)

    def set_gc_min_objects(self, n):
        """Set the number of objects required before a garbage collection cycle is allowed."""
        lib.jsonnet_max_stack(self._vm, n)

    def set_gc_growth_trigger(self, n):
        """Run the garbage collector after this amount of growth in the number of objects."""
        lib.jsonnet_gc_growth_trigger(self._vm, n)

    def set_string_output(self, flag):
        """Expect a string as output and don't JSON encode it."""
        lib.jsonnet_string_output(self._vm, 1 if flag else 0)

    def set_max_trace(self, n):
        """Set the number of lines of stack trace to display (0 for all of them)."""
        lib.jsonnet_max_trace(self._vm, n)

    def add_to_jpath(self, path):
        """Add to the default import callback's library search path."""
        c_path = ffi.new('char []', fsencode(path))
        lib.jsonnet_jpath_add(self._vm, c_path)

    def bind_ext_var(self, name, val):
        """Bind a Jsonnet external var to the given string."""
        c_name = ffi.new('char []', str_encode(name))
        c_val = ffi.new('char []', str_encode(val))
        lib.jsonnet_ext_var(self._vm, c_name, c_val)

    def bind_ext_code(self, name, val):
        """Bind a Jsonnet external var to the given code."""
        c_name = ffi.new('char []', str_encode(name))
        c_val = ffi.new('char []', str_encode(val))
        lib.jsonnet_ext_code(self._vm, c_name, c_val)

    def bind_tla_var(self, name, val):
        """Bind a string top-level argument for a top-level parameter."""
        c_name = ffi.new('char []', str_encode(name))
        c_val = ffi.new('char []', str_encode(val))
        lib.jsonnet_tla_var(self._vm, c_name, c_val)

    def bind_tla_code(self, name, val):
        """Bind a code top-level argument for a top-level parameter."""
        c_name = ffi.new('char []', str_encode(name))
        c_val = ffi.new('char []', str_encode(val))
        lib.jsonnet_tla_code(self._vm, c_name, c_val)

    def set_import_callback(self, cb):
        """Override the callback used to locate imports."""
        argspec = self._getfullargspec(cb)
        if len(argspec.args) != 2:
            raise TypeError('Callback must take two arguments, rel')

        self._import_callback = cb
        lib.jsonnet_import_callback(self._vm, lib._import_callback, self._handle)

    @staticmethod
    def _getfullargspec(func):
        # Python 2.x doesn't have getfullargspec
        if hasattr(inspect, 'getfullargspec'):
            return inspect.getfullargspec(func)
        else:
            return inspect.getargspec(func)

    @staticmethod
    @ffi.def_extern()
    def _import_callback(ctx, base, rel, found_here_ptr, success_ptr):
        """Callback used to load imports."""
        self = ffi.from_handle(ctx)  # type: VMHandle
        try:
            imprt = self._import_callback(from_c_str(base), from_c_str(rel))
            if not isinstance(imprt, tuple) or len(imprt) != 2:
                raise TypeError('Expected import callback to return tuple of size 2, got {!r}'.format(imprt))

            content, found_here = imprt
            if not isinstance(content, (Text, bytes)):
                raise TypeError('Import content must be unicode str or bytes, got {}'.format(type(content).__name__))

            found_here_ptr[0] = self.alloc_c_str(fsencode(found_here))
            success_ptr[0] = 1
            return self.alloc_c_str(content)

        # If we don't handle an exception, the program will segfault
        except BaseException as e:
            success_ptr[0] = 0
            return self.alloc_c_str('{e.__class__.__name__}: {e}'.format(e=e))

    def register_native_callback(self, name, cb):
        """Register a native extension."""
        name = str_encode(name)
        c_name = ffi.new('char []', name)

        argspec = self._getfullargspec(cb)
        params = [ffi.new('char []', str_encode(p)) for p in argspec.args] + [ffi.NULL]
        c_params = ffi.new('char *[]', params)

        handle = ffi.new_handle((self, cb))
        self._native_callbacks[name] = handle

        lib.jsonnet_native_callback(self._vm, c_name, lib._native_callback, handle, c_params)

    @staticmethod
    @ffi.def_extern()
    def _native_callback(ctx, argv, success_ptr):
        """Callback to provide native extensions to Jsonnet."""
        self, cb = ffi.from_handle(ctx)  # type: VMHandle, Callable
        try:
            argspec = self._getfullargspec(cb)
            args = [self.from_jsonvalue(argv[i]) for i in range(len(argspec.args))]
            result = self.jsonvalue(cb(*args))
            success_ptr[0] = 1
            return result

        # If we don't handle an exception, the program will segfault
        except BaseException as e:
            success_ptr[0] = 0
            return self.jsonvalue('{e.__class__.__name__}: {e}'.format(e=e))

    def evaluate_file(self, filename):
        """Evaluate a file containing Jsonnet code, return a JSON string."""
        filename = fsencode(filename)
        error_ptr = ffi.new('int *')
        result = lib.jsonnet_evaluate_file(self._vm, filename, error_ptr)
        try:
            output = from_c_str(result)
        finally:
            realloc(result, 0, vm=self._vm)

        if error_ptr[0]:
            raise JsonnetError(output.rstrip())

        return output

    def evaluate_snippet(self, filename, snippet):
        """Evaluate a string containing Jsonnet code, return a JSON string."""
        filename = fsencode(filename)
        error_ptr = ffi.new('int *')
        result = lib.jsonnet_evaluate_snippet(self._vm, filename, str_encode(snippet), error_ptr)
        try:
            output = from_c_str(result)
        finally:
            realloc(result, 0, vm=self._vm)

        if error_ptr[0]:
            raise JsonnetError(output.rstrip())

        return output

    def alloc_c_str(self, value):
        """Allocate a null-terminated string."""
        return alloc_c_str(value, vm=self._vm)

    def from_jsonvalue(self, c_jsonvalue):
        """Convert from native JsonnetJsonValue to Python value."""
        return from_jsonvalue(self._vm, c_jsonvalue)

    def jsonvalue(self, value):
        """Convert a Python value to a native JsonnetJsonValue."""
        return jsonvalue(value, vm=self._vm)


def from_jsonvalue(vm, c_jsonvalue):
    """Convert from native JsonnetJsonValue to Python value."""
    c_str = lib.jsonnet_json_extract_string(vm, c_jsonvalue)
    if c_str:
        return from_c_str(c_str)

    c_number_ptr = ffi.new('double *')
    if lib.jsonnet_json_extract_number(vm, c_jsonvalue, c_number_ptr):
        return c_number_ptr[0]

    c_bool = lib.jsonnet_json_extract_bool(vm, c_jsonvalue)
    if c_bool != 2:
        return bool(c_bool)

    if lib.jsonnet_json_extract_null(vm, c_jsonvalue):
        return None

    raise RuntimeError('Non-primitive types are not supported')


def jsonvalue(value, vm):
    """Convert a Python value to a native JsonnetJsonValue."""
    if value is None:
        return jsonvalue_null(vm=vm)

    _jsonvalue = _JSONVALUE.get(type(value))
    if _jsonvalue is None:
        raise TypeError('Unsupported type: {}'.format(type(value)))

    return _jsonvalue(value, vm=vm)


def jsonvalue_str(value, vm):
    """Convert a Python string to a native JsonnetJsonValue (string)."""
    # Must be null-terminated
    return lib.jsonnet_json_make_string(vm, str_encode(value) + b'\0')


def jsonvalue_number(value, vm):
    """Convert a Python number to a native JsonnetJsonValue (number)."""
    return lib.jsonnet_json_make_number(vm, value)


def jsonvalue_bool(value, vm):
    """Convert a Python bool to a native JsonnetJsonValue (boolean)."""
    return lib.jsonnet_json_make_bool(vm, value)


def jsonvalue_array(array, vm):
    """Convert a Python list to a native JsonnetJsonValue (array)."""
    arr = lib.jsonnet_json_make_array(vm)
    try:
        for v in array:
            val = jsonvalue(v, vm=vm)
            lib.jsonnet_json_array_append(vm, arr, val)
    except Exception:
        jsonvalue_destroy(arr, vm=vm)
        raise

    return arr


def jsonvalue_object(object, vm):
    """Convert a Python list to a native JsonnetJsonValue (object)."""
    obj = lib.jsonnet_json_make_object(vm)
    try:
        for name, val in object.items():
            if not isinstance(name, (Text, str)):
                raise TypeError('Names in JSON objects must be unicode strings')

            val = jsonvalue(val, vm=vm)
            lib.jsonnet_json_object_append(vm, obj, str_encode(name), val)
    except Exception:
        jsonvalue_destroy(obj, vm=vm)
        raise

    return obj


def jsonvalue_null(vm):
    """Convert a Python list to a native JsonnetJsonValue (null)."""
    return lib.jsonnet_json_make_null(vm)


_JSONVALUE = {
    Text: jsonvalue_str,
    str: jsonvalue_str,  # bytes on Python 2.x
    int: jsonvalue_number,
    float: jsonvalue_number,
    bool: jsonvalue_bool,
    list: jsonvalue_array,
    dict: jsonvalue_object,
}


def jsonvalue_destroy(value, vm):
    """Clean up a JSON subtree."""
    lib.jsonnet_json_destroy(vm, value)


def jsonnet_version():
    """Version string of th Jsonnet interpreter."""
    return from_c_str(lib.jsonnet_version())


def from_c_str(c_str):
    """Convert from native string to a Python unicode string."""
    # Jsonnet strings are always UTF-8
    return ffi.string(c_str).decode('utf-8')


def alloc_c_str(value, vm):
    """Allocate a null-terminated string."""
    value = str_encode(value)
    nbytes = len(value) + 1  # string and null-byte
    buf = realloc(ffi.NULL, nbytes, vm=vm)
    if not buf:
        raise RuntimeError('jsonnet_realloc of {} bytes failed'.format(nbytes))

    buffer = ffi.buffer(buf, nbytes)
    buffer[:] = value + b'\0'

    return buf


def realloc(buf, size, vm):
    """Allocate, resize, or free a buffer."""
    return lib.jsonnet_realloc(vm, buf, size)
