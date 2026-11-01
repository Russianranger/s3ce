#!/usr/bin/env python3
"""Observe API35 ABI compatibility and run exact candidate viewport DEX separately.

The platform probe is a separate test APK, never a repackaged game. Its child is
a SurfaceView input fixture; no native engine or game progression is exercised.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'io.github.russianranger.s3ce.viewportprobe'
ACTIVITY = PACKAGE + '/.ViewportProbe'
HELPER = 'com.ideaworks3d.thesims3.GameViewport'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def candidate_identity(candidate):
    with zipfile.ZipFile(candidate) as apk:
        if apk.namelist().count('classes2.dex') != 1:
            raise ValueError('Candidate must contain exactly one launcher classes2.dex')
        dex = apk.read('classes2.dex')
    if not dex.startswith(b'dex\n'):
        raise ValueError('Candidate launcher code is not a DEX file')
    return {'apk_sha256': sha(candidate), 'apk_bytes': candidate.stat().st_size,
            'classes2_sha256': hashlib.sha256(dex).hexdigest(), 'helper': HELPER}, dex


def physical_size_from_wm(text, rotation):
    """WindowManager reports natural dimensions; apply actual display rotation."""
    if type(rotation) is not int or rotation not in (0, 1, 2, 3):
        raise ValueError('Actual display rotation is unavailable')
    physical = re.findall(r'^Physical size: (\d+)x(\d+)\s*$', text, re.M)
    override = re.findall(r'^Override size: (\d+)x(\d+)\s*$', text, re.M)
    if len(physical) != 1 or len(override) > 1:
        raise ValueError('WindowManager natural display size is missing or ambiguous')
    width, height = map(int, (override or physical)[0])
    if min(width, height) <= 0:
        raise ValueError('WindowManager display dimensions are not positive')
    return [height, width] if rotation in (1, 3) else [width, height]


def geometry_projection(report):
    """Own the boundary between legacy app-compatible and physical coordinates.

    A nonresizable target28 Activity may retain virtual Display/View dimensions
    after wm-size changes. Keep all View/Insets/Surface facts in that app space;
    only uniformly project screenshot rectangles into WindowManager's physical
    space. Unequal scaling is rejected, never treated as an acceptable stretch.
    """
    app = report.get('display_size')
    physical = report.get('physical_display_size', app)
    for size in (app, physical):
        if type(size) is not list or len(size) != 2 or any(type(v) is not int or v <= 0 for v in size):
            raise ValueError('App and physical display dimensions must be explicit positive pairs')
    sx, sy = physical[0] / app[0], physical[1] / app[1]
    if abs(sx - sy) > .001:
        raise ValueError('App-compatible to physical display mapping is not uniform')
    return app, physical, (sx, sy)


def projected_bounds(report, key):
    _, _, (sx, sy) = geometry_projection(report)
    bounds = report[key]
    return [bounds[0] * sx, bounds[1] * sy, bounds[2] * sx, bounds[3] * sy]


def validate_geometry(report, identity, expected_display):
    """Check actual framework measurements against the exact fitted-content rule."""
    if report.get('failure'):
        raise ValueError('Android probe failure: ' + str(report['failure']))
    app_display, physical_display, _ = geometry_projection(report)
    if report.get('api') != 35 or physical_display != list(expected_display):
        raise ValueError(f'Unexpected Android API/display: api={report.get("api")} physical={physical_display} '
                         f'app-compatible={app_display}, expected physical={list(expected_display)}')
    if (report.get('target_sdk') != 28 or report.get('hardware_accelerated') is not False
            or report.get('requested_orientation') != 6 or report.get('window_cutout_mode') != 2):
        raise ValueError('Probe window differs from candidate target28/software/sensorLandscape/cutoutNEVER policy')
    loaded = report.get('identity', {})
    if (loaded.get('apk_sha256') != identity['apk_sha256']
            or loaded.get('classes2_sha256') != identity['classes2_sha256']
            or loaded.get('loaded_helper') != HELPER
            or loaded.get('helper_loader') != 'dalvik.system.DexClassLoader'):
        raise ValueError('Probe did not execute the exact candidate helper DEX')
    if report.get('parent_class') != HELPER:
        raise ValueError('Actual parent is not the candidate viewport')
    parent, child = report.get('parent_bounds'), report.get('child_bounds')
    for bounds in (parent, child):
        if (type(bounds) is not list or len(bounds) != 4 or any(type(v) is not int for v in bounds)
                or bounds[2] <= bounds[0] or bounds[3] <= bounds[1]):
            raise ValueError('Missing positive actual view bounds')
    left, top, right, bottom = parent
    if not 0 <= left < right <= app_display[0] or not 0 <= top < bottom <= app_display[1]:
        raise ValueError('Activity content is outside its reported app-compatible display')
    insets = report.get('system_insets')
    if (type(insets) is not list or len(insets) != 4
            or any(type(v) is not int or v < 0 for v in insets)):
        raise ValueError('Actual root-window insets are unavailable')
    if (left < insets[0] or top < insets[1] or right > app_display[0] - insets[2]
            or bottom > app_display[1] - insets[3]):
        raise ValueError('Fitted activity content overlaps a reported system inset')
    # Root WindowInsets use the same translated app space as View bounds.
    # Display.getCutout is a separate display-level physical observation.
    cutout = report.get('display_cutout_insets')
    if cutout is not None:
        if type(cutout) is not list or len(cutout) != 4 or any(type(v) is not int or v < 0 for v in cutout):
            raise ValueError('Malformed actual display cutout insets')
        physical_parent = projected_bounds(report, 'parent_bounds')
        if (physical_parent[0] < cutout[0] or physical_parent[1] < cutout[1]
                or physical_parent[2] > physical_display[0] - cutout[2]
                or physical_parent[3] > physical_display[1] - cutout[3]):
            raise ValueError('Physical activity content overlaps the measured display cutout')
    unit = min((right - left) // 16, (bottom - top) // 9)
    width, height = unit * 16, unit * 9
    x, y = left + (right - left - width) // 2, top + (bottom - top - height) // 2
    if child != [x, y, x + width, y + height]:
        raise ValueError('Actual child is stretched, offset, or not centered in fitted content')
    if report.get('child_measured_size') != [width, height] or report.get('surface_frame') != [width, height]:
        raise ValueError('Surface buffer and actual measured child differ')
    return child


def validate_black_margins(path, report):
    """Inspect physical pixels strictly inside both actual side margins."""
    _, physical_display, scales = geometry_projection(report)
    parent, child = projected_bounds(report, 'parent_bounds'), projected_bounds(report, 'child_bounds')
    # In size compatibility mode the compositor can filter one boundary pixel.
    # Exclude that edge; every interior pixel still must be black.
    edge = 1 if scales != (1., 1.) else 0
    rectangles = [(math.ceil(parent[0]), math.ceil(parent[1]), math.floor(child[0]) - edge, math.floor(parent[3])),
                  (math.ceil(child[2]) + edge, math.ceil(parent[1]), math.floor(parent[2]), math.floor(parent[3]))]
    checks = []
    with Image.open(path) as image:
        image = image.convert('RGB')
        if list(image.size) != physical_display:
            raise ValueError('Screenshot and measured physical display dimensions differ')
        for rectangle in rectangles:
            if rectangle[2] <= rectangle[0]:
                raise ValueError('Expected physical side margin is absent')
            extrema = image.crop(rectangle).getextrema()
            if any(high > 3 for low, high in extrema):
                raise ValueError('Physical side-margin pixels are not black')
            checks.append({'rectangle': list(rectangle), 'rgb_extrema': extrema,
                           'pixels': (rectangle[2] - rectangle[0]) * (rectangle[3] - rectangle[1]),
                           'app_to_physical_scale': scales})
    return checks


def validate_center_tap(events, child):
    if [e.get('action') for e in events] != [0, 1]:
        raise ValueError('Center tap did not reach fixture as exactly DOWN/UP')
    center = ((child[2] - child[0]) // 2, (child[3] - child[1]) // 2)
    if any(abs(e.get('x', -9999) - center[0]) > 1 or abs(e.get('y', -9999) - center[1]) > 1 for e in events):
        raise ValueError('Framework did not deliver correct child-local center coordinates')


def validate_visible_restoration(before_path, before, after_path, after):
    """Require actual static fixture pixels to survive Home/return unchanged."""
    def crop(path, report):
        box = tuple(round(v) for v in projected_bounds(report, 'child_bounds'))
        with Image.open(path) as image:
            result = image.convert('RGB').crop(box)
        if result.getextrema() == ((0, 0), (0, 0), (0, 0)):
            raise ValueError('Actual fixture child is entirely black')
        return result
    first, second = crop(before_path, before), crop(after_path, after)
    if first.size != second.size or first.tobytes() != second.tobytes():
        raise ValueError('Visible fixture pixels did not survive Home/return unchanged')
    return {'child_pixels_sha256': hashlib.sha256(first.tobytes()).hexdigest(),
            'child_pixels_size': first.size, 'identical_after_return': True}


def validate_cancel(events, child, label):
    actions = [e.get('action') for e in events]
    if not actions or actions[0] != 0 or actions[-1] != 3 or actions.count(3) != 1 or 1 in actions:
        raise ValueError(label + ' did not produce one CANCEL without a later UP')
    width, height = child[2] - child[0], child[3] - child[1]
    if any(e.get('action') == 2 and not (0 <= e['x'] < width and 0 <= e['y'] < height) for e in events):
        raise ValueError(label + ' forwarded an out-of-bounds MOVE before cancellation')
    previous = events[-2] if len(events) >= 2 else {}
    expected, actual = previous.get('pointers'), events[-1].get('pointers')
    if type(expected) is not list or not expected or type(actual) is not list or not actual:
        raise ValueError(label + ' lacks actual pointer-ID/child-coordinate samples')
    for points in (expected, actual):
        ids = []
        for point in points:
            if (type(point) is not dict or type(point.get('id')) is not int
                    or not 0 <= point['id'] <= 31
                    or any(type(point.get(axis)) not in (int, float)
                           or not math.isfinite(point[axis]) for axis in ('x', 'y'))):
                raise ValueError(label + ' has invalid pointer-ID/coordinate facts')
            ids.append(point['id'])
        if len(ids) != len(set(ids)):
            raise ValueError(label + ' has duplicate pointer IDs')
    if previous.get('action') == 6:
        index = previous.get('action_index')
        if type(index) is not int or not 0 <= index < len(expected):
            raise ValueError(label + ' has an invalid POINTER_UP index')
        expected = [point for i, point in enumerate(expected) if i != index]
    if [p.get('id') for p in actual] != [p.get('id') for p in expected]:
        raise ValueError(label + ' changed active pointer IDs or retained a lifted pointer')
    for original, cancelled in zip(expected, actual):
        if any(abs(original.get(axis, -9999) - cancelled.get(axis, -19999)) > .01 for axis in ('x', 'y')):
            raise ValueError(label + ' CANCEL coordinates differ from the last valid child-local sample')


def geometry_key(report):
    """Only actual layout/window facts participate in the settling observation."""
    names = ('display_size', 'physical_display_size', 'display_rotation',
             'parent_bounds', 'child_bounds', 'child_measured_size', 'surface_frame',
             'system_insets', 'display_cutout_insets')
    return json.dumps({name: report.get(name) for name in names}, sort_keys=True)


def capture_settled_geometry(device, identity, expected_display, label, timeout=30):
    """Capture valid geometry after three quiet seconds, within thirty seconds.

    A focused API35 layout may precede fullscreen system-bar settling. Compare
    the actual capture again and retain/retry any changed capture.
    """
    deadline = time.monotonic() + timeout
    previous = quiet_since = None
    evidence = {'quiet_seconds': 3, 'timeout_seconds': timeout, 'captures': [], 'accepted': False}
    try:
        for attempt in range(6):
            def settled():
                nonlocal previous, quiet_since
                report = device.report()
                try:
                    validate_geometry(report, identity, expected_display)
                except ValueError:
                    previous = quiet_since = None
                    raise
                if not report.get('window_focused') or not report.get('resumed'):
                    previous = quiet_since = None
                    return None
                key, now = geometry_key(report), time.monotonic()
                if key != previous:
                    previous, quiet_since = key, now
                    return None
                return report if now - quiet_since >= 3 else None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Actual captured viewport did not settle: ' + label)
            ready = device.wait('settled actual geometry ' + label, settled, remaining)
            capture_label = label if attempt == 0 else f'{label}-settling-{attempt:02d}'
            captured = device.capture(capture_label)
            validate_geometry(captured, identity, expected_display)
            matches = (captured.get('window_focused') and captured.get('resumed')
                       and geometry_key(captured) == geometry_key(ready))
            evidence['captures'].append({'capture': capture_label, 'matches_quiet_layout': bool(matches),
                'parent_bounds': captured['parent_bounds'], 'child_bounds': captured['child_bounds']})
            if matches:
                evidence.update(accepted=True, accepted_capture=capture_label)
                return captured, capture_label
            previous = quiet_since = None
        raise TimeoutError('Captured viewport repeatedly changed after readiness: ' + label)
    finally:
        (device.output / f'{label}-geometry-settling.json').write_text(json.dumps(evidence, indent=2) + '\n')


def build_probe(candidate, sdk, directory):
    identity, dex = candidate_identity(candidate)
    directory.mkdir(parents=True, exist_ok=True)
    assets, classes, dex_out = (directory / name for name in ('assets', 'classes', 'dex'))
    for path in (assets, classes, dex_out):
        path.mkdir(exist_ok=True)
    (assets / 'candidate-classes2.dex').write_bytes(dex)
    (assets / 'candidate-identity.json').write_text(json.dumps(identity) + '\n')
    bt, jar = sdk / 'build-tools/35.0.0', sdk / 'platforms/android-35/android.jar'
    java_home = Path(os.environ['JAVA_HOME']) if os.environ.get('JAVA_HOME') else None
    tool = lambda name: str(java_home / 'bin' / name) if java_home else name
    def run(*args):
        try:
            subprocess.run(list(map(str, args)), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as error:
            raise RuntimeError('Probe build tool failed: ' + str(args[0]) + '\n'
                               + error.stderr.decode(errors='replace')[-8000:]) from error
    run(tool('javac'), '--release', '8', '-classpath', jar, '-d', classes,
        ROOT / 'scripts/platform_probe/ViewportProbe.java')
    run(bt / 'd8', '--min-api', '26', '--lib', jar, '--output', dex_out, *sorted(classes.rglob('*.class')))
    raw, aligned, signed = (directory / name for name in ('unsigned.apk', 'aligned.apk', 'viewport-probe.apk'))
    run(bt / 'aapt', 'package', '-f', '-M', ROOT / 'scripts/platform_probe/AndroidManifest.xml',
        '-I', jar, '-A', assets, '-F', raw)
    with zipfile.ZipFile(raw, 'a') as apk:
        apk.write(dex_out / 'classes.dex', 'classes.dex', compress_type=zipfile.ZIP_DEFLATED)
    run(bt / 'zipalign', '-f', '4', raw, aligned)
    key = directory / 'ephemeral-probe.jks'
    if not key.exists():
        run(tool('keytool'), '-genkeypair', '-noprompt', '-keystore', key, '-alias', 'platform-probe',
            '-storepass', 'platform-test-only', '-keypass', 'platform-test-only', '-keyalg', 'RSA',
            '-keysize', '2048', '-validity', '2', '-dname', 'CN=S3CE Ephemeral Platform Probe')
    run(bt / 'apksigner', 'sign', '--ks', key, '--ks-key-alias', 'platform-probe',
        '--ks-pass', 'pass:platform-test-only', '--key-pass', 'pass:platform-test-only', '--out', signed, aligned)
    run(bt / 'apksigner', 'verify', signed)
    return signed, identity


class Platform:
    def __init__(self, sdk, port, output):
        self.adb_path, self.serial, self.output = sdk / 'platform-tools/adb', 'emulator-' + str(port), output

    def adb(self, *args, check=True, timeout=45):
        result = subprocess.run([str(self.adb_path), '-s', self.serial, *map(str, args)],
                                capture_output=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError('ADB command failed: ' + result.stderr.decode(errors='replace')[-2000:])
        return result

    def shell(self, *args, **kwargs):
        return self.adb('shell', *args, **kwargs).stdout.decode(errors='replace')

    def wait(self, description, predicate, timeout=60):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except (ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
                last = error
            time.sleep(1)
        raise TimeoutError(description + ': ' + str(last))

    def report(self):
        report = json.loads(self.adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/probe.json').stdout)
        report['wm_size'] = self.shell('wm', 'size')
        try:
            report['physical_display_size'] = physical_size_from_wm(report['wm_size'], report.get('display_rotation'))
        except ValueError as error:
            report['physical_display_size'] = None
            report['physical_geometry_error'] = str(error)
        report['coordinate_spaces'] = {'view_display_and_root_insets': 'app-compatible',
            'wm_size_and_screenshot': 'physical', 'app_display_size': report.get('display_size'),
            'physical_display_size': report['physical_display_size']}
        try:
            report['coordinate_spaces']['app_to_physical_scale'] = geometry_projection(report)[2]
        except ValueError as error:
            report['coordinate_spaces']['mapping_error'] = str(error)
        return report

    def capture(self, label):
        directory = self.output / label
        directory.mkdir(exist_ok=True)
        png = self.adb('exec-out', 'screencap', '-p').stdout
        if not png.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('No actual screenshot for ' + label)
        (directory / 'screen.png').write_bytes(png)
        report = self.report()
        (directory / 'probe.json').write_text(json.dumps(report, indent=2) + '\n')
        (directory / 'wm-size.txt').write_text(report['wm_size'])
        for name, command in [('windows.txt', ('dumpsys', 'window', 'windows')),
                              ('activity.txt', ('dumpsys', 'activity', 'activities')),
                              ('display.txt', ('dumpsys', 'display'))]:
            (directory / name).write_text(self.shell(*command))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--avd', required=True)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--build-dir', required=True, type=Path)
    parser.add_argument('--sdk', type=Path, default=Path(os.environ.get('ANDROID_HOME', '/nonexistent-sdk')))
    parser.add_argument('--emulator-dir', type=Path)
    parser.add_argument('--port', type=int, default=5556)
    args = parser.parse_args()
    sdk, output = args.sdk.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    device = Platform(sdk, args.port, output)
    result = {'status': 'pending', 'gameplay_tested': False,
              'scope': 'API35 ABI/install observation and exact-candidate-helper platform fixture only',
              'git_sha': os.environ.get('GITHUB_SHA'), 'checks': []}
    emulator = None
    emulator_log = (output / 'emulator.txt').open('wb')
    try:
        probe, identity = build_probe(args.candidate.resolve(), sdk, args.build_dir.resolve())
        result['candidate'] = identity
        result['probe_apk_sha256'] = sha(probe)
        emulator_dir = args.emulator_dir.resolve() if args.emulator_dir else sdk / 'emulator'
        command = [str(emulator_dir / 'emulator'), '-avd', args.avd, '-port', str(args.port), '-accel', 'on',
                   '-gpu', 'swiftshader_indirect', '-no-window', '-no-audio', '-no-boot-anim', '-no-snapshot',
                   '-memory', '3072', '-cores', '4', '-prop', 'qemu.hw.mainkeys=1']
        result['emulator_command'] = command
        result['emulator_version'] = subprocess.check_output([str(emulator_dir / 'emulator'), '-version'], text=True)
        image = sdk / 'system-images/android-35/google_apis/x86_64'
        result['system_image'] = {'properties': (image / 'source.properties').read_text(),
                                 'bytes': (image / 'system.img').stat().st_size,
                                 'sha256': sha(image / 'system.img')}
        emulator = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=emulator_log, stderr=subprocess.STDOUT)
        def booted():
            if emulator.poll() is not None:
                raise ChildProcessError('API35 emulator exited before boot: ' + str(emulator.returncode))
            return device.shell('getprop', 'sys.boot_completed').strip() == '1'
        device.wait('API35 boot', booted, 600)
        device.wait('PackageManager', lambda: 'package:' in device.shell('pm', 'path', 'android'), 120)
        device.shell('settings', 'put', 'system', 'accelerometer_rotation', '0')
        device.shell('settings', 'put', 'system', 'user_rotation', '1')
        device.shell('input', 'keyevent', '82')
        properties = ['ro.build.version.sdk', 'ro.product.cpu.abilist', 'ro.product.cpu.abilist32',
                      'ro.product.cpu.abilist64', 'ro.dalvik.vm.native.bridge', 'ro.zygote']
        result['platform'] = {key: device.shell('getprop', key).strip() for key in properties}
        result['platform']['page_size'] = device.shell('getconf', 'PAGE_SIZE').strip()
        if result['platform']['ro.build.version.sdk'] != '35':
            raise RuntimeError('Prepared AVD is not Android15/API35')
        install = device.adb('install', '-r', args.candidate.resolve(), check=False, timeout=120)
        result['actual_candidate_install'] = {'returncode': install.returncode,
            'stdout': install.stdout.decode(errors='replace'), 'stderr': install.stderr.decode(errors='replace')}
        if install.returncode:
            if ('INSTALL_FAILED_NO_MATCHING_ABIS' not in result['actual_candidate_install']['stderr']
                    + result['actual_candidate_install']['stdout']):
                raise RuntimeError('Candidate install failed for a reason other than the observed ABI limitation')
            result['candidate_install_limit'] = 'Exact ARM32 game APK cannot install on this measured API35 emulator ABI set'
        else:
            result['candidate_install_limit'] = None
        device.adb('install', '-r', '-t', probe, timeout=120)
        device.shell('am', 'start', '-W', '-n', ACTIVITY)
        def ready(size=(2640, 1080)):
            report = device.report()
            validate_geometry(report, identity, size)
            return report if report.get('window_focused') and report.get('resumed') else None
        initial, initial_capture = capture_settled_geometry(device, identity, (2640, 1080), 'initial')
        result['initial_geometry_capture'] = initial_capture
        child = validate_geometry(initial, identity, (2640, 1080))
        parent = initial['parent_bounds']
        cy, cx = (child[1] + child[3]) // 2, (child[0] + child[2]) // 2
        if not child[0] > parent[0] or not child[2] < parent[2]:
            raise ValueError('Wide-display probe requires two real black margins')
        before = len(initial['touch_events'])
        for x in ((parent[0] + child[0]) // 2, (child[2] + parent[2]) // 2):
            device.shell('input', 'tap', x, cy)
        time.sleep(1)
        bars = device.capture('black-margins')
        if geometry_key(bars) != geometry_key(initial):
            raise ValueError('Actual geometry changed after settled initial capture; margin input evidence retained')
        if len(bars['touch_events']) != before:
            raise ValueError('Black-margin tap reached SurfaceView fixture')
        result['physical_black_margins'] = {'black-margins': validate_black_margins(output / 'black-margins/screen.png', bars)}
        result['checks'].append('both-black-margin-taps-inert')
        device.shell('input', 'tap', cx, cy)
        time.sleep(.5)
        center = device.capture('center-tap')
        if geometry_key(center) != geometry_key(initial):
            raise ValueError('Actual geometry changed during center tap; input evidence retained')
        validate_center_tap(center['touch_events'][before:], child)
        result['checks'].append('center-tap-real-child-local-coordinates')
        before = len(center['touch_events'])
        device.shell('input', 'swipe', cx, cy, (parent[0] + child[0]) // 2, cy, '400')
        time.sleep(.5)
        outside = device.capture('drag-leaves-child')
        validate_cancel(outside['touch_events'][before:], child, 'Drag leaving child')
        result['checks'].append('drag-leaves-child-cancels-without-outside-move-or-up')
        before = len(outside['touch_events'])
        device.shell('am', 'start', '-W', '-n', ACTIVITY, '-f', '0x20000000',
                     '--es', 'probe_action', 'multi-pointer-cancel')
        def multi_ready():
            report = device.report()
            sequences = report.get('fixture_sequences', [])
            return report if (sequences and sequences[-1].get('state') == 'completed'
                and sequences[-1].get('touch_event_start') == before
                and len(report.get('touch_events', [])) >= before + 4) else None
        device.wait('fixed real-framework multi-pointer fixture completed', multi_ready)
        multi = device.capture('multi-pointer-cancel')
        sequence = multi['touch_events'][before:]
        if [event.get('action') for event in sequence] != [0, 5, 6, 3]:
            raise ValueError('Fixed multi-pointer fixture did not preserve the expected real dispatch sequence')
        validate_cancel(sequence, child, 'POINTER_UP followed by out-of-child MOVE')
        result['checks'].append('real-framework-lifted-pointer-retired-and-child-local-cancel-preserved')
        before = len(multi['touch_events'])
        device.shell('input', 'motionevent', 'DOWN', cx, cy)
        device.shell('input', 'keyevent', '3')
        time.sleep(.5)
        background = device.capture('home-during-touch')
        validate_cancel(background['touch_events'][before:], child, 'Home/focus loss')
        device.shell('input', 'motionevent', 'UP', cx, cy)
        device.shell('am', 'start', '-W', '-n', ACTIVITY, '-f', '0x20000')
        restored = device.wait('Home return', ready)
        if len(restored['touch_events']) < len(background['touch_events']):
            raise ValueError('Home return created a new fixture instead of resuming the same input owner')
        returned = device.capture('home-return')
        validate_geometry(returned, identity, (2640, 1080))
        result['home_visible_restoration'] = validate_visible_restoration(
            output / initial_capture / 'screen.png', initial, output / 'home-return/screen.png', returned)
        result['checks'].append('home-focus-loss-cancel-and-same-fixture-return')
        before = len(restored['touch_events'])
        device.shell('input', 'motionevent', 'DOWN', cx, cy)
        before_resize = device.report()
        natural_target = (1080, 2160) if restored['display_rotation'] in (1, 3) else (2160, 1080)
        result['resize_request'] = {'natural_dimensions': natural_target,
                                    'expected_physical_dimensions': [2160, 1080],
                                    'actual_rotation_before': restored['display_rotation']}
        device.shell('wm', 'size', f'{natural_target[0]}x{natural_target[1]}')
        def resized_report():
            report = device.report()
            return report if (report['physical_display_size'] == [2160, 1080]
                and report.get('report_sequence', 0) > before_resize.get('report_sequence', 0)) else None
        device.wait('actual physical resize and fresh framework report', resized_report)
        resized = device.capture('live-resized')
        validate_cancel(resized['touch_events'][before:], child, 'Viewport resize')
        device.shell('input', 'motionevent', 'UP', cx, cy)
        result['resize_request']['raw_live_coordinate_spaces'] = resized['coordinate_spaces']
        # Legacy nonresizable Activities may expose mixed/latched app geometry
        # during live wm-size changes. Retain that observation; do not reinterpret
        # old app pixels as physical coordinates or waive a helper-fit failure.
        try:
            geometry_projection(resized)
        except ValueError as error:
            result['resize_request']['live_geometry_limit'] = str(error)
            device.shell('am', 'force-stop', PACKAGE)
            device.shell('am', 'start', '-W', '-n', ACTIVITY)
            resized, capture = capture_settled_geometry(device, identity, (2160, 1080), 'resized-fresh-fixture')
            result['resize_request']['geometry_scope'] = 'New fixture process at resized display; live CANCEL tested separately'
        else:
            validate_geometry(resized, identity, (2160, 1080))
            result['resize_request']['geometry_scope'] = 'Live fixture; app-compatible bounds uniformly mapped to physical pixels'
            capture = 'live-resized'
        result['physical_black_margins']['resized'] = validate_black_margins(output / capture / 'screen.png', resized)
        device.shell('wm', 'size', 'reset')
        # Start clean after restoring physical geometry, preserving the exact
        # candidate helper bytes and all prior process evidence.
        device.shell('am', 'force-stop', PACKAGE)
        device.shell('am', 'start', '-W', '-n', ACTIVITY)
        restored, restored_capture = capture_settled_geometry(device, identity, (2640, 1080), 'restored')
        result['physical_black_margins']['restored'] = validate_black_margins(output / restored_capture / 'screen.png', restored)
        result['checks'].append('real-framework-resize-cancel-and-observed-resized-restored-fitted-surfaces')
        def rotation_ready(rotation):
            report = device.report()
            return report if report.get('display_rotation') == rotation else None
        reverse = result['reverse_landscape'] = {'status': 'unavailable', 'requested_rotation': 3}
        try:
            device.shell('settings', 'put', 'system', 'accelerometer_rotation', '1')
            device.shell('wm', 'user-rotation', 'lock', '3')
            sensor = device.adb('emu', 'sensor', 'set', 'acceleration', '9.8:0:0', check=False)
            reverse['sensor_stimulus'] = {'acceleration': '9.8:0:0', 'returncode': sensor.returncode,
                'output': (sensor.stdout + sensor.stderr).decode(errors='replace')}
            try:
                rotated = device.wait('actual reverse-landscape rotation3', lambda: rotation_ready(3), 15)
            except TimeoutError as error:
                reverse['limitation'] = str(error)
                device.capture('reverse-landscape-unavailable')
            else:
                validate_geometry(rotated, identity, (2640, 1080))
                rotated = device.capture('reverse-landscape')
                result['physical_black_margins']['reverse-landscape'] = validate_black_margins(output / 'reverse-landscape/screen.png', rotated)
                reverse.update(status='actual-rotation3-observed', observed_rotation=rotated['display_rotation'])
                result['checks'].append('actual-reverse-landscape-rotation3-fitted-surface')
        finally:
            sensor = device.adb('emu', 'sensor', 'set', 'acceleration', '-9.8:0:0', check=False)
            reverse['restore_sensor_stimulus'] = {'acceleration': '-9.8:0:0', 'returncode': sensor.returncode,
                'output': (sensor.stdout + sensor.stderr).decode(errors='replace')}
            device.shell('settings', 'put', 'system', 'accelerometer_rotation', '0')
            device.shell('wm', 'user-rotation', 'lock', '1')
            device.wait('restore actual landscape rotation1', lambda: rotation_ready(1), 15)
            device.wait('restore rotation1 viewport', ready)
            device.capture('rotation-restored')
        overlay_package = 'com.android.internal.display.cutout.emulation.tall'
        overlays = device.shell('cmd', 'overlay', 'list', '--user', '0')
        (output / 'cutout-overlays-before.txt').write_text(overlays)
        cutout = result['cutout_probe'] = {'package': overlay_package, 'status': 'unavailable',
            'scope': 'One stock tall-cutout developer overlay; no physical Samsung cutout certification'}
        if re.search(r'^\[ \] ' + re.escape(overlay_package) + r'$', overlays, re.M) and not re.search(
                r'^\[x\] com\.android\.internal\.display\.cutout\.emulation\.', overlays, re.M):
            enable = device.adb('shell', 'cmd', 'overlay', 'enable', '--user', '0', overlay_package, check=False)
            cutout['enable_returncode'] = enable.returncode
            cutout['enable_output'] = (enable.stdout + enable.stderr).decode(errors='replace')
            if enable.returncode == 0:
                try:
                    active = device.shell('cmd', 'overlay', 'list', '--user', '0')
                    (output / 'cutout-overlays-enabled.txt').write_text(active)
                    if not re.search(r'^\[x\] ' + re.escape(overlay_package) + r'$', active, re.M):
                        raise ValueError('Overlay command returned success but tall cutout is not enabled')
                    def nonzero_cutout():
                        report = device.report()
                        return report if any(report.get('display_cutout_insets') or []) else None
                    try:
                        enabled = device.wait('actual nonzero display cutout insets', nonzero_cutout, 15)
                    except TimeoutError as error:
                        cutout['limitation'] = 'Overlay enabled but no nonzero display cutout was observed: ' + str(error)
                        device.capture('cutout-no-effective-insets')
                    else:
                        validate_geometry(enabled, identity, (2640, 1080))
                        enabled = device.capture('cutout-enabled')
                        result['physical_black_margins']['cutout-enabled'] = validate_black_margins(output / 'cutout-enabled/screen.png', enabled)
                        (output / 'cutout-enabled-display.txt').write_text(device.shell('dumpsys', 'display'))
                        cutout.update(status='stock-overlay-nonzero-insets-observed',
                                      observed_system_insets=enabled.get('system_insets'),
                                      observed_display_cutout_insets=enabled['display_cutout_insets'],
                                      observed_window_cutout_insets=enabled.get('cutout_insets'),
                                      parent_bounds=enabled['parent_bounds'], child_bounds=enabled['child_bounds'])
                        result['checks'].append('one-stock-cutout-nonzero-insets-fitted-once')
                finally:
                    device.shell('cmd', 'overlay', 'disable', '--user', '0', overlay_package)
                    device.wait('restore original no-cutout-overlay viewport', ready)
                    device.capture('cutout-restored')
                    (output / 'cutout-overlays-restored.txt').write_text(device.shell('cmd', 'overlay', 'list', '--user', '0'))
        if cutout['status'] == 'unavailable' and 'limitation' not in cutout:
            cutout['limitation'] = 'Tall overlay absent/already-active or enable permission unavailable; no new cutout-emulation acceptance'
        result['status'] = 'platform-probe-passed-game-ABI-limit-recorded' if install.returncode else 'platform-probe-passed-candidate-installed-engine-untested'
    except BaseException as error:
        result['status'] = 'blocked'
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if emulator is not None:
            try:
                final = device.capture('final-platform-state')
                result['final_coordinate_spaces'] = final.get('coordinate_spaces')
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
                result['final_capture_error'] = str(error)
            for name, command in [('logcat.txt', ('logcat', '-d', '-v', 'threadtime')),
                                  ('properties.txt', ('shell', 'getprop'))]:
                try:
                    (output / name).write_bytes(device.adb(*command, check=False).stdout)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            emulator.terminate()
            try:
                emulator.wait(timeout=15)
            except subprocess.TimeoutExpired:
                emulator.kill(); emulator.wait()
        (output / 'platform-acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
        emulator_log.close()


if __name__ == '__main__':
    main()
