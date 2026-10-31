#!/usr/bin/env python3
"""Capture a real Android touch run; no game memory or save data is written.

Only evidence files enter --output. APKs remain in a separate internal directory.
Scene observations come from the application's guarded read-only input observer.
Visible controls and the resulting game scene still require screenshot review.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import time
import xml.etree.ElementTree as ET

PACKAGE = 'io.github.russianranger.s3ce'
LAUNCHER = PACKAGE + '/com.ideaworks3d.thesims3.CompatActivity'
SCENE = re.compile(r'Scene=(SceneMenu|SceneGame)(?:@[^\s]+)?')
MENU = re.compile(r'menuState=(\d+)')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Android:
    def __init__(self, sdk, output):
        self.sdk, self.output = sdk, output
        self.adb_path = str(sdk / 'platform-tools/adb')
        self.serial = 'emulator-5554'
        self.events = []
        self.latest_native = ''
        self.screen_size = (1920, 1080)

    def adb(self, *args, timeout=45, check=True):
        result = subprocess.run([self.adb_path, '-s', self.serial, *map(str, args)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError(f'adb {args[:3]} failed: {result.stderr.decode(errors="replace")[-1500:]}')
        return result.stdout

    def shell(self, *args, **kwargs):
        return self.adb('shell', *args, **kwargs).decode(errors='replace')

    def wait_for(self, label, predicate, timeout, interval=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if predicate():
                    print(f'Ready: {label}', flush=True)
                    return
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
            time.sleep(interval)
        raise TimeoutError(f'Timed out waiting for {label}')

    def snapshot(self, label):
        safe = re.sub(r'[^A-Za-z0-9_-]', '-', label)
        directory = self.output / safe
        directory.mkdir(parents=True, exist_ok=True)
        png = self.adb('exec-out', 'screencap', '-p')
        if png[:8] != b'\x89PNG\r\n\x1a\n':
            raise RuntimeError('screencap did not return PNG')
        self.screen_size = struct.unpack('>II', png[16:24])
        (directory / 'screen.png').write_bytes(png)
        (directory / 'logcat.txt').write_bytes(self.adb('logcat', '-d', '-v', 'threadtime'))
        try:
            self.shell('uiautomator', 'dump', '/data/local/tmp/s3ce-window.xml', timeout=15, check=False)
            hierarchy = self.adb('exec-out', 'cat', '/data/local/tmp/s3ce-window.xml', check=False)
        except subprocess.TimeoutExpired:
            hierarchy = b'<!-- UI hierarchy unavailable: animated native surface did not idle. -->\n'
        (directory / 'hierarchy.xml').write_bytes(hierarchy)
        (directory / 'activity.txt').write_text(self.shell('dumpsys', 'activity', 'activities', check=False))
        (directory / 'app-files.txt').write_text(self.shell('ls', '-lR', f'/data/data/{PACKAGE}/files', check=False))
        self.latest_native = self.shell('cat', f'/data/data/{PACKAGE}/files/compat-native.log', check=False)
        (directory / 'native.log').write_text(self.latest_native)
        observers = [line for line in self.latest_native.splitlines() if SCENE.search(line)]
        event = {'name': label, 'time': time.time(), 'screen_size': list(self.screen_size),
                 'scene': self.last_scene(), 'menu_state': self.last_menu_state(),
                 'game_pid': self.shell('pidof', PACKAGE, check=False).strip(),
                 'observer': observers[-1] if observers else None}
        self.events.append(event)
        (directory / 'observation.json').write_text(json.dumps(event, indent=2) + '\n')
        print(json.dumps(event), flush=True)
        return hierarchy

    def last_scene(self):
        matches = SCENE.findall(self.latest_native)
        return matches[-1] if matches else None

    def last_menu_state(self):
        lines = self.latest_native.splitlines()
        for line in reversed(lines):
            if SCENE.search(line):
                match = MENU.search(line)
                return int(match[1]) if match else None
        return None

    def native_scene(self):
        self.latest_native = self.shell('cat', f'/data/data/{PACKAGE}/files/compat-native.log', check=False)
        return self.last_scene()

    def click_text(self, text, timeout=45):
        def click():
            self.shell('uiautomator', 'dump', '/data/local/tmp/s3ce-launcher.xml', check=False)
            data = self.adb('exec-out', 'cat', '/data/local/tmp/s3ce-launcher.xml', check=False)
            try:
                nodes = ET.fromstring(data).iter('node')
                for node in nodes:
                    if node.get('text', '').lower() == text.lower():
                        values = list(map(int, re.findall(r'\d+', node.get('bounds', ''))))
                        if len(values) == 4:
                            self.shell('input', 'tap', (values[0] + values[2]) // 2,
                                       (values[1] + values[3]) // 2)
                            return True
            except ET.ParseError:
                pass
            return False
        self.wait_for('launcher ' + text, click, timeout)

    def launch(self):
        self.shell('am', 'start', '-W', '-n', LAUNCHER)
        self.click_text('Start game')

    def tap(self, position, coordinate_size):
        x, y = [round(value * actual / expected) for value, actual, expected
                in zip(position, self.screen_size, coordinate_size)]
        self.shell('input', 'tap', x, y)

    def run_plan(self, plan, prefix, limit=None):
        checkpoints = {}
        for index, step in enumerate(plan['steps'][:limit]):
            name = f'{prefix}-{index:02d}-{step["name"]}'
            if step.get('when_menu_state') is not None:
                self.native_scene()
                if self.last_menu_state() not in step['when_menu_state']:
                    print(f'Skipping conditional {name}', flush=True)
                    continue
            if 'tap' in step:
                self.tap(step['tap'], plan['coordinate_size'])
            elif 'swipe' in step:
                x1, y1, x2, y2, duration = step['swipe']
                scaled = [round(v * a / e) for v, a, e in zip(
                    [x1, y1, x2, y2], self.screen_size * 2, plan['coordinate_size'] * 2)]
                self.shell('input', 'swipe', *scaled, duration)
            elif 'text' in step:
                if not re.fullmatch(r'[A-Za-z0-9_%.-]+', step['text']):
                    raise ValueError('Plan text must be shell-safe Android input text')
                self.shell('input', 'text', step['text'])
            elif 'keyevent' in step:
                self.shell('input', 'keyevent', int(step['keyevent']))
            elif step.get('relaunch'):
                self.shell('am', 'force-stop', PACKAGE)
                self.launch()
            time.sleep(step.get('wait', 2))
            # A touch is the observer trigger. Scene checkpoints may poll the
            # observer using a source-selected harmless point, never memory writes.
            if step.get('expect_scene') or step.get('expect_menu_state') is not None:
                expected = step.get('expect_scene')
                expected_menu = step.get('expect_menu_state')
                before_probe = self.latest_native
                def scene_ready():
                    if step.get('probe_tap'):
                        self.tap(step['probe_tap'], plan['coordinate_size'])
                        time.sleep(.3)
                    observed = self.native_scene()
                    matches = (expected is None or observed == expected) and (
                        expected_menu is None or self.last_menu_state() == expected_menu)
                    fresh = not step.get('probe_tap') or self.latest_native != before_probe
                    return matches and fresh
                self.wait_for(name + ' scene/menu observation', scene_ready,
                              step.get('timeout', 90))
            self.snapshot(name)
            if step.get('expect_menu_state') is not None and self.last_menu_state() != step['expect_menu_state']:
                raise RuntimeError(f'{name}: expected menu state {step["expect_menu_state"]}, '
                                   f'observed {self.last_menu_state()}')
            if 'checkpoint' in step:
                checkpoints[step['checkpoint']] = self.events[-1]
        return checkpoints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--avd', required=True)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sdk = Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])
    image = sdk / 'system-images/android-30/google_apis/x86'
    original_size = (image / 'system.img').stat().st_size
    plan = json.loads(args.plan.read_text())
    result = {'status': 'pending', 'candidate_sha256': sha(args.candidate),
              'baseline_sha256': sha(args.baseline), 'git_sha': os.environ.get('GITHUB_SHA'),
              'environment': {}, 'checkpoints': {}, 'visual_review': 'required',
              'gate_passed': False, 'actions': 'Android UI input only; no game-state writes'}
    android = Android(sdk, output)
    emulator = logcat = None
    emulator_log = (output / 'emulator.txt').open('wb')
    try:
        command = [str(sdk / 'emulator/emulator'), '-avd', args.avd, '-port', '5554',
                   '-accel', 'on', '-gpu', 'swiftshader', '-no-window', '-no-audio',
                   '-no-boot-anim', '-no-snapshot', '-skip-adb-auth', '-memory', '3072',
                   '-cores', '4', '-feature', '-Vulkan,DynamicPartition', '-show-kernel',
                   '-partition-size', str(math.ceil(original_size / 1048576))]
        result['environment']['emulator_command'] = command
        result['environment']['emulator_version'] = subprocess.check_output(
            [str(sdk / 'emulator/emulator'), '-no-window', '-version'], text=True)
        result['environment']['image_properties'] = (image / 'source.properties').read_text()
        result['environment']['system_image_bytes'] = original_size
        result['environment']['system_image_sha256'] = sha(image / 'system.img')
        build_tools = sdk / 'build-tools/35.0.0'
        for label, apk in [('baseline', args.baseline), ('candidate', args.candidate)]:
            signature = subprocess.check_output(
                [str(build_tools / 'apksigner'), 'verify', '--verbose', '--print-certs', str(apk)], text=True)
            badging = subprocess.check_output([str(build_tools / 'aapt'), 'dump', 'badging', str(apk)], text=True)
            (output / f'{label}-signature.txt').write_text(signature)
            (output / f'{label}-identity.txt').write_text(badging)
            if '3c3d5fdfb1db4082e7e488773c2d59cd56ad77c4bfc0aa2e66076e988f02a0c4' not in signature:
                raise RuntimeError(label + ' signing identity changed')
            if f"name='{PACKAGE}'" not in badging or "native-code: 'armeabi-v7a'" not in badging:
                raise RuntimeError(label + ' APK package or ABI changed')
        emulator = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=emulator_log,
                                    stderr=subprocess.STDOUT)
        android.wait_for('Android boot', lambda: android.shell('getprop', 'sys.boot_completed').strip() == '1', 600)
        android.wait_for('PackageManager', lambda: 'package:' in android.shell('pm', 'path', 'android'), 120)
        android.adb('root', check=False)
        android.adb('wait-for-device', timeout=90)
        android.shell('settings', 'put', 'system', 'accelerometer_rotation', '0')
        android.shell('settings', 'put', 'system', 'user_rotation', '1')
        android.shell('settings', 'put', 'global', 'window_animation_scale', '0')
        android.shell('settings', 'put', 'global', 'transition_animation_scale', '0')
        android.shell('settings', 'put', 'global', 'animator_duration_scale', '0')
        android.shell('input', 'keyevent', '82')
        result['environment']['abi_list'] = android.shell('getprop', 'ro.product.cpu.abilist').strip()
        result['environment']['native_bridge'] = android.shell('getprop', 'ro.dalvik.vm.native.bridge').strip()
        result['environment']['page_size'] = android.shell('getconf', 'PAGE_SIZE').strip()
        result['environment']['kernel'] = android.shell('uname', '-a').strip()
        if 'armeabi-v7a' not in result['environment']['abi_list']:
            raise RuntimeError('Android image does not expose required ARMv7 ABI')
        if result['environment']['page_size'] != '4096':
            raise RuntimeError('Candidate requires 4096-byte pages')
        if (image / 'system.img').stat().st_size != original_size:
            raise RuntimeError('Emulator resized GPT system image')
        for label, apk in [('baseline', args.baseline), ('candidate', args.candidate)]:
            android.adb('uninstall', PACKAGE, check=False)
            android.adb('logcat', '-c')
            android.adb('install', '-r', '-d', apk.resolve(), timeout=120)
            android.launch()
            time.sleep(plan.get('launch_wait', 20))
            android.snapshot(label + '-00-launched')
            if label == 'baseline':
                try:
                    android.run_plan(plan, label, limit=plan.get('baseline_steps', 3))
                except Exception as error:
                    result['baseline_observation'] = str(error)
                    android.snapshot('baseline-final')
                android.shell('am', 'force-stop', PACKAGE)
            else:
                result['checkpoints'] = android.run_plan(plan, label)
                result['events'] = android.events
                for checkpoint in ['gameplay', 'resume']:
                    observation = result['checkpoints'].get(checkpoint, {})
                    if observation.get('scene') != 'SceneGame' or not observation.get('game_pid'):
                        raise RuntimeError('No observed real SceneGame at ' + checkpoint)
                result['status'] = 'runtime-progression-observed-awaiting-visual-review'
        android.snapshot('candidate-final')
    except Exception as error:
        result['status'] = 'blocked'
        result['error'] = type(error).__name__ + ': ' + str(error)
        try:
            android.snapshot('failure')
        except Exception as capture_error:
            result['capture_error'] = str(capture_error)
        raise
    finally:
        result['events'] = android.events
        (output / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
        if emulator is not None:
            emulator.terminate()
            try:
                emulator.wait(timeout=15)
            except subprocess.TimeoutExpired:
                emulator.kill()
                emulator.wait()
        emulator_log.close()


if __name__ == '__main__':
    main()
