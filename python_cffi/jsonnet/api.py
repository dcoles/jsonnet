import json
import os
from typing import Callable, Iterable, Mapping, Optional, Tuple, Union

from jsonnet import bindings
from jsonnet.types import JsonValue, PathLike


class JsonnetVM:
    """Jsonnet virtual machine."""

    # Import callback: fn(base: str, rel: str) -> (content: str, found_here: str)
    ImportCallback = Callable[[str, str], Tuple[str, str]]

    # Native callback: fn(JsonValue, ...) -> JsonValue
    NativeCallback = Callable[..., JsonValue]

    def __init__(self,
                 jpath: Optional[Iterable[str]] = None,
                 import_callback: Optional[ImportCallback] = None,
                 native_callbacks: Optional[Mapping[str, NativeCallback]] = None,
                 *, max_stack: Optional[int] = None,
                 gc_min_objects: Optional[int] = None,
                 gc_growth_trigger: Optional[float] = None,
                 string_output: Optional[bool] = None,
                 max_trace: Optional[int] = None,
                 ext_vars: Mapping[str, str] = None,
                 ext_codes: Mapping[str, str] = None,
                 tla_vars: Mapping[str, str] = None,
                 tla_codes: Mapping[str, str] = None):
        """
        Create a new Jsonnet virtual machine.

        :param jpath: List of paths to add to the default search path.
        :param import_callback: Callback used to load imports.
        :param native_callbacks: Python extension callbacks to Jsonnet.
        :param max_stack: Maximum stack depth.
        :param gc_min_objects: Number of objects required before a garbage collection cycle is allowed.
        :param gc_growth_trigger: Run the garbage collector after this amount of growth in the number of objects.
        :param string_output: Expect a string as output and don't JSON encode it.
        :param max_trace: number of lines of stack trace to display (0 for all of them).
        :param ext_vars: Mapping of external vars to set to the given string.
        :param ext_codes: Mapping of external vars to set to the given Jsonnet code.
        :param tla_vars: Mapping of top-level arguments to set to the given string.
        :param tla_codes: Mapping of top-level arguments to set to the given Jsonnet code.
        """
        jpath = jpath or []
        ext_vars = ext_vars or {}
        ext_codes = ext_codes or {}
        tla_vars = tla_vars or {}
        tla_codes = tla_codes or {}

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

    def destroy(self):
        """
        Destroy JsonVM.

        Calling any JsonVM methods after this method will raise a `RuntimeError`.
        """
        if self._handle:
            self._handle.destroy()
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.destroy()

    def evaluate_file(self, filename: PathLike, deserialize: Union[bool, Callable] = False) \
            -> Union[str, JsonValue]:
        """
        Evaluate a file containing Jsonnet code, return a JSON string.

        :param filename: Path to a file containing Jsonnet code.
        :param deserialize: If True, parse resulting JSON to a Python object.
            Can also be used to supply a custom deserialization function.
        :return: The result of evaluation.
        """
        filename = os.fspath(filename)

        if not self._handle:
            raise RuntimeError('JsonVM has been closed')

        result = self._handle.evaluate_file(filename)
        return self._deserialize(result, deserialize=deserialize)

    def evaluate_snippet(self, snippet: str, filename: PathLike = '<string>', deserialize=None) \
            -> Union[str, JsonValue]:
        """
        Evaluate a string containing Jsonnet code, return a JSON string.

        :param snippet: Jsonnet code to execute.
        :param filename: Path to a file (used in error messages).
        :param deserialize: If True, parse resulting JSON to a Python object.
            Can also be used to supply a custom deserialization function.
        :return: The result of evaluation.
        """
        filename = os.fspath(filename)

        if not self._handle:
            raise RuntimeError('JsonVM has been closed')

        result = self._handle.evaluate_snippet(filename, snippet)
        return self._deserialize(result, deserialize=deserialize)

    @staticmethod
    def _deserialize(string: str, deserialize=False) -> Union[str, JsonValue]:
        """Optionally deserialize value."""
        if isinstance(deserialize, Callable):
            return deserialize(string)

        if deserialize:
            return json.loads(string)

        # Don't parse at all
        return string


def version() -> str:
    """Return the version string of the Jsonnet interpreter."""
    return bindings.jsonnet_version()
