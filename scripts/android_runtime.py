#!/usr/bin/env python3
"""Capture a real Android touch run; no game memory or save data is written.

Only evidence files enter --output. APKs remain in a separate internal directory.
Scene observations come from the application's guarded read-only input observer.
Visible controls and the resulting game scene still require screenshot review.
"""
import argparse
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import time
import shutil
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from android_runtime_control import MAX_INTERACTIVE_COMMANDS

PACKAGE = 'io.github.russianranger.s3ce'
LAUNCHER = PACKAGE + '/com.ideaworks3d.thesims3.CompatActivity'
SCENE = re.compile(r'Scene=(SceneMenu|SceneGame)(?:@[^\s]+)?')
MENU = re.compile(r'menuState=(\d+)')
BOUNDS = re.compile(r'\[(-?\d+),\s*(-?\d+)\]\[(-?\d+),\s*(-?\d+)\]')
CONTROL_URL = 'https://raw.githubusercontent.com/Russianranger/s3ce/qa/object-actions-ui/.validation/runtime-control.json'
CONTROL_CONTENTS_URL = 'https://api.github.com/repos/Russianranger/s3ce/contents/.validation/runtime-control.json?ref=qa%2Fobject-actions-ui'


def fetch_control_document():
    """Read the fixed QA document without exposing the optional read-only token."""
    from android_runtime_control import ControlError, MAX_DOCUMENT_BYTES
    token = os.environ.get('S3CE_CONTROL_GITHUB_TOKEN')
    headers = {'Cache-Control': 'no-cache', 'User-Agent': 'S3CE-runtime-validation'}
    if not token:
        request = urllib.request.Request(CONTROL_URL + '?t=' + str(time.time_ns()), headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read(MAX_DOCUMENT_BYTES + 1)
    headers.update({'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28'})
    request = urllib.request.Request(CONTROL_CONTENTS_URL + '&t=' + str(time.time_ns()), headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read(MAX_DOCUMENT_BYTES * 4 + 1)
    if len(data) > MAX_DOCUMENT_BYTES * 4:
        raise ControlError('GitHub Contents response exceeds its bounded size')
    try:
        content = json.loads(data)
        if content.get('encoding') != 'base64' or type(content.get('content')) is not str:
            raise ValueError('encoding')
        raw = base64.b64decode(''.join(content['content'].split()), validate=True)
    except (ValueError, TypeError, AttributeError, binascii.Error) as error:
        raise ControlError('GitHub Contents response is not a base64 control file') from error
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ControlError('Decoded GitHub control exceeds its bounded size')
    return raw


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plan_execution_scope(plan, interactive, interactive_after):
    """Bound unattended smoke runs without changing the normal input prefix."""
    endpoint = interactive_after if interactive else plan.get('automated_stop_after')
    mode = 'frame-guided' if interactive else 'automated-prefix' if endpoint else 'automated-full-plan'
    if endpoint is None:
        return {'mode': mode, 'endpoint': None, 'limit': None}
    matches = [index for index, step in enumerate(plan['steps']) if step['name'] == endpoint]
    if len(matches) != 1:
        raise ValueError('Runtime prefix endpoint is missing or ambiguous: ' + str(endpoint))
    return {'mode': mode, 'endpoint': endpoint, 'limit': matches[0] + 1}


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
        self.checkpoints = {}
        self.object_actions = []
        self.quit_observation = {}
        self.interactive_observation = {'commands': [], 'frames': [], 'finish_requested': False}
        self.cold_starts = []
        self.runtime_started = time.monotonic()

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
        # Only named diagnostics are collected; game saves are never copied or
        # edited. Older baseline builds may not contain session rotation yet.
        for filename in ('compat-session.log', 'compat-boot.log', 'compat-events.log',
                         'compat-java-gl.log', 'compat-java-crash.log'):
            (directory / filename).write_text(self.shell(
                'cat', f'/data/data/{PACKAGE}/files/{filename}', check=False))
        (directory / 'session-diagnostic-pull.txt').write_bytes(self.adb(
            'pull', f'/data/data/{PACKAGE}/files/compat-sessions',
            str(directory / 'previous-sessions'), check=False))
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

    def observe_cold_starts(self, attempts, launch_wait):
        """Observe every bounded normal startup; preserve data and every failure.

        Readiness is a process/window observation, not visual gameplay acceptance.
        A log marker bounds each attempt without deleting earlier logcat records.
        The final successful attempt stays in the main menu for the normal plan.
        """
        if type(attempts) is not int or not 1 <= attempts <= 6:
            raise ValueError('Cold-start observation requires 1 through 6 attempts')
        seen_pids = set()
        for index in range(attempts):
            label = f'candidate-cold-start-{index + 1:02d}'
            marker = f'S3CE-cold-start-{index + 1}-{time.time_ns()}'
            record = {'attempt': index + 1, 'marker': marker, 'start_epoch': time.time(),
                      'status': 'failed', 'visual_review': 'required',
                      'scope': 'normal launcher/Start; process-cold; app data retained'}
            self.cold_starts.append(record)
            self.viewport = self.viewport_source = None
            try:
                self.shell('log', '-t', 'S3CEColdStart', marker)
                self.shell('am', 'force-stop', PACKAGE)
                self.wait_for('previous game process stopped',
                              lambda: not self.shell('pidof', PACKAGE, check=False).strip(), 15)
                self.launch()
                time.sleep(launch_wait)
                self.snapshot(label)
                directory = self.output / label
                event = self.events[-1]
                record.update(game_pid=event.get('game_pid'), native_viewport=self.viewport,
                              viewport_source=self.viewport_source,
                              screenshot_sha256=sha(directory / 'screen.png'))
                log = (directory / 'logcat.txt').read_text(errors='replace')
                if marker not in log:
                    raise RuntimeError('Attempt log marker is missing; log window is unknown')
                attempt_log = log.partition(marker)[2]
                (directory / 'attempt-logcat.txt').write_text(attempt_log)
                fatal = [line for line in attempt_log.splitlines()
                         if re.search(r'Fatal signal|FATAL EXCEPTION|SIGSEGV|SIGABRT|ANR in|am_crash|am_anr', line)]
                record['fatal_or_anr_lines'] = fatal
                activity = (directory / 'activity.txt').read_text(errors='replace')
                resumed = [line.strip() for line in activity.splitlines()
                           if 'mResumedActivity' in line or 'topResumedActivity' in line]
                record['resumed_activity_lines'] = resumed
                pid = record['game_pid']
                if not pid or pid in seen_pids:
                    raise RuntimeError('No distinct live game process after cold start')
                seen_pids.add(pid)
                if (self.viewport is None or not any('com.ideaworks3d.thesims3.Main' in line
                                                     for line in resumed)):
                    raise RuntimeError('No verified native game canvas and resumed Main activity')
                if fatal:
                    raise RuntimeError('Fatal/ANR evidence in this startup window')
                record['status'] = 'ready-awaiting-visual-review'
            except Exception as error:
                record['error'] = type(error).__name__ + ': ' + str(error)
                # Even a launch failure before the normal snapshot must remain
                # reviewable. A capture failure is recorded, never substituted.
                if not (self.output / label / 'screen.png').exists():
                    try:
                        self.snapshot(label)
                    except Exception as capture_error:
                        record['capture_error'] = str(capture_error)
            finally:
                record['end_epoch'] = time.time()
                (self.output / 'cold-start-attempts.json').write_text(
                    json.dumps(self.cold_starts, indent=2) + '\n')
        failures = sum(record['status'] == 'failed' for record in self.cold_starts)
        if failures:
            raise RuntimeError(f'{failures} of {attempts} process-cold startup observations failed; all retained')

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

    def gameplay_overlay(self, name):
        from android_runtime_visual import analyze_gameplay_overlay
        self.snapshot(name)
        directory = self.output / re.sub(r'[^A-Za-z0-9_-]', '-', name)
        overlay = analyze_gameplay_overlay(directory / 'screen.png', directory / 'overlay-ocr', self.viewport)
        print(json.dumps({'gameplay_overlay': name, 'kind': overlay['kind'],
                          'point': overlay['point'], 'text': overlay['text']}), flush=True)
        return overlay

    def tap_visible_point(self, point):
        self.assert_native_canvas()
        self.shell('input', 'tap', *[round(value) for value in point])

    def clear_gameplay_overlays(self, prefix, open_pause=False):
        clear_frames = 0
        for attempt in range(10):
            overlay = self.gameplay_overlay(f'{prefix}-overlay-{attempt:02d}')
            kind = overlay['kind']
            if kind in ('new-wish', 'recipes', 'edit-appearance'):
                self.tap_visible_point(overlay['point'])
                clear_frames = 0
            elif kind == 'pause-menu':
                if open_pause:
                    return
                raise RuntimeError('Unexpected pause menu while clearing onboarding dialogs')
            elif kind == 'none':
                if open_pause:
                    self.tap([113, 965], [1920, 1080])
                else:
                    clear_frames += 1
                    if clear_frames >= 2:
                        return
            else:
                # A panel may be between its 400ms animation and text draw.
                # Unknown dialogs are never dismissed by guessed coordinates.
                clear_frames = 0
            time.sleep(2)
        raise RuntimeError('Known onboarding dialogs did not settle into ' + ('Paused menu' if open_pause else 'unobstructed gameplay'))

    def choose_save_visually(self, prefix, confirmation=False):
        expected = 'save-confirmation' if confirmation else 'pause-menu'
        overlay = self.gameplay_overlay(prefix + '-verified')
        if overlay['kind'] != expected:
            raise RuntimeError(f'Expected visible {expected}, observed {overlay["kind"]}')
        self.tap_visible_point(overlay['point'])

    def context_menu(self, name):
        from android_runtime_visual import analyze_context_menu
        self.snapshot(name)
        directory = self.output / re.sub(r'[^A-Za-z0-9_-]', '-', name)
        menu = analyze_context_menu(directory / 'screen.png', directory / 'context-ocr', self.viewport)
        print(json.dumps({'context_menu': name, 'title': menu['title']['text'],
                          'actions': [{'text': a['text'], 'point': a['point']} for a in menu['actions']]}), flush=True)
        return menu

    def context_action(self, prefix, config, menu=None):
        from android_runtime_visual import normalized
        menu = menu or self.context_menu(prefix + '-before')
        title = menu['title']['text']
        if not title or (config.get('title') and normalized(title) != normalized(config['title'])):
            raise RuntimeError('Visible context-menu title does not match the intended object')
        options = [a for a in menu['actions'] if normalized(a['text']) == normalized(config['action'])]
        if len(options) != 1:
            raise RuntimeError('Cannot locate exactly one visible ' + config['action'] + ' action')
        point = options[0]['point']
        event = {'name': prefix, 'title': title, 'action': config['action'], 'point': point,
                 'status': 'touch-sent-awaiting-observation', 'captures': [],
                 'completion': 'manual review of queue and Sim pose required'}
        self.object_actions.append(event)
        self.tap_visible_point(point)
        started = time.monotonic()
        for seconds in config.get('capture_seconds', [2, 8, 20, 45]):
            time.sleep(max(0, started + seconds - time.monotonic()))
            elapsed = time.monotonic() - started
            label = f'{prefix}-after-{seconds:02d}s'
            if len(event['captures']) == 0:
                after = self.context_menu(label)
                persisted = (normalized(after['title']['text']) == normalized(title)
                             and any(normalized(a['text']) == normalized(config['action']) for a in after['actions']))
                event['status'] = 'menu-remained' if persisted else 'menu-closed-awaiting-pose-review'
            else:
                self.snapshot(label)
            event['captures'].append({'name': label, 'requested_seconds': seconds,
                                      'elapsed_seconds_at_capture_start': elapsed})
        (self.output / (prefix + '-action-observation.json')).write_text(json.dumps(event, indent=2) + '\n')
        if event['status'] == 'menu-remained':
            raise RuntimeError('Visible action menu remained after tapping its actual action text')

    def find_context_action(self, prefix, config):
        from android_runtime_visual import normalized
        tried = []
        menu = self.context_menu(prefix + '-initial')
        for index, target in enumerate(config['targets']):
            if menu['actions']:
                if not menu['title']['text']:
                    raise RuntimeError('Cannot safely close an unidentified action panel')
                self.tap([254, 142], [1920, 1080])
                time.sleep(1)
            self.tap(target, [1920, 1080])
            time.sleep(2)
            menu = self.context_menu(f'{prefix}-target-{index:02d}')
            tried.append({'target': target, 'title': menu['title']['text'],
                          'actions': [a['text'] for a in menu['actions']]})
            if (menu['title']['text'] and (not config.get('title')
                    or normalized(menu['title']['text']) == normalized(config['title']))
                    and any(normalized(a['text']) == normalized(config['action']) for a in menu['actions'])):
                self.context_action(prefix + '-selected', config, menu)
                return target
        description = config.get('title') or config.get('description', config['action'] + ' object')
        outcome = {'name': prefix, 'title': description, 'action': config['action'],
                   'status': 'object-not-found', 'tried': tried,
                   'completion': 'No action was selected without the required visible title and label'}
        self.object_actions.append(outcome)
        (self.output / (prefix + '-search-observation.json')).write_text(json.dumps(outcome, indent=2) + '\n')
        if config.get('required', True):
            raise RuntimeError('Bounded normal-touch search did not find ' + description)

    def lamp_toggle_cycle(self, prefix, config):
        from android_runtime_visual import normalized
        title = 'Retro Tall Lamp'
        world_point = self.find_context_action(prefix + '-turn-off', {
            'title': title, 'action': 'Turn off', 'targets': config['targets'],
            'capture_seconds': [2, 8], 'required': True})
        cycle = {'name': prefix, 'title': title, 'world_selection_point': world_point,
                 'status': 'awaiting-offered-action-transition', 'state_checks': []}
        self.object_actions.append(cycle)

        def await_offered_action(expected, absent, suffix):
            menu = self.context_menu(prefix + '-' + suffix + '-initial')
            for attempt in range(6):
                if menu['actions']:
                    if not menu['title']['text']:
                        raise RuntimeError('Cannot safely refresh an unidentified action panel')
                    self.tap([254, 142], [1920, 1080])
                    time.sleep(1)
                self.tap(world_point, [1920, 1080])
                time.sleep(3)
                label = f'{prefix}-{suffix}-{attempt:02d}'
                menu = self.context_menu(label)
                actions = {normalized(a['text']) for a in menu['actions']}
                if (normalized(menu['title']['text']) == normalized(title)
                        and normalized(expected) in actions and normalized(absent) not in actions):
                    cycle['state_checks'].append({'capture': label, 'offered_action': expected,
                                                   'absent_action': absent, 'time': time.time()})
                    return menu
                time.sleep(3)
            raise RuntimeError('Lamp action did not produce the expected visible ' + expected + ' state')

        menu = await_offered_action('Turn on', 'Turn off', 'verified-off')
        self.context_action(prefix + '-turn-on', {'title': title, 'action': 'Turn on',
                                                'capture_seconds': [2, 8]}, menu)
        await_offered_action('Turn off', 'Turn on', 'verified-on')
        cycle['status'] = 'off-on-object-state-observed'
        (self.output / (prefix + '-lamp-state-observation.json')).write_text(json.dumps(cycle, indent=2) + '\n')
        self.tap([254, 142], [1920, 1080])

    def close_context_if_visible(self, prefix):
        menu = self.context_menu(prefix + '-before')
        if menu['actions']:
            if not menu['title']['text']:
                raise RuntimeError('Cannot safely close an unidentified action panel')
            self.tap([254, 142], [1920, 1080])

    def main_quit_visually(self, prefix):
        from android_runtime_visual import analyze_context_menu
        self.snapshot(prefix + '-before')
        directory = self.output / (prefix + '-before')
        menu = analyze_context_menu(directory / 'screen.png', directory / 'main-menu-ocr',
                                    self.viewport, layout='main')
        if menu['kind'] != 'main-menu' or not menu['point']:
            raise RuntimeError('Cannot verify visible main-menu Options/Help/Quit controls')
        self.tap_visible_point(menu['point'])

    def confirm_quit_visually(self, prefix):
        dialog = self.gameplay_overlay(prefix + '-before')
        if dialog['kind'] != 'quit-confirmation':
            raise RuntimeError('Cannot verify the normal Quit question and green confirmation')
        self.tap_visible_point(dialog['point'])

    def verify_native_quit(self, prefix):
        def finished():
            logs = self.adb('logcat', '-d', '-v', 'threadtime').decode(errors='replace')
            activity = self.shell('dumpsys', 'activity', 'activities', check=False)
            resumed = [line.strip() for line in activity.splitlines()
                       if 'mResumedActivity' in line or 'topResumedActivity' in line]
            self.quit_observation = {
                'native_main_returned': bool(re.search(r'Native code done\.\s+Shutting down', logs)),
                'activity_finish_requested': 'calling finish on activity' in logs,
                'resumed_activity_lines': resumed,
                'game_main_resumed': any('com.ideaworks3d.thesims3.Main' in line for line in resumed),
                'compat_launcher_resumed': any('com.ideaworks3d.thesims3.CompatActivity' in line for line in resumed),
                'retained_package_pid': self.shell('pidof', PACKAGE, check=False).strip(),
                'fatal_or_anr_lines': [line for line in logs.splitlines()
                                      if re.search(r'Fatal signal|FATAL EXCEPTION|SIGSEGV|SIGABRT|ANR in|am_crash|am_anr', line)]}
            return (self.quit_observation['native_main_returned']
                    and self.quit_observation['activity_finish_requested'] and resumed
                    and not self.quit_observation['game_main_resumed']
                    and self.quit_observation['compat_launcher_resumed'])
        self.wait_for('native Main returned and game Activity finished', finished, 60)
        time.sleep(2)
        if not finished() or self.quit_observation['fatal_or_anr_lines']:
            raise RuntimeError('Normal native Quit did not finish without fatal/ANR evidence')
        (self.output / (prefix + '-shutdown-observation.json')).write_text(
            json.dumps(self.quit_observation, indent=2) + '\n')

    def interactive_loop(self, run_id, max_commands=MAX_INTERACTIVE_COMMANDS):
        from android_runtime_control import ControlError, validate_control
        if (not re.fullmatch(r'[1-9][0-9]*', run_id) or type(max_commands) is not int
                or not 1 <= max_commands <= MAX_INTERACTIVE_COMMANDS):
            raise ValueError(f'Interactive mode requires a real run ID and at most {MAX_INTERACTIVE_COMMANDS} commands')
        live = self.output / 'live'
        live.mkdir(parents=True, exist_ok=True)
        overall = self.runtime_started + 4500
        if os.environ.get('S3CE_RUNTIME_DEADLINE_EPOCH'):
            overall = min(overall, time.monotonic() + max(0, float(os.environ['S3CE_RUNTIME_DEADLINE_EPOCH']) - time.time()))
        deadline = min(time.monotonic() + 3600, overall)
        seen_rejections = set()
        for frame_index in range(max_commands):
            label = f'live-frame-{frame_index:03d}'
            self.snapshot(label)
            source = self.output / label
            frame = live / f'frame-{frame_index:03d}'
            frame.mkdir(exist_ok=True)
            shutil.copyfile(source / 'screen.png', frame / 'screen.png')
            log = (source / 'logcat.txt').read_text(errors='replace')
            activity = (source / 'activity.txt').read_text(errors='replace')
            observation = self.events[-1]
            metadata = {'schema': 1, 'run_id': run_id, 'frame': frame_index,
                        'seq': frame_index + 1, 'frame_sha256': sha(frame / 'screen.png'),
                        'coordinate_size': list(self.screen_size), 'viewport': self.viewport,
                        'scene': observation['scene'], 'menu_state': observation['menu_state'],
                        'game_pid': observation['game_pid'], 'time': time.time(),
                        'input_observer': observation.get('observer'),
                        'control_transport': 'github-contents-api' if os.environ.get('S3CE_CONTROL_GITHUB_TOKEN') else 'public-raw',
                        'resumed_activity_lines': [line.strip() for line in activity.splitlines()
                                                  if 'mResumedActivity' in line or 'topResumedActivity' in line],
                        'native_main_returned': bool(re.search(r'Native code done\.\s+Shutting down', log)),
                        'activity_finish_requested': 'calling finish on activity' in log,
                        'fatal_or_anr_count': len(re.findall(r'Fatal signal|FATAL EXCEPTION|SIGSEGV|SIGABRT|ANR in|am_crash|am_anr', log))}
            (frame / 'frame.json').write_text(json.dumps(metadata, indent=2) + '\n')
            ready = live / f'ready-{frame_index:03d}.json'
            temporary = ready.with_suffix('.tmp')
            temporary.write_text(json.dumps(metadata, indent=2) + '\n')
            temporary.replace(ready)
            self.interactive_observation['frames'].append(metadata)
            print(json.dumps({'interactive_frame_ready': frame_index, **metadata}), flush=True)
            command = None
            while time.monotonic() < deadline:
                try:
                    raw = fetch_control_document()
                    command = validate_control(raw, run_id, frame_index + 1,
                        metadata['frame_sha256'], self.screen_size, viewport=self.viewport)
                    document = json.loads(raw)
                    break
                except (ControlError, urllib.error.URLError, TimeoutError) as error:
                    rejection = type(error).__name__ + ': ' + str(error)
                    if rejection not in seen_rejections:
                        seen_rejections.add(rejection)
                        print('Interactive control waiting: ' + rejection, flush=True)
                    time.sleep(5)
            if command is None:
                raise TimeoutError('Interactive UI control deadline expired')
            record = {'seq': frame_index + 1, 'frame_sha256': metadata['frame_sha256'],
                      'command': command, 'note': document.get('note'), 'time': time.time()}
            (live / f'accepted-command-{frame_index + 1:03d}.json').write_text(json.dumps(record, indent=2) + '\n')
            self.interactive_observation['commands'].append(record)
            print(json.dumps({'interactive_command': record}), flush=True)
            kind = command['type']
            if kind == 'finish':
                self.interactive_observation['finish_requested'] = True
                self.verify_native_quit('interactive-finish')
                return
            if kind == 'tap':
                self.tap_visible_point([command['x'], command['y']])
            elif kind == 'swipe':
                self.assert_native_canvas()
                self.shell('input', 'swipe', command['x1'], command['y1'], command['x2'], command['y2'], command['duration_ms'])
            elif kind == 'key':
                self.shell('input', 'keyevent', command['code'])
            elif kind == 'wait':
                time.sleep(command['seconds'])
            elif kind == 'relaunch':
                self.shell('am', 'force-stop', PACKAGE)
                self.launch()
                time.sleep(30)
            if kind != 'wait':
                time.sleep(2)
        raise RuntimeError(f'Interactive frame budget ({max_commands} commands) exhausted without finish')

    def run_plan(self, plan, prefix, limit=None):
        checkpoints = {}
        self.checkpoints = checkpoints
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
            elif step.get('clear_gameplay_overlays'):
                self.clear_gameplay_overlays(name)
            elif step.get('open_pause_visually'):
                self.clear_gameplay_overlays(name, open_pause=True)
            elif step.get('choose_save_visually'):
                self.choose_save_visually(name)
            elif step.get('confirm_save_visually'):
                self.choose_save_visually(name, confirmation=True)
            elif step.get('context_action'):
                self.context_action(name, step['context_action'])
            elif step.get('find_context_action'):
                self.find_context_action(name, step['find_context_action'])
            elif step.get('lamp_toggle_cycle'):
                self.lamp_toggle_cycle(name, step['lamp_toggle_cycle'])
            elif step.get('close_context_if_visible'):
                self.close_context_if_visible(name)
            elif step.get('main_quit_visually'):
                self.main_quit_visually(name)
            elif step.get('confirm_quit_visually'):
                self.confirm_quit_visually(name)
            elif step.get('verify_native_quit'):
                self.verify_native_quit(name)
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
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--interactive-after', default='close-alex-context-before-object-test')
    parser.add_argument('--cold-start-attempts', type=int,
                        default=int(os.environ.get('S3CE_RUNTIME_COLD_START_ATTEMPTS', '0')))
    args = parser.parse_args()
    if not 0 <= args.cold_start_attempts <= 6:
        parser.error('--cold-start-attempts must be between 0 and 6')
    def terminate_controller(signum, frame):
        raise RuntimeError('Runtime controller received termination signal')
    signal.signal(signal.SIGTERM, terminate_controller)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sdk = Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])
    emulator_dir = Path(os.environ.get('S3CE_EMULATOR_DIR', sdk / 'emulator'))
    image = sdk / 'system-images/android-30/google_apis/x86'
    original_size = (image / 'system.img').stat().st_size
    plan = json.loads(args.plan.read_text())
    execution_scope = plan_execution_scope(plan, args.interactive, args.interactive_after)
    result = {'status': 'pending', 'candidate_sha256': sha(args.candidate),
              'baseline_sha256': sha(args.baseline), 'git_sha': os.environ.get('GITHUB_SHA'),
              'environment': {}, 'checkpoints': {}, 'visual_review': 'required',
              'gate_passed': False, 'actions': 'Android UI input only; no game-state writes',
              'execution_scope': execution_scope}
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
            if label == 'candidate' and args.cold_start_attempts:
                android.observe_cold_starts(args.cold_start_attempts, plan.get('launch_wait', 20))
            else:
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
                result['checkpoints'] = android.run_plan(plan, label, limit=execution_scope['limit'])
                result['events'] = android.events
                for checkpoint in ['gameplay', 'resume']:
                    observation = result['checkpoints'].get(checkpoint, {})
                    if observation.get('scene') != 'SceneGame' or not observation.get('game_pid'):
                        raise RuntimeError('No observed real SceneGame at ' + checkpoint)
                if args.interactive:
                    android.interactive_loop(os.environ.get('GITHUB_RUN_ID', ''))
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
        result['checkpoints'] = android.checkpoints
        result['object_actions'] = android.object_actions
        result['native_quit'] = android.quit_observation
        result['interactive'] = android.interactive_observation
        result['cold_starts'] = android.cold_starts
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
        live = output / 'live'
        live.mkdir(exist_ok=True)
        marker = live / 'controller-exit.json'
        temporary = marker.with_suffix('.tmp')
        temporary.write_text(json.dumps({'status': result['status'], 'error': result.get('error'),
                                         'exit_code': 0 if result['status'] == 'runtime-progression-observed-awaiting-visual-review' else 1}, indent=2) + '\n')
        temporary.replace(marker)


if __name__ == '__main__':
    main()
