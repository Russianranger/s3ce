"""Host validation boundaries only; actual API35 framework execution is separate."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flip3_platform import (HELPER, candidate_identity, validate_black_margins, validate_cancel,
                           validate_center_tap, validate_geometry, physical_size_from_wm,
                           projected_bounds, validate_visible_restoration)


class PlatformProbeTests(unittest.TestCase):
    def report(self):
        identity = {'apk_sha256': 'a' * 64, 'classes2_sha256': 'b' * 64}
        report = {'api': 35, 'display_size': [2640, 1080], 'failure': None,
                  'target_sdk': 28, 'hardware_accelerated': False, 'requested_orientation': 6, 'window_cutout_mode': 2,
                  'identity': {**identity, 'loaded_helper': HELPER, 'helper_loader': 'dalvik.system.DexClassLoader'},
                  'parent_class': HELPER, 'parent_bounds': [0, 0, 2640, 1080],
                  'child_bounds': [360, 0, 2280, 1080], 'child_measured_size': [1920, 1080],
                  'surface_frame': [1920, 1080], 'system_insets': [0, 0, 0, 0]}
        return report, identity

    def test_exact_candidate_dex_and_real_geometry_required(self):
        report, identity = self.report()
        self.assertEqual(validate_geometry(report, identity, (2640, 1080)), [360, 0, 2280, 1080])
        for key, value in [('api', 30), ('child_bounds', [0, 0, 2640, 1080]),
                           ('child_bounds', [359, 0, 2279, 1080]), ('surface_frame', [2640, 1080]),
                           ('system_insets', [0, 24, 0, 0]), ('parent_class', 'android.view.ViewGroup'),
                           ('target_sdk', 35), ('hardware_accelerated', True),
                           ('requested_orientation', 0), ('window_cutout_mode', 0),
                           ('failure', 'actual reflection failure')]:
            wrong = {**report, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_geometry(wrong, identity, (2640, 1080))
        wrong = copy.deepcopy(report)
        wrong['identity']['classes2_sha256'] = 'c' * 64
        with self.assertRaises(ValueError):
            validate_geometry(wrong, identity, (2640, 1080))

    def test_single_inset_owner_and_resized_content(self):
        report, identity = self.report()
        report.update(parent_bounds=[0, 24, 2640, 1080], system_insets=[0, 24, 0, 0],
                      child_bounds=[384, 25, 2256, 1078], child_measured_size=[1872, 1053], surface_frame=[1872, 1053])
        self.assertEqual(validate_geometry(report, identity, (2640, 1080)), report['child_bounds'])
        report.update(display_size=[2160, 1080], parent_bounds=[0, 0, 2160, 1080], system_insets=[0, 0, 0, 0],
                      child_bounds=[120, 0, 2040, 1080], child_measured_size=[1920, 1080], surface_frame=[1920, 1080])
        self.assertEqual(validate_geometry(report, identity, (2160, 1080)), report['child_bounds'])

    def test_natural_size_and_actual_app_compat_coordinates_are_owned_separately(self):
        wm = 'Physical size: 1080x2640\nOverride size: 1080x2160\n'
        self.assertEqual(physical_size_from_wm(wm, 1), [2160, 1080])
        self.assertEqual(physical_size_from_wm(wm, 3), [2160, 1080])
        self.assertEqual(physical_size_from_wm(wm, 0), [1080, 2160])
        with self.assertRaises(ValueError):
            physical_size_from_wm('Override size: 1080x2160\n', 1)
        report, identity = self.report()
        # Recorded failed-run helper bounds, paired with a derived uniform
        # compatibility-display fixture. The failed archive did not retain that
        # last Display-metrics sample; live execution must measure it anew.
        report.update(display_size=[2640, 1320], physical_display_size=[2160, 1080],
                      parent_bounds=[0, 115, 2640, 1146], child_bounds=[408, 117, 2232, 1143],
                      child_measured_size=[1824, 1026], surface_frame=[1824, 1026],
                      system_insets=[0, 0, 0, 59])
        self.assertEqual(validate_geometry(report, identity, (2160, 1080)), report['child_bounds'])
        self.assertAlmostEqual(projected_bounds(report, 'parent_bounds')[2], 2160)
        report['display_size'] = [2640, 1080]
        with self.assertRaisesRegex(ValueError, 'not uniform'):
            validate_geometry(report, identity, (2160, 1080))

    def test_physical_black_margin_pixels_cannot_be_substituted_by_geometry(self):
        report, identity = self.report()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'frame.png'
            image = Image.new('RGB', (2640, 1080), (0, 0, 0))
            ImageDraw.Draw(image).rectangle((360, 0, 2279, 1079), fill=(30, 110, 140))
            image.save(path)
            checks = validate_black_margins(path, report)
            self.assertEqual(sum(r['pixels'] for r in checks), 720 * 1080)
            image.putpixel((200, 540), (20, 0, 0)); image.save(path)
            with self.assertRaises(ValueError):
                validate_black_margins(path, report)

    def test_actual_nonzero_cutout_must_fit_once(self):
        report, identity = self.report()
        report.update(display_cutout_insets=[80, 0, 0, 0], parent_bounds=[80, 0, 2640, 1080],
                      child_bounds=[400, 0, 2320, 1080])
        self.assertEqual(validate_geometry(report, identity, (2640, 1080)), report['child_bounds'])
        report['child_bounds'] = [440, 0, 2360, 1080]
        with self.assertRaises(ValueError):
            validate_geometry(report, identity, (2640, 1080))

    def test_center_coordinates_and_cancellation_cannot_be_substituted(self):
        child = [360, 0, 2280, 1080]
        validate_center_tap([{'action': 0, 'x': 960, 'y': 540}, {'action': 1, 'x': 960, 'y': 540}], child)
        with self.assertRaises(ValueError):
            validate_center_tap([{'action': 0, 'x': 1320, 'y': 540}, {'action': 1, 'x': 1320, 'y': 540}], child)
        def event(action, x=100, y=540):
            return {'action': action, 'x': x, 'y': y, 'action_index': 0,
                    'pointers': [{'id': 0, 'x': x, 'y': y}]}
        validate_cancel([event(0), event(2), event(3)], child, 'exit')
        for events in ([{'action': 0}, {'action': 1}], [{'action': 0}, {'action': 3}, {'action': 1}],
                       [{'action': 0}, {'action': 2, 'x': -1, 'y': 540}, {'action': 3}]):
            with self.assertRaises(ValueError):
                validate_cancel(events, child, 'exit')
        # Actual API35 counterexample from the rejected candidate: DOWN was
        # child-local912,513, but super's special CANCEL path retained1320,516.
        with self.assertRaisesRegex(ValueError, 'child-local'):
            validate_cancel([event(0, 912, 513), event(3, 1320, 516)], child, 'Home')

    def test_pointer_up_retires_only_the_lifted_id_before_cancel(self):
        seven = {'id': 7, 'x': 300, 'y': 200}
        thirteen = {'id': 13, 'x': 380, 'y': 230}
        events = [{'action': 0, 'action_index': 0, 'pointers': [seven]},
                  {'action': 5, 'action_index': 1, 'pointers': [seven, thirteen]},
                  {'action': 6, 'action_index': 0, 'pointers': [seven, thirteen]},
                  {'action': 3, 'action_index': 0, 'pointers': [thirteen]}]
        validate_cancel(events, [360, 0, 2280, 1080], 'Remaining pointer')
        for points in ([seven, thirteen], [seven], [{**thirteen, 'x': 788}],
                       [{**thirteen, 'id': None}], [{**thirteen, 'x': float('nan')}]):
            wrong = [*events[:-1], {**events[-1], 'pointers': points}]
            with self.assertRaises(ValueError):
                validate_cancel(wrong, [360, 0, 2280, 1080], 'Remaining pointer')

    def test_visible_home_restoration_uses_actual_pixels(self):
        report, _ = self.report()
        with tempfile.TemporaryDirectory() as temporary:
            before, after = (Path(temporary) / name for name in ('before.png', 'after.png'))
            image = Image.new('RGB', (2640, 1080), (0, 0, 0))
            ImageDraw.Draw(image).rectangle((360, 0, 2279, 1079), fill=(30, 110, 140))
            image.save(before); image.save(after)
            self.assertTrue(validate_visible_restoration(before, report, after, report)['identical_after_return'])
            Image.new('RGB', image.size).save(after)
            with self.assertRaises(ValueError):
                validate_visible_restoration(before, report, after, report)

    def test_candidate_carrier_identity_preserved_and_ambiguous_dex_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            apk = Path(temporary) / 'candidate.apk'
            with zipfile.ZipFile(apk, 'w') as out:
                out.writestr('classes2.dex', b'dex\n035\0fixture')
            identity, payload = candidate_identity(apk)
            self.assertEqual(payload, b'dex\n035\0fixture')
            self.assertEqual(identity['helper'], HELPER)
            self.assertEqual(len(identity['classes2_sha256']), 64)
            with zipfile.ZipFile(apk, 'w') as out:
                out.writestr('classes.dex', b'dex\n035\0fixture')
            with self.assertRaises(ValueError):
                candidate_identity(apk)


if __name__ == '__main__':
    unittest.main()
