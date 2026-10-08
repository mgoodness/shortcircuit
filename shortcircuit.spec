# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the macOS ``.app``.

PyInstaller's CLI has no way to set the bundle version or arbitrary
``Info.plist`` keys -- ``version=`` and ``info_plist=`` exist only on ``BUNDLE``
in a spec file. The ``.app`` therefore builds from this spec (see
``build_mac_installer.sh``) so that ``CFBundleShortVersionString`` and
``CFBundleVersion`` report the real release version instead of PyInstaller's
hardcoded ``0.0.0`` default.

``__version__`` is release-please's single bump target; this spec must not carry
a second copy (see docs/adr/0002-both-macos-arches-and-fork-release-channel.md).

The target architecture is passed as a spec argument after ``--`` rather than
via ``--target-arch``: that is a makespec-only option, and PyInstaller rejects
it when building from a spec file.
"""

import os
import sys

# The package lives under src/, which the directory PyInstaller evaluates the
# spec from (the repo root) does not expose to the interpreter.
sys.path.insert(0, os.path.join(SPECPATH, 'src'))

from shortcircuit import __version__  # noqa: E402

target_arch = sys.argv[1] if len(sys.argv) > 1 else None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/database/*', 'database')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    # Defer to the interpreter: build_mac_installer.sh runs ``python -O``, and a
    # hardcoded level here would silently override it (asserts retained).
    optimize=None,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Short Circuit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources/images/app_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Short Circuit',
)
app = BUNDLE(
    coll,
    name='Short Circuit.app',
    icon='resources/images/app_icon.icns',
    bundle_identifier='net.opsgoodness.shortcircuit',
    version=__version__,
    info_plist={
        'CFBundleShortVersionString': __version__,
        'CFBundleVersion': __version__,
    },
)
