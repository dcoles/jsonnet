import json
import os
import tempfile
import unittest

from jsonnet import api, types


class APITestCase(unittest.TestCase):
    def test_evaluate_snippet(self):
        with api.JsonnetVM() as vm:
            result = vm.evaluate_snippet('{"a": 1, "b": [], "c": null}')

        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})

    def test_evaluate_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'test.jsonnet')
            with open(test_file, 'w') as f:
                f.write('{"a": 1, "b": [], "c": null}')

            with api.JsonnetVM() as vm:
                result = vm.evaluate_file(test_file)

        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})

    def test_deserialize(self):
        with api.JsonnetVM() as vm:
            result = vm.evaluate_snippet('{"a": 1, "b": [], "c": null}', deserialize=True)

        self.assertEqual(result, {'a': 1, 'b': [], 'c': None})

    def test_deserialize_callable(self):
        def _upper_keys(string):
            return {k.upper(): v for k, v in json.loads(string).items()}

        with api.JsonnetVM() as vm:
            result = vm.evaluate_snippet('{"a": 1, "b": [], "c": null}', deserialize=_upper_keys)

        self.assertEqual(result, {'A': 1, 'B': [], 'C': None})

    def test_import_callback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            def _import_callback(_base, rel):
                path = os.path.join(tmpdir, rel)
                with open(path, 'r') as f:
                    return f.read(), f.name

            test_file = os.path.join(tmpdir, 'test.jsonnet')
            with open(test_file, 'w') as f:
                f.write('{"a": 1, "b": [], "c": null}')

            with api.JsonnetVM(import_callback=_import_callback) as vm:
                result = vm.evaluate_snippet('import "test.jsonnet"')

        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})

    def test_import_callback_error(self):
        def _import_error(_base, _rel):
            raise RuntimeError('Test')

        with api.JsonnetVM(import_callback=_import_error) as vm:
            with self.assertRaisesRegex(types.JsonnetError, 'RuntimeError: Test'):
                vm.evaluate_snippet('import "test"')

    def test_native_callbacks(self):
        with api.JsonnetVM(native_callbacks={'add': lambda x, y: x + y}) as vm:
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
        with api.JsonnetVM(native_callbacks={'return_types': lambda: types}) as vm:
            self.assertEqual(
                vm.evaluate_snippet('std.native("return_types")()', deserialize=True),
                types)

    def test_native_callbacks_error(self):
        def _throw_error():
            raise RuntimeError('Test')

        with api.JsonnetVM(native_callbacks={'throw_error': _throw_error}) as vm:
            with self.assertRaisesRegex(types.JsonnetError, 'RuntimeError: Test'):
                vm.evaluate_snippet('std.native("throw_error")()')


if __name__ == '__main__':
    unittest.main()
