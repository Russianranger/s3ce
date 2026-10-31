#include "game_pointer_observer.h"
#include <stdio.h>
#include <string.h>

static int address32(uintptr_t base, uint32_t offset, uintptr_t *result) {
    if (base > UINT32_MAX || offset > UINT32_MAX - base) return 0;
    *result = base + offset;
    return 1;
}

static int word(s3ce_game_read read, void *context, uintptr_t base,
                uint32_t offset, uint32_t *result) {
    uintptr_t address;
    unsigned char bytes[4];
    if (!address32(base, offset, &address) || address > UINT32_MAX - 3
            || !read(context, address, bytes, sizeof(bytes))) return 0;
    *result = (uint32_t)bytes[0] | (uint32_t)bytes[1] << 8
            | (uint32_t)bytes[2] << 16 | (uint32_t)bytes[3] << 24;
    return 1;
}

static int fingerprint(s3ce_game_read read, void *context, uintptr_t base,
                       uint32_t offset, const unsigned char expected[8]) {
    uintptr_t address;
    unsigned char bytes[8];
    return address32(base, offset, &address) && address <= UINT32_MAX - 7
            && read(context, address, bytes, sizeof(bytes))
            && !memcmp(bytes, expected, sizeof(bytes));
}

static int unavailable(char *out, size_t capacity, const char *stage) {
    snprintf(out, capacity, "Game input snapshot unavailable: %s", stage);
    return 0;
}

int s3ce_observe_game_pointer(uintptr_t base, uintptr_t original,
                            s3ce_game_read read, void *context,
                            char *out, size_t capacity) {
    static const unsigned char button[8] = {0x30,0x40,0x2d,0xe9,0x04,0x20,0x90,0xe5};
    static const unsigned char move[8] = {0x04,0xe0,0x2d,0xe5,0x00,0x10,0x90,0xe5};
    static const unsigned char getter[8] = {0x04,0x00,0x9f,0xe5,0x00,0x00,0x90,0xe5};
    uintptr_t button_address, move_address, expected_engine_vtable, menu_vtable, game_vtable;
    if (!out || !capacity) return 0;
    out[0] = 0;
    if (!read || !address32(base, 0x3aeb4, &button_address)
            || !address32(base, 0x3af84, &move_address)
            || !address32(base, 0x15f690, &expected_engine_vtable)
            || !address32(base, 0x15fb70, &menu_vtable)
            || !address32(base, 0x15fac8, &game_vtable)
            || (original != button_address && original != move_address))
        return unavailable(out, capacity, "unrecognized callback/profile");
    if (!fingerprint(read, context, base, 0x3aeb4, button)
            || !fingerprint(read, context, base, 0x3af84, move)
            || !fingerprint(read, context, base, 0xeddd4, getter))
        return unavailable(out, capacity, "source instruction guard");

    uint32_t display_slot, display_again, scene_display, globals, globals_again, getter_slot;
    if (!word(read, context, base, 0x3af78, &display_slot)
            || !word(read, context, base, 0x3afdc, &display_again)
            || !word(read, context, base, 0x11644c, &scene_display)
            || !word(read, context, base, 0x3af7c, &globals)
            || !word(read, context, base, 0x3afe0, &globals_again)
            || !word(read, context, base, 0xedde0, &getter_slot))
        return unavailable(out, capacity, "relocated literal reads");
    uintptr_t globals_expected, getter_expected;
    if (!display_slot || (display_slot & 3)
            || display_slot != display_again || display_slot != scene_display
            || globals != globals_again
            || !address32(display_slot, 8, &globals_expected) || globals != globals_expected
            || !address32(globals, 0xa0, &getter_expected) || getter_slot != getter_expected)
        return unavailable(out, capacity, "relocated split-data layout");

    uint32_t engine, engine_again, engine_vtable, active, counts_record, counts_data, count0, count1, scene;
    uint32_t engine420, engine430, transition424, direction428, speed42c;
    if (!word(read, context, globals, 0x44, &engine)
            || !word(read, context, getter_slot, 0, &engine_again))
        return unavailable(out, capacity, "AppEngine global reads");
    if (!engine || (engine & 3) || engine != engine_again
            || !word(read, context, engine, 0, &engine_vtable) || engine_vtable != expected_engine_vtable)
        return unavailable(out, capacity, "AppEngine pointer/vtable");
    if (!word(read, context, engine, 0x330, &active)
            || !word(read, context, engine, 0x340, &counts_record)
            || !counts_record || (counts_record & 3)
            || !word(read, context, counts_record, 8, &counts_data)
            || !counts_data || (counts_data & 3)
            || !word(read, context, counts_data, 0, &count0)
            || !word(read, context, counts_data, 4, &count1)
            || !word(read, context, engine, 0x40, &scene)
            || !word(read, context, engine, 0x420, &engine420)
            || !word(read, context, engine, 0x424, &transition424)
            || !word(read, context, engine, 0x428, &direction428)
            || !word(read, context, engine, 0x42c, &speed42c)
            || !word(read, context, engine, 0x430, &engine430))
        return unavailable(out, capacity, "AppEngine queue/scene reads");
    if (!scene) {
        snprintf(out, capacity, "Game input AppEngine=0x%08x active=%u counts=%u,%u engine420=%u engine430=%u transition424=0x%08x direction428=%d speed42c=%u Scene=none",
                 engine, active, count0, count1, engine420 & 255, engine430 & 255,
                 transition424, (int32_t)direction428, speed42c);
        return 1;
    }
    uint32_t scene_vtable;
    if ((scene & 3) || !word(read, context, scene, 0, &scene_vtable))
        return unavailable(out, capacity, "Scene pointer/vtable read");
    if (scene_vtable != menu_vtable && scene_vtable != game_vtable) {
        snprintf(out, capacity, "Game input AppEngine=0x%08x active=%u counts=%u,%u engine420=%u engine430=%u transition424=0x%08x direction428=%d speed42c=%u Scene=other vtable=0x%08x",
                 engine, active, count0, count1, engine420 & 255, engine430 & 255,
                 transition424, (int32_t)direction428, speed42c, scene_vtable);
        return 1;
    }
    uint32_t state, primary, origin_x, origin_y, current_x, current_y;
    if (!word(read, context, scene, 0x84, &state)
            || !word(read, context, scene, 0x90, &primary)
            || !word(read, context, scene, 0x98, &origin_x)
            || !word(read, context, scene, 0x9c, &origin_y)
            || !word(read, context, scene, 0xa0, &current_x)
            || !word(read, context, scene, 0xa4, &current_y))
        return unavailable(out, capacity, "Scene gesture fields");
    char menu[140] = "";
    if (scene_vtable == menu_vtable) {
        uint32_t menu_state, menu_route, menu_transition, angle_bits;
        float angle;
        if (!word(read, context, scene, 0x1ac, &menu_state)
                || !word(read, context, scene, 0xf8, &menu_route)
                || !word(read, context, scene, 0x1bc, &menu_transition)
                || !word(read, context, scene, 0xe20, &angle_bits))
            return unavailable(out, capacity, "SceneMenu state/CAS angle");
        memcpy(&angle, &angle_bits, sizeof(angle));
        snprintf(menu, sizeof(menu), " menuState=%u menuRoute=%d menu1bc=%u angleBits=0x%08x angle=%.5g",
                 menu_state, (int32_t)menu_route, menu_transition, angle_bits, (double)angle);
    }
    snprintf(out, capacity,
             "Game input AppEngine=0x%08x active=%u counts=%u,%u%s engine420=%u engine430=%u "
             "transition424=0x%08x direction428=%d speed42c=%u Scene=%s@0x%08x "
             "gesture=%u primary=%u origin=%d,%d current=%d,%d%s",
             engine, active, count0, count1,
             active > 1 || count0 > 50 || count1 > 50 ? " INVALID_QUEUE" : "",
             engine420 & 255, engine430 & 255,
             transition424, (int32_t)direction428, speed42c,
             scene_vtable == menu_vtable ? "SceneMenu" : "SceneGame", scene,
             state, primary, (int32_t)origin_x, (int32_t)origin_y,
             (int32_t)current_x, (int32_t)current_y, menu);
    return 1;
}
