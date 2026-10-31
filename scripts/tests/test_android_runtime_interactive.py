"""Synthetic protocol tests only; no Android process or game state is accessed."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from android_runtime import Android, CONTROL_URL, sha


class FakeAndroid(Android):
    def __init__(self, output):
        super().__init__(Path('/unused-sdk'), output)
        self.taps = []
        self.quit_checked = False
        self.viewport = (0, 0, 1920, 1080)

    def snapshot(self, label):
        directory = self.output / label
        directory.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (1920, 1080)).save(directory / 'screen.png')
        (directory / 'logcat.txt').write_text('')
        (directory / 'activity.txt').write_text('mResumedActivity: test Main\n')
        self.events.append({'scene': 'SceneGame', 'menu_state': None, 'game_pid': 'test-pid'})

    def tap_visible_point(self, point):
        self.taps.append(point)

    def verify_native_quit(self, prefix):
        self.quit_checked = True


class InteractiveProtocolTests(unittest.TestCase):
    def test_stale_and_wrong_frame_never_execute_and_finish_calls_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            android = FakeAndroid(Path(temporary))
            responses = 0
            accepted = None

            def response(request, timeout):
                nonlocal responses, accepted
                self.assertTrue(request.full_url.startswith(CONTROL_URL + '?t='))
                self.assertFalse(request.has_header('Authorization'))
                frame = android.interactive_observation['frames'][-1]
                document = {'schema': 1, 'run_id': '123', 'seq': frame['seq'],
                            'frame_sha256': frame['frame_sha256'], 'coordinate_size': [1920, 1080],
                            'command': {'type': 'tap', 'x': 1000, 'y': 500}}
                responses += 1
                if responses == 1:
                    document['run_id'] = '0'
                elif responses == 2:
                    document['frame_sha256'] = '0' * 64
                elif responses == 3:
                    accepted = document.copy()
                elif responses == 4:
                    document = accepted
                else:
                    document['command'] = {'type': 'finish'}
                return io.BytesIO(json.dumps(document).encode())

            with patch('android_runtime.urllib.request.urlopen', side_effect=response), patch('android_runtime.time.sleep'):
                android.interactive_loop('123', max_commands=3)
            self.assertEqual(android.taps, [[1000, 500]])
            self.assertTrue(android.quit_checked)
            self.assertTrue(android.interactive_observation['finish_requested'])
            self.assertEqual(len(android.interactive_observation['frames']), 2)
            self.assertEqual([c['command']['type'] for c in android.interactive_observation['commands']], ['tap', 'finish'])
            frame = Path(temporary) / 'live/frame-000'
            metadata = json.loads((frame / 'frame.json').read_text())
            self.assertEqual(metadata['frame_sha256'], sha(frame / 'screen.png'))
            self.assertEqual(metadata['coordinate_size'], [1920, 1080])
            self.assertFalse(list(Path(temporary).rglob('*.tmp')))

    def test_frame_wait_and_final_exit_preserve_controller_status(self):
        script = Path(__file__).resolve().parents[1] / 'android_runtime_frame.py'
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            live = output / 'live'
            frame = live / 'frame-000'
            frame.mkdir(parents=True)
            (frame / 'screen.png').write_bytes(b'fixture')
            (frame / 'frame.json').write_text('{}')
            (live / 'ready-000.json').write_text('{"seq":1}')
            github_output = output / 'outputs'
            environment = {**os.environ, 'GITHUB_OUTPUT': str(github_output)}
            result = subprocess.run([sys.executable, str(script), '--output', str(output), '--frame', '0', '--timeout', '1'],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('available=true', github_output.read_text())
            (live / 'controller-exit.json').write_text('{"status":"blocked","exit_code":1}')
            result = subprocess.run([sys.executable, str(script), '--output', str(output), '--frame', '1', '--timeout', '1'],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('available=false', github_output.read_text())
            result = subprocess.run([sys.executable, str(script), '--output', str(output), '--finish', '--timeout', '1'],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)


if __name__ == '__main__':
    unittest.main()
