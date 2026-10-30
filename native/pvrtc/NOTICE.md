# PowerVR software texture decoder

`PVRTDecompress.cpp` and `PVRTDecompress.h` are unmodified files from
[Imagination Technologies' PowerVR Native SDK](https://github.com/powervr-graphics/Native_SDK)
at commit `63f0098acdc11ec9a072c30000d2fa670a955bee`.

Original paths:

- `framework/PVRCore/texture/PVRTDecompress.cpp`
- `framework/PVRCore/texture/PVRTDecompress.h`

The upstream MIT license is preserved in `LICENSE.md`.

SHA-256 of the preserved upstream files:

| File | SHA-256 |
| --- | --- |
| PVRTDecompress.cpp | 74559c5a4b8161aafce1ebe984bf8060896feaa81276b614491dbee755d6e4c7 |
| PVRTDecompress.h | 67123a36b99df380af76a65f3dfa3a7f368a153f5401b36a9ff1ed233cee6f5f |
| LICENSE.md | b1aea79afab593649ede742eccbb7feb74d216d52d120b99c4d349133871ba9f |

`pvrtc_bridge.cpp` and `.h` add S3CE buffer and dimension validation, a C
interface, word alignment for unaligned client data, and exception handling. `test_bridge.cpp` uses synthetic uniform-red
blocks to check PVRTC 2/4 bpp, cropping, unaligned inputs, output boundaries, and invalid inputs.
No extracted game assets are included.

A host check can be run with:

```sh
g++ -std=c++17 -O1 -g -fno-rtti -fsanitize=address,undefined \
  -fno-omit-frame-pointer native/pvrtc/PVRTDecompress.cpp \
  native/pvrtc/pvrtc_bridge.cpp native/pvrtc/test_bridge.cpp \
  -o /tmp/s3ce-pvrtc-test
ASAN_OPTIONS=detect_leaks=0 /tmp/s3ce-pvrtc-test
```

LeakSanitizer is disabled only because it cannot enumerate processes inside the
managed container; AddressSanitizer and UndefinedBehaviorSanitizer stay enabled.
