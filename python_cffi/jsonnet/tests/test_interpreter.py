from __future__ import absolute_import

import contextlib
import json
import os
import shutil
import tempfile
import unittest

from jsonnet import interpreter
from jsonnet import types


if hasattr(tempfile, 'TemporaryDirectory'):
    TemporaryDirectory = tempfile.TemporaryDirectory
else:
    # Python 2.x doesn't have tmpfile.TemporaryDirectory
    @contextlib.contextmanager
    def TemporaryDirectory(*args, **kwargs):
        path = tempfile.mkdtemp(*args, **kwargs)
        try:
            yield path
        finally:
            shutil.rmtree(path, True)


class APITestCase(unittest.TestCase):
    # Was assertRexexpMatch in Python 2.x
    assertRegex = unittest.TestCase.assertRegex \
        if hasattr(unittest.TestCase, 'assertRegex') else unittest.TestCase.assertRegexpMatches

    # Was assertRaiseRegexp in Python 2.x
    assertRaisesRegex = unittest.TestCase.assertRaisesRegex \
        if hasattr(unittest.TestCase, 'assertRaisesRegex') else unittest.TestCase.assertRaisesRegexp

    def test_version(self):
        self.assertRegex(interpreter.version(), r'^v\d+\.\d+\.\d+$')

    def test_evaluate_snippet(self):
        result = interpreter.evaluate_snippet('{"a": 1, "b": [], "c": null}')
        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})

    def test_evaluate_file(self):
        with TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'test.jsonnet')
            with open(test_file, 'w') as f:
                f.write('{"a": 1, "b": [], "c": null}')

            result = interpreter.evaluate_file(test_file)

        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})

    def test_deserialize(self):
        with interpreter.JsonnetVM() as vm:
            result = vm.evaluate_snippet('{"a": 1, "b": [], "c": null}', deserialize=True)

        self.assertEqual(result, {'a': 1, 'b': [], 'c': None})

    def test_deserialize_callable(self):
        def _upper_keys(string):
            return {k.upper(): v for k, v in json.loads(string).items()}

        with interpreter.JsonnetVM() as vm:
            result = vm.evaluate_snippet('{"a": 1, "b": [], "c": null}', deserialize=_upper_keys)

        self.assertEqual(result, {'A': 1, 'B': [], 'C': None})

    def test_import_callback(self):
        with TemporaryDirectory() as tmpdir:
            def _import_callback(_base, rel):
                path = os.path.join(tmpdir, rel)
                with open(path, 'r') as f:
                    return f.read(), f.name

            test_file = os.path.join(tmpdir, 'test.jsonnet')
            with open(test_file, 'w') as f:
                f.write('{"a": 1, "b": [], "c": null}')

            with interpreter.JsonnetVM(import_callback=_import_callback) as vm:
                result = vm.evaluate_snippet('import "test.jsonnet"')

        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})

    def test_import_callback_error(self):
        def _import_error(_base, _rel):
            raise RuntimeError('Test')

        with interpreter.JsonnetVM(import_callback=_import_error) as vm:
            with self.assertRaisesRegex(types.JsonnetError, 'RuntimeError: Test'):
                vm.evaluate_snippet('import "test"')

    def test_native_callbacks(self):
        with interpreter.JsonnetVM(native_callbacks={'add': lambda x, y: x + y}) as vm:
            self.assertEqual(
                vm.evaluate_snippet('std.native("add")(40, 2)', deserialize=True),
                42)

    def test_native_callbacks_all_types(self):
        types = {
            'str': 'abc',
            'int': 42,
            'float': 3.141592654,
            'bool': False,
            'array': [1, 1.0, 'two', True, [], {}, None],
            'object': {'Hello': 'World!'},
            'nil': None,
        }
        with interpreter.JsonnetVM(native_callbacks={'return_types': lambda: types}) as vm:
            self.assertEqual(
                vm.evaluate_snippet('std.native("return_types")()', deserialize=True),
                types)

    def test_native_callbacks_error(self):
        def _throw_error():
            raise RuntimeError('Test')

        with interpreter.JsonnetVM(native_callbacks={'throw_error': _throw_error}) as vm:
            with self.assertRaisesRegex(types.JsonnetError, 'RuntimeError: Test'):
                vm.evaluate_snippet('std.native("throw_error")()')

    def test_ext_var(self):
        with interpreter.JsonnetVM(ext_vars={'ext': '{"life": 42}'}) as vm:
            result = vm.evaluate_snippet('std.extVar("ext")', deserialize=True)

        self.assertEqual(result, '{"life": 42}')

    def test_ext_code(self):
        with interpreter.JsonnetVM(ext_codes={'x': '{"life": 42}'}) as vm:
            result = vm.evaluate_snippet('std.extVar("x")', deserialize=True)

        self.assertEqual(result, {'life': 42})

    def test_tla_var(self):
        with interpreter.JsonnetVM(tla_vars={'x': '{"life": 42}'}) as vm:
            result = vm.evaluate_snippet('function(x) x', deserialize=True)

        self.assertEqual(result, '{"life": 42}')

    def test_tla_code(self):
        with interpreter.JsonnetVM(tla_codes={'x': '{"life": 42}'}) as vm:
            result = vm.evaluate_snippet('function(x) x', deserialize=True)

        self.assertEqual(result, {'life': 42})

    def test_string_output(self):
        with interpreter.JsonnetVM(string_output=True) as vm:
            result = vm.evaluate_snippet('"Hello, world!"')

        self.assertEqual(result, u"Hello, world!\n")


if __name__ == '__main__':
    unittest.main()
