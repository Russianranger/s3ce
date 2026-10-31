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
BOUNDS = re.compile(r'\[(-?\d+),\s*(-?\d+)\]\[(-?\d+),\s*(-?\d+)\]')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def game_viewport(hierarchy, windows):
    """Prefer the actual native view; otherwise use its fullscreen Main window."""
    candidates = []
    try:
        for node in ET.fromstring(hierarchy).iter('node'):
            name = node.get('class', '')
            if node.get('package', PACKAGE) == PACKAGE and ('SurfaceView' in name or 'AirplayView' in name):
                match = BOUNDS.fullmatch(node.get('bounds', ''))
                if match:
                    bounds = tuple(map(int, match.groups()))
                    if valid_native_canvas(bounds):
                        candidates.append(bounds)
    except ET.ParseError:
        pass
    if candidates:
        return max(candidates, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])), 'SurfaceView hierarchy'
    frames = []
    for section in re.split(r'(?=\n\s*Window #\d+ Window\{)', windows):
        heading = section.splitlines()[0:2]
        if not any('com.ideaworks3d.thesims3.Main}' in line for line in heading):
            continue
        match = re.search(r'(?:mFrame=|\bframe=)(\[-?\d+,\s*-?\d+\]\[-?\d+,\s*-?\d+\])', section)
        if match:
            bounds = tuple(map(int, BOUNDS.fullmatch(match[1]).groups()))
            if valid_native_canvas(bounds):
                base = 'ty=BASE_APPLICATION' in section
                frames.append((base, (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]), bounds))
    if frames:
        base, _, bounds = max(frames)
        return bounds, 'Main BASE_APPLICATION frame' if base else 'largest Main native frame'
    return None, None


def valid_native_canvas(bounds):
    left, top, right, bottom = bounds
    return right > left and bottom > top and abs((right - left) / (bottom - top) - 16 / 9) <= .002


def keyboard_is_visible(windows):
    for section in re.split(r'(?=\n\s*Window #\d+ Window\{)', windows):
        if any(re.search(r'\bu\d+ InputMethod\}', line) for line in section.splitlines()[:2]):
            return ('mViewVisibility=0x0' in section and 'mHasSurface=true' in section
                    and 'isReadyForDisplay()=true' in section)
    return False


class Android:
    def __init__(self, sdk, output):
        self.sdk, self.output = sdk, output
        self.adb_path = str(sdk / 'platform-tools/adb')
        self.serial = 'emulator-5554'
        self.events = []
        self.latest_native = ''
        self.screen_size = (1920, 1080)
        self.viewport, self.viewport_source = None, None

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
            self.shell('uiautomator', 'dump', '/data/local/tmp/s3ce-window.xml', timeout=5, check=False)
            hierarchy = self.adb('exec-out', 'cat', '/data/local/tmp/s3ce-window.xml', check=False)
        except subprocess.TimeoutExpired:
            hierarchy = b'<!-- UI hierarchy unavailable: animated native surface did not idle. -->\n'
        (directory / 'hierarchy.xml').write_bytes(hierarchy)
        windows = self.shell('dumpsys', 'window', 'windows', check=False)
        (directory / 'windows.txt').write_text(windows)
        observed_viewport, observed_source = game_viewport(hierarchy, windows)
        if observed_viewport is not None:
            self.viewport, self.viewport_source = observed_viewport, observed_source
        elif self.viewport is not None:
            self.viewport_source = 'retained last verified native canvas through Android UI'
        (directory / 'activity.txt').write_text(self.shell('dumpsys', 'activity', 'activities', check=False))
        (directory / 'app-files.txt').write_text(self.shell('ls', '-lR', f'/data/data/{PACKAGE}/files', check=False))
        self.latest_native = self.shell('cat', f'/data/data/{PACKAGE}/files/compat-native.log', check=False)
        (directory / 'native.log').write_text(self.latest_native)
        observers = [line for line in self.latest_native.splitlines() if SCENE.search(line)]
        event = {'name': label, 'time': time.time(), 'screen_size': list(self.screen_size),
                 'scene': self.last_scene(), 'menu_state': self.last_menu_state(),
                 'native_viewport': self.viewport, 'viewport_source': self.viewport_source,
                 'keyboard_visible': keyboard_is_visible(windows),
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
        self.assert_native_canvas()
        x, y = self.coordinates(position, coordinate_size)
        self.shell('input', 'tap', x, y)

    def assert_native_canvas(self):
        if self.viewport is None or not valid_native_canvas(self.viewport):
            raise RuntimeError('Native input requires a verified 16:9 game canvas')
        if not self.shell('pidof', PACKAGE, check=False).strip():
            raise RuntimeError('Native input requires a live game process')

    def hide_keyboard(self):
        if keyboard_is_visible(self.shell('dumpsys', 'window', 'windows')):
            self.shell('input', 'keyevent', 4)
            self.wait_for('visible keyboard to hide',
                          lambda: not keyboard_is_visible(self.shell('dumpsys', 'window', 'windows')),
                          15, interval=1)

    def coordinates(self, position, coordinate_size):
        left, top, right, bottom = self.viewport or (0, 0, *self.screen_size)
        return (round(left + position[0] * (right - left) / coordinate_size[0]),
                round(top + position[1] * (bottom - top) / coordinate_size[1]))

    def swipe(self, values, coordinate_size):
        self.assert_native_canvas()
        x1, y1, x2, y2, duration = values
        scaled = [*self.coordinates([x1, y1], coordinate_size),
                  *self.coordinates([x2, y2], coordinate_size)]
        self.shell('input', 'swipe', *scaled, duration)

    def select_traits_visually(self, prefix, targets, max_scrolls=12):
        from android_runtime_visual import analyze_traits
        chosen = set()
        sequence = 0

        def inspect(suffix):
            nonlocal sequence
            name = f'{prefix}-visual-{sequence:02d}-{suffix}'
            sequence += 1
            self.snapshot(name)
            directory = self.output / re.sub(r'[^A-Za-z0-9_-]', '-', name)
            observation = analyze_traits(directory / 'screen.png', directory / 'trait-ocr', self.viewport)
            print(json.dumps({'visual_traits': name, **{key: observation[key]
                              for key in ('selected_count', 'next_visible', 'matches')}}), flush=True)
            return observation

        observation = inspect('initial')
        if observation['selected_count'] != 2:
            raise RuntimeError('Visual trait selection requires the two initial compatible checks')
        for attempt in range(max_scrolls + 1):
            for target in targets:
                row = observation['matches'].get(target)
                if target in chosen or row is None:
                    continue
                if not row['checked']:
                    previous_count = observation['selected_count']
                    x = self.coordinates([1449, 0], [1920, 1080])[0]
                    self.assert_native_canvas()
                    self.shell('input', 'tap', x, round(row['center_y']))
                    time.sleep(1)
                    after = inspect('selected-' + target)
                    checked = after['matches'].get(target, {}).get('checked')
                    if not checked or after['selected_count'] != previous_count + 1:
                        raise RuntimeError(f'Visible checkbox/count did not confirm selecting {target}')
                    observation = after
                chosen.add(target)
            if chosen == set(targets):
                if observation['selected_count'] != 5 or not observation['next_visible']:
                    raise RuntimeError('All desired trait labels were chosen without five checks and Next')
                return
            if attempt == max_scrolls:
                break
            self.swipe([1449, 800, 1449, 300, 1000], [1920, 1080])
            time.sleep(1.5)
            observation = inspect(f'scrolled-{attempt + 1}')
        raise RuntimeError('Visual trait selection did not find all desired rows: ' + ', '.join(set(targets) - chosen))

    def run_plan(self, plan, prefix, limit=None):
        checkpoints = {}
        for index, step in enumerate(plan['steps'][:limit]):
            name = f'{prefix}-{index:02d}-{step["name"]}'
            previous_pid = next((event['game_pid'] for event in reversed(self.events) if event.get('game_pid')), None)
            if step.get('when_menu_state') is not None:
                self.native_scene()
                if self.last_menu_state() not in step['when_menu_state']:
                    print(f'Skipping conditional {name}', flush=True)
                    continue
            if 'tap' in step:
                self.tap(step['tap'], plan['coordinate_size'])
            elif 'swipe' in step:
                self.swipe(step['swipe'], plan['coordinate_size'])
            elif 'text' in step:
                if not re.fullmatch(r'[A-Za-z0-9_%.-]+', step['text']):
                    raise ValueError('Plan text must be shell-safe Android input text')
                self.shell('input', 'text', step['text'])
            elif 'keyevent' in step:
                self.shell('input', 'keyevent', int(step['keyevent']))
            elif 'click_text' in step:
                self.click_text(step['click_text'], timeout=step.get('timeout', 45))
            elif 'select_traits' in step:
                self.select_traits_visually(name, step['select_traits'], step.get('max_scrolls', 12))
            elif step.get('hide_keyboard'):
                self.hide_keyboard()
            elif step.get('relaunch'):
                self.shell('am', 'force-stop', PACKAGE)
                self.launch()
            elif step.get('reopen'):
                self.launch()
            time.sleep(step.get('wait', 2))
            # A touch is the observer trigger. Scene checkpoints may poll the
            # observer using a source-selected harmless point, never memory writes.
            if step.get('expect_scene') or step.get('expect_menu_state') is not None:
                expected = step.get('expect_scene')
                expected_menu = step.get('expect_menu_state')
                before_probe = self.latest_native
                def scene_ready():
                    if step.get('probe_swipe'):
                        self.swipe(step['probe_swipe'], plan['coordinate_size'])
                        if step.get('probe_return'):
                            x1, y1, x2, y2, duration = step['probe_swipe']
                            self.swipe([x2, y2, x1, y1, duration], plan['coordinate_size'])
                        time.sleep(.3)
                    elif step.get('probe_tap'):
                        self.tap(step['probe_tap'], plan['coordinate_size'])
                        time.sleep(.3)
                    observed = self.native_scene()
                    matches = (expected is None or observed == expected) and (
                        expected_menu is None or self.last_menu_state() == expected_menu)
                    fresh = not (step.get('probe_tap') or step.get('probe_swipe')) or self.latest_native != before_probe
                    return matches and fresh
                self.wait_for(name + ' scene/menu observation', scene_ready,
                              step.get('timeout', 90), interval=step.get('probe_interval', 2))
            self.snapshot(name)
            if step.get('expect_same_pid') and (not previous_pid or self.events[-1]['game_pid'] != previous_pid):
                raise RuntimeError(f'{name}: game process changed across Home/reopen')
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
    emulator_dir = Path(os.environ.get('S3CE_EMULATOR_DIR', sdk / 'emulator'))
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
        command = [str(emulator_dir / 'emulator'), '-avd', args.avd, '-port', '5554',
                   '-accel', 'on', '-gpu', os.environ.get('S3CE_GPU_MODE', 'swiftshader'), '-no-window', '-no-audio',
                   '-no-boot-anim', '-no-snapshot', '-skip-adb-auth', '-verbose', '-memory', '3072',
                   '-cores', '4', '-feature', '-Vulkan,DynamicPartition', '-show-kernel',
                   '-prop', 'qemu.hw.mainkeys=1',
                   '-partition-size', str(math.ceil(original_size / 1048576))]
        result['environment']['emulator_command'] = command
        result['environment']['emulator_version'] = subprocess.check_output(
            [str(emulator_dir / 'emulator'), '-no-window', '-version'], text=True)
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
        def boot_ready():
            if emulator.poll() is not None:
                raise ChildProcessError('Emulator exited during boot with status ' + str(emulator.returncode))
            return android.shell('getprop', 'sys.boot_completed').strip() == '1'
        android.wait_for('Android boot', boot_ready, 600)
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
        live_log = (output / 'logcat-live.txt').open('wb')
        logcat = subprocess.Popen([android.adb_path, '-s', android.serial, 'logcat', '-v', 'threadtime'],
                                  stdin=subprocess.DEVNULL, stdout=live_log, stderr=subprocess.STDOUT)
        variants = [('baseline', args.baseline), ('candidate', args.candidate)] if plan.get('run_baseline', True) else [('candidate', args.candidate)]
        for label, apk in variants:
            android.adb('uninstall', PACKAGE, check=False)
            # Diagnostic clearing is best effort; the live stream and fresh
            # installation delimit this run even when logd rejects a clear.
            android.adb('logcat', '-c', check=False)
            android.adb('install', '-r', '-d', apk.resolve(), timeout=120)
            android.launch()
            time.sleep(plan.get('launch_wait', 20))
            android.snapshot(label + '-00-launched')
            result['environment'][label + '_native_viewport'] = android.viewport
            if android.viewport is None:
                raise RuntimeError('Cannot establish native SurfaceView/Main window bounds')
            left, top, right, bottom = android.viewport
            expected_width, expected_height = plan['coordinate_size']
            if abs((right - left) / (bottom - top) - expected_width / expected_height) > .002:
                raise RuntimeError('Native viewport aspect ratio differs from source-proven touch plan')
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
        result['environment']['emulator_exit_before_cleanup'] = emulator.poll() if emulator else None
        result['environment']['live_logcat_exit_before_cleanup'] = logcat.poll() if logcat else None
        for name, command in [('host-kernel.txt', ['dmesg', '-T']),
                              ('host-memory.txt', ['cat', '/proc/meminfo']),
                              ('host-memory-events.txt', ['cat', '/sys/fs/cgroup/memory.events'])]:
            try:
                state = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
                (output / name).write_bytes(state.stdout)
            except (OSError, subprocess.TimeoutExpired):
                pass
        (output / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
        if emulator is not None:
            emulator.terminate()
            try:
                emulator.wait(timeout=15)
            except subprocess.TimeoutExpired:
                emulator.kill()
                emulator.wait()
        if logcat is not None:
            logcat.terminate()
            try:
                logcat.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logcat.kill()
                logcat.wait()
            live_log.close()
        emulator_log.close()


if __name__ == '__main__':
    main()
