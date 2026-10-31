#!/usr/bin/env python3
"""Validate the exact source runtime and simulate every ELF32 relocation.

No game code executes. Run against the user-supplied APK before packaging.
The optional freshly built shim is checked for NX stack/no text relocations.
"""
import argparse
import collections
import hashlib
import json
import lzma
import pathlib
import re
import struct
import subprocess
import zipfile

EXPECTED_APK = "d42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0"
EXPECTED_PATCH_SITES = {
    0x37148: bytes.fromhex("00b581b000f018f8"),
    0x36434: bytes.fromhex("00b581b000f096fe"),
    0x3397c: bytes.fromhex("f0b5194e81b0336a"),
    0x169c8: bytes.fromhex("2af02abb4218034c"),
    0x223b8: bytes.fromhex("f0b5474680b41b4c"),
    0x3752c: bytes.fromhex("10b582b0041c0092"),
    0x3766c: bytes.fromhex("00b583b00b1c0021"),
}
EXPECTED_S3E_SHA256 = "8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a"
EXPECTED_UI_SCALE = bytes.fromhex(
    "10402de90040a0e12c009fe5001090e50000a0e30c00c1e5170ca0e3"
    "b047fdeb2f48fdeb000094e5080084e51040bde80020a0e10010a0e12f48fdea")
EXPECTED_UI_PROJECTION = bytes.fromhex(
    "70402de968509fe50040a0e1000095e50c00d0e5000050e30400a0017040bd08"
    "ba28fb0ab828fbeb000095e5080090e50020a0e10010a0e13b29fbeb000095e5"
    "0020a0e3201090e5240090e5fe35a0e3000051e1ad07a0c30000a0d3010180c2"
    "0210a0e12e29fbeb0400a0e17040bde81d29fbea")


def parse_elf(data):
    assert data[:7] == b"\x7fELF\x01\x01\x01", "Expected little-endian ELF32"
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    assert header[2] == 40 and header[1] == 3, "Expected ARM ET_DYN"
    phoff, phsize, phcount = header[5], header[9], header[10]
    assert phsize == 32
    ph = [struct.unpack_from("<IIIIIIII", data, phoff+i*32) for i in range(phcount)]
    return header, ph


def virtual_bytes(data, programs):
    size = max(p[2]+p[5] for p in programs if p[0] == 1)
    image = bytearray(size)
    for p in programs:
        if p[0] == 1:
            image[p[2]:p[2]+p[4]] = data[p[1]:p[1]+p[4]]
    return image


def dynamic_tags(image, programs):
    p = next(p for p in programs if p[0] == 2)
    tags = collections.defaultdict(list)
    for offset in range(p[2], p[2]+p[5], 8):
        tag, value = struct.unpack_from("<II", image, offset)
        if not tag:
            return tags
        tags[tag].append(value)
    raise AssertionError("Missing DT_NULL")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=pathlib.Path)
    parser.add_argument("--shim", type=pathlib.Path)
    parser.add_argument("--ndk", type=pathlib.Path, help="Audit imports against API28 ARM system library stubs")
    args = parser.parse_args()
    apk = args.apk.read_bytes()
    assert hashlib.sha256(apk).hexdigest() == EXPECTED_APK, "Unexpected source APK"
    with zipfile.ZipFile(args.apk) as archive:
        data = archive.read("lib/armeabi/libairplay.so")
        game = lzma.decompress(archive.read("assets/The Sims 3.s3e.jpg"))
    assert hashlib.sha256(game).hexdigest() == EXPECTED_S3E_SHA256, "Unexpected source S3E"
    assert struct.unpack_from("<I", game, 0x14)[0] == 0xd2a0
    game_code = game[0xd2a0:0xd2a0 + 0x166ad8]
    assert game_code[0xae180:0xae1bc] == EXPECTED_UI_SCALE, "UI scale fingerprint mismatch"
    assert game_code[0x135d50:0x135dc4] == EXPECTED_UI_PROJECTION, "UI projection fingerprint mismatch"
    for filename, profiles in [
        ('context_menu.c', [('render_head', 0x857ac, 68), ('render_tail', 0x86310, 40),
                            ('display_y', 0xae458, 152), ('convert_int', 0x1494a0, 16),
                            ('set_bounds', 0x81bc4, 16), ('render_return', 0x86338, 12)]),
        ('hud_input.c', [('input_head', 0x107254, 0x34),
                         ('pause_radius', 0x1073c4, 0x20),
                         ('buy_radius', 0x1074f8, 0x28),
                         ('sim_radius', 0x1075d8, 0x38),
                         ('bar_choice', 0x1077d0, 0x30),
                         ('convert_touch', 0xae4f0, 0xb0),
                         ('circle_hit', 0x11eeb0, 0x2c),
                         ('rect_hit', 0x11ef00, 0x38),
                         ('status_hit', 0x107834, 0x40),
                         ('status_width', 0x130a60, 0x4c),
                         ('display_scale', 0xae348, 0x20)]),
        ('shutdown_order.c', [('display_cleanup', 0x33f74, 64),
                              ('main_cleanup', 0x139260, 184),
                              ('dlc_cleanup', 0x5c52c, 28),
                              ('pack_image_release', 0xc3f44, 80)])]:
        source = pathlib.Path(__file__).with_name(filename).read_text()
        for name, offset, size in profiles:
            array = re.search(r'static const uint32_t ' + name + r'\[\] = \{([^}]+)\}', source)
            assert array, 'Missing game instruction guard: ' + filename + ':' + name
            words = [int(value, 16) for value in re.findall(r'(0x[0-9a-f]+)u', array[1])]
            expected = struct.pack('<' + 'I' * len(words), *words)
            assert len(expected) == size and game_code[offset:offset + size] == expected, \
                'Game instruction fingerprint mismatch: ' + filename + ':' + name
    for offset in (0x33fb4, 0xb1490, 0xb14a0):
        assert struct.unpack_from('<I', game_code, offset)[0] == 0x4a166b9c, \
            'Shutdown renderer global alias mismatch'
    # Resolve this function's tail branch against the original named import
    # table, rather than assuming offset0x27c is a particular GL operation.
    names = game[0x52:0xd2a0].split(b"\0")[:struct.unpack_from("<H", game, 0x50)[0]]
    imports_by_offset, cursor = {}, 0
    for name in names:
        assert game_code[cursor:cursor + 4] == bytes.fromhex("feffffea")
        imports_by_offset[cursor] = name.decode("ascii")
        cursor += 4
        if game_code[cursor:cursor + 4] == bytes.fromhex("7847c046"):
            cursor += 4
    branch = struct.unpack_from("<I", game_code, 0x135d88)[0]
    displacement = (branch & 0xffffff) << 2
    if displacement & 0x2000000:
        displacement -= 0x4000000
    target = 0x135d88 + 8 + displacement
    assert branch >> 24 == 0xeb and target == 0x27c
    assert imports_by_offset[target] == "glScalef"
    ui_projection_import = imports_by_offset[target]
    assert len(data) == 410811
    header, programs = parse_elf(data)
    # Decode the original wrapper's PC-relative LDR and confirm its private
    # dispatch slot against the unstripped ELF symbol table, not version globals.
    load_at = 0x3397e
    load_instruction = struct.unpack_from("<H", data, load_at)[0]
    assert load_instruction == 0x4e19  # LDR r6,[PC,#0x64]
    literal_at = ((load_at + 4) & ~3) + (load_instruction & 0xff) * 4
    table_base = struct.unpack_from("<I", data, literal_at)[0]
    dispatch_slot = table_base + 0x20
    assert literal_at == 0x339e4 and table_base == 0x55a44 and dispatch_slot == 0x55a64
    assert header[11] == 40
    sections = [struct.unpack_from("<IIIIIIIIII", data, header[6] + i*40)
                for i in range(header[12])]
    symbol_values = {}
    for section in sections:
        if section[1] != 2:  # SHT_SYMTAB
            continue
        table_strings = sections[section[6]]
        names = data[table_strings[4]:table_strings[4]+table_strings[5]]
        assert section[9] == 16
        for at in range(section[4], section[4]+section[5], 16):
            name_at, value, _, _, _, _ = struct.unpack_from("<IIIBBH", data, at)
            name = names[name_at:names.index(0, name_at)].decode("ascii")
            symbol_values[name] = value
    assert symbol_values["g_glGetString"] == dispatch_slot
    assert symbol_values["s3eGL_start"] == 0x210a5
    assert symbol_values["g_s3eAndroidGlobals"] == 0x53af0
    assert symbol_values["g_s3eGLGlobals"] == 0x55a04
    assert struct.unpack_from("<I", data, 0x210e8)[0] == 0x55a04
    assert struct.unpack_from("<I", data, 0x210ec)[0] == 0x1ff
    assert struct.unpack_from("<I", data, 0x210f0)[0] == 0x53af0
    assert any(p[0] == 1 and p[6] & 1 and p[2] <= 0x210a4 < p[2]+p[5]
               for p in programs), "Original GL start callback must be in executable ELF code"
    assert data[0x210a4:0x210ac] == bytes.fromhex("10b5104c104b2268")
    assert symbol_values["s3eStackSwitchCallS3EFuncR12_Void"] == 0x3c7f0
    assert symbol_values["g_LoaderStack"] == 0x56758
    assert symbol_values["g_s3eFibreGlobals"] == 0x54b68
    assert struct.unpack_from("<I", data, 0x3c964)[0] == 0x54b68
    assert symbol_values["s3eExecICacheFlush"] == 0x169c9
    assert symbol_values["_Z12get_mem_infoRiS_"] == 0x223b9
    assert symbol_values["AirplayView_onMotionEvent"] == 0x2148d
    assert symbol_values["g_s3ePointerGlobals"] == 0x55d80
    assert symbol_values["s3ePointerRegister"] == 0x3752d
    assert symbol_values["s3ePointerUnRegister"] == 0x3766d
    assert symbol_values["s3eCallbacksRegister"] == 0x26edd
    assert symbol_values["s3eCallbacksUnRegister"] == 0x27525
    assert symbol_values["s3eStackSwitchCallCallback"] == 0x3c558
    assert symbol_values["s3eStackSwitchGetDynamicCallbackAddr"] == 0x3c9a1
    assert data[0x26edc:0x26ee4] == bytes.fromhex("30b585b008ac20cc")
    assert data[0x27524:0x2752c] == bytes.fromhex("f0b557464e464546")
    assert data[0x3c558:0x3c560] == bytes.fromhex("f04f2de90050a0e1")
    assert data[0x3c9a0:0x3c9a8] == bytes.fromhex("f0b581b00e1c171c")
    assert struct.unpack_from("<I", data, 0x3ca94)[0] == 0x3c808
    assert data[0x41020:0x41028] == bytes.fromhex("f0b5051c0e1c030b")
    assert data[0x3c7f0:0x3c7fc] == bytes.fromhex("00402de997ffffeb0040bde8")
    assert struct.unpack_from("<I", data, 0x3c750)[0] == 0x56758
    assert any(p[0] == 1 and p[6] & 2 and p[2] <= 0x56758 < p[2]+p[5]
               for p in programs), "Saved loader SP must be in writable ELF data"
    assert any(p[0] == 1 and p[6] & 2 and p[2] <= dispatch_slot < p[2]+p[5]
               for p in programs), "GL dispatch slot must be in writable ELF data"
    image = virtual_bytes(data, programs)
    assert struct.unpack_from("<III", image, 0x457d8) == (0x46140, 0x46150, 0x2148d)
    assert image[0x46140:0x46140+14] == b"onMotionEvent\0"
    assert image[0x46150:0x46150+8] == b"(IIII)V\0"
    assert image[0x2148c:0x21494] == bytes.fromhex("00b5101c191c8622")
    assert any(p[0] == 1 and p[6] & 1 and p[2] <= 0x2148c < p[2]+p[5]
               for p in programs), "Original motion callback must be executable code"
    assert any(p[0] == 1 and p[6] & 2 and p[2] <= 0x55d80 and 0x55d80+48 <= p[2]+p[5]
               for p in programs), "Pointer diagnostics must sample writable runtime globals"
    tags = dynamic_tags(image, programs)
    assert tags[22], "Expected original DT_TEXTREL"
    assert all((p[6] & 3) != 3 for p in programs if p[0] == 1), "Unexpected RWX segment"
    assert tags[17] == [0x16f0] and tags[18] == [32936]
    assert tags[23] == [0x9798] and tags[2] == [1040]
    assert not any(tag in tags for tag in [7, 12, 25, 32]), "Unexpected constructors/RELA"
    strings_at = tags[5][0]
    strings_size = tags[10][0]
    strings = bytes(image[strings_at:strings_at+strings_size])
    syms_at = tags[6][0]
    hash_at = tags[4][0]
    _, symbol_count = struct.unpack_from("<II", image, hash_at)
    assert symbol_count == 167
    symbols = [struct.unpack_from("<IIIBBH", image, syms_at+i*16) for i in range(symbol_count)]

    def string(offset):
        assert 0 <= offset < strings_size
        return strings[offset:strings.index(0, offset)].decode("ascii")

    assert set(string(offset) for offset in tags[1]) == {
        "libc.so", "libm.so", "liblog.so", "libstdc++.so", "libz.so", "libdl.so"}
    imports = set()
    counters = collections.Counter()
    base = 0x60000000
    for offset, size in [(tags[17][0], tags[18][0]), (tags[23][0], tags[2][0])]:
        assert not size % 8
        for at in range(offset, offset+size, 8):
            target, info = struct.unpack_from("<II", image, at)
            index, kind = info >> 8, info & 0xff
            assert kind in [2, 21, 22, 23], f"Unsupported relocation {kind}"
            assert target % 4 == 0 and target+4 <= len(image)
            assert index < symbol_count
            counters[kind] += 1
            old = struct.unpack_from("<I", image, target)[0]
            if kind == 23:
                assert index == 0
                value = (old + base) & 0xffffffff
            else:
                name_off, address, _, _, _, section = symbols[index]
                name = string(name_off)
                if section == 0:
                    imports.add(name)
                    address = 0x70000000 + index * 16  # deterministic stand-in
                elif section != 0xfff1:
                    address += base
                value = (address + old if kind == 2 else address) & 0xffffffff
            struct.pack_into("<I", image, target, value)
    assert counters == {23: 4115, 2: 2, 22: 130}, counters
    for address, expected in EXPECTED_PATCH_SITES.items():
        assert image[address:address+8] == expected, "Runtime patch fingerprint mismatch"
        image[address:address+8] = bytes.fromhex("dff800f0") + struct.pack("<I", 0x71000001)
    onload = [s[1] for s in symbols if string(s[0]) == "JNI_OnLoad"]
    assert onload == [0x21115]
    results = {"source_apk_sha256": EXPECTED_APK,
               "legacy_elf_sha256": hashlib.sha256(data).hexdigest(),
               "relocations_simulated": sum(counters.values()),
               "relocation_types": dict(counters), "imports": sorted(imports),
               "allocator_guards": "pass", "gl_context_guard": "pass", "gl_dispatch_slot": hex(dispatch_slot), "jni_onload": hex(onload[0]),
               "ui_depth_profile": {"s3e_sha256": EXPECTED_S3E_SHA256,
                   "function": "0x135d50", "z_argument": "0x135d80",
                   "scale_import": ui_projection_import, "fingerprint": "pass"},
               "context_menu_profile": {"function": "0x857ac", "tail": "0x86310",
                   "rectangle": "0x81bc4", "anchor_y": "0xae458", "fingerprints": "pass"},
               "hud_input_profile": {"function": "0x107254", "circle_radii":
                   ["0x1073cc", "0x107500", "0x1075e0"], "bar_choice": "0x1077e0", "status_width_gateway": "0x107844",
                   "fingerprints": "pass"},
               "shutdown_order_profile": {"early": "0x33f94", "late": "0x1392d8",
                   "dlc_images": "0x5c52c", "fingerprints": "pass"}}
    if args.shim:
        shim_data = args.shim.read_bytes()
        _, shim_programs = parse_elf(shim_data)
        shim_tags = dynamic_tags(virtual_bytes(shim_data, shim_programs), shim_programs)
        assert 22 not in shim_tags, "Shim contains DT_TEXTREL"
        assert all((p[6] & 3) != 3 for p in shim_programs if p[0] == 1), "Shim has RWX LOAD"
        stack = next(p for p in shim_programs if p[0] == 0x6474e551)
        assert not stack[6] & 1, "Shim requests executable stack"
        results["shim_sha256"] = hashlib.sha256(shim_data).hexdigest()
        results["shim_hardening"] = "no text relocations; non-executable stack; no RWX LOAD segments"
    if args.ndk:
        assert args.shim, "--ndk requires --shim"
        toolchain = args.ndk / "toolchains/llvm/prebuilt/linux-x86_64"
        readelf = toolchain / "bin/llvm-readelf"
        system = toolchain / "sysroot/usr/lib/arm-linux-androideabi/28"
        available = set()
        for library in ["libc.so", "libm.so", "liblog.so", "libstdc++.so", "libz.so", "libdl.so"]:
            listing = subprocess.check_output([str(readelf), "--dyn-syms", "-W", str(system/library)], text=True)
            available.update(line.split()[-1].split("@")[0] for line in listing.splitlines()
                             if " DEFAULT " in line and " UND " not in line)
        listing = subprocess.check_output([str(readelf), "--symbols", "-W", str(args.shim)], text=True)
        builtins = {line.split()[-1] for line in listing.splitlines()
                    if len(line.split()) >= 8 and line.split()[6] != "UND" and line.split()[0].endswith(":")}
        custom = {"atexit", "__srget", "_Znaj", "_Znwj", "_ZdlPv", "_ZdaPv"}
        needed_builtins = {name for name in imports if name.startswith("__aeabi_")}
        assert needed_builtins <= builtins, f"Missing linked EABI helpers: {needed_builtins-builtins}"
        missing = imports - available - needed_builtins - custom
        assert not missing, f"Unresolved legacy imports: {sorted(missing)}"
        results["import_audit"] = {"imports_checked": len(imports), "missing": [],
                                   "compiler_rt_helpers": len(needed_builtins)}
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
