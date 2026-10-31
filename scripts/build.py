#!/usr/bin/env python3
"""Build the compatibility APK from the exact supplied original and local tools."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA256 = 'd42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0'

def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'apktool', 'sdk', 'ndk', 'jdk', 'keystore', 'signing-json'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--build-dir', type=Path, default=ROOT / 'build')
    p.add_argument('--dist-dir', type=Path, default=ROOT / 'dist')
    a = p.parse_args()
    if digest(a.input) != INPUT_SHA256:
        raise SystemExit('Unrecognized input APK: this patch set is version-specific.')
    a.sdk, a.ndk, a.jdk = a.sdk.resolve(), a.ndk.resolve(), a.jdk.resolve()
    build, dist = a.build_dir.resolve(), a.dist_dir.resolve()
    build.mkdir(parents=True, exist_ok=True)
    dist.mkdir(parents=True, exist_ok=True)
    decoded = build / 'decoded'
    env = os.environ.copy()
    env['JAVA_HOME'] = str(a.jdk)
    env['PATH'] = str(a.jdk / 'bin') + os.pathsep + env['PATH']
    def run(*command):
        print('+', ' '.join(str(v) for v in command), flush=True)
        subprocess.run([str(v) for v in command], check=True, env=env)
    java = a.jdk / 'bin/java'
    run(java, '-jar', a.apktool.resolve(), 'd', '-f', a.input.resolve(), '-o', decoded)
    for patch in ('apply', 'gl_version_config'):
        spec = importlib.util.spec_from_file_location('s3ce_' + patch, ROOT / 'patches' / (patch + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.apply(decoded)
    shutil.copyfile(ROOT / 'app/AndroidManifest.xml', decoded / 'AndroidManifest.xml')
    metadata = decoded / 'apktool.yml'
    data = metadata.read_text()
    data = data.replace('minSdkVersion: 3\n', 'minSdkVersion: 26\n')
    data = data.replace('targetSdkVersion: 7\n', 'targetSdkVersion: 28\n')
    data = data.replace('versionCode: 1\n', 'versionCode: 113\n')
    data = data.replace('versionName: 1.0\n', 'versionName: 0.1.13-camera-input\n')
    metadata.write_text(data)
    legacy = decoded / 'assets/compat/libairplay-legacy.so'
    legacy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(decoded / 'lib/armeabi/libairplay.so', legacy)
    shutil.rmtree(decoded / 'lib')
    libdir = decoded / 'lib/armeabi-v7a'
    libdir.mkdir(parents=True)
    env['ANDROID_NDK_HOME'] = str(a.ndk)
    run('bash', ROOT / 'native/build.sh', libdir / 'libairplay.so')
    notices = ROOT / 'native/THIRD_PARTY_NOTICES.md'
    if notices.exists():
        shutil.copyfile(notices, legacy.parent / 'THIRD_PARTY_NOTICES.md')
    pvrtc_license = ROOT / 'native/pvrtc/LICENSE.md'
    if pvrtc_license.exists():
        shutil.copyfile(pvrtc_license, legacy.parent / 'PowerVR-LICENSE.txt')
    versions = sorted((a.sdk / 'build-tools').iterdir(), key=lambda v: tuple(int(n) for n in v.name.split('.')))
    bt = versions[-1]
    android_jar = a.sdk / 'platforms/android-35/android.jar'
    classes, dex = build / 'launcher-classes', build / 'launcher-dex'
    if classes.exists(): shutil.rmtree(classes)
    if dex.exists(): shutil.rmtree(dex)
    classes.mkdir()
    dex.mkdir()
    run(a.jdk / 'bin/javac', '--release', '8', '-classpath', android_jar, '-d', classes,
        *sorted((ROOT / 'app/src').rglob('*.java')))
    run(bt / 'd8', '--min-api', '26', '--lib', android_jar, '--output', dex,
        *sorted(classes.rglob('*.class')))
    raw, aligned = build / 'unsigned.apk', build / 'aligned.apk'
    run(java, '-jar', a.apktool.resolve(), 'b', decoded, '-o', raw)
    with zipfile.ZipFile(raw, 'a') as apk:
        apk.write(dex / 'classes.dex', 'classes2.dex', compress_type=zipfile.ZIP_DEFLATED)
    run(bt / 'zipalign', '-f', '-p', '4', raw, aligned)
    signing = json.loads(a.signing_json.read_text())
    env['S3CE_STORE_PASS'] = signing['password']
    if not a.keystore.exists():
        a.keystore.parent.mkdir(parents=True, exist_ok=True)
        run(a.jdk / 'bin/keytool', '-genkeypair', '-keystore', a.keystore,
            '-storepass:env', 'S3CE_STORE_PASS', '-keypass:env', 'S3CE_STORE_PASS',
            '-alias', signing['alias'], '-dname', 'CN=S3CE Compatibility',
            '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000')
        a.keystore.chmod(0o600)
    final = dist / 'S3CE-0.1.13-camera-input-arm32.apk'
    run(bt / 'apksigner', 'sign', '--ks', a.keystore, '--ks-key-alias', signing['alias'],
        '--ks-pass', 'env:S3CE_STORE_PASS', '--key-pass', 'env:S3CE_STORE_PASS',
        '--out', final, aligned)
    run(bt / 'apksigner', 'verify', '--verbose', '--print-certs', final)
    badging = subprocess.check_output([str(bt / 'aapt'), 'dump', 'badging', str(final)], env=env, text=True)
    for expected in ("package: name='io.github.russianranger.s3ce' versionCode='113'",
                     "versionName='0.1.13-camera-input'", "targetSdkVersion:'28'",
                     "launchable-activity: name='com.ideaworks3d.thesims3.CompatActivity'"):
        if expected not in badging:
            raise SystemExit('Unexpected APK identity or launcher: ' + expected)
    run('python3', ROOT / 'scripts/verify.py', a.input.resolve(), final)
    run('python3', ROOT / 'native/verify_legacy.py', a.input.resolve(), '--shim', libdir / 'libairplay.so',
        '--ndk', a.ndk)
    (dist / 'SHA256SUMS').write_text(digest(final) + '  ' + final.name + '\n')
    print(final)

if __name__ == '__main__':
    main()
