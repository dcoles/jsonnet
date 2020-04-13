from __future__ import absolute_import

import os
import sys


class JsonnetError(Exception):
    """Jsonnet raised an error."""
    pass


# Unicode string type for backward compatibility with Python 2
Text = type(u'')


if hasattr(os, 'fsencode'):
    fsencode = os.fsencode
else:
    # Python 2.x doesn't have os.fsencode
    def fsencode(path):
        if isinstance(path, Text):
            return path.encode(sys.getfilesystemencoding())
        elif isinstance(path, bytes):
            return path
        else:
            raise TypeError('Expected str or bytes, got {!r}'.format(type(path)))


def str_encode(string):
    """Encode a string as UTF-8"""
    # In Python 2.x str is the same as bytes, so assume string is already UTF-8 encoded
    return string.encode('utf-8') if not isinstance(string, bytes) else string
