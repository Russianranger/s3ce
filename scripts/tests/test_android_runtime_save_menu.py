"""SaveQuit stale-observer regression; synthetic evidence, no Android/game writes."""
import io
import json
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from android_runtime import Android, saved_main_menu_visual_allowed


BOUNDS = (360, 0, 2280, 1080)
SAVE = {'sim3dat0': {'bytes': 2562, 'mtime_epoch_seconds': 100},
        'sim3set': {'bytes': 90, 'mtime_epoch_seconds': 100}}
NEW_SAVE = {name: {**facts, 'mtime_epoch_seconds': 200} for name, facts in SAVE.items()}
STEP = {'name': 'confirm-save-and-quit', 'confirm_save_visually': True,
        'expect_scene': 'SceneMenu', 'expect_menu_state': 5,
        'checkpoint': 'saved-to-menu', 'wait': 0}
MENU = {'kind': 'main-menu', 'point': [1069.5, 798.5]}
OBSERVER = 'Pointer callback EXIT #4366 Scene=SceneGame gamePhase=14'


class SaveAndroid(Android):
    def __init__(self, output):
        super().__init__(Path('/unused-sdk'), output)
        self.viewport, self.viewport_source = BOUNDS, 'GameViewport actual child layout witness'
        self.latest_native = OBSERVER
        self.events = [{'game_pid': '6059'}]
        self.saves = deepcopy(NEW_SAVE)
        self.pid, self.bounds, self.resumed = '6059', BOUNDS, True

    def save_fingerprints(self):
        return deepcopy(self.saves)

    def snapshot(self, label):
        directory = self.output / label
        directory.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (2640, 1080), 'blue').save(directory / 'screen.png')
        activity = 'mResumedActivity: com.ideaworks3d.thesims3.Main' if self.resumed else 'Launcher'
        (directory / 'activity.txt').write_text(activity)
        self.viewport = self.bounds
        self.events.append({'name': label, 'scene': 'SceneGame', 'menu_state': None,
                            'game_pid': self.pid, 'observer': OBSERVER})

    def choose_save_visually(self, *args, **kwargs):
        self.saves = deepcopy(NEW_SAVE)


class SavedMainMenuTests(unittest.TestCase):
    def test_scope_is_only_normal_savequit_main_menu(self):
        self.assertTrue(saved_main_menu_visual_allowed(STEP))
        for key, value in (('name', 'reopen-save'), ('confirm_save_visually', False),
                           ('expect_scene', 'SceneGame'), ('expect_menu_state', 4),
                           ('checkpoint', 'resume')):
            self.assertFalse(saved_main_menu_visual_allowed({**STEP, key: value}))

    def test_readonly_stat_retains_only_named_save_size_and_epoch(self):
        android = Android(Path('/unused-sdk'), Path('/unused-output'))
        with patch.object(android, 'shell', return_value=(
                '/data/data/package/files/sim3dat0:2562:100\n'
                '/data/data/package/files/sim3set:90:100\n'
                '/private/other:500:100\nstat: sim3dat0: No such file\n')) as shell:
            self.assertEqual(android.save_fingerprints(), SAVE)
        self.assertEqual(shell.call_args.args[:3], ('stat', '-c', '%n:%s:%Y'))

    def test_stable_real_menu_evidence_keeps_original_sample(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = SaveAndroid(Path(temporary))
            with patch('android_runtime_visual.analyze_context_menu', return_value=MENU), \
                    patch('android_runtime.time.sleep'):
                evidence = android.observe_saved_main_menu('save', SAVE, '6059', BOUNDS)
            self.assertTrue(evidence['accepted'])
            self.assertEqual(len(evidence['captures']), 2)
            self.assertTrue(all(c['raw_scene'] == 'SceneGame' and c['raw_observer'] == OBSERVER
                                for c in evidence['captures']))
            self.assertEqual(android.latest_native, OBSERVER)
            self.assertEqual(android.events[-1]['scene'], 'SceneGame')

    def test_visual_fallback_rejects_missing_proofs(self):
        cases = ('wrong-menu', 'changed-pid', 'changed-canvas', 'retained-canvas',
                 'not-main', 'no-save-progress', 'missing-save', 'empty-save', 'moving-menu')
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                android = SaveAndroid(Path(temporary))
                menus = [deepcopy(MENU), deepcopy(MENU)]
                if case == 'wrong-menu': menus[0]['kind'] = 'unknown'
                if case == 'changed-pid': android.pid = '9999'
                if case == 'changed-canvas': android.bounds = (0, 0, 1920, 1080)
                if case == 'retained-canvas': android.viewport_source = 'retained last verified native canvas through Android UI'
                if case == 'not-main': android.resumed = False
                if case == 'no-save-progress': android.saves = deepcopy(SAVE)
                if case == 'missing-save': del android.saves['sim3set']
                if case == 'empty-save': android.saves['sim3dat0']['bytes'] = 0
                if case == 'moving-menu': menus[1]['point'][0] += 5
                with patch('android_runtime_visual.analyze_context_menu', side_effect=menus), \
                        patch('android_runtime.time.sleep'):
                    self.assertIsNone(android.observe_saved_main_menu('save', SAVE, '6059', BOUNDS))
                evidence = json.loads((Path(temporary) / 'save-main-menu-visual-00.json').read_text())
                self.assertFalse(evidence['accepted'])

    def test_plan_savequit_uses_verified_capture_and_distinct_scene_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = SaveAndroid(Path(temporary))
            android.saves = deepcopy(SAVE)
            with patch('android_runtime_visual.analyze_context_menu', return_value=MENU), \
                    patch('android_runtime.time.sleep'), redirect_stdout(io.StringIO()):
                checkpoints = android.run_plan({'steps': [STEP], 'coordinate_size': [1920, 1080]}, 'candidate')
            checkpoint = checkpoints['saved-to-menu']
            self.assertEqual(checkpoint['scene'], 'SceneMenu')
            self.assertEqual(checkpoint['menu_state'], 5)
            self.assertEqual(checkpoint['scene_source'], 'visual-main-menu-and-save-mtime')
            self.assertEqual(checkpoint['raw_scene'], 'SceneGame')
            self.assertIsNone(checkpoint['raw_menu_state'])
            self.assertEqual(checkpoint['observer'], OBSERVER)
            self.assertEqual(android.latest_native, OBSERVER)
            self.assertEqual(checkpoint['name'], checkpoint['scene_evidence']['captures'][-1]['capture'])
            persisted = json.loads((Path(temporary) / checkpoint['name'] / 'observation.json').read_text())
            self.assertEqual(persisted, json.loads(json.dumps(checkpoint)))

    def test_other_scene_checkpoint_cannot_use_visual_menu(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = SaveAndroid(Path(temporary))
            def once(label, predicate, timeout, interval=2):
                if not predicate():
                    raise TimeoutError(label)
            with patch.object(android, 'wait_for', side_effect=once), \
                    patch.object(android, 'native_scene', return_value='SceneGame'), \
                    patch.object(android, 'observe_saved_main_menu') as fallback, \
                    patch('android_runtime.time.sleep'), self.assertRaises(TimeoutError):
                android.run_plan({'steps': [{**STEP, 'name': 'other-boundary'}]}, 'candidate')
            fallback.assert_not_called()


if __name__ == '__main__':
    unittest.main()
