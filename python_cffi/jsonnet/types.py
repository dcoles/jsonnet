import os
from typing import Union

PathLike = Union[bytes, str, os.PathLike]
JsonValue = Union[dict, list, str, int, float, bool, None]


class JsonnetError(Exception):
    pass
