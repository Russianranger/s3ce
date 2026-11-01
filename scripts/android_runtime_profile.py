"""Pinned repository-local runtime profiles, separate from remote UI commands."""


def runtime_profile(branch):
    if branch == 'flip3':
        return {'name': 'flip3', 'candidate_staging': '.validation/flip3',
                'baseline_staging': '.publish/v0.1.13-camera-input',
                'screen_width': 2640, 'screen_height': 1080,
                'expected_game_bounds': (360, 0, 2280, 1080),
                'verify_letterbox': True, 'verify_home_return': True, 'verify_rotations': True}
    return {'name': 'main', 'candidate_staging': '.validation/camera-input',
            'baseline_staging': '.publish/v0.1.12-hud-startup',
            'screen_width': 1920, 'screen_height': 1080,
            'expected_game_bounds': None,
            'verify_letterbox': False, 'verify_home_return': False, 'verify_rotations': False}
