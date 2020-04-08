import json
import tempfile
import unittest
from pathlib import Path

from jsonnet import api


class APITestCase(unittest.TestCase):
    def test_evaluate_snippet(self):
        with api.JsonnetVM() as vm:
            result = vm.evaluate_snippet('{"a": 1, "b": [], "c": null}')

        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})

    def test_evaluate_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'test.jsonnet'
            with test_file.open('w') as f:
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
            tmpdir = Path(tmpdir)

            def _import_callback(base, rel):
                path = tmpdir / rel
                with path.open('r') as f:
                    return f.read(), f.name

            test_file = tmpdir / 'test.jsonnet'
            with test_file.open('w') as f:
                f.write('{"a": 1, "b": [], "c": null}')

            with api.JsonnetVM(import_callback=_import_callback) as vm:
                result = vm.evaluate_snippet('import "test.jsonnet"')

        self.assertEqual(json.loads(result), {'a': 1, 'b': [], 'c': None})


    def test_native_callbacks(self):
        with api.JsonnetVM(native_callbacks={'add': lambda x, y: x + y}) as vm:
            self.assertEqual(
                vm.evaluate_snippet('std.native("add")(40, 2)', deserialize=True),
                42)


if __name__ == '__main__':
    unittest.main()
