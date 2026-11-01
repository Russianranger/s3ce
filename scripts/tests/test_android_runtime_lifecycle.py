"""Synthetic pixels/window observations only; no Android or game process runs."""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from android_runtime import Android, main_window_rotation, native_frame_visibility

BOUNDS = (30, 0, 190, 90)
PID = 'fixture-pid'


def frame(path, kind):
    image = Image.new('RGB', (220, 90), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    if kind == 'flat':
        draw.rectangle((30, 0, 189, 89), fill=(40, 110, 140))
    elif kind == 'complex':
        for x in range(160):
            draw.line((30 + x, 0, 30 + x, 89), fill=((x * 3) % 256, (x * 7) % 256, (x * 11) % 256))
    elif kind != 'black':
        raise ValueError('Unknown synthetic frame kind')
    image.save(path)


def window(rotation):
    return ('Window #0 Window{fixture u0 io.github.russianranger.s3ce/com.ideaworks3d.thesims3.Main}:\n'
            '  mAttrs={ty=BASE_APPLICATION}\n'
            '  mFullConfiguration={mRotation=ROTATION_' + str(rotation * 90) + '}\n')


class ObservedAndroid(Android):
    def __init__(self, output, visible_frames=None, changed=None, reverse_unavailable=False,
                 restore_fails=False, unavailable_rotation=1):
        super().__init__(Path('/unused-sdk'), output)
        self.viewport = BOUNDS
        self.events.append({'game_pid': PID})
        self.visible_frames = visible_frames or ['complex']
        self.visible_count = 0
        self.visible_counts = {}
        self.labels = []
        self.changed = changed or {}
        self.actual_rotation = 1
        self.requested_rotations = []
        self.sensor_rotations = []
        self.reverse_unavailable, self.restore_fails = reverse_unavailable, restore_fails
        self.unavailable_rotation = unavailable_rotation

    def snapshot(self, label):
        self.labels.append(label)
        directory = self.output / label
        directory.mkdir(parents=True, exist_ok=True)
        if label.startswith('landscape-rotation-'):
            kind = 'complex'
        else:
            prefix = label.rsplit('-', 1)[0]
            count = self.visible_counts.get(prefix, 0)
            kind = self.visible_frames[min(count, len(self.visible_frames) - 1)]
            self.visible_counts[prefix] = count + 1
            self.visible_count += 1
        changed = self.changed.get(label, {})
        self.viewport = changed.get('bounds', BOUNDS)
        event = {'game_pid': changed.get('pid', PID), 'native_viewport': self.viewport}
        self.events.append(event)
        frame(directory / 'screen.png', kind)
        (directory / 'windows.txt').write_text(window(self.actual_rotation))
        (directory / 'observation.json').write_text(json.dumps(event))

    def shell(self, *args, **kwargs):
        if args[:4] == ('settings', 'put', 'system', 'user_rotation'):
            self.requested_rotations.append((int(args[4]), self.actual_rotation))
            # A request is deliberately not an actual Main-window observation.
            return ''
        if args == ('dumpsys', 'window', 'windows'):
            return window(self.actual_rotation)
        raise AssertionError('Unexpected synthetic shell operation: ' + repr(args))

    def adb(self, *args, **kwargs):
        if args[:4] != ('emu', 'sensor', 'set', 'acceleration'):
            raise AssertionError('Unexpected synthetic ADB operation: ' + repr(args))
        x, y, _ = map(float, args[4].split(':'))
        # Independent AOSP orientation-judge model: -atan2(-x,y), then
        # nearest((angle+45)//90)%4. It catches a reversed stimulus sign.
        angle = -math.degrees(math.atan2(-x, y))
        measured = int((angle + 45) // 90) % 4
        self.sensor_rotations.append(measured)
        if measured == 3 and self.reverse_unavailable:
            self.actual_rotation = self.unavailable_rotation
            return b'OK; sensor accepted but Main did not take requested reverse rotation'
        if measured == 1 and self.restore_fails:
            return b'OK; sensor accepted but Main did not restore'
        self.actual_rotation = measured
        return b'OK'

    def wait_for(self, label, predicate, timeout, interval=2):
        if not predicate():
            raise TimeoutError('Synthetic measured orientation unavailable: ' + label)


class NativeFrameLifecycleTests(unittest.TestCase):
    def test_black_and_flat_nonblack_are_not_visible_game_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'frame.png'
            for kind in ('black', 'flat', 'complex'):
                frame(path, kind)
                facts = native_frame_visibility(path, BOUNDS)
                self.assertEqual(facts['rendered_pixels'], kind == 'complex')
                self.assertTrue(facts['readiness_only'])
                if kind == 'flat':
                    self.assertGreater(facts['nonblack_pixels'], facts['canvas_pixels'] // 10)
                    self.assertEqual(facts['distinct_colors_capped_at_65'], 1)

    def test_black_capture_is_retained_before_complex_frame_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            device = ObservedAndroid(output, ['black', 'complex'])
            with patch('android_runtime.time.sleep'):
                facts = device.wait_for_visible_native_frame('return', PID, BOUNDS)
            self.assertTrue(facts['rendered_pixels'])
            evidence = json.loads((output / 'return-readiness.json').read_text())
            self.assertTrue(evidence['accepted'])
            self.assertEqual([r['rendered_pixels'] for r in evidence['captures']], [False, True])
            self.assertTrue((output / 'return-00/screen.png').is_file())
            self.assertTrue((output / 'return-01/screen.png').is_file())

    def test_flat_nonblack_readiness_stops_after_twelve_retained_captures(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            device = ObservedAndroid(output, ['flat'])
            with patch('android_runtime.time.sleep'), self.assertRaisesRegex(RuntimeError, 'stayed blank'):
                device.wait_for_visible_native_frame('flat', PID, BOUNDS)
            evidence = json.loads((output / 'flat-readiness.json').read_text())
            self.assertFalse(evidence['accepted'])
            self.assertEqual(len(evidence['captures']), 12)
            self.assertEqual(len(list(output.glob('flat-*/screen.png'))), 12)

    def test_changed_process_or_canvas_fails_immediately_without_retry(self):
        for changed in ({'pid': 'replacement'}, {'bounds': (30, 0, 220, 90)}):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)
                device = ObservedAndroid(output, ['complex'], changed={'return-00': changed})
                with patch('android_runtime.time.sleep'), self.assertRaisesRegex(RuntimeError, 'same game process'):
                    device.wait_for_visible_native_frame('return', PID, BOUNDS)
                self.assertEqual(device.labels, ['return-00'])
                self.assertTrue((output / 'return-00/screen.png').is_file())
                observation = json.loads((output / 'return-00/observation.json').read_text())
                self.assertTrue(observation['game_pid'] != PID or tuple(observation['native_viewport']) != BOUNDS)
                self.assertFalse(json.loads((output / 'return-readiness.json').read_text())['accepted'])

    def test_sensor_signs_produce_measured_reverse_three_then_restore_one(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            device = ObservedAndroid(output)
            with patch('android_runtime.time.sleep'):
                device.verify_landscape_rotations(BOUNDS)
            self.assertEqual(device.sensor_rotations, [3, 1])
            self.assertEqual(device.requested_rotations, [(3, 1), (1, 1)])
            observations = json.loads((output / 'landscape-rotations.json').read_text())
            self.assertEqual([r['actual_main_window_rotation'] for r in observations], [3, 1])
            self.assertEqual([r['status'] for r in observations], ['actual-rotation-observed', 'restored-actual-rotation1'])
            self.assertTrue(observations[-1]['visible_readiness']['rendered_pixels'])
            for record in observations:
                self.assertEqual(main_window_rotation((output / record['capture'] / 'windows.txt').read_text()),
                                 record['actual_main_window_rotation'])

    def test_unavailable_reverse_continues_only_after_measured_one_and_visible_return(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            device = ObservedAndroid(output, ['black', 'complex'], reverse_unavailable=True)
            with patch('android_runtime.time.sleep'):
                device.verify_landscape_rotations(BOUNDS)
            observations = json.loads((output / 'landscape-rotations.json').read_text())
            self.assertEqual([r['actual_main_window_rotation'] for r in observations], [1, 1])
            self.assertEqual(observations[0]['status'], 'unavailable')
            self.assertIn('limitation', observations[0])
            self.assertTrue(observations[-1]['visible_readiness']['rendered_pixels'])
            self.assertEqual([r['rendered_pixels'] for r in json.loads(
                (output / 'landscape-restored-visible-readiness.json').read_text())['captures']], [False, True])

    def test_failed_restore_retains_actual_three_and_rejects_continuation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            device = ObservedAndroid(output, restore_fails=True)
            with patch('android_runtime.time.sleep'), self.assertRaisesRegex(RuntimeError, 'restored measured Main'):
                device.verify_landscape_rotations(BOUNDS)
            observations = json.loads((output / 'landscape-rotations.json').read_text())
            self.assertEqual(observations[-1]['status'], 'restoration-failed')
            self.assertEqual(observations[-1]['actual_main_window_rotation'], 3)
            self.assertTrue((output / observations[-1]['capture'] / 'screen.png').is_file())

    def test_unavailable_reverse_does_not_waive_pid_canvas_or_pixel_guards(self):
        cases = ({'changed': {'landscape-rotation-1': {'pid': 'replacement'}}},
                 {'changed': {'landscape-rotation-1': {'bounds': (30, 0, 220, 90)}}},
                 {'visible_frames': ['flat']}, {'unavailable_rotation': 0})
        for arguments in cases:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)
                device = ObservedAndroid(output, reverse_unavailable=True, **arguments)
                with patch('android_runtime.time.sleep'), self.assertRaises(RuntimeError):
                    device.verify_landscape_rotations(BOUNDS)
                observations = json.loads((output / 'landscape-rotations.json').read_text())
                self.assertEqual(observations[0]['status'], 'unavailable')
                self.assertTrue((output / observations[-1]['capture'] / 'screen.png').is_file())
                if 'visible_frames' in arguments:
                    self.assertFalse(json.loads((output / 'landscape-restored-visible-readiness.json').read_text())['accepted'])


if __name__ == '__main__':
    unittest.main()
