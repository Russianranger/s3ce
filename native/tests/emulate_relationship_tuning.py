#!/usr/bin/env python3
"""Execute the original ARM loader/resolver/setter on a candidate APK's tuning.

Uses the supplied SHA-pinned original S3E and exact signed 0.1.15 baseline APK.
The candidate resource is extracted independently of the production patcher.
Actual scalar readers, vector constructors/copies/destructors, ordered threshold
comparisons, state writes and score clearing execute. Resource acquisition,
allocation/memcpy, unrelated delegated SimWorld consumers, logging, goal awards,
scene lookup and notification/art endpoints are modeled explicitly. Synthetic
relationship inputs are isolated in Unicorn; no Android process or save is edited.
This is instruction evidence, not completed Android conversation/animation proof.
"""
import argparse
import copy
import hashlib
import json
import lzma
from pathlib import Path
import struct
import zipfile

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR
from emulate_context_menu import Machine, REGS, SOURCE_SHA

BASELINE_APK_SHA = 'a759fb156efb526149e3c0e3a9ca3bba4d5646aff4198ae8946dbc7947c7f5eb'
BASELINE_RESOURCE_SHA = '778c385d6ee62e48bacfea06d5a61b71d1caced5a68b45edaf3cfdb1801511f4'
NAMES = {1: 'Ruth', 2: 'Jack', 6: 'Jake', 9: 'Walter', 11: 'Luke'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def resource(apk):
    """Independent read-only DZ entry6 extraction, no patch-module imports."""
    with zipfile.ZipFile(apk) as package:
        dz = package.read('assets/res.dz.jpg')
    assert dz[:4] == b'DTRZ'
    count, directories = struct.unpack_from('<HH', dz, 4)
    assert count == 678 and directories == 15
    cursor, names = 8, []
    for _ in range(count + directories):
        end = dz.index(0, cursor)
        names.append(dz[cursor:end].decode('utf-8'))
        cursor = end + 1
    table = cursor + count * 6 + 4
    assert names[7] == 'simsdata.bin'
    offset, size, duplicate, flags = struct.unpack_from('<4I', dz, table + 16 * 6)
    end = struct.unpack_from('<I', dz, table + 16 * 7)[0]
    assert table + 16 * count <= offset < end <= len(dz)
    body = dz[offset:end]
    if flags & 0x200:
        body = lzma.decompress(body, format=lzma.FORMAT_ALONE)
    assert len(body) == size == duplicate
    return body


class Loaded:
    def __init__(self, source, raw, high):
        self.p = p = Machine(source, high)
        self.v = v = p.vm
        body = p.zero(len(raw))
        v.mem_write(body, raw)
        stream = p.zero(32)
        p.call(0xb321c, (stream, body, len(raw)))

        def acquire(offset, args, sp):
            assert args[0] == 178
            p.ret(stream)
        p.hook(0x8c45c, acquire)
        # These independent SimWorld consumers are outside the parsed constants.
        for offset in (0xe7120, 0xdc120, 0xed2cc):
            p.hook(offset, lambda offset, args, sp: p.ret())
        self.db, owner = p.zero(0xa00), p.zero(0x1000)

        def stop(vm, pc, size, unused):
            vm.emu_stop()
        v.hook_add(UC_HOOK_CODE, stop, begin=p.code + 0xd3f80, end=p.code + 0xd3f80)
        v.reg_write(UC_ARM_REG_SP, p.stack_top)
        v.reg_write(UC_ARM_REG_LR, p.stop)
        for register, value in zip(REGS, (self.db, owner, p.code + 0x15f4e8, 0)):
            v.reg_write(register, value)
        v.emu_start(p.code + 0xd38b4, p.stop, count=10000000)
        assert v.reg_read(UC_ARM_REG_PC) == p.code + 0xd3f80
        self.consumed = p.read(stream + 0x1c)
        self.high = high
        self.graph = [dict(zip(('targets', 'channels', 'thresholds'), values))
                      for values in zip(self.nested(0x3e0, 'b'), self.nested(0x3f4, 'b'),
                                        self.nested(0x408, 'h'))]
        assert len(self.graph) == 15
        for row in self.graph:
            assert len(row['targets']) == len(row['channels']) == len(row['thresholds'])
        # Decode post-graph data to catch insertion/stream-alignment mistakes too.
        fields = ((0x3a4, 'b'), (0x3b8, 'h'), (0x3cc, 'h'), (0x420, 'h'),
                  (0x434, 'h'), (0x448, 'b'), (0x470, 'h'), (0x484, 'b'),
                  (0x498, 'b'), (0x4ac, 'b'), (0x4c0, 'b'))
        nested_fields = ((0x4d4, 'b'), (0x564, 'b'), (0x578, 'b'), (0x58c, 'i'),
                         (0x5a0, 'i'), (0x5b4, 'b'), (0x5c8, 'b'), (0x5dc, 'b'), (0x5f0, 'b'))
        self.preserved = {hex(field): self.flat(field, kind) for field, kind in fields}
        self.preserved.update({hex(field): self.nested(field, kind) for field, kind in nested_fields})
        self.state_data = self.make_flat(self.db + 0x8c4, [0] * 14, 'b')
        outer = self.make_flat(self.db + 0x8ec, [0] * 70, 'i')
        p.write(self.db + 0x8ec + 8, 14)
        self.scores = [self.make_flat(outer + i * 20, [0, 0], 'i') for i in range(14)]
        self.goals, self.notices, self.art = [], [], []
        p.hook(0xcaad8, lambda offset, args, sp: (self.goals.append(args[1]), p.ret()))
        p.hook(0x6214c, lambda offset, args, sp: (self.notices.append(args), p.ret()))
        p.hook(0xea7e4, lambda offset, args, sp: p.ret(0))
        p.hook(0xffd90, lambda offset, args, sp: (self.art.append(args), p.ret()))

    def vector(self, address, kind):
        p = self.p
        count, wrapper = p.read(address + 8), p.read(address + 12)
        assert count <= 1000
        if not count:
            return []
        data, stride = p.read(wrapper + 8), p.read(wrapper + 12)
        assert stride == struct.calcsize(kind)
        return list(struct.unpack('<' + kind * count, self.v.mem_read(data, stride * count)))

    def flat(self, field, kind):
        return self.vector(self.db + field - 12, kind)

    def nested(self, field, kind):
        p = self.p
        count, wrapper = p.read(self.db + field - 4), p.read(self.db + field)
        assert count <= 1000 and p.read(wrapper + 12) == 20
        data = p.read(wrapper + 8)
        return [self.vector(data + i * 20, kind) for i in range(count)]

    def make_flat(self, address, values, kind):
        p = self.p
        p.call({'b': 0x142934, 'i': 0x14343c}[kind], (address, len(values)))
        data = p.read(p.read(address + 12) + 8)
        self.v.mem_write(data, struct.pack('<' + kind * len(values), *values))
        return data

    def run(self, state, friendship, romance, npc, label):
        p, v = self.p, self.v
        before_states = [0] + [1] * 13
        before_states[npc] = state
        before_scores = [[i * 65536, -i * 65536] for i in range(14)]
        before_scores[npc] = [friendship, romance]
        v.mem_write(self.state_data, bytes(before_states))
        for data, values in zip(self.scores, before_scores):
            v.mem_write(data, struct.pack('<ii', *values))
        self.goals.clear()
        self.notices.clear()
        self.art.clear()
        expected = state
        row = self.graph[state]
        for target, channel, threshold in zip(row['targets'], row['channels'], row['thresholds']):
            score = before_scores[npc][channel]
            boundary = threshold * 65536
            if (threshold < 0 and score <= boundary) or (threshold >= 0 and score >= boundary):
                expected = target
                break
        result = p.call(0xce014, (self.db, npc))
        after_states = list(v.mem_read(self.state_data, 14))
        expected_states = before_states[:]
        expected_states[npc] = expected
        assert after_states == expected_states, (label, state, npc, expected, after_states)
        assert result == int(expected != state)
        after_scores = [list(struct.unpack('<ii', v.mem_read(data, 8))) for data in self.scores]
        expected_scores = copy.deepcopy(before_scores)
        if expected != state:
            expected_scores[npc] = [0, 0]
        assert after_scores == expected_scores
        if expected == 8 and state != 8:
            assert len(self.notices) == 1 and self.notices[0][2] == 2531, (label, state, npc, self.goals, self.notices)
            if state in (5, 6, 7):
                assert 12 in self.goals, (label, state, npc, self.goals)
            assert len(self.art) == 1
        if expected == state:
            assert not self.goals and not self.notices and not self.art
        return {'group': label, 'npc': npc, 'name': NAMES.get(npc), 'before': state,
                'friendship_16_16': friendship, 'romance_16_16': romance,
                'after': expected, 'other_npcs_unchanged': True,
                'score_reset': expected != state, 'high_mapping': self.high}


def cases(graph):
    for state in range(15):
        yield state, 0, 0, 1, 'neutral_all_states'
        yield state, 0, 30 * 65536, 1, 'romance_cap_all_states'
        # Exercise every original edge at its exact 16.16 boundary and neighbors.
        for channel, threshold in zip(graph[state]['channels'], graph[state]['thresholds']):
            for delta in (-1, 0, 1):
                values = [0, 0]
                values[channel] = threshold * 65536 + delta
                yield state, *values, 1, 'all_original_edge_boundaries'
    for npc in range(1, 14):
        for state in (6, 7):
            for romance in (10 * 65536 - 1, 10 * 65536, 30 * 65536):
                yield state, 0, romance, npc, 'new_edges_all_npcs'
    for state, friendship in ((5, -10), (5, 15), (6, -10), (6, 25), (7, -15)):
        yield state, friendship * 65536, 10 * 65536, 1, 'original_priority'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'baseline-apk', 'candidate-apk', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expected-candidate-sha256', required=True)
    args = parser.parse_args()
    source = args.source.read_bytes()
    assert digest(source) == SOURCE_SHA
    assert digest(args.baseline_apk.read_bytes()) == BASELINE_APK_SHA
    assert digest(args.candidate_apk.read_bytes()) == args.expected_candidate_sha256
    for apk in (args.baseline_apk, args.candidate_apk):
        with zipfile.ZipFile(apk) as package:
            packed_source = package.read('assets/The Sims 3.s3e.jpg')
        assert lzma.decompress(packed_source, format=lzma.FORMAT_ALONE) == source
    baseline_raw, candidate_raw = resource(args.baseline_apk), resource(args.candidate_apk)
    assert digest(baseline_raw) == BASELINE_RESOURCE_SHA
    assert len(candidate_raw) == len(baseline_raw) + 8
    records, loaders, changed = [], [], 0
    baseline_graph = None
    for high in (False, True):
        before, after = Loaded(source, baseline_raw, high), Loaded(source, candidate_raw, high)
        assert before.consumed == 8867 and after.consumed == 8875
        assert after.preserved == before.preserved
        expected_graph = copy.deepcopy(before.graph)
        for state in (6, 7):
            expected_graph[state]['targets'].append(8)
            expected_graph[state]['channels'].append(1)
            expected_graph[state]['thresholds'].append(10)
        assert after.graph == expected_graph
        baseline_graph = before.graph
        loaders.append({'high_mapping': high, 'baseline_cursor': before.consumed,
                        'candidate_cursor': after.consumed, 'all_15_graph_rows_checked': True,
                        'preserved_metadata_npc_traits_and_action_vectors': sorted(before.preserved)})
        for case in cases(before.graph):
            a, b = before.run(*case), after.run(*case)
            if a['after'] != b['after']:
                assert a['before'] in (6, 7) and a['after'] == a['before'] and b['after'] == 8
                changed += 1
            records.append({'baseline': a, 'candidate': b})
    result = {'source_sha256': SOURCE_SHA, 'baseline_apk_sha256': BASELINE_APK_SHA,
              'candidate_apk_sha256': args.expected_candidate_sha256,
              'baseline_resource_sha256': digest(baseline_raw),
              'candidate_resource_sha256': digest(candidate_raw),
              'boundary': __doc__, 'original_graph': baseline_graph, 'loaders': loaders,
              'summary': {'paired_cases': len(records), 'resolver_setter_runs': len(records) * 2,
                          'changed_cases': changed, 'failures': 0,
                          'all_other_results_unchanged': True, 'all_13_npcs_checked': True,
                          'both_relocations': True}, 'cases': records}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
