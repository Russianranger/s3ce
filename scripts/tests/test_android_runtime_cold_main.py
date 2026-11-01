"""Synthetic direct-entry evidence only; no Android process or JNI runtime runs."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from android_runtime import Android, MAIN, PACKAGE, cold_main_session_phases
from android_runtime_profile import runtime_profile

BOUNDS = (30, 0, 190, 90)
BEFORE_PID, FRESH_PID = '200', '201'
PHASES = ['Main entry requires native bootstrap (process restoration)',
          'nativeBootstrap RETURN version=65542', 'Native Main ENTER']


def session(pid=FRESH_PID, phases=None):
    identity = f'SESSION package={PACKAGE} version=test code=115 process={PACKAGE} process64=false pid={pid} wallMs=100 elapsedMs=10'
    return identity + '\n' + ''.join(f'wallMs={101 + index} elapsedMs={11 + index} {phase}\n'
                                      for index, phase in enumerate(PHASES if phases is None else phases))


class DirectMainAndroid(Android):
    def __init__(self, output, captures=None, start_ok=True):
        super().__init__(Path('/unused-sdk'), output)
        self.operations, self.marker = [], ''
        self.started, self.stopped, self.start_ok = False, False, start_ok
        self.captures = captures or [{}]
        self.capture_index = 0
        # Deliberately separate existing normal cold attempts from this probe.
        self.cold_starts = [{'game_pid': '198', 'status': 'ready-awaiting-visual-review'},
                            {'game_pid': BEFORE_PID, 'status': 'ready-awaiting-visual-review'}]

    def shell(self, *args, **kwargs):
        self.operations.append(args)
        if args == ('pidof', PACKAGE):
            return '' if self.stopped else BEFORE_PID
        if args[:3] == ('log', '-t', 'S3CEDirectMain'):
            self.marker = args[3]
            return ''
        if args == ('am', 'force-stop', PACKAGE):
            self.stopped = True
            return ''
        if args == ('am', 'start', '-W', '-n', MAIN):
            self.started = True
            return 'Status: ok\nActivity: ' + MAIN + '\n' if self.start_ok else 'Error: not exported\n'
        raise AssertionError('Unexpected synthetic shell operation: ' + repr(args))

    def snapshot(self, label):
        observation = self.captures[min(self.capture_index, len(self.captures) - 1)]
        self.capture_index += 1
        directory = self.output / label
        directory.mkdir(parents=True, exist_ok=True)
        self.viewport = observation.get('bounds', BOUNDS)
        self.viewport_source = observation.get('viewport_source', 'GameViewport actual child layout witness')
        pid = observation.get('pid', FRESH_PID)
        self.events.append({'game_pid': pid})
        image = Image.new('RGB', (220, 90), (0, 0, 0))
        if not observation.get('black'):
            for x in range(30, 190):
                for y in range(90):
                    image.putpixel((x, y), ((x * 3) % 256, (x * 7) % 256, (y * 11) % 256))
        image.save(directory / 'screen.png')
        (directory / 'activity.txt').write_text('mResumedActivity: ' + observation.get('activity', MAIN))
        (directory / 'logcat.txt').write_text(observation.get('marker', self.marker) + '\n'
                                              + observation.get('log', ''))
        (directory / 'compat-session.log').write_text(observation.get('session', session(pid)))


class ColdMainSessionTests(unittest.TestCase):
    def test_current_process_has_one_successful_bootstrap_before_native_entry(self):
        facts = cold_main_session_phases(session(), FRESH_PID)
        self.assertEqual(facts['ordered_phases'], PHASES)
        self.assertIn('pid=' + FRESH_PID, facts['session_identity'])

    def test_old_missing_bootstrap_wrong_order_or_duplicate_never_passes(self):
        cases = (PHASES[1:], PHASES[::-1], PHASES + PHASES[:1],
                 [PHASES[0], 'nativeBootstrap RETURN version=-1', PHASES[2]],
                 PHASES + ['Activity com.ideaworks3d.thesims3.GameBootActivity created restored=false'])
        for phases in cases:
            with self.subTest(phases=phases), self.assertRaises(RuntimeError):
                cold_main_session_phases(session(phases=phases), FRESH_PID)

    def test_stale_foreign_or_multiple_session_identity_never_passes(self):
        for text, pid in ((session(BEFORE_PID), FRESH_PID), (session(), FRESH_PID + ' 202'),
                          (session().replace('process=' + PACKAGE, 'process=other'), FRESH_PID),
                          (session() + session(), FRESH_PID)):
            with self.subTest(text=text, pid=pid), self.assertRaises(RuntimeError):
                cold_main_session_phases(text, pid)


class DirectColdMainTests(unittest.TestCase):
    def run_probe(self, android):
        with patch('android_runtime.time.sleep'):
            return android.verify_cold_main_entry(BOUNDS, launch_wait=0)

    def test_retains_first_black_frame_then_fresh_visible_process_without_counting_normal_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            android = DirectMainAndroid(output, [{'black': True}, {}])
            records_before = list(android.cold_starts)
            record = self.run_probe(android)
            self.assertEqual(record['status'], 'cold-Main-bootstrap-visible-awaiting-menu-review')
            self.assertEqual(record['visual_review'], 'normal menu required')
            self.assertEqual(record['game_pid'], FRESH_PID)
            self.assertEqual(record['ordered_phases'], PHASES)
            self.assertEqual([row['rendered_pixels'] for row in record['captures']], [False, True])
            self.assertEqual(android.cold_starts, records_before)
            self.assertFalse(record['normal_launcher_cold_start_counted'])
            self.assertEqual(sum(op == ('am', 'force-stop', PACKAGE) for op in android.operations), 1)
            self.assertIn(('am', 'start', '-W', '-n', MAIN), android.operations)
            self.assertFalse(any('clear' in op or 'uninstall' in op or 'input' in op for op in android.operations))
            for row in record['captures']:
                self.assertTrue((output / row['capture'] / 'screen.png').is_file())
                self.assertTrue((output / row['capture'] / 'attempt-logcat.txt').is_file())
            self.assertEqual(json.loads((output / 'cold-main-entry-observation.json').read_text())['game_pid'], FRESH_PID)

    def test_pid_bounds_resume_session_or_fatal_failure_is_retained_and_rejected(self):
        cases = [{'pid': BEFORE_PID}, {'pid': '198'}, {'pid': ''}, {'pid': '201 202'},
                 {'bounds': (0, 0, 220, 90)}, {'activity': PACKAGE + '/other.Activity'},
                 {'viewport_source': 'retained last verified native canvas through Android UI'},
                 {'session': session(phases=PHASES[1:])}, {'session': session(BEFORE_PID)},
                 {'marker': 'unrelated'}, {'log': 'FATAL EXCEPTION: main\njava.lang.UnsatisfiedLinkError\n'},
                 {'log': 'Fatal signal 11 (SIGSEGV)\n'}, {'log': 'ANR in ' + PACKAGE + '\n'}]
        for failure in cases:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)
                android = DirectMainAndroid(output, [failure])
                with self.assertRaises(RuntimeError):
                    self.run_probe(android)
                evidence = json.loads((output / 'cold-main-entry-observation.json').read_text())
                self.assertEqual(evidence['status'], 'failed')
                self.assertEqual(len(evidence['captures']), 1)
                self.assertTrue((output / evidence['captures'][0]['capture'] / 'screen.png').is_file())
                self.assertTrue(evidence['error'])

    def test_replacement_process_after_black_frame_is_not_hidden_by_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = DirectMainAndroid(Path(temporary), [{'black': True}, {'pid': '202'}])
            with self.assertRaisesRegex(RuntimeError, 'distinct fresh game process'):
                self.run_probe(android)
            self.assertEqual([row['game_pid'] for row in android.cold_main_entry_observation['captures']], ['201', '202'])

    def test_missing_current_child_after_black_frame_cannot_pass_using_retained_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = DirectMainAndroid(Path(temporary), [{'black': True},
                {'viewport_source': 'retained last verified native canvas through Android UI'}])
            with self.assertRaisesRegex(RuntimeError, 'actual native child bounds'):
                self.run_probe(android)
            self.assertEqual(len(android.cold_main_entry_observation['captures']), 2)

    def test_black_canvas_stops_after_twelve_retained_captures(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = DirectMainAndroid(Path(temporary), [{'black': True}])
            with self.assertRaisesRegex(RuntimeError, 'bounded readiness'):
                self.run_probe(android)
            self.assertEqual(len(android.cold_main_entry_observation['captures']), 12)
            self.assertEqual(len(list(Path(temporary).glob('candidate-direct-cold-main-*/screen.png'))), 12)

    def test_failed_direct_launch_retains_am_output_and_failure_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            android = DirectMainAndroid(output, start_ok=False)
            with self.assertRaisesRegex(RuntimeError, 'am start'):
                self.run_probe(android)
            evidence = json.loads((output / 'cold-main-entry-observation.json').read_text())
            self.assertEqual((output / 'direct-main-am-start.txt').read_text(), 'Error: not exported\n')
            self.assertTrue((output / evidence['failure_capture'] / 'screen.png').is_file())

    def test_flip3_only_enables_probe_and_uses_its_accepted_baseline(self):
        self.assertTrue(runtime_profile('flip3').get('verify_cold_main_entry', False))
        self.assertEqual(runtime_profile('flip3')['baseline_staging'], '.publish/v0.1.14-flip3')
        self.assertFalse(runtime_profile('main').get('verify_cold_main_entry', False))


if __name__ == '__main__':
    unittest.main()
