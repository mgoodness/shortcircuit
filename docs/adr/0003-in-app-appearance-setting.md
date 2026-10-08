---
status: accepted
---

# Keep an in-app appearance setting and drive native chrome via Qt's colour scheme

Short Circuit offers a Light / Dark / System appearance setting. Apple's Human
Interface Guidelines advise against app-specific appearance settings — people
"may think your app is broken because it doesn't respond to their systemwide
appearance choice" — and prefer an app to follow the system. We keep the
in-app setting anyway: it is a shipped feature, and this is a cross-platform
app (Windows and Linux users expect an in-app theme), not a macOS-only one.
**System** stays the default, so a user who never opens the View menu gets
OS-following behaviour.

The mechanism is Qt's own colour-scheme API rather than platform code. Pinned
modes call `QStyleHints.setColorScheme()`; System calls `unsetColorScheme()` so
Qt keeps following the OS and keeps emitting `colorSchemeChanged`. Qt carries
the choice to native chrome (macOS `NSAppearance`, Windows) and to the default
palette. `apply_color_scheme()` in
[`src/shortcircuit/view/theme.py`](../../src/shortcircuit/view/theme.py) is the
single place that does this; `MainWindow._apply_theme()` calls it and then
resolves the effective light/dark for the style sheet and widget colours.

## Considered options

- **Follow the OS only; drop the Light/Dark pins.** The Apple-idiomatic choice,
  and the least code. Rejected: it removes a shipped feature and ignores
  Windows and Linux, where an in-app theme is the norm.
- **Set `NSAppearance` directly through `libobjc`.** Works on macOS (it was
  tried first) but reimplements a public Qt API by hand, on one platform only,
  and needs `ctypes`. Rejected once Qt 6.8's `setColorScheme()` was confirmed to
  drive the same native appearance. Revisit only if a platform's theme does not
  implement `requestColorScheme()` — the offscreen platform and some Linux
  desktop themes currently do not.

## Consequences

The native effect is not observable under Qt's `offscreen` platform, which the
test suite uses, so the tests pin the mode→scheme mapping and assert the native
appearance in a macOS child process under `cocoa`.
