"""Candidate-bound workflow selection and accounted cold-start protocol tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from android_runtime import Android, PACKAGE
from android_runtime_mode import runtime_mode


class RuntimeModeTests(unittest.TestCase):
    def config(self, **overrides):
        return json.dumps({'schema': 1, 'candidate_sha256': 'a' * 64, 'interactive': True,
                           'cold_start_attempts': 4, **overrides})

    def test_absent_opt_in_keeps_existing_push_and_dispatch_defaults(self):
        self.assertEqual(runtime_mode('push', '', None, 'a' * 64),
                         {'interactive': False, 'cold_start_attempts': 0})
        self.assertTrue(runtime_mode('workflow_dispatch', 'true', None, 'a' * 64)['interactive'])
        self.assertFalse(runtime_mode('workflow_dispatch', 'false', None, 'a' * 64)['interactive'])

    def test_push_opt_in_is_exact_candidate_bound_and_dispatch_retains_choice(self):
        self.assertEqual(runtime_mode('push', '', self.config(), 'a' * 64),
                         {'interactive': True, 'cold_start_attempts': 4})
        self.assertEqual(runtime_mode('workflow_dispatch', 'false', self.config(), 'a' * 64),
                         {'interactive': False, 'cold_start_attempts': 4})
        with self.assertRaises(ValueError):
            runtime_mode('push', '', self.config(), 'b' * 64)

    def test_malformed_unbounded_and_unknown_modes_are_rejected(self):
        for raw in ('{}', '[]', self.config(schema=True), self.config(interactive='true'),
                    self.config(cold_start_attempts=True), self.config(cold_start_attempts=-1),
                    self.config(cold_start_attempts=7), self.config(candidate_sha256='A' * 64),
                    self.config(unexpected='command'), self.config().replace('"schema": 1', '"schema": 1, "schema": 1')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                runtime_mode('push', '', raw, 'a' * 64)
        with self.assertRaises(ValueError):
            runtime_mode('unknown_event', '', None, 'a' * 64)


class FakeStartupAndroid(Android):
    def __init__(self, output, outcomes):
        super().__init__(Path('/unused-sdk'), output)
        self.outcomes = outcomes
        self.attempt = -1
        self.marker = ''
        self.operations = []

    def shell(self, *args, **kwargs):
        self.operations.append(args)
        if args[:3] == ('log', '-t', 'S3CEColdStart'):
            self.attempt += 1
            self.marker = args[3]
        return ''

    def wait_for(self, label, predicate, timeout, interval=2):
        self.assert_stopped = predicate()

    def launch(self):
        self.operations.append(('launch-normal',))

    def snapshot(self, label):
        directory = self.output / label
        directory.mkdir(parents=True, exist_ok=True)
        status = self.outcomes[self.attempt]
        self.viewport = (0, 0, 1920, 1080) if status != 'no-canvas' else None
        self.viewport_source = 'fixture-native-canvas' if self.viewport else None
        event = {'game_pid': str(1000 + self.attempt) if status != 'dead' else ''}
        self.events.append(event)
        (directory / 'screen.png').write_bytes(b'fixture-frame')
        (directory / 'activity.txt').write_text('mResumedActivity: com.ideaworks3d.thesims3.Main')
        marker = self.marker if status != 'missing-marker' else 'unrelated'
        log = marker + '\n' + ('Fatal signal 11\n' if status == 'fatal' else '')
        (directory / 'logcat.txt').write_text(log)


class ColdStartupTests(unittest.TestCase):
    def test_distinct_cold_process_observations_leave_data_and_final_menu_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = FakeStartupAndroid(Path(temporary), ['ready'] * 4)
            with patch('android_runtime.time.sleep'):
                android.observe_cold_starts(4, 30)
            records = json.loads((Path(temporary) / 'cold-start-attempts.json').read_text())
            self.assertEqual([r['attempt'] for r in records], [1, 2, 3, 4])
            self.assertEqual({r['status'] for r in records}, {'ready-awaiting-visual-review'})
            self.assertEqual(len({r['game_pid'] for r in records}), 4)
            self.assertEqual(sum(op == ('am', 'force-stop', PACKAGE) for op in android.operations), 4)
            self.assertFalse(any('uninstall' in op or 'clear' in op for op in android.operations))
            self.assertEqual(android.viewport, (0, 0, 1920, 1080))

    def test_failure_is_retained_does_not_hide_later_attempts_and_fails_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = FakeStartupAndroid(Path(temporary), ['fatal', 'ready', 'dead', 'ready'])
            with patch('android_runtime.time.sleep'), self.assertRaisesRegex(RuntimeError, '2 of 4'):
                android.observe_cold_starts(4, 30)
            self.assertEqual([r['status'] for r in android.cold_starts],
                             ['failed', 'ready-awaiting-visual-review', 'failed', 'ready-awaiting-visual-review'])
            self.assertTrue(android.cold_starts[0]['fatal_or_anr_lines'])
            self.assertEqual(len(list(Path(temporary).glob('candidate-cold-start-*/screen.png'))), 4)

    def test_missing_log_window_or_native_canvas_cannot_pass(self):
        for outcome in ('missing-marker', 'no-canvas'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temporary:
                android = FakeStartupAndroid(Path(temporary), [outcome])
                with patch('android_runtime.time.sleep'), self.assertRaises(RuntimeError):
                    android.observe_cold_starts(1, 30)
                self.assertEqual(android.cold_starts[0]['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
