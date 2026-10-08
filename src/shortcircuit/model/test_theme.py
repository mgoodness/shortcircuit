# test_theme.py
"""
Tests for the theme-resolution logic in ``view/theme.py``.

The light/dark/system preference is mostly Qt plumbing (menus, QSettings,
style swapping), which the app already exercises end to end. ``resolve_dark``
is the one piece worth testing directly: it is pure, needs no QApplication,
and is exactly the decision the rest of the feature is wired around.
"""

from PySide6 import QtCore

from shortcircuit.view.theme import (
  THEME_DARK,
  THEME_LIGHT,
  THEME_MODES,
  THEME_SYSTEM,
  resolve_dark,
)

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
