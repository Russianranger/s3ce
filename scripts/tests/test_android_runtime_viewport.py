"""Native child geometry and black-margin input checks; synthetic Android boundary."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from android_runtime import Android, game_viewport, letterbox_probe_points, main_window_rotation
from android_runtime_profile import runtime_profile


WIDE_WINDOW = '\nWindow #0 Window{123 u0 io.github.russianranger.s3ce/com.ideaworks3d.thesims3.Main}:\n ty=BASE_APPLICATION mFrame=[0,0][2640,1080]\n'
LAYOUT = 'VIEWPORT child=com.ideaworks3d.airplay.AirplayView bounds=[360,0][2280,1080] parent=[0,0][2640,1080]'
BOUNDS = (360, 0, 2280, 1080)


class ViewportGeometryTests(unittest.TestCase):
    def test_wide_activity_alone_never_becomes_a_stretched_game_canvas(self):
        self.assertEqual(game_viewport('', WIDE_WINDOW, screen_size=(2640, 1080)), (None, None))
        legacy = WIDE_WINDOW.replace('2640', '1920')
        self.assertEqual(game_viewport('', legacy, screen_size=(1920, 1080))[0], (0, 0, 1920, 1080))

    def test_actual_child_layout_requires_current_window_and_screen_containment(self):
        self.assertEqual(game_viewport('', WIDE_WINDOW, LAYOUT, (2640, 1080)),
                         (BOUNDS, 'GameViewport actual child layout witness'))
        for events, windows, size in (
            (LAYOUT, '', (2640, 1080)),
            (LAYOUT, WIDE_WINDOW, (1080, 2640)),
            (LAYOUT.replace('2280,1080', '2640,1080'), WIDE_WINDOW, (2640, 1080)),
            (LAYOUT.replace('parent=[0,0][2640,1080]', 'parent=[0,0][2800,1080]'), WIDE_WINDOW, (2640, 1080)),
            (LAYOUT.replace('com.ideaworks3d.airplay.AirplayView', 'unrelated.SurfaceView'), WIDE_WINDOW, (2640, 1080))):
            with self.subTest(events=events, size=size):
                self.assertEqual(game_viewport('', windows, events, size), (None, None))

    def test_native_hierarchy_has_priority_and_logical_input_maps_into_child(self):
        hierarchy = '<hierarchy><node class="android.view.SurfaceView" package="io.github.russianranger.s3ce" bounds="[360,0][2280,1080]"/></hierarchy>'
        self.assertEqual(game_viewport(hierarchy, WIDE_WINDOW, LAYOUT, (2640, 1080)),
                         (BOUNDS, 'SurfaceView hierarchy'))
        android = Android(Path('/unused-sdk'), Path('/unused-output'))
        android.viewport = BOUNDS
        self.assertEqual(android.coordinates([0, 0], [1920, 1080]), (360, 0))
        self.assertEqual(android.coordinates([960, 540], [1920, 1080]), (1320, 540))
        self.assertEqual(android.coordinates([1804, 965], [1920, 1080]), (2164, 965))
        self.assertEqual(letterbox_probe_points((2640, 1080), BOUNDS), [(180, 540), (2460, 540)])
        with self.assertRaises(ValueError):
            letterbox_probe_points((1920, 1080), (0, 0, 1920, 1080))

    def test_flip3_profile_preserves_existing_main_profile(self):
        wide, main = runtime_profile('flip3'), runtime_profile('main')
        self.assertEqual((wide['screen_width'], wide['screen_height']), (2640, 1080))
        self.assertEqual(wide['expected_game_bounds'], BOUNDS)
        self.assertEqual(wide['candidate_staging'], '.validation/flip3')
        self.assertEqual(main['candidate_staging'], '.validation/camera-input')
        self.assertFalse(main['verify_letterbox'])

    def test_rotation_comes_from_actual_main_window_configuration(self):
        for degrees, expected in ((90, 1), (270, 3)):
            windows = WIDE_WINDOW + f'mFullConfiguration={{winConfig={{mRotation=ROTATION_{degrees}}}}}\n'
            self.assertEqual(main_window_rotation(windows), expected)
        self.assertIsNone(main_window_rotation(WIDE_WINDOW + 'user_rotation=3\n'))
        self.assertIsNone(main_window_rotation(WIDE_WINDOW.replace('thesims3.Main}', 'thesims3.CompatActivity}')
                                              + 'mFullConfiguration={mRotation=ROTATION_270}\n'))


class MarginAndroid(Android):
    def __init__(self, output, forwards=False):
        super().__init__(Path('/unused-sdk'), output)
        self.forwards = forwards
        self.operations = []
        self.pointer_events = 0

    def shell(self, *args, **kwargs):
        self.operations.append(args)
        if args[:2] == ('input', 'tap') and self.forwards:
            self.pointer_events += 1
        return ''

    def snapshot(self, label):
        directory = self.output / label
        directory.mkdir(parents=True, exist_ok=True)
        image = Image.new('RGB', (2640, 1080), (0, 0, 0))
        image.paste((0, 80, 160), BOUNDS)
        image.save(directory / 'screen.png')
        self.screen_size, self.viewport = (2640, 1080), BOUNDS
        self.latest_native = ''.join(f'Pointer callback ENTER #{n} event=0\n' for n in range(1, self.pointer_events + 1))
        self.events.append({'game_pid': '100'})


class MarginInputTests(unittest.TestCase):
    def test_inert_margins_are_recorded_without_game_or_save_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = MarginAndroid(Path(temporary))
            with patch('android_runtime.time.sleep'):
                android.verify_letterbox_margins(BOUNDS)
            report = json.loads((Path(temporary) / 'letterbox-observation.json').read_text())
            self.assertEqual(report['status'], 'callback-inert-awaiting-visual-review')
            self.assertEqual(android.operations, [('input', 'tap', 180, 540), ('input', 'tap', 2460, 540)])
            self.assertTrue(all(row['callback_witness_unchanged'] for row in report['observations']))

    def test_callback_interception_cannot_pass_as_an_inert_black_bar(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = MarginAndroid(Path(temporary), forwards=True)
            with patch('android_runtime.time.sleep'), self.assertRaisesRegex(RuntimeError, 'reached native input'):
                android.verify_letterbox_margins(BOUNDS)


if __name__ == '__main__':
    unittest.main()
