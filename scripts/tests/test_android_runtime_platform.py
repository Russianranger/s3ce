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
from android_runtime_platform import HELPER, candidate_identity, validate_black_margins, validate_cancel, validate_center_tap, validate_geometry


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
        validate_cancel([{'action': 0}, {'action': 2, 'x': 100, 'y': 540}, {'action': 3}], child, 'exit')
        for events in ([{'action': 0}, {'action': 1}], [{'action': 0}, {'action': 3}, {'action': 1}],
                       [{'action': 0}, {'action': 2, 'x': -1, 'y': 540}, {'action': 3}]):
            with self.assertRaises(ValueError):
                validate_cancel(events, child, 'exit')

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
