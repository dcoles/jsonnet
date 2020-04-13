from typing import *

from jsonnet.types import PathLike, ImportCallback, NativeCallback, Deserialize, Str


class JsonnetVM:
    def __init__(self,
                 jpath: Optional[Iterable[PathLike]] = None,
                 max_stack: Optional[int] = None,
                 gc_min_objects: Optional[int] = None,
                 gc_growth_trigger: Optional[float] = None,
                 string_output: Optional[bool] = None,
                 max_trace: Optional[int] = None,
                 ext_vars: Mapping[Str, Str] = None,
                 ext_codes: Mapping[Str, Str] = None,
                 tla_vars: Mapping[Str, Str] = None,
                 tla_codes: Mapping[Str, Str] = None,
                 import_callback: Optional[ImportCallback] = None,
                 native_callbacks: Optional[Mapping[Str, NativeCallback]] = None) -> JsonnetVM:
        self._handle = ...
        ...

    def destroy(self) -> None:
        ...

    def __enter__(self) -> JsonnetVM:
        ...

    def __exit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        ...

    def evaluate_file(self, filename: PathLike, deserialize: Deserialize = None) -> Any:
        ...

    def evaluate_snippet(self, snippet: Str, filename: PathLike = '<string>', deserialize: Deserialize = None) -> Any:
        ...

    @staticmethod
    def _deserialize(string: Str, deserialize: Deserialize = None) -> Any:
        ...


def evaluate_file(filename: PathLike, deserialize: Deserialize = None, **kwargs) -> Any:
    ...


def evaluate_snippet(snippet: Str, filename: PathLike = '<String>', deserialize: Deserialize = None, **kwargs) -> Any:
    ...

def version() -> Text:
    ...
