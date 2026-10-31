"""Validate one frame-bound Android QA command; this module performs no I/O.

Pass the raw response bytes to validate_control so duplicate JSON keys and
nonstandard numeric constants are rejected before decoding. Coordinates are
actual PNG pixels, with an optional narrower app viewport supplied by the caller.
The returned command contains only fixed UI operations. In particular, finish
ends interaction and never asserts that gameplay or shutdown acceptance passed.
"""
import json
import math
import re

MAX_DOCUMENT_BYTES = 4096
MAX_SEQUENCE = 2**31 - 1
MAX_DIMENSION = 16384
MAX_WAIT_SECONDS = 60
MAX_SWIPE_MS = 2000
_RUN_ID = re.compile(r'[1-9][0-9]{0,24}')
_SHA256 = re.compile(r'[0-9a-f]{64}')


class ControlError(ValueError):
    """The document or its frame context is invalid; no command may run."""


def _fail(message):
    raise ControlError(message)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('duplicate JSON key')
        result[key] = value
    return result


def _invalid_constant(value):
    _fail('non-finite JSON constant')


def parse_control(raw):
    """Decode bounded strict JSON without executing, fetching or writing anything."""
    if type(raw) is str:
        try:
            encoded = raw.encode('utf-8', errors='strict')
        except UnicodeError as error:
            raise ControlError('control is not valid UTF-8') from error
    elif type(raw) is bytes:
        encoded = raw
    else:
        _fail('raw control must be UTF-8 bytes or text')
    if not encoded or len(encoded) > MAX_DOCUMENT_BYTES:
        _fail('control document is empty or too large')
    try:
        text = encoded.decode('utf-8', errors='strict')
        result = json.loads(text, object_pairs_hook=_unique_object,
                            parse_constant=_invalid_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        if isinstance(error, ControlError):
            raise
        raise ControlError('malformed control JSON') from error
    if type(result) is not dict:
        _fail('control must be a JSON object')
    return result


def _keys(value, required, optional=()):
    if type(value) is not dict:
        _fail('control object has the wrong type')
    keys = set(value)
    if not set(required) <= keys or not keys <= set(required) | set(optional):
        _fail('missing or unexpected control fields')


def _integer(value, low, high, field):
    # bool is an int subclass in Python, but is never a coordinate or sequence.
    if type(value) is not int or not low <= value <= high:
        _fail('invalid ' + field)
    return value


def _size(value):
    if type(value) not in (list, tuple) or len(value) != 2:
        _fail('invalid coordinate size')
    return tuple(_integer(n, 1, MAX_DIMENSION, 'coordinate size') for n in value)


def _frame_context(run_id, sequence, digest, coordinate_size, viewport):
    if type(run_id) is not str or not _RUN_ID.fullmatch(run_id):
        _fail('invalid expected run ID')
    _integer(sequence, 1, MAX_SEQUENCE, 'expected sequence')
    if type(digest) is not str or not _SHA256.fullmatch(digest):
        _fail('invalid expected frame SHA256')
    width, height = _size(coordinate_size)
    if viewport is None:
        viewport = (0, 0, width, height)
    if type(viewport) not in (list, tuple) or len(viewport) != 4:
        _fail('invalid app viewport')
    left, top, right, bottom = viewport
    for value in viewport:
        _integer(value, 0, MAX_DIMENSION, 'app viewport')
    if not 0 <= left < right <= width or not 0 <= top < bottom <= height:
        _fail('app viewport exceeds the PNG')
    return (width, height), (left, top, right, bottom)


def validate_control(document, expected_run_id, expected_seq,
                     expected_frame_sha256, coordinate_size, *, viewport=None):
    """Return a normalized command only when run, next sequence and frame match.

    Expected sequence is the *next* command number: command1 references frame0.
    The caller advances it only after executing and recording the returned UI
    operation. A key or relaunch operation must map to the caller's fixed known
    app/launcher; the control document cannot select a package or activity.
    """
    size, bounds = _frame_context(expected_run_id, expected_seq,
                                  expected_frame_sha256, coordinate_size, viewport)
    if type(document) in (bytes, str):
        document = parse_control(document)
    _keys(document, ('schema', 'run_id', 'seq', 'frame_sha256',
                     'coordinate_size', 'command'), ('note',))
    if type(document['schema']) is not int or document['schema'] != 1:
        _fail('unsupported control schema')
    if type(document['run_id']) is not str or document['run_id'] != expected_run_id:
        _fail('control belongs to another run')
    if _integer(document['seq'], 1, MAX_SEQUENCE, 'sequence') != expected_seq:
        _fail('stale or future control sequence')
    digest = document['frame_sha256']
    if type(digest) is not str or not _SHA256.fullmatch(digest) or digest != expected_frame_sha256:
        _fail('control references another frame')
    if type(document['coordinate_size']) is not list or _size(document['coordinate_size']) != size:
        _fail('control coordinate size does not match the frame')
    if 'note' in document:
        if type(document['note']) is not str or len(document['note']) > 256:
            _fail('invalid control note')
        try:
            document['note'].encode('utf-8', errors='strict')
        except UnicodeError as error:
            raise ControlError('invalid control note Unicode') from error
    command = document['command']
    if type(command) is not dict or type(command.get('type')) is not str:
        _fail('invalid command type')
    kind = command['type']
    left, top, right, bottom = bounds

    def point(x_key, y_key):
        x = _integer(command[x_key], left, right - 1, x_key)
        y = _integer(command[y_key], top, bottom - 1, y_key)
        return x, y

    if kind == 'tap':
        _keys(command, ('type', 'x', 'y'))
        x, y = point('x', 'y')
        return {'type': kind, 'x': x, 'y': y}
    if kind == 'swipe':
        _keys(command, ('type', 'x1', 'y1', 'x2', 'y2', 'duration_ms'))
        x1, y1 = point('x1', 'y1')
        x2, y2 = point('x2', 'y2')
        duration = _integer(command['duration_ms'], 50, MAX_SWIPE_MS, 'swipe duration')
        return {'type': kind, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'duration_ms': duration}
    if kind == 'wait':
        _keys(command, ('type', 'seconds'))
        seconds = command['seconds']
        if type(seconds) not in (int, float) or not 0 <= seconds <= MAX_WAIT_SECONDS:
            _fail('invalid wait duration')
        if type(seconds) is float and not math.isfinite(seconds):
            _fail('invalid wait duration')
        return {'type': kind, 'seconds': seconds}
    if kind == 'key':
        _keys(command, ('type', 'code'))
        code = _integer(command['code'], 3, 4, 'key code')
        return {'type': kind, 'code': code}
    if kind in ('relaunch', 'finish'):
        _keys(command, ('type',))
        return {'type': kind}
    _fail('command is not allowlisted')
