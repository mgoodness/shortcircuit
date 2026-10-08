# test_theme.py
"""
Tests for the theme logic in ``view/theme.py``.

``resolve_dark`` is pure and needs no QApplication, so it is tested directly.
``apply_color_scheme`` is the piece that reaches native chrome: Qt drives the
OS title bar from the colour scheme, but the offscreen platform this suite
selects ignores ``setColorScheme``, so the native effect is checked under the
real cocoa platform in a child process.
"""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6 import QtCore

from shortcircuit.view import theme
from shortcircuit.view.theme import (
  THEME_DARK,
  THEME_LIGHT,
  THEME_MODES,
  THEME_SYSTEM,
  resolve_dark,
)

_SRC = Path(__file__).resolve().parents[2]

_DARK = QtCore.Qt.ColorScheme.Dark
_LIGHT = QtCore.Qt.ColorScheme.Light
_UNKNOWN = QtCore.Qt.ColorScheme.Unknown


def test_exposes_the_three_modes():
  assert THEME_MODES == (THEME_LIGHT, THEME_DARK, THEME_SYSTEM)


def test_pinned_dark_mode_ignores_the_os_scheme():
  for scheme in (_DARK, _LIGHT, _UNKNOWN):
    assert resolve_dark(THEME_DARK, scheme) is True


def test_pinned_light_mode_ignores_the_os_scheme():
  for scheme in (_DARK, _LIGHT, _UNKNOWN):
    assert resolve_dark(THEME_LIGHT, scheme) is False


def test_system_mode_follows_the_os_scheme():
  assert resolve_dark(THEME_SYSTEM, _DARK) is True
  assert resolve_dark(THEME_SYSTEM, _LIGHT) is False


def test_system_mode_treats_an_unknown_scheme_as_light():
  # Some platforms never report a scheme; falling back to light matches the
  # historical default rather than guessing.
  assert resolve_dark(THEME_SYSTEM, _UNKNOWN) is False


def test_unrecognised_mode_falls_back_to_following_the_os():
  assert resolve_dark("sepia", _DARK) is True
  assert resolve_dark("sepia", _LIGHT) is False


class _RecordingHints:
  """Stands in for QStyleHints, recording which scheme call was made."""

  def __init__(self):
    self.calls = []

  def setColorScheme(self, scheme):
    self.calls.append(("set", scheme))

  def unsetColorScheme(self):
    self.calls.append(("unset", None))


def test_apply_color_scheme_pins_light_dark_and_unpins_for_system(monkeypatch):
  hints = _RecordingHints()
  monkeypatch.setattr(
    theme,
    "QtGui",
    SimpleNamespace(QGuiApplication=SimpleNamespace(styleHints=lambda: hints)),
  )
  theme.apply_color_scheme(THEME_DARK)
  theme.apply_color_scheme(THEME_LIGHT)
  theme.apply_color_scheme(THEME_SYSTEM)
  assert hints.calls == [
    ("set", QtCore.Qt.ColorScheme.Dark),
    ("set", QtCore.Qt.ColorScheme.Light),
    ("unset", None),
  ]


# Qt drives the OS title bar from the colour scheme, but the offscreen platform
# this suite selects ignores setColorScheme, so the native effect is checked
# under the real cocoa platform in a child process.
_MACOS_APPEARANCE_PROBE = """
import ctypes
import ctypes.util

from PySide6 import QtWidgets

from shortcircuit.view import theme

app = QtWidgets.QApplication([])
theme.apply_color_scheme(theme.THEME_DARK)

objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")
objc.objc_getClass.restype = ctypes.c_void_p
objc.objc_getClass.argtypes = [ctypes.c_char_p]
objc.sel_registerName.restype = ctypes.c_void_p
objc.sel_registerName.argtypes = [ctypes.c_char_p]
msg = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
  ("objc_msgSend", objc)
)
sel = lambda name: objc.sel_registerName(name.encode())
nsapp = msg(objc.objc_getClass(b"NSApplication"), sel("sharedApplication"))
appearance = msg(nsapp, sel("effectiveAppearance"))
name = msg(appearance, sel("name"))
print(ctypes.c_char_p(msg(name, sel("UTF8String"))).value.decode())
"""


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS native chrome")
def test_apply_color_scheme_darkens_the_native_macos_appearance():
  result = subprocess.run(
    [sys.executable, "-c", _MACOS_APPEARANCE_PROBE],
    capture_output=True,
    text=True,
    timeout=60,
    env=dict(os.environ, QT_QPA_PLATFORM="cocoa", PYTHONPATH=str(_SRC)),
  )
  assert result.returncode == 0, result.stderr
  assert result.stdout.strip() == "NSAppearanceNameDarkAqua"
