# Development handoff

First compatibility candidate is published as `v0.1.0-compat`. Source + payload
publication commit: `34d4c197e810966e23d1f457e7dc2beddc11a9fa`.
See VALIDATION.md for the artifact/certificate hashes and successful CI receipt.

Do not call this a playable port yet. Next meaningful gate is a Thor test:
startup, menu, create Sim, enter house, audio/touch, save/reload, suspend/resume.
Use the launcher's Share diagnostics report for Java/loader failures. Native
crashes require an Android logcat/tombstone, including fault address and loaded
map. Since the original ELF is loaded manually, its mapping is anonymous.
The current loader logs size but not its base address; infer the mapping base
from the tombstone map or add address logging in the next diagnostic build.

ARM32 support, 4 KiB pages, and target SDK 28 are deliberate current constraints.
Do not raise target SDK or claim ARM64/16 KiB support without reworking the S3E
code-memory layout and proving execution. Preserve the original Java/JNI class
names even though the manifest application ID is different.

The exact original APK is required to rebuild; scripts reject other inputs.
The separately saved private `S3CE-private-signing-backup.zip` contains the key
and signing configuration for future install-over updates. Never add that
backup, its password, or the keystore to this public repository.

Temporary APK upload chunks are removed from the current source branch after
publication; the pinned manifest remains. CI retries fetch the existing release
when chunks are absent and verify it against the same digest/certificate. A new
candidate requires its own version, manifest, signing-preserving build, and
release-workflow update.
