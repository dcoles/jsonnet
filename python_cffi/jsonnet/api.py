import json
from typing import Any, Callable, Iterable, Mapping, Optional, Tuple, Union

from jsonnet import bindings
from jsonnet.types import JsonValue


class JsonnetVM:
    """Jsonnet virtual machine."""

    def __init__(self,
                 jpath: Optional[Iterable[str]] = None,
                 import_callback: Optional[Callable[[str, str], Tuple[str, str]]] = None,
                 native_callbacks: Optional[Mapping[str, Callable[[JsonValue], JsonValue]]] = None,
                 *, max_stack: Optional[int] = None,
                 gc_min_objects: Optional[int] = None,
                 gc_growth_trigger: Optional[float] = None,
                 string_output: Optional[bool] = None,
                 max_trace: Optional[int] = None,
                 ext_vars: Mapping[str, str] = None,
                 ext_codes: Mapping[str, str] = None,
                 tla_vars: Mapping[str, str] = None,
                 tla_codes: Mapping[str, str] = None,
                 decode: Optional[Union[bool, Callable[[str], Any]]] = None):
        """
        Create Jsonnet virtual machine.

        :param jpath: List of paths to add to the default search path
        :param import_callback: Callback used to load imports
        :param native_callbacks: Python extension callbacks to Jsonnet
        :param max_stack: Maximum stack depth
        :param gc_min_objects: Number of objects required before a garbage collection cycle is allowed
        :param gc_growth_trigger: Run the garbage collector after this amount of growth in the number of objects
        :param string_output: Expect a string as output and don't JSON encode it
        :param max_trace: number of lines of stack trace to display (0 for all of them)
        :param ext_vars: Mapping of external vars to set to the given string
        :param ext_codes: Mapping of external vars to set to the given Jsonnet code
        :param tla_vars: Mapping of top-level arguments to set to the given string
        :param tla_codes: Mapping of top-level arguments to set to the given Jsonnet code
        :param decode: Function to decode output (e.g. `json.loads`)
        """
        jpath = jpath or []
        ext_vars = ext_vars or {}
        ext_codes = ext_codes or {}
        tla_vars = tla_vars or {}
        tla_codes = tla_codes or {}

        if decode is True:
            if string_output:
                raise ValueError('Can\'t automatically decode string output')

            # Explicitly JSON decode
            self.decode = json.loads
        elif decode is False:
            # Explicitly don't decode
            self.decode = None
        elif isinstance(decode, Callable):
            # Decode using callable
            self.decode = decode
        elif decode is None:
            # Default behaviour (JSON decode if not `string_output`)
            self.decode = None if string_output else json.loads
        else:
            raise TypeError('decode must be `bool`, `Callable` or `None`')

        self._handle: bindings.VMHandle = bindings.VMHandle.create()

        for path in jpath:
            self._handle.add_to_jpath(path)

        if import_callback:
            self._handle.import_callback = import_callback

        if native_callbacks:
            for name, cb in native_callbacks.items():
                self._handle.register_native_callback(name, cb)

        if max_stack:
            self._handle.set_max_stack(max_stack)

        if gc_min_objects:
            self._handle.set_gc_min_objects(gc_min_objects)

        if gc_growth_trigger:
            self._handle.set_gc_growth_trigger(gc_growth_trigger)

        if string_output:
            self._handle.set_string_output(string_output)

        if max_stack:
            self._handle.set_max_trace(max_trace)

        for name, value in ext_vars.items():
            self._handle.bind_ext_var(name, value)

        for name, value in ext_codes.items():
            self._handle.bind_ext_code(name, value)

        for name, value in tla_vars.items():
            self._handle.bind_tla_var(name, value)

        for name, value in tla_codes.items():
            self._handle.bind_tla_code(name, value)

    def close(self):
        if self._handle:
            self._handle.close()
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.close()

    def evaluate_file(self, filename: str):
        result = self._handle.evaluate_file(filename)
        return self.decode(result) if self.decode else result

    def evaluate_snippet(self, snippet: str, filename: str = '<string>'):
        result = self._handle.evaluate_snippet(filename, snippet)
        return self.decode(result) if self.decode else result


def evaluate_file(filename: str, *args, decode=False, **kwargs) -> str:
    with _make_vm(*args, decode=decode, **kwargs) as vm:
        return vm.evaluate_file(filename)


def evaluate_snippet(filename: str, src: str, *args, decode=False, **kwargs) -> str:
    with _make_vm(*args, decode=decode, **kwargs) as vm:
        return vm.evaluate_snippet(src, filename=filename)


def _make_vm(
        jpathdir: str = None,
        max_stack: int = None,
        gc_min_objects: int = None,
        gc_growth_trigger: float = None,
        ext_vars=None,
        ext_codes=None,
        tla_vars=None,
        tla_codes=None,
        max_trace: int = None,
        import_callback=None,
        native_callbacks=None,
        *, decode=None) -> JsonnetVM:
    """Create `JsonnetVM` for legacy functions."""

    jpath = [jpathdir] if jpathdir else None
    native_callbacks = ({n: cb for n, (_, cb) in native_callbacks.items()}
                        if native_callbacks else None)

    return JsonnetVM(
        jpath, import_callback, native_callbacks,
        max_stack=max_stack,
        gc_min_objects=gc_min_objects,
        gc_growth_trigger=gc_growth_trigger,
        max_trace=max_trace,
        ext_vars=ext_vars,
        ext_codes=ext_codes,
        tla_vars=tla_vars,
        tla_codes=tla_codes,
        decode=decode,
    )


def version():
    """Return the version string of the Jsonnet interpreter."""
    return bindings.jsonnet_version()
