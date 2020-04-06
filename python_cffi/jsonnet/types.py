from typing import Union


JsonValue = Union[dict, list, str, int, float, bool, None]


class JsonnetError(Exception):
    pass
