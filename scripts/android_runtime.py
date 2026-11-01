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
from android_runtime_profile import runtime_profile

PACKAGE = 'io.github.russianranger.s3ce'
LAUNCHER = PACKAGE + '/com.ideaworks3d.thesims3.CompatActivity'
MAIN = PACKAGE + '/com.ideaworks3d.thesims3.Main'
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


def saved_main_menu_visual_allowed(step):
    """Only the source-proven SaveQuit→main-menu boundary has this fallback."""
    return (step.get('name') == 'confirm-save-and-quit'
            and step.get('confirm_save_visually') is True
            and step.get('expect_scene') == 'SceneMenu'
            and step.get('expect_menu_state') in (None, 5)
            and step.get('checkpoint') == 'saved-to-menu')


def cold_main_session_phases(session, pid):
    """Require this cold process to bootstrap before entering original native Main."""
    identities = [line for line in session.splitlines() if line.startswith('SESSION ')]
    if (not re.fullmatch(r'[1-9]\d*', pid or '') or len(identities) != 1
            or f'package={PACKAGE} ' not in identities[0]
            or f'process={PACKAGE} ' not in identities[0]
            or not re.search(r'(?:^| )pid=' + re.escape(pid) + r'(?: |$)', identities[0])):
        raise RuntimeError('Direct Main diagnostic session does not identify the fresh game PID')
    phases = [match.group(1) for line in session.splitlines()
              if (match := re.fullmatch(r'wallMs=\d+ elapsedMs=\d+ (.+)', line))]
    required = ('Main entry requires native bootstrap (process restoration)',
                'nativeBootstrap RETURN version=', 'Native Main ENTER')
    positions = [[index for index, phase in enumerate(phases)
                  if phase == value or (value.endswith('=') and phase.startswith(value))]
                 for value in required]
    if (any(len(indices) != 1 for indices in positions)
            or not positions[0][0] < positions[1][0] < positions[2][0]):
        raise RuntimeError('Direct Main lacks one ordered restoration bootstrap and native Main entry')
    if not re.fullmatch(r'nativeBootstrap RETURN version=\d+', phases[positions[1][0]]):
        raise RuntimeError('Direct Main native bootstrap did not return a successful version')
    if any('Activity com.ideaworks3d.thesims3.GameBootActivity ' in phase
           or phase.startswith('Main startActivity ENTER') for phase in phases):
        raise RuntimeError('Direct Main unexpectedly passed through the normal Boot Activity')
    return {'session_identity': identities[0],
            'ordered_phases': [phases[indices[0]] for indices in positions]}


def native_frame_visibility(path, bounds):
    """Pixel readiness only; resulting gameplay actions still need visual review."""
    from PIL import Image
    with Image.open(path) as image:
        if not bounds or not within_screen(bounds, image.size):
            raise RuntimeError('Visible native frame requires an actual in-screen canvas')
        crop = image.convert('RGB').crop(tuple(bounds))
    area = crop.width * crop.height
    colors = crop.getcolors(64)
    distinct = len(colors) if colors is not None else 65
    histogram = crop.convert('L').histogram()
    nonblack = area - sum(histogram[:4])
    return {'rendered_pixels': nonblack >= area // 10 and distinct >= 32,
            'nonblack_pixels': nonblack, 'canvas_pixels': area,
            'distinct_colors_capped_at_65': distinct,
            'rgb_extrema': crop.getextrema(), 'readiness_only': True}


def game_viewport(hierarchy, windows, viewport_events='', screen_size=None):
    """Prefer actual child bounds; a wide Activity frame is never a game canvas."""
    candidates = []
    try:
        for node in ET.fromstring(hierarchy).iter('node'):
            name = node.get('class', '')
            if node.get('package', PACKAGE) == PACKAGE and ('SurfaceView' in name or 'AirplayView' in name):
                match = BOUNDS.fullmatch(node.get('bounds', ''))
                if match:
                    bounds = tuple(map(int, match.groups()))
                    if valid_native_canvas(bounds) and within_screen(bounds, screen_size):
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
            if within_screen(bounds, screen_size):
                base = 'ty=BASE_APPLICATION' in section
                frames.append((base, (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]), bounds))
    # Animated SurfaceViews may never idle for UIAutomator. The candidate's
    # bounded layout witness records its real child location/size, not a fitted
    # rectangle inferred from display or Activity dimensions. Require both its
    # parent and child to remain inside an observed Main window and actual PNG.
    layout = re.compile(r'VIEWPORT child=([A-Za-z0-9_.$]+) bounds=(\[-?\d+,\s*-?\d+\]\[-?\d+,\s*-?\d+\])'
                        r' parent=(\[-?\d+,\s*-?\d+\]\[-?\d+,\s*-?\d+\])')
    for match in reversed(list(layout.finditer(viewport_events))):
        name, child_text, parent_text = match.groups()
        if not (name.startswith('com.ideaworks3d.airplay.') or name == 'android.view.SurfaceView'):
            continue
        child = tuple(map(int, BOUNDS.fullmatch(child_text).groups()))
        parent = tuple(map(int, BOUNDS.fullmatch(parent_text).groups()))
        if (valid_native_canvas(child) and within_screen(parent, screen_size)
                and contains_bounds(parent, child)
                and any(contains_bounds(window, parent) for _, _, window in frames)):
            return child, 'GameViewport actual child layout witness'
    if frames:
        compatible = [row for row in frames if valid_native_canvas(row[2])]
        if compatible:
            base, _, bounds = max(compatible)
            return bounds, 'Main BASE_APPLICATION frame' if base else 'largest Main native frame'
    return None, None


def contains_bounds(outer, inner):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def within_screen(bounds, size):
    return size is None or contains_bounds((0, 0, *size), bounds)


def letterbox_probe_points(screen_size, viewport):
    """Select one physical point strictly inside each vertical black margin."""
    if not valid_native_canvas(viewport) or not within_screen(viewport, screen_size):
        raise ValueError('Letterbox probes require actual in-screen native bounds')
    left, top, right, bottom = viewport
    width, _ = screen_size
    if left < 2 or right > width - 2:
        raise ValueError('Both visible vertical margins are required')
    return [(left // 2, (top + bottom) // 2), ((right + width) // 2, (top + bottom) // 2)]


def valid_native_canvas(bounds):
    left, top, right, bottom = bounds
    return right > left and bottom > top and abs((right - left) / (bottom - top) - 16 / 9) <= .002


def main_window_rotation(windows):
    """Read the actual Main window configuration, never the requested setting."""
    observations = []
    for section in re.split(r'(?=\n\s*Window #\d+ Window\{)', windows):
        if not any('com.ideaworks3d.thesims3.Main}' in line for line in section.splitlines()[:2]):
            continue
        match = re.search(r'\bmFullConfiguration=[^\n]*\bmRotation=(?:ROTATION_(0|90|180|270)|([0-3]))\b', section)
        if match:
            observations.append(('ty=BASE_APPLICATION' in section,
                                 int(match[1]) // 90 if match[1] is not None else int(match[2])))
    if any(base for base, _ in observations):
        observations = [row for row in observations if row[0]]
    rotations = {rotation for _, rotation in observations}
    return rotations.pop() if len(rotations) == 1 else None


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
        self.cold_main_entry_observation = {}
        self.letterbox_observation = {}
        self.home_return_observation = {}
        self.rotation_observations = []
        self.saved_menu_visual_attempts = 0
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
        viewport_events = self.shell('cat', f'/data/data/{PACKAGE}/files/compat-events.log', check=False)
        (directory / 'viewport-events.log').write_text(viewport_events)
        observed_viewport, observed_source = game_viewport(hierarchy, windows, viewport_events, self.screen_size)
        if observed_viewport is not None:
            self.viewport, self.viewport_source = observed_viewport, observed_source
        elif self.viewport is not None and within_screen(self.viewport, self.screen_size):
            self.viewport_source = 'retained last verified native canvas through Android UI'
        else:
            self.viewport = self.viewport_source = None
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
                 'scene_source': 'sampled-native-input-observer' if observers else 'unobserved',
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

    def observe_cold_starts(self, attempts, launch_wait, expected_bounds=None):
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
                if expected_bounds is not None and tuple(self.viewport or ()) != tuple(expected_bounds):
                    raise RuntimeError('Cold start did not retain the expected actual native child bounds')
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

    def verify_cold_main_entry(self, expected_bounds, launch_wait=30):
        """Bypass Boot in a fresh emulator process; retain data and every frame.

        This probes the missing-bootstrap boundary seen on task restoration. It
        does not simulate Android's saved-instance-state Bundle or accept a menu
        visually; the normal UI prefix continues from the resulting menu.
        """
        if (type(launch_wait) not in (int, float) or not 0 <= launch_wait <= 60
                or expected_bounds is None):
            raise ValueError('Direct Main requires expected child bounds and a bounded launch wait')
        marker = 'S3CE-direct-cold-Main-' + str(time.time_ns())
        prefix = 'candidate-direct-cold-main'
        before_pid = self.shell('pidof', PACKAGE, check=False).strip()
        record = self.cold_main_entry_observation = {
            'status': 'failed', 'before_pid': before_pid, 'marker': marker,
            'start_epoch': time.time(), 'expected_game_bounds': expected_bounds,
            'scope': 'root emulator direct Main; process-cold; app data retained; no Boot intent',
            'limitation': 'Cold-entry boundary only; Android saved-state Bundle restoration is not simulated',
            'normal_launcher_cold_start_counted': False, 'visual_review': 'normal menu required',
            'launch_wait_seconds': launch_wait, 'readiness_timeout_seconds': 90,
            'captures': [], 'fatal_or_anr_lines': []}
        try:
            if not re.fullmatch(r'[1-9]\d*', before_pid):
                raise RuntimeError('Direct Main needs the preceding live normal-menu process')
            self.shell('log', '-t', 'S3CEDirectMain', marker)
            self.shell('am', 'force-stop', PACKAGE)
            self.wait_for('previous normal-menu process stopped',
                          lambda: not self.shell('pidof', PACKAGE, check=False).strip(), 15)
            self.viewport = self.viewport_source = None
            launch = self.shell('am', 'start', '-W', '-n', MAIN)
            (self.output / 'direct-main-am-start.txt').write_text(launch)
            record['am_start_output'] = launch
            if not re.search(r'^Status:\s*ok\s*$', launch, re.MULTILINE):
                raise RuntimeError('Direct Main am start did not report Status: ok')
            time.sleep(launch_wait)
            deadline = time.monotonic() + 90
            expected_pid = None
            for attempt in range(12):
                if time.monotonic() >= deadline:
                    break
                label = f'{prefix}-{attempt:02d}'
                self.snapshot(label)
                directory = self.output / label
                event = self.events[-1]
                pid = event.get('game_pid')
                capture = {'capture': label, 'game_pid': pid, 'native_viewport': self.viewport,
                           'viewport_source': self.viewport_source,
                           'screenshot_sha256': sha(directory / 'screen.png')}
                record['captures'].append(capture)
                log = (directory / 'logcat.txt').read_text(errors='replace')
                if marker not in log:
                    raise RuntimeError('Direct Main log marker is missing; log window is unknown')
                attempt_log = log.partition(marker)[2]
                (directory / 'attempt-logcat.txt').write_text(attempt_log)
                fatal = [line for line in attempt_log.splitlines()
                         if re.search(r'Fatal signal|FATAL EXCEPTION|SIGSEGV|SIGABRT|ANR in|am_crash|am_anr', line)]
                record['fatal_or_anr_lines'] = fatal
                if fatal:
                    raise RuntimeError('Fatal/ANR evidence in direct Main startup window')
                previous_pids = {before_pid, *(row.get('game_pid') for row in self.cold_starts)}
                if (not re.fullmatch(r'[1-9]\d*', pid or '') or pid in previous_pids
                        or (expected_pid is not None and pid != expected_pid)):
                    raise RuntimeError('Direct Main did not retain one distinct fresh game process')
                expected_pid = record['game_pid'] = pid
                if (tuple(self.viewport or ()) != tuple(expected_bounds)
                        or self.viewport_source not in ('SurfaceView hierarchy',
                                                       'GameViewport actual child layout witness')):
                    raise RuntimeError('Direct Main lost the expected actual native child bounds')
                activity = (directory / 'activity.txt').read_text(errors='replace')
                resumed = [line.strip() for line in activity.splitlines()
                           if 'mResumedActivity' in line or 'topResumedActivity' in line]
                capture['resumed_activity_lines'] = resumed
                if not any(MAIN in line for line in resumed):
                    raise RuntimeError('Direct Main is not the resumed game Activity')
                session = (directory / 'compat-session.log').read_text(errors='replace')
                record.update(cold_main_session_phases(session, pid))
                capture.update(native_frame_visibility(directory / 'screen.png', self.viewport))
                if capture['rendered_pixels']:
                    record['status'] = 'cold-Main-bootstrap-visible-awaiting-menu-review'
                    record['visible_capture'] = label
                    return record
                time.sleep(2)
            raise RuntimeError('Direct Main native canvas stayed blank within bounded readiness observation')
        except Exception as error:
            record['error'] = type(error).__name__ + ': ' + str(error)
            if not record['captures']:
                try:
                    self.snapshot(prefix + '-failure')
                    record['failure_capture'] = prefix + '-failure'
                except Exception as capture_error:
                    record['capture_error'] = str(capture_error)
            raise
        finally:
            record['end_epoch'] = time.time()
            (self.output / 'cold-main-entry-observation.json').write_text(json.dumps(record, indent=2) + '\n')

    def verify_letterbox_margins(self, expected_bounds):
        """Tap actual black margins before the first native touch of the plan."""
        from PIL import Image
        self.snapshot('letterbox-before')
        if tuple(self.viewport or ()) != tuple(expected_bounds):
            raise RuntimeError('Measured native child differs from the requested Flip3 viewport')
        points = letterbox_probe_points(self.screen_size, self.viewport)
        before_pid = self.events[-1]['game_pid']
        before_callbacks = re.findall(r'Pointer callback ENTER #\d+[^\n]*', self.latest_native)
        if before_callbacks:
            raise RuntimeError('Black-margin check must precede the first native callback so bounded tracing cannot hide input')
        observations = []
        self.letterbox_observation = {'status': 'pending', 'viewport': self.viewport,
            'screen_size': self.screen_size, 'game_pid': before_pid, 'points': points,
            'scope': 'Physical black-margin taps; callback witness and screenshots only',
            'observations': observations}
        for index, point in enumerate(points):
            color = Image.open(self.output / 'letterbox-before/screen.png').convert('RGB').getpixel(point)
            if max(color) > 8:
                raise RuntimeError('Requested letterbox tap point is not visibly black')
            self.shell('input', 'tap', *point)
            time.sleep(.5)
            label = f'letterbox-margin-{index + 1}'
            self.snapshot(label)
            callbacks = re.findall(r'Pointer callback ENTER #\d+[^\n]*', self.latest_native)
            row = {'capture': label, 'point': point, 'before_color': color,
                   'game_pid': self.events[-1]['game_pid'],
                   'callback_witness_unchanged': callbacks == before_callbacks,
                   'viewport_unchanged': tuple(self.viewport or ()) == tuple(expected_bounds)}
            observations.append(row)
            if not row['callback_witness_unchanged'] or not row['viewport_unchanged'] or row['game_pid'] != before_pid:
                raise RuntimeError('Black-margin tap reached native input or changed the active game viewport/process')
        self.letterbox_observation['status'] = 'callback-inert-awaiting-visual-review'
        (self.output / 'letterbox-observation.json').write_text(json.dumps(self.letterbox_observation, indent=2) + '\n')

    def verify_home_return(self, expected_bounds):
        """Exercise ordinary Home and launcher return without force-stop/data edits."""
        self.snapshot('home-return-before')
        before_pid = self.events[-1]['game_pid']
        self.home_return_observation = {'status': 'pending', 'before_pid': before_pid,
                                       'expected_game_bounds': expected_bounds}
        self.shell('input', 'keyevent', 3)
        time.sleep(2)
        self.snapshot('home-return-home')
        self.launch()
        self.viewport = self.viewport_source = None
        self.wait_for('Main activity resumed after Home', lambda: 'com.ideaworks3d.thesims3.Main' in '\n'.join(
            line for line in self.shell('dumpsys', 'activity', 'activities', check=False).splitlines()
            if 'mResumedActivity' in line or 'topResumedActivity' in line), 45)
        time.sleep(2)
        self.snapshot('home-return-resumed')
        after_pid = self.events[-1]['game_pid']
        self.home_return_observation.update(after_pid=after_pid, native_viewport=self.viewport,
            status='same-process-return-awaiting-visual-review')
        if not before_pid or after_pid != before_pid or tuple(self.viewport or ()) != tuple(expected_bounds):
            self.home_return_observation['status'] = 'failed'
            raise RuntimeError('Home/return changed the game process or lost its measured native viewport')
        # A recreated translated EGL surface can be black well after onResume.
        # Retain that first capture and wait on actual pixels, not frame counters.
        try:
            visible = self.wait_for_visible_native_frame('home-return-visible', before_pid, expected_bounds)
            self.home_return_observation.update(status='same-process-visible-return-awaiting-action-review',
                visible_capture=visible['capture'], visibility=visible,
                subsequent_action='Requires ordinary UI action and resulting visible frame review')
        except Exception:
            self.home_return_observation['status'] = 'visible-readiness-failed'
            raise
        finally:
            (self.output / 'home-return-observation.json').write_text(json.dumps(self.home_return_observation, indent=2) + '\n')

    def wait_for_visible_native_frame(self, prefix, expected_pid, expected_bounds, timeout=90):
        """Retain each real frame; never retry past changed process/canvas."""
        deadline = time.monotonic() + timeout
        evidence = {'timeout_seconds': timeout, 'accepted': False, 'captures': []}
        try:
            for attempt in range(12):
                if time.monotonic() >= deadline:
                    break
                label = f'{prefix}-{attempt:02d}'
                self.snapshot(label)
                event = self.events[-1]
                if (not expected_pid or event.get('game_pid') != expected_pid
                        or tuple(self.viewport or ()) != tuple(expected_bounds)):
                    raise RuntimeError('Visible frame lost the same game process or measured canvas')
                facts = {'capture': label, 'game_pid': event['game_pid'],
                         'native_viewport': self.viewport,
                         **native_frame_visibility(self.output / label / 'screen.png', self.viewport)}
                evidence['captures'].append(facts)
                if facts['rendered_pixels']:
                    evidence['accepted'] = True
                    return facts
                time.sleep(2)
            raise RuntimeError('Actual native canvas stayed blank within bounded visible-readiness observation')
        finally:
            (self.output / f'{prefix}-readiness.json').write_text(json.dumps(evidence, indent=2) + '\n')

    def verify_landscape_rotations(self, expected_bounds):
        """Retain unavailable reverse rotation; require measured landscape return."""
        before_pid = self.events[-1]['game_pid']
        def capture(rotation, status, limitation=None):
            self.viewport = self.viewport_source = None
            time.sleep(2)
            label = 'landscape-rotation-' + str(rotation) + ('-unavailable' if status == 'unavailable' else '')
            self.snapshot(label)
            actual = main_window_rotation((self.output / label / 'windows.txt').read_text())
            record = {'requested_rotation': rotation, 'actual_main_window_rotation': actual,
                      'status': status, 'game_pid': self.events[-1]['game_pid'],
                      'native_viewport': self.viewport, 'capture': label, 'visual_review': 'required'}
            if limitation:
                record['limitation'] = limitation
            self.rotation_observations.append(record)
            if (record['game_pid'] != before_pid or not before_pid
                    or tuple(self.viewport or ()) != tuple(expected_bounds)):
                raise RuntimeError('Landscape attempt lost the same game process or actual native viewport')
            return record
        try:
            self.shell('settings', 'put', 'system', 'user_rotation', 3)
            # AOSP uses -atan2(-x,y): negativeX→270deg, positiveX→90deg.
            stimulus = self.adb('emu', 'sensor', 'set', 'acceleration', '-9.8:0:0', check=False)
            unavailable = None
            try:
                self.wait_for('actual Main window landscape rotation3',
                    lambda: main_window_rotation(self.shell('dumpsys', 'window', 'windows')) == 3, 30)
            except TimeoutError as error:
                unavailable = str(error)
            record = capture(3, 'unavailable' if unavailable else 'actual-rotation-observed', unavailable)
            record['sensor_acceleration'] = '-9.8:0:0'
            record['sensor_stimulus_output'] = stimulus.decode(errors='replace')
            if record['actual_main_window_rotation'] not in ((1, 3) if unavailable else (3,)):
                raise RuntimeError('Reverse-landscape attempt ended in an unverified Main orientation')
            record['visible_readiness'] = self.wait_for_visible_native_frame(
                'landscape-reverse-visible', before_pid, expected_bounds)
        finally:
            try:
                stimulus = self.adb('emu', 'sensor', 'set', 'acceleration', '9.8:0:0', check=False)
                self.shell('settings', 'put', 'system', 'user_rotation', 1)
                unavailable = None
                try:
                    self.wait_for('restore actual Main window landscape rotation1',
                        lambda: main_window_rotation(self.shell('dumpsys', 'window', 'windows')) == 1, 30)
                except TimeoutError as error:
                    unavailable = str(error)
                record = capture(1, 'restoration-failed' if unavailable else 'restored-actual-rotation1', unavailable)
                record['sensor_acceleration'] = '9.8:0:0'
                record['sensor_stimulus_output'] = stimulus.decode(errors='replace')
                if unavailable or record['actual_main_window_rotation'] != 1:
                    raise RuntimeError('Ordinary UI requires restored measured Main landscape rotation1')
                record['visible_readiness'] = self.wait_for_visible_native_frame(
                    'landscape-restored-visible', before_pid, expected_bounds)
            finally:
                (self.output / 'landscape-rotations.json').write_text(json.dumps(self.rotation_observations, indent=2) + '\n')

    def save_fingerprints(self):
        """Read only size/mtime facts; never read or modify save contents."""
        names = ('sim3dat0', 'sim3set')
        text = self.shell('stat', '-c', '%n:%s:%Y',
                          *(f'/data/data/{PACKAGE}/files/{name}' for name in names), check=False)
        facts = {}
        for line in text.splitlines():
            parts = line.rsplit(':', 2)
            if len(parts) != 3:
                continue
            name = parts[0].rsplit('/', 1)[-1]
            if name in names and all(re.fullmatch(r'[0-9]+', value) for value in parts[1:]):
                facts[name] = {'bytes': int(parts[1]), 'mtime_epoch_seconds': int(parts[2])}
        return facts

    def observe_saved_main_menu(self, prefix, before_save, expected_pid, expected_bounds):
        """Confirm two real main-menu frames and a newer normal progress save.

        This does not alter the sampled native observer or game state. Its
        separately labeled conclusion is available only to the SaveQuit step.
        """
        from android_runtime_visual import analyze_context_menu
        attempt = self.saved_menu_visual_attempts
        self.saved_menu_visual_attempts += 1
        result = {'source': 'visual-main-menu-and-save-mtime', 'accepted': False,
                  'before_save': before_save, 'captures': [], 'expected_pid': expected_pid}
        path = self.output / f'{prefix}-main-menu-visual-{attempt:02d}.json'
        try:
            if set(before_save) != {'sim3dat0', 'sim3set'} or not expected_pid or expected_bounds is None:
                return None
            point = None
            for index in range(2):
                if index:
                    time.sleep(2)
                label = f'{prefix}-main-menu-visual-{attempt:02d}-{index}'
                self.snapshot(label)
                directory = self.output / label
                observed = self.events[-1]
                activity = (directory / 'activity.txt').read_text(errors='replace')
                resumed = [line for line in activity.splitlines()
                           if 'mResumedActivity' in line or 'topResumedActivity' in line]
                menu = analyze_context_menu(directory / 'screen.png', directory / 'main-menu-ocr',
                                            self.viewport, layout='main')
                saves = self.save_fingerprints()
                row = {'capture': label, 'frame_sha256': sha(directory / 'screen.png'),
                       'raw_scene': observed.get('scene'), 'raw_menu_state': observed.get('menu_state'),
                       'raw_observer': observed.get('observer'), 'game_pid': observed.get('game_pid'),
                       'native_viewport': self.viewport, 'viewport_source': self.viewport_source,
                       'menu_kind': menu.get('kind'),
                       'quit_point': menu.get('point'), 'save_fingerprints': saves}
                result['captures'].append(row)
                if (observed.get('game_pid') != expected_pid
                        or tuple(self.viewport or ()) != tuple(expected_bounds)
                        or self.viewport_source not in ('SurfaceView hierarchy',
                            'GameViewport actual child layout witness',
                            'Main BASE_APPLICATION frame', 'largest Main native frame')
                        or not any('com.ideaworks3d.thesims3.Main' in line for line in resumed)
                        or menu.get('kind') != 'main-menu' or not menu.get('point')
                        or set(saves) != {'sim3dat0', 'sim3set'}
                        or any(saves[name]['bytes'] <= 0 for name in saves)
                        or saves['sim3dat0']['mtime_epoch_seconds'] <= before_save['sim3dat0']['mtime_epoch_seconds']
                        or saves['sim3set']['mtime_epoch_seconds'] < before_save['sim3set']['mtime_epoch_seconds']):
                    return None
                if point is not None and any(abs(a - b) > 4 for a, b in zip(point, menu['point'])):
                    return None
                point = menu['point']
            result['accepted'] = True
            return result
        finally:
            path.write_text(json.dumps(result, indent=2) + '\n')

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
            saved_menu_fallback = saved_main_menu_visual_allowed(step)
            before_save = self.save_fingerprints() if saved_menu_fallback else None
            before_bounds = self.viewport
            visual_main_menu = None
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
                    nonlocal visual_main_menu
                    # Original pointer logging is deliberately sampled. After a
                    # long game its last SceneGame callback can outlive SaveQuit.
                    # At this one boundary require the rendered complete menu,
                    # same process/canvas and newer normal save, rather than
                    # pretending an unchanged native sample is fresh evidence.
                    if saved_menu_fallback:
                        visual_main_menu = self.observe_saved_main_menu(
                            name, before_save, previous_pid, before_bounds)
                        if visual_main_menu is not None:
                            return True
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
            if visual_main_menu is None:
                self.snapshot(name)
            else:
                # Keep the exact second OCR-verified capture as the checkpoint;
                # retain the raw observer verbatim beside the visual conclusion.
                event = self.events[-1]
                event.update(raw_scene=event.get('scene'), raw_menu_state=event.get('menu_state'),
                             scene='SceneMenu', menu_state=5,
                             scene_source=visual_main_menu['source'],
                             scene_evidence=visual_main_menu, step_name=name)
                (self.output / event['name'] / 'observation.json').write_text(json.dumps(event, indent=2) + '\n')
                print(json.dumps(event), flush=True)
            if step.get('expect_same_pid') and (not previous_pid or self.events[-1]['game_pid'] != previous_pid):
                raise RuntimeError(f'{name}: game process changed across Home/reopen')
            if (step.get('expect_menu_state') is not None
                    and (5 if visual_main_menu is not None else self.last_menu_state()) != step['expect_menu_state']):
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
    profile = runtime_profile(os.environ.get('GITHUB_REF_NAME', 'main'))
    execution_scope = plan_execution_scope(plan, args.interactive, args.interactive_after)
    result = {'status': 'pending', 'candidate_sha256': sha(args.candidate),
              'baseline_sha256': sha(args.baseline), 'git_sha': os.environ.get('GITHUB_SHA'),
              'environment': {}, 'checkpoints': {}, 'visual_review': 'required',
              'gate_passed': False, 'actions': 'Android UI input only; no game-state writes',
              'execution_scope': execution_scope, 'runtime_profile': profile}
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
                android.observe_cold_starts(args.cold_start_attempts, plan.get('launch_wait', 20),
                                           profile['expected_game_bounds'])
            else:
                android.launch()
                time.sleep(plan.get('launch_wait', 20))
            if label == 'candidate' and profile.get('verify_cold_main_entry', False):
                android.verify_cold_main_entry(profile['expected_game_bounds'], plan.get('launch_wait', 20))
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
                if profile['verify_letterbox']:
                    android.verify_letterbox_margins(profile['expected_game_bounds'])
                result['checkpoints'] = android.run_plan(plan, label, limit=execution_scope['limit'])
                result['events'] = android.events
                for checkpoint in ['gameplay', 'resume']:
                    observation = result['checkpoints'].get(checkpoint, {})
                    if observation.get('scene') != 'SceneGame' or not observation.get('game_pid'):
                        raise RuntimeError('No observed real SceneGame at ' + checkpoint)
                if profile['verify_home_return']:
                    android.verify_home_return(profile['expected_game_bounds'])
                if profile['verify_rotations']:
                    android.verify_landscape_rotations(profile['expected_game_bounds'])
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
        result['cold_main_entry'] = android.cold_main_entry_observation
        result['letterbox'] = android.letterbox_observation
        result['home_return'] = android.home_return_observation
        result['landscape_rotations'] = android.rotation_observations
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
