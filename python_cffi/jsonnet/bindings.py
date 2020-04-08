import inspect
import os
from functools import singledispatch
from typing import Callable, Tuple, Union

from jsonnet._jsonnet import ffi, lib
from jsonnet.types import JsonValue, JsonnetError, PathLike


class VMHandle:
    """Low-level wrapper around a `struct JsonnetVm *`."""

    @classmethod
    def create(cls):
        """Create a new JsonnetVm and wrap it."""

        vm = lib.jsonnet_make()
        if not vm:
            raise RuntimeError('Failed to create JsonnetVM')

        return cls(vm)

    def __init__(self, vm: ffi.CData):
        self._vm = vm
        self._handle = ffi.new_handle(self)
        self._import_callback = None
        self._native_callbacks = {}

    def destroy(self):
        if self._vm:
            lib.jsonnet_destroy(self._vm)
            self._vm = None

        if self._handle:
            self._handle = None

    def set_max_stack(self, n: int):
        lib.jsonnet_max_stack(self._vm, n)

    def set_gc_min_objects(self, n: int):
        lib.jsonnet_max_stack(self._vm, n)

    def set_gc_growth_trigger(self, n: float):
        lib.jsonnet_gc_growth_trigger(self._vm, n)

    def set_string_output(self, flag: bool):
        lib.jsonnet_string_output(self._vm, 1 if flag else 0)

    def set_max_trace(self, n: int):
        lib.jsonnet_max_trace(self._vm, n)

    def add_to_jpath(self, path: str):
        c_path = ffi.new('char []', path.encode())
        lib.jsonnet_jpath_add(self._vm, c_path)

    def bind_ext_var(self, name: str, val: str):
        c_name = ffi.new('char []', name.encode())
        c_val = ffi.new('char []', val.encode())
        lib.jsonnet_ext_var(self._vm, c_name, c_val)

    def bind_ext_code(self, name: str, val: str):
        c_name = ffi.new('char []', name.encode())
        c_val = ffi.new('char []', val.encode())
        lib.jsonnet_ext_code(self._vm, c_name, c_val)

    def bind_tla_var(self, name: str, val: str):
        c_name = ffi.new('char []', name.encode())
        c_val = ffi.new('char []', val.encode())
        lib.jsonnet_tla_var(self._vm, c_name, c_val)

    def bind_tla_code(self, name: str, val: str):
        c_name = ffi.new('char []', name.encode())
        c_val = ffi.new('char []', val.encode())
        lib.jsonnet_tla_code(self._vm, c_name, c_val)

    @property
    def import_callback(self):
        return self._import_callback

    @import_callback.setter
    def import_callback(self, cb: Callable):
        sig = inspect.signature(cb)
        if len(sig.parameters) != 2:
            raise TypeError('Callback must take two arguments: dir, rel')

        self._import_callback = cb
        lib.jsonnet_import_callback(self._vm, lib._import_callback, self._handle)

    @staticmethod
    @ffi.def_extern()
    def _import_callback(ctx, base, rel, found_here_ptr, success_ptr):
        self = ffi.from_handle(ctx)  # type: VMHandle
        try:
            imprt = self._import_callback(from_c_str(base), from_c_str(rel))
            if not isinstance(imprt, Tuple) or len(imprt) != 2:
                raise TypeError(f'Expected import callback to return Tuple of size 2, got {imprt!r}')

            content, found_here = imprt
            if not isinstance(content, (str, bytes)):
                raise TypeError(f'Import content must be str or bytes, got {type(content).__name__}')

            if not isinstance(found_here, (str, bytes, os.PathLike)):
                raise TypeError(f'Import found_here must be str, bytes or PathLike, got {type(content).__name__}')

            found_here_ptr[0] = self.alloc_c_str(os.fsencode(found_here))
            success_ptr[0] = 1
            return self.alloc_c_str(content)
        except Exception as e:
            return self.alloc_c_str(f'{e.__class__.__name__}: {e}')

    def register_native_callback(self, name: str, cb: Callable):
        handle = ffi.new_handle((self, cb))
        self._native_callbacks[name] = handle

        name = name.encode()
        c_name = ffi.new('char []', name)

        sig = inspect.signature(cb)
        params = [*(ffi.new('char []', p.encode()) for p in sig.parameters), ffi.NULL]
        c_params = ffi.new('char *[]', params)

        lib.jsonnet_native_callback(self._vm, c_name, lib._native_callback, handle, c_params)

    @staticmethod
    @ffi.def_extern()
    def _native_callback(ctx, argv, success):
        self, cb = ffi.from_handle(ctx)  # type: VMHandle, Callable
        try:
            sig = inspect.signature(cb)
            args = [self.from_jsonvalue(argv[i]) for i in range(len(sig.parameters))]
            result = self.jsonvalue(cb(*args))
            success[0] = 1
            return result
        except Exception as e:
            return self.jsonvalue(f'{e.__class__.__name__}: {e}')

    def evaluate_file(self, filename: PathLike):
        filename = os.fsencode(filename)
        error_ptr = ffi.new('int *')
        result = lib.jsonnet_evaluate_file(self._vm, filename, error_ptr)
        try:
            output = from_c_str(result)
        finally:
            realloc(result, 0, vm=self._vm)

        if error_ptr[0]:
            raise JsonnetError(output.rstrip())

        return output

    def evaluate_snippet(self, filename: PathLike, snippet: str):
        filename = os.fsencode(filename)
        error_ptr = ffi.new('int *')
        result = lib.jsonnet_evaluate_snippet(self._vm, filename, snippet.encode(), error_ptr)
        try:
            output = from_c_str(result)
        finally:
            realloc(result, 0, vm=self._vm)

        if error_ptr[0]:
            raise JsonnetError(output.rstrip())

        return output

    def alloc_c_str(self, value: Union[str, bytes]):
        return alloc_c_str(value, vm=self._vm)

    def from_jsonvalue(self, c_jsonvalue: ffi.CData) -> JsonValue:
        return from_jsonvalue(self._vm, c_jsonvalue)

    def jsonvalue(self, value: JsonValue) -> ffi.CData:
        return jsonvalue(value, vm=self._vm)


def from_jsonvalue(vm: ffi.CData, c_jsonvalue: ffi.CData) -> JsonValue:
    c_str = lib.jsonnet_json_extract_string(vm, c_jsonvalue)
    if c_str:
        return from_c_str(c_str)

    c_number = ffi.new('double *')
    if lib.jsonnet_json_extract_number(vm, c_jsonvalue, c_number):
        return c_number[0]

    c_bool = lib.jsonnet_json_extract_bool(vm, c_jsonvalue)
    if c_bool != 2:
        return bool(c_bool)

    if lib.jsonnet_json_extract_null(vm, c_jsonvalue):
        return None

    raise RuntimeError('Non-primitive types are not supported')


@singledispatch
def jsonvalue(value, *, vm: ffi.CData) -> ffi.CData:
    raise TypeError(f'Unsupported type: {type(value)}')


@jsonvalue.register(str)
def _jsonvalue_str(value: str, *, vm: ffi.CData) -> ffi.CData:
    value = value.encode() + b'\0'
    return lib.jsonnet_json_make_string(vm, value)


@jsonvalue.register(int)
@jsonvalue.register(float)
def _jsonvalue_number(value, *, vm: ffi.CData) -> ffi.CData:
    return lib.jsonnet_json_make_number(vm, value)


@jsonvalue.register(bool)
def _jsonvalue_bool(value: bool, *, vm: ffi.CData) -> ffi.CData:
    return lib.jsonnet_json_make_bool(vm, value)


@jsonvalue.register(list)
def _jsonvalue_array(array: list, *, vm: ffi.CData) -> ffi.CData:
    arr = lib.jsonnet_json_make_array(vm)
    try:
        for v in array:
            val = jsonvalue(v, vm=vm)
            lib.jsonnet_json_array_append(vm, arr, val)
    except Exception:
        jsonvalue_destroy(arr, vm=vm)
        raise

    return arr


@jsonvalue.register(dict)
def _jsonvalue_object(object: dict, *, vm: ffi.CData) -> ffi.CData:
    obj = lib.jsonnet_json_make_object(vm)
    try:
        for n, v in object.items():
            if not isinstance(n, str):
                raise TypeError('Names in a JSON object must be strings')
            name = n.encode()
            val = jsonvalue(v, vm=vm)
            lib.jsonnet_json_object_append(vm, obj, name, val)
    except Exception:
        jsonvalue_destroy(obj, vm=vm)
        raise

    return obj


@jsonvalue.register(type(None))
def _jsonvalue_null(_, *, vm: ffi.CData) -> ffi.CData:
    return lib.jsonnet_json_make_null(vm)


def jsonvalue_destroy(value: ffi.CData, *, vm: ffi.CData):
    lib.jsonnet_json_destroy(vm, value)


def jsonnet_version() -> str:
    return from_c_str(lib.jsonnet_version())


def from_c_str(c_str: ffi.CData) -> str:
    return ffi.string(c_str).decode()


def alloc_c_str(value: Union[str, bytes], *, vm: ffi.CData):
    """Allocate a null-terminated string."""
    value = (value.encode() if isinstance(value, str) else value) + b'\0'
    buf = realloc(ffi.NULL, len(value), vm=vm)
    if not buf:
        raise RuntimeError(f'jsonnet_realloc of {len(value)} bytes failed')

    buffer = ffi.buffer(buf, len(value))
    buffer[:] = value

    return buf


def realloc(buf: ffi.CData, size: int, *, vm: ffi.CData) -> ffi.CData:
    return lib.jsonnet_realloc(vm, buf, size)
