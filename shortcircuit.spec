# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller build for both platforms; run it through build_win_installer.bat
# or build_mac_installer.sh. On macOS the target architecture (arm64, x86_64 or
# universal2) is passed after `--`; the default is the running Python's.
#
# The app only uses QtCore, QtGui and QtWidgets, but PyInstaller's PySide6
# hooks collect every Qt plugin those modules can load, and the plugins drag
# in whole Qt modules (the virtual keyboard brings Quick and Qml, the PDF image
# format brings Pdf, TLS and TUIO touch bring Network). Filtering them out
# below roughly halves the bundle.

import argparse
import importlib.util
import os
import re
import sys
import tempfile

# The package's __init__ only defines metadata, so importing it is cheap.
sys.path.insert(0, os.path.join(SPECPATH, 'src'))
from shortcircuit import __version__

parser = argparse.ArgumentParser()
parser.add_argument('--target-arch', default=None)
target_arch = parser.parse_args().target_arch

# Qt modules nothing in the app needs once the plugins below are gone.
UNUSED_QT_MODULES = (
  'Network', 'OpenGL', 'Pdf', 'Qml', 'QmlMeta', 'QmlModels',
  'QmlWorkerScript', 'Quick', 'Svg', 'VirtualKeyboard',
)
# Qt6Quick.dll on Windows, QtQuick.framework on macOS.
UNUSED_QT_LIB = re.compile(
  r'(^|/)Qt6?(%s)(\.dll$|\.framework/)' % '|'.join(UNUSED_QT_MODULES)
)
# Only the native platform integration and widget styles are needed; images
# are all PNG, which QtGui decodes without a plugin.
QT_PLUGIN = re.compile(r'/plugins/([^/]+)/([^/]+)$')
KEPT_PLATFORMS = ('qwindows.dll', 'libqcocoa.dylib')
UNUSED_FILES = re.compile(
  r'(^|/)('
  # Qt's software OpenGL fallback; widgets paint without OpenGL.
  r'opengl32sw\.dll'
  # OpenSSL copies shipped for Qt's TLS plugin; Python's _ssl uses its own.
  r'|lib(crypto|ssl)-3-x64\.dll'
  # Universal CRT shims for pre-Windows 10 systems. Qt 6 and Python 3.13 need
  # Windows 10, which always loads its own UCRT and ignores app-local copies.
  r'|api-ms-win-[^/]+\.dll|ucrtbase\.dll'
  r')$',
  re.IGNORECASE,
)
# No QTranslator is installed, so Qt's own translations are never loaded.
QT_TRANSLATIONS = re.compile(r'^PySide6/(Qt/)?translations/')


def is_unused(dest):
  dest = dest.replace('\\', '/')
  if UNUSED_QT_LIB.search(dest) or UNUSED_FILES.search(dest):
    return True
  if QT_TRANSLATIONS.match(dest):
    return True
  plugin = QT_PLUGIN.search(dest)
  if plugin:
    kind, name = plugin.groups()
    if kind == 'styles':
      return False
    return not (kind == 'platforms' and name in KEPT_PLATFORMS)
  return False


def windows_version_file():
  """Path to the generated VERSIONINFO PyInstaller embeds in the exe.

  The generator is plain source (no PyInstaller or ``pefile`` import), so it
  can be loaded and called here without the Windows-only dependency. Its text
  is written under the temp dir because PyInstaller's ``--clean`` empties the
  workpath before the resource is read.
  """
  path = os.path.join(SPECPATH, 'scripts', 'windows_version_info.py')
  helper_spec = importlib.util.spec_from_file_location(
    'windows_version_info', path
  )
  helper = importlib.util.module_from_spec(helper_spec)
  helper_spec.loader.exec_module(helper)

  out = os.path.join(tempfile.gettempdir(), 'shortcircuit_version_info.txt')
  with open(out, 'w', encoding='utf-8') as fh:
    fh.write(helper.version_file())
  return out


a = Analysis(
  ['src/main.py'],
  pathex=['build/libs'],
  datas=[('src/database/*', 'database')],
  excludes=[
    'PySide6.QtNetwork',
    # Collected only because it's installed in the build venv; its runtime
    # hook then pulls in setuptools' vendored packages.
    'setuptools', 'pkg_resources', '_distutils_hack',
  ],
  optimize=1,
)
a.binaries = [entry for entry in a.binaries if not is_unused(entry[0])]
a.datas = [entry for entry in a.datas if not is_unused(entry[0])]

pyz = PYZ(a.pure)

if sys.platform == 'darwin':
  exe = EXE(
    pyz,
    a.scripts,
    [('O', None, 'OPTION')],
    exclude_binaries=True,
    name='Short Circuit',
    upx=False,
    console=False,
    target_arch=target_arch,
    icon='resources/images/app_icon.icns',
  )
  coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='Short Circuit')
  # PyInstaller's BUNDLE defaults CFBundleShortVersionString to 0.0.0, so the
  # bundle version is stamped from __version__ -- release-please's single bump
  # target. CFBundleVersion must be present too; Finder and the update check
  # read one or the other.
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
else:
  # The exe stays slugged, per the Windows convention of a space-free
  # filename; the user-visible name and the real version live in the
  # VERSIONINFO resource that Explorer, Task Manager and the taskbar read.
  exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION')],
    name='shortcircuit',
    upx=True,
    console=False,
    icon='resources/images/app_icon.ico',
    version=windows_version_file(),
  )
