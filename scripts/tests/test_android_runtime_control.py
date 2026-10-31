"""The remote QA control channel can produce only frame-bound UI commands."""
import importlib.util
import json
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'android_runtime_control.py'
SPEC = importlib.util.spec_from_file_location('runtime_control', PATH)
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)


class ControlTest(unittest.TestCase):
    def envelope(self, command=None):
        return {'schema': 1, 'run_id': '41207302290', 'seq': 1,
                'frame_sha256': 'a' * 64, 'coordinate_size': [1920, 1080],
                'command': command or {'type': 'tap', 'x': 1250, 'y': 170}}

    def validate(self, document, **kwargs):
        return control.validate_control(document, '41207302290', 1,
                                        'a' * 64, [1920, 1080], **kwargs)

    def rejected(self, document, **kwargs):
        with self.assertRaises(control.ControlError):
            self.validate(document, **kwargs)

    def test_all_allowed_ui_operations(self):
        for command in ({'type': 'tap', 'x': 0, 'y': 1079},
                        {'type': 'swipe', 'x1': 0, 'y1': 0, 'x2': 1919,
                         'y2': 1079, 'duration_ms': 50},
                        {'type': 'wait', 'seconds': 0},
                        {'type': 'wait', 'seconds': 60},
                        {'type': 'wait', 'seconds': .5},
                        {'type': 'key', 'code': 3}, {'type': 'key', 'code': 4},
                        {'type': 'relaunch'}, {'type': 'finish'}):
            with self.subTest(command=command):
                document = self.envelope(command)
                self.assertEqual(self.validate(json.dumps(document).encode()), command)
                document['note'] = 'Metadata only; never a command.'
                self.assertEqual(self.validate(document), command)

    def test_result_has_no_alias_to_untrusted_command(self):
        document = self.envelope()
        result = self.validate(document)
        document['command']['x'] = -100
        self.assertEqual(result, {'type': 'tap', 'x': 1250, 'y': 170})

    def test_run_next_sequence_frame_and_size_are_bound(self):
        for key, values in {'schema': [True, 0, 2, '1'],
                            'run_id': ['41207302291', 41207302290, None],
                            'seq': [0, 2, True, 1.0, '1', 2**31],
                            'frame_sha256': ['b'*64, 'A'*64, 'a'*63, None],
                            'coordinate_size': [[1080, 1920], [1920, 1079],
                                                [1920, True], [1920], '1920x1080']}.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    document = self.envelope()
                    document[key] = value
                    self.rejected(document)

    def test_unknown_and_missing_fields_fail_closed(self):
        for key in self.envelope():
            document = self.envelope()
            del document[key]
            self.rejected(document)
        for key in ('shell', 'package', 'activity', 'save_file', 'memory', 'actions', 'passed'):
            document = self.envelope()
            document[key] = 'unexpected'
            self.rejected(document)
            document = self.envelope()
            document['command'][key] = 'unexpected'
            self.rejected(document)
        for kind in ('exec', 'shell', 'write', 'text', 'start_activity', 'force_stop', 'memory'):
            self.rejected(self.envelope({'type': kind}))
        for kind in ('relaunch', 'finish'):
            self.rejected(self.envelope({'type': kind, 'passed': True}))
            self.rejected(self.envelope({'type': kind, 'package': 'other.app'}))

    def test_pixel_edges_and_viewport(self):
        self.validate(self.envelope({'type': 'tap', 'x': 100, 'y': 40}),
                      viewport=(100, 40, 1820, 1040))
        for x, y in ((-1, 0), (1920, 0), (0, 1080), (1.0, 1), (True, 1)):
            self.rejected(self.envelope({'type': 'tap', 'x': x, 'y': y}))
        for x, y in ((99, 40), (100, 39), (1820, 40), (100, 1040)):
            self.rejected(self.envelope({'type': 'tap', 'x': x, 'y': y}),
                          viewport=(100, 40, 1820, 1040))
        for field in ('x1', 'x2', 'y1', 'y2'):
            command = {'type': 'swipe', 'x1': 100, 'y1': 100,
                       'x2': 200, 'y2': 200, 'duration_ms': 1000}
            command[field] = -1
            self.rejected(self.envelope(command))
        for viewport in ((-1, 0, 1920, 1080), (0, 0, 1921, 1080),
                         (100, 0, 100, 1080), (0, 0, True, 1080)):
            self.rejected(self.envelope(), viewport=viewport)

    def test_durations_and_keys_are_bounded(self):
        for seconds in (-1, 60.1, float('inf'), float('nan'), True, '1', 10**500):
            self.rejected(self.envelope({'type': 'wait', 'seconds': seconds}))
        for duration in (0, 49, 2001, 500.0, True, '500'):
            self.rejected(self.envelope({'type': 'swipe', 'x1': 1, 'y1': 1,
                                        'x2': 2, 'y2': 2, 'duration_ms': duration}))
        for code in (0, 2, 5, 66, True, 3.0, 'HOME'):
            self.rejected(self.envelope({'type': 'key', 'code': code}))

    def test_strict_raw_json(self):
        valid = json.dumps(self.envelope())
        for raw in ('', '[]', 'null', '{', valid + valid,
                    valid.replace('"seq": 1', '"seq": 1, "seq": 2'),
                    valid.replace('"x": 1250', '"x": 1250, "x": 1'),
                    valid.replace('"x": 1250', '"x": NaN'),
                    valid.replace('"x": 1250', '"x": Infinity'),
                    '['*1100 + '0' + ']'*1100,
                    valid + ' ' * control.MAX_DOCUMENT_BYTES):
            self.rejected(raw)
        self.rejected(b'\xff')
        self.rejected(bytearray(valid.encode()))
        self.rejected(None)

    def test_notes_are_only_bounded_metadata(self):
        document = self.envelope()
        document['note'] = 'x'*256
        self.validate(document)
        document['note'] += 'x'
        self.rejected(document)
        document['note'] = {'shell': 'not allowed'}
        self.rejected(document)
        document['note'] = '\ud800'
        self.rejected(json.dumps(document).encode())

    def test_invalid_expected_context_never_allows_a_command(self):
        document = self.envelope()
        contexts = [('0', 1, 'a'*64, [1920, 1080]),
                    ('41207302290', True, 'a'*64, [1920, 1080]),
                    ('41207302290', 1, 'A'*64, [1920, 1080]),
                    ('41207302290', 1, 'a'*64, [0, 1080])]
        for context in contexts:
            with self.subTest(context=context), self.assertRaises(control.ControlError):
                control.validate_control(document, *context)


if __name__ == '__main__':
    unittest.main()
