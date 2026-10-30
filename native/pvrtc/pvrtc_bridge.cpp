/* S3CE bounds validation around the PowerVR SDK reference decoder. */
#include "pvrtc_bridge.h"
#include "PVRTDecompress.h"
#include <algorithm>
#include <new>
#include <cstdint>
#include <cstring>
#include <vector>

extern "C" int s3ce_pvrtc_decode(const void *data, size_t data_size,
        unsigned bits_per_pixel, unsigned width, unsigned height,
        void *rgba, size_t rgba_size) {
    if (!data || !rgba || (bits_per_pixel != 2 && bits_per_pixel != 4) ||
        !width || !height || width > 4096 || height > 4096 ||
        (width & (width - 1)) || (height & (height - 1))) return -1;
    const unsigned minimum_width = bits_per_pixel == 2 ? 16 : 8;
    const size_t input_needed = static_cast<size_t>(std::max(width, minimum_width)) *
        std::max(height, 8u) * bits_per_pixel / 8;
    const size_t output_needed = static_cast<size_t>(width) * height * 4;
    if (data_size < input_needed || rgba_size < output_needed) return -1;
    try {
        /* GL client memory need not be word aligned; the upstream decoder
         * reads uint32_t words, so normalize only unaligned source buffers. */
        const void *source = data;
        std::vector<uint32_t> aligned;
        if (reinterpret_cast<uintptr_t>(data) % alignof(uint32_t)) {
            aligned.resize(input_needed / sizeof(uint32_t));
            std::memcpy(aligned.data(), data, input_needed);
            source = aligned.data();
        }
        const unsigned consumed = pvr::PVRTDecompressPVRTC(source,
            bits_per_pixel == 2 ? 1u : 0u, width, height,
            static_cast<unsigned char *>(rgba));
        return consumed == input_needed ? 0 : -2;
    } catch (const std::bad_alloc &) {
        return -2;
    } catch (...) {
        return -2;
    }
}
