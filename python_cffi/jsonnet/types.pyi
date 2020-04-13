import os
from typing import *

Str = Union[Text, str]  # On Python 2.x we allow byte strings (utf-8 encoded)
PathLike = Union[Str, os.PathLike]
JsonValue = Union[dict, list, Str, int, float, bool, None]
ImportCallback = Callable[[Str, Str], Tuple[Str, PathLike]]
NativeCallback = Callable[..., JsonValue]
Deserialize = Optional[Union[bool, Callable[[Text], Any]]]


class JsonnetError(Exception):
    ...


def fsencode(path: PathLike) -> bytes:
    ...


def str_encode(string: Str) -> bytes:
    ...
