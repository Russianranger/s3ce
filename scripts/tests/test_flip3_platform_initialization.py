"""Synthetic fixture-start boundaries; actual API35 execution remains separate."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flip3_platform import ACTIVITY, HELPER, PACKAGE, capture_initial_geometry, validate_geometry

IDENTITY = {'apk_sha256': 'a' * 64, 'classes2_sha256': 'b' * 64}
INITIAL_PID, FRESH_PID = 2016, 2017


def report(pid=FRESH_PID, rejected=False):
    value = {'api': 35, 'display_size': [2640, 1080], 'physical_display_size': [2640, 1080],
        'failure': None, 'target_sdk': 28, 'hardware_accelerated': False,
        'requested_orientation': 6, 'window_cutout_mode': 2, 'process_id': pid,
        'identity': {**IDENTITY, 'loaded_helper': HELPER, 'helper_loader': 'dalvik.system.DexClassLoader'},
        'parent_class': HELPER, 'parent_bounds': [0, 0, 2640, 1032],
        'child_bounds': [408, 3, 2232, 1029], 'child_measured_size': [1824, 1026],
        'surface_frame': [1824, 1026], 'system_insets': [0, 0, 0, 48],
        'window_focused': True, 'resumed': True, 'touch_events': [], 'fixture_sequences': []}
    if rejected:
        # Measured rejected API35 size-compat geometry, with synthetic identity.
        value.update(parent_bounds=[62, 0, 2702, 1080], child_bounds=[422, 0, 2342, 1080],
            child_measured_size=[1920, 1080], surface_frame=[1920, 1080], system_insets=[0, 0, 0, 0])
    return value


WINDOW = f'''  Window #7 Window{{fixture u0 {PACKAGE}/{PACKAGE}.ViewportProbe}}:
    mSession=Session{{fixture {INITIAL_PID}:u0a10209}}
    mCompatFrame=[62,0][2702,1080]
    Frames: parent=[59,0][2582,1032] display=[59,0][2582,1032] frame=[59,0][2582,1032]
    mGlobalScale=0.95555556
  Window #8 Window{{unrelated u0 wallpaper}}:
    mGlobalScale=1.0
'''


class Device:
    def __init__(self, output, rejected=None, windows=WINDOW, start_ok=True):
        self.output, self.rejected = output, rejected or report(INITIAL_PID, rejected=True)
        self.windows, self.start_ok, self.operations = windows, start_ok, []
        self.captures = []

    def capture(self, label):
        self.captures.append(label)
        directory = self.output / label
        directory.mkdir()
        (directory / 'windows.txt').write_text(self.windows)
        (directory / 'probe.json').write_text(json.dumps(self.rejected))
        (directory / 'screen.png').write_bytes(b'synthetic-capture')
        return copy.deepcopy(self.rejected)

    def shell(self, *args, **kwargs):
        self.operations.append(args)
        if args == ('pidof', PACKAGE):
            return ''
        if args == ('am', 'force-stop', PACKAGE):
            return ''
        if args == ('am', 'start', '-W', '-n', ACTIVITY, '-f', '0x10008000'):
            return 'Status: ok\n' if self.start_ok else 'Error: fixture unavailable\n'
        raise AssertionError('Unexpected probe preparation mutation: ' + repr(args))

    def wait(self, label, predicate, timeout):
        if not predicate():
            raise TimeoutError(label)


class InitialFixtureTests(unittest.TestCase):
    def test_normal_initial_geometry_does_not_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            device, result = Device(Path(temporary)), {}
            with patch('flip3_platform.capture_settled_geometry', return_value=(report(), 'initial')):
                observed, capture = capture_initial_geometry(device, IDENTITY, (2640, 1080), result)
            self.assertEqual(capture, 'initial')
            self.assertEqual(result['initial_preparation']['status'], 'not-needed')
            self.assertEqual(device.operations, [])
            self.assertEqual(device.captures, [])

    def test_size_compat_rejection_retained_before_one_fresh_strict_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, result = Path(temporary), {}
            device = Device(output)
            with patch('flip3_platform.capture_settled_geometry', side_effect=[
                    TimeoutError('initial bounds outside display'), (report(), 'initial-fresh-fixture')]) as settle:
                observed, capture = capture_initial_geometry(device, IDENTITY, (2640, 1080), result)
            self.assertEqual(validate_geometry(observed, IDENTITY, (2640, 1080)), [408, 3, 2232, 1029])
            self.assertEqual(settle.call_count, 2)
            evidence = json.loads((output / 'initial-compat-preparation.json').read_text())
            self.assertEqual(evidence['status'], 'fresh-strict-fixture-ready')
            self.assertEqual((evidence['rejected_pid'], evidence['fresh_pid']), (INITIAL_PID, FRESH_PID))
            self.assertIn('outside', evidence['initial_error'])
            self.assertEqual(evidence['rejected_parent_bounds'], [62, 0, 2702, 1080])
            self.assertTrue((output / evidence['rejected_capture'] / 'screen.png').is_file())
            self.assertEqual(sum(op == ('am', 'force-stop', PACKAGE) for op in device.operations), 1)
            self.assertFalse(any('clear' in op or 'uninstall' in op or 'settings' in op for op in device.operations))

    def test_foreign_pid_unscaled_or_unmatched_window_never_allows_restart(self):
        cases = (WINDOW.replace(f'{INITIAL_PID}:', '9999:'), WINDOW.replace('0.95555556', '1.0'),
                 WINDOW.replace('[62,0][2702,1080]', '[0,0][2640,1080]'),
                 WINDOW.replace(PACKAGE, 'foreign'), WINDOW + WINDOW,
                 WINDOW.replace('.ViewportProbe}', '.ViewportProbeOther}'))
        for windows in cases:
            with self.subTest(windows=windows), tempfile.TemporaryDirectory() as temporary:
                device = Device(Path(temporary), windows=windows)
                with patch('flip3_platform.capture_settled_geometry', side_effect=TimeoutError('initial')), \
                        self.assertRaises(RuntimeError):
                    capture_initial_geometry(device, IDENTITY, (2640, 1080), {})
                self.assertEqual(device.operations, [])

    def test_unrelated_geometry_or_identity_failure_never_allows_restart(self):
        wrong_identity = report(INITIAL_PID, rejected=True)
        wrong_identity['identity']['classes2_sha256'] = 'c' * 64
        bad_child = report(INITIAL_PID)
        bad_child['child_bounds'] = [0, 0, 2640, 1032]
        for rejected in (wrong_identity, bad_child, report(INITIAL_PID)):
            with self.subTest(rejected=rejected), tempfile.TemporaryDirectory() as temporary:
                device = Device(Path(temporary), rejected=rejected)
                with patch('flip3_platform.capture_settled_geometry', side_effect=TimeoutError('initial')), \
                        self.assertRaises(RuntimeError):
                    capture_initial_geometry(device, IDENTITY, (2640, 1080), {})
                self.assertEqual(device.operations, [])

    def test_same_pid_or_second_invalid_geometry_stays_blocked(self):
        for fresh in (report(INITIAL_PID), report(FRESH_PID, rejected=True)):
            with self.subTest(fresh=fresh), tempfile.TemporaryDirectory() as temporary:
                device = Device(Path(temporary))
                with patch('flip3_platform.capture_settled_geometry', side_effect=[
                        TimeoutError('initial'), (fresh, 'initial-fresh-fixture')]), self.assertRaises((ValueError, RuntimeError)):
                    capture_initial_geometry(device, IDENTITY, (2640, 1080), {})
                self.assertEqual(sum(op == ('am', 'force-stop', PACKAGE) for op in device.operations), 1)
                evidence = json.loads((Path(temporary) / 'initial-compat-preparation.json').read_text())
                self.assertNotEqual(evidence['status'], 'fresh-strict-fixture-ready')

    def test_preparation_cannot_discard_existing_input_test_evidence(self):
        rejected = report(INITIAL_PID, rejected=True)
        rejected['touch_events'] = [{'action': 0}]
        with tempfile.TemporaryDirectory() as temporary:
            device = Device(Path(temporary), rejected=rejected)
            with patch('flip3_platform.capture_settled_geometry', side_effect=TimeoutError('initial')), \
                    self.assertRaisesRegex(RuntimeError, 'precede every fixture input'):
                capture_initial_geometry(device, IDENTITY, (2640, 1080), {})
            self.assertEqual(device.operations, [])

    def test_second_timeout_retained_without_third_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            device = Device(Path(temporary))
            with patch('flip3_platform.capture_settled_geometry', side_effect=TimeoutError('still invalid')) as settle, \
                    self.assertRaises(TimeoutError):
                capture_initial_geometry(device, IDENTITY, (2640, 1080), {})
            self.assertEqual(settle.call_count, 2)
            self.assertEqual(sum(op == ('am', 'force-stop', PACKAGE) for op in device.operations), 1)

    def test_failed_fresh_activity_launch_stays_blocked_with_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            device = Device(Path(temporary), start_ok=False)
            with patch('flip3_platform.capture_settled_geometry', side_effect=TimeoutError('initial')) as settle, \
                    self.assertRaisesRegex(RuntimeError, 'Activity start'):
                capture_initial_geometry(device, IDENTITY, (2640, 1080), {})
            self.assertEqual(settle.call_count, 1)
            evidence = json.loads((Path(temporary) / 'initial-compat-preparation.json').read_text())
            self.assertIn('Error:', evidence['fresh_am_start_output'])


if __name__ == '__main__':
    unittest.main()
