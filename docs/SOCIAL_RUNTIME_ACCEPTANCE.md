# 0.1.15 Flip3 socials — validation in progress

Frozen candidate: S3CE-0.1.15-flip3-socials-arm32.apk, code115,76774745bytes.
SHA256 a759fb156efb526149e3c0e3a9ca3bba4d5646aff4198ae8946dbc7947c7f5eb.
Original signing certificate, package/private data, ARM32,4KiB,min26,target28.
Recovered source parent ec4ee9fc1e8e5044824ce7903852157380347f98.

Host/native evidence:16 native programs;64 Java startup admission assertions;
52 runtime harness tests; exact candidate assembled boot/input/audio/surface/
session/viewport suites and original-asset/signature/hardening checks pass.
All107 original Image2D objects produce identical pixels/mips with borrowed
source, plus12 compiled adapter ownership/cleanup cases. See
[sanitized image receipt](social-image-validation.json) and
[mechanism and limits](SOCIAL_IMAGES.md). These are not Android social completion.

Actual candidate Android execution and separate manual visual acceptance are
pending. Target:API30 x86/ARMv7 translation with2640x1080 display;API35 exact
helper framework probe separately. New direct-Main entry test must start a fresh
process bypassing Boot, validate native initialization order and show normal menu.
Count it separately from normal cold starts. Retain every failed attempt.

Physical Samsung evidence belongs to0.1.14:good UI and reported Hot Smooch crash
on SM-F711U1/Android15. Candidate115 Hot Smooch completion with the user's save
remains a phone regression. No game phase, memory, relationship or save writes
are allowed to manufacture it. Runtime saves must be ordinary gameplay.
