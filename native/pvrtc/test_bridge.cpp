#include "pvrtc_bridge.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>

int main() {
    /* Four identical opaque-red PVRTC words. This fixture is synthetic and
     * contains no extracted game artwork. */
    const uint32_t words[] = {0, 0xfc00fc00, 0, 0xfc00fc00,
                              0, 0xfc00fc00, 0, 0xfc00fc00};
    unsigned char pixels[16*8*4];
    std::memset(pixels, 0xcd, sizeof(pixels));
    assert(s3ce_pvrtc_decode(words, sizeof(words), 4, 8, 8, pixels, 8*8*4) == 0);
    for (unsigned i = 0; i < 8*8; ++i) {
        assert(pixels[i*4] == 255 && pixels[i*4+1] == 0 &&
               pixels[i*4+2] == 0 && pixels[i*4+3] == 255);
    }
    for (unsigned i = 8*8*4; i < sizeof(pixels); ++i) assert(pixels[i] == 0xcd);
    assert(s3ce_pvrtc_decode(words, sizeof(words), 2, 16, 8, pixels, sizeof(pixels)) == 0);
    for (unsigned i = 0; i < 16*8; ++i) {
        assert(pixels[i*4] == 255 && pixels[i*4+1] == 0 &&
               pixels[i*4+2] == 0 && pixels[i*4+3] == 255);
    }
    unsigned char unaligned[sizeof(words)+1];
    std::memcpy(unaligned+1, words, sizeof(words));
    assert(s3ce_pvrtc_decode(unaligned+1, sizeof(words), 4, 8, 8, pixels, sizeof(pixels)) == 0);
    for (unsigned i = 0; i < 8*8; ++i) assert(pixels[i*4] == 255 && pixels[i*4+3] == 255);
    /* Minimum PVRTC extent: decoder crops a full block to the requested size. */
    assert(s3ce_pvrtc_decode(words, sizeof(words), 4, 1, 1, pixels, 4) == 0);
    assert(s3ce_pvrtc_decode(words, sizeof(words)-1, 4, 8, 8, pixels, sizeof(pixels)) == -1);
    assert(s3ce_pvrtc_decode(words, sizeof(words), 4, 8, 8, pixels, 255) == -1);
    assert(s3ce_pvrtc_decode(words, sizeof(words), 3, 8, 8, pixels, sizeof(pixels)) == -1);
    assert(s3ce_pvrtc_decode(words, sizeof(words), 4, 7, 8, pixels, sizeof(pixels)) == -1);
    assert(s3ce_pvrtc_decode(words, sizeof(words), 4, 0, 8, pixels, sizeof(pixels)) == -1);
    assert(s3ce_pvrtc_decode(words, sizeof(words), 4, 8192, 8, pixels, sizeof(pixels)) == -1);
    assert(s3ce_pvrtc_decode(nullptr, sizeof(words), 4, 8, 8, pixels, sizeof(pixels)) == -1);
    assert(s3ce_pvrtc_decode(words, sizeof(words), 4, 8, 8, nullptr, sizeof(pixels)) == -1);
    std::puts("PVRTC bridge: solid-colour 2/4bpp, crop, output guard and invalid-buffer tests passed");
}
