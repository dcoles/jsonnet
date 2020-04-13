from typing import *

from jsonnet._jsonnet import ffi
from jsonnet.types import JsonValue, ImportCallback, NativeCallback, Str, PathLike


class VMHandle:
    """Low-level wrapper around a `struct JsonnetVm *`."""

    @classmethod
    def create(cls):
        ...

    def __init__(self, vm: ffi.CData):
        self._vm = ...
        self._handle = ...
        self._native_callbacks = None
        ...

    def destroy(self):
        ...

    def set_max_stack(self, n: int):
        ...

    def set_gc_min_objects(self, n: int):
        ...

    def set_gc_growth_trigger(self, n: float):
        ...

    def set_string_output(self, flag: bool):
        ...

    def set_max_trace(self, n: int):
        ...

    def add_to_jpath(self, path: PathLike):
        ...

    def bind_ext_var(self, name: Str, val: Str):
        ...

    def bind_ext_code(self, name: Str, val: Str):
        ...

    def bind_tla_var(self, name: Str, val: Str):
        ...

    def bind_tla_code(self, name: Str, val: Str):
        ...

    def set_import_callback(self, cb: ImportCallback):
        ...

    @staticmethod
    def _getfullargspec(func: Callable):
        ...

    @staticmethod
    @ffi.def_extern()
    def _import_callback(ctx, base, rel, found_here_ptr, success_ptr):
        ...

    def register_native_callback(self, name: Str, cb: NativeCallback):
        ...

    @staticmethod
    @ffi.def_extern()
    def _native_callback(ctx, argv, success_ptr):
        ...


def from_jsonvalue(vm: ffi.CData, c_jsonvalue: ffi.CData) -> JsonValue:
    ...


def jsonvalue(value: JsonValue, vm: ffi.CData) -> ffi.CData:
    ...


def jsonvalue_str(value: Str, vm: ffi.CData) -> ffi.CData:
    ...


def jsonvalue_number(value, vm: ffi.CData) -> ffi.CData:
    ...


def jsonvalue_bool(value: bool, vm: ffi.CData) -> ffi.CData:
    ...


def jsonvalue_array(array: list, vm: ffi.CData) -> ffi.CData:
    ...


def jsonvalue_object(object: dict, vm: ffi.CData) -> ffi.CData:
    ...

def jsonvalue_null(vm: ffi.CData) -> ffi.CData:
    ...


def jsonvalue_destroy(value: ffi.CData, vm: ffi.CData):
    ...


def jsonnet_version() -> Text:
    ...


def from_c_str(c_str: ffi.CData) -> Text:
    ...


def alloc_c_str(value: Union[Text, bytes], vm: ffi.CData) -> ffi.CData:
    ...

def realloc(buf: ffi.CData, size: int, vm: ffi.CData) -> ffi.CData:
    ...
