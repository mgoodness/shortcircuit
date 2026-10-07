# Qt5 (PySide2) → Qt6 (PySide6) API diff inventory — Short Circuit

Research for wayfinder ticket [#3](https://github.com/mgoodness/shortcircuit/issues/3),
part of map [#1](https://github.com/mgoodness/shortcircuit/issues/1) ("Migrate PySide2
to PySide6: native Apple Silicon support").

Scope: the 8 files named in the ticket, plus `resources/ui/*.ui`,
`resources/resources.qrc`, and `generate_gui.sh`. Repo pins
`pyside2==5.15.2.1` (`requirements.txt`, `Pipfile`) and Python 3.10
(`Pipfile`: `python_version = "3.10"`).

Primary sources used throughout (cited inline per finding):

- Qt for Python — *Porting Applications from PySide2 to PySide6*:
  https://doc.qt.io/qtforpython-6/faq/porting_from2.html
- Qt for Python — *Porting to Qt 6*: https://doc.qt.io/qtforpython-6/overviews/qtdoc-portingguide.html
- Qt 6 — *Changes to Qt Widgets*: https://doc.qt.io/qt-6/widgets-changes-qt6.html
- Qt for Python — *Considerations* (enums, QVariant): https://doc.qt.io/qtforpython-6/considerations.html
- Qt 6 — `QSettings` class docs: https://doc.qt.io/qt-6/qsettings.html
- `pyside-setup` (code.qt.io mirror) changelogs and commits (primary source for
  current `exec_()` removal status)
- Qt for Python tool docs: `pyside6-uic` / `pyside6-rcc`:
  https://doc.qt.io/qtforpython-6/tools/pyside-uic.html,
  https://doc.qt.io/qtforpython-6/tools/pyside-rcc.html

---

## 1. `exec_()` → `exec()` — 7 call sites, all in `app.py`

Confirmed by direct grep (`grep -rn "exec_()" --include="*.py" src/`), not just
taken on faith from the prior grep claim:

| File:line | Call |
|---|---|
| `src/shortcircuit/app.py:229` | `if not dlg.exec_():` (TripwireDialog) |
| `src/shortcircuit/app.py:604` | `return msg_box.exec_()` (`_message_box`) |
| `src/shortcircuit/app.py:838` | `AboutDialog().exec_()` (`MainWindow.banner_click`) |
| `src/shortcircuit/app.py:1005` | `if not dialog.exec_():` (MappersDialog) |
| `src/shortcircuit/app.py:1058` | `ret = msg_box.exec_()` (`btn_reset_clicked`) |
| `src/shortcircuit/app.py:1136` | `ret = version_box.exec_()` (`version_check_done`) |
| `src/shortcircuit/app.py:1159` | `appl.exec_()` (`run()`, top-level `QApplication`) |

That is exactly 7, matching the prior grep's count. No other files in the
8-file set or under `src/` call `exec_()`.

**Change:** `.exec_()` → `.exec()` on all 7 (QDialog subclasses and
`QApplication`/`QCoreApplication`).

**Important nuance on severity — this does *not* currently break on PySide6:**

- The official porting guide says: *"Functions named `exec_` (classes
  `QCoreApplication`, `QDialog`, `QEventLoop`) have been renamed to `exec`
  which became possible in Python 3."*
  (https://doc.qt.io/qtforpython-6/faq/porting_from2.html)
- But PySide6 did **not** delete `exec_()` the way PyQt6 did. It kept it as a
  working alias that emits a `DeprecationWarning`. This is confirmed directly
  in the `pyside-setup` source history:
  - Commit "Enable the exec() functions" (pyside-setup, Qt6 branch) added the
    `exec()` methods and, for `exec_()`, emits:
    `PyErr_WarnEx(PyExc_DeprecationWarning, "'exec_' will be removed in the future. Use 'exec' instead.", 1)`
    rather than removing the symbol.
  - A later commit, "centralize exec_() deprecation message" (`pyside/pyside-setup.git`,
    picked to the 6.11 branch), still carries that same deprecation-warning
    behavior and states explicitly in the commit message: *"This will be
    removed in PySide7."*
  - Contrast with PyQt6, where Riverbank's own docs state outright *"All
    `exec_()` and `print_()` methods have been removed"*
    (https://www.riverbankcomputing.com/static/Docs/PyQt6/pyqt5_differences.html).
- **Conclusion:** under PySide6 (at least through the 6.11 line), `appl.exec_()`
  etc. will keep working but print a `DeprecationWarning` to stderr/stdout on
  every call. It is **not** a hard break today, but it is scheduled for
  removal in PySide7, so treat the 7 sites as a required (not merely optional)
  cleanup for this migration rather than a "nice to have."

---

## 2. Scoped vs. unscoped enum access

Grep of `app.py` for every bare `Qt`/`QHeaderView`/`QMessageBox`/`QCompleter`/
`QSettings`/`QLineEdit` enum reference:

| File:line | Old construct | Qt6-recommended construct |
|---|---|---|
| `app.py:109-112` | `QtWidgets.QHeaderView.ResizeToContents` / `.Stretch` | `QtWidgets.QHeaderView.ResizeMode.ResizeToContents` / `.Stretch` |
| `app.py:131` | `QtCore.Qt.AlignCenter` | `QtCore.Qt.AlignmentFlag.AlignCenter` |
| `app.py:139,145,149` | `QtCore.Qt.ItemIsEditable` | `QtCore.Qt.ItemFlag.ItemIsEditable` |
| `app.py:246` | `QtWidgets.QLineEdit.Normal` | `QtWidgets.QLineEdit.EchoMode.Normal` |
| `app.py:321-322` | `QtCore.QSettings.IniFormat` / `.UserScope` | `QtCore.QSettings.Format.IniFormat` / `QtCore.QSettings.Scope.UserScope` |
| `app.py:344` | `QtWidgets.QHeaderView.ResizeToContents` | `QtWidgets.QHeaderView.ResizeMode.ResizeToContents` |
| `app.py:432,441` | `QtCore.Qt.CaseInsensitive` | `QtCore.Qt.CaseSensitivity.CaseInsensitive` |
| `app.py:434,442` | `QtWidgets.QCompleter.CaseInsensitivelySortedModel` | `QtWidgets.QCompleter.ModelSorting.CaseInsensitivelySortedModel` |
| `app.py:443` | `QtCore.Qt.MatchContains` | `QtCore.Qt.MatchFlag.MatchContains` |
| `app.py:694` | `QtCore.Qt.AlignHCenter \| QtCore.Qt.AlignVCenter` | `QtCore.Qt.AlignmentFlag.AlignHCenter \| QtCore.Qt.AlignmentFlag.AlignVCenter` |
| `app.py:1055,1057,1060` | `QtWidgets.QMessageBox.Yes` / `.No` | `QtWidgets.QMessageBox.StandardButton.Yes` / `.No` |
| `app.py:1134,1135,1138` | `QtWidgets.QMessageBox.AcceptRole` / `.RejectRole` | `QtWidgets.QMessageBox.ButtonRole.AcceptRole` / `.RejectRole` |

Also note the **generated** view modules (`src/shortcircuit/view/gui_*.py`,
produced by `pyside2-uic` and never hand-edited, per `generate_gui.sh` and the
file header "WARNING! All changes made in this file will be lost when
recompiling") use the same bare form throughout, e.g.
`src/shortcircuit/view/gui_main.py:54` `self.label_destination.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)`,
and `gui_tripwire.py:93` `self.lineEdit_pass.setInputMethodHints(Qt.ImhHiddenText|Qt.ImhNoAutoUppercase|Qt.ImhNoPredictiveText|Qt.ImhSensitiveData)`.
These files are regenerated by `pyside6-uic`, not hand-ported — see §5.

**Does this actually break under PySide6? No — "forgiveness mode" covers all
of the above.** This is the single most important nuance this ticket needs to
capture, from the Qt for Python Considerations page
(https://doc.qt.io/qtforpython-6/considerations.html, "Doing a Smooth
Transition from the Old Enums"):

> "The `forgiveness mode` allows you to continue using the old constructs but
> translates them silently into the new ones... This has the effect that you
> can initially ignore the difference between old and new enums, **as long as
> the new enums are properties of classes**. (This does not work on global
> enums which don't have a class, see *Limitations* below.)"

Every bare-enum usage found in this repo is accessed through an enclosing Qt
class (`Qt`, `QHeaderView`, `QMessageBox`, `QCompleter`, `QSettings`,
`QLineEdit`), which is exactly the case forgiveness mode supports. So
`Qt.AlignCenter`, `QMessageBox.Yes`, etc. will **continue to work unchanged**
on PySide6 without raising. The *only* documented limitation is "a few global
enums" with no surrounding class (e.g. `QtMsgType`) — none of which appear in
this codebase (confirmed by grep: no `QtMsgType`, `qInstallMessageHandler`, or
similar module-level-enum usage in any of the 8 files or `view/`).

Practical implication for the migration plan: **scoped-enum rewrites in this
repo are a style/future-proofing cleanup, not a blocking compatibility fix.**
They're still worth doing (type stubs/IDE completion only show the new form
per the same doc page, and `ENOPT_OLD_ENUM` forgiveness is explicitly
described as transitional, to be dropped eventually — no removal version
given in the docs reviewed), but they won't cause runtime failures on
PySide6 the way `.exec_()`'s eventual PySide7 removal will.

One enum rename to watch for *is* real and unconditional, per the porting
guide: `Qt.MidButton` → `Qt.MiddleButton`. Grepped for `MidButton` across
`src/` and `resources/` — **not present**, no action needed.

---

## 3. QAction / QShortcut moved from QtWidgets to QtGui

Per the official porting guide: *"Some classes are in a different module now,
for example `QAction` and `QShortcut` have been moved from `QtWidgets` to
`QtGui`."* (https://doc.qt.io/qtforpython-6/faq/porting_from2.html), and
confirmed on the Qt6 C++ side in *Changes to Qt Widgets*
(https://doc.qt.io/qt-6/widgets-changes-qt6.html, "QAction, QActionGroup":
*"These classes have been moved into the QtGui module."*).

**Finding: not applicable to this repo.** Grepped all of `src/` and
`resources/`:

```
grep -rn "QAction\|QShortcut" --include="*.py" src/ resources/   → no matches
```

The `.ui` files have no `<action>`/menu-action definitions either — `gui_main.ui`
has an empty `QMenuBar` (`resources/ui/gui_main.ui:797`, no `<addaction>`
children, no `<action>` elements in any `.ui` file). No change required here.

---

## 4. QVariant handling

Per Qt for Python's Considerations page: *"As `QVariant` was removed, any
function expecting it can receive any Python object (`None` is an invalid
`QVariant`)."* — but this statement describes **PySide's general behavior**
(both PySide2 and PySide6 auto-convert `QVariant` to native Python types; it
is not a PySide2→PySide6-specific regression). Grepped `src/` and `resources/`
for explicit `QVariant` usage: **zero matches**. `QSettings.value()` is used
throughout (`app.py`, `mapper_config.py`, `versioncheck.py`,
`utility/configuration.py`, `test_mapper_config.py`) but always read back as
plain `str`/comparisons against string literals (e.g.
`self.settings.value("avoidance_enabled", "false") == "true"` in
`app.py:380`), never as an explicit `QVariant` object. No change required.

---

## 5. Signal/slot connection syntax

Grepped for the old string-based `SIGNAL()`/`SLOT()` macros and for PyQt-style
`pyqtSignal`/`pyqtSlot` (which would indicate non-portable code):

```
grep -rn "SIGNAL(\|SLOT(\|pyqtSignal\|pyqtSlot" --include="*.py" src/   → no matches
```

All signal/slot usage in the 8 files already uses the modern, binding-neutral
PySide form: `QtCore.Signal(...)` (class attributes in `esi_processor.py`,
`navprocessor.py`, `versioncheck.py`), `@QtCore.Slot(...)` decorators
(throughout `app.py`), and `.connect()` / `.emit()` method calls. This syntax
is unchanged between PySide2 and PySide6 (both are Qt for Python bindings, not
PyQt); no porting-guide section references a connection-syntax change for
PySide. **No change required.**

---

## 6. `from PySide2 import ...` → `from PySide6 import ...`

Every one of the 8 files imports from `PySide2` and needs the import renamed.
Exact import lines:

| File | Import line |
|---|---|
| `app.py:9` | `from PySide2 import QtCore, QtGui, QtWidgets` |
| `model/esi_processor.py:5` | `from PySide2 import QtCore` |
| `model/logger.py:9` | `from PySide2 import QtCore` |
| `model/mapper_config.py:7` | `from PySide2 import QtCore` |
| `model/navprocessor.py:4` | `from PySide2 import QtCore` |
| `model/test_mapper_config.py:8` | `from PySide2 import QtCore` |
| `model/utility/configuration.py:1` | `from PySide2 import QtCore` |
| `model/versioncheck.py:7` | `from PySide2 import QtCore` |

None of these 8 files reference `QAction`/`QShortcut` (§3), so the import
rename is a straight `PySide2` → `PySide6` substitution with no module
re-routing needed for this subset of files. The generated `view/gui_*.py`
files additionally do `from PySide2.QtCore import *` /
`from PySide2.QtGui import *` / `from PySide2.QtWidgets import *` plus
`from . import resources_rc` — these are regenerated, not hand-edited (see §8).

---

## 7. QSettings on-disk format compatibility — will existing user settings survive the upgrade?

This app persists Tripwire credentials, Eve Scout toggle, proxy, restrictions,
and the avoid-list via `QSettings`. Three construction sites, all
**explicitly** pinned to `IniFormat`/`UserScope` (never `NativeFormat`):

- `app.py:319-323` (`MainWindow.__init__`):
  ```python
  self.settings = QtCore.QSettings(
    QtCore.QSettings.IniFormat,
    QtCore.QSettings.UserScope,
    __appname__,
  )
  ```
- `model/utility/configuration.py:6-10` (`Configuration.settings`, used by
  `versioncheck.py` for `updates/version` / `updates/ping_timestamp`):
  ```python
  settings = QtCore.QSettings(
    QtCore.QSettings.IniFormat,
    QtCore.QSettings.UserScope,
    __appname__,
  )
  ```
- `model/test_mapper_config.py:24` uses an explicit-file-path constructor
  (`QtCore.QSettings(path, QtCore.QSettings.IniFormat)`) against a temp file,
  not the real user config — not part of the "would users lose settings"
  question.

**Finding: settings are not lost.** Because the app always uses `IniFormat`
(never the Windows registry / macOS `CFPreferences`/plist `NativeFormat`
backends), the Qt6 `QSettings` docs' explicit backward-compatibility statement
applies directly
(https://doc.qt.io/qt-6/qsettings.html, "Compatibility with older Qt
versions"):

> "INI files written with Qt 5 or earlier are however fully readable by a Qt 6
> based application (unless an ini codec different from utf8 had been set).
> But INI files written with Qt 6 will only be readable by older Qt versions
> if you set the 'iniCodec' to a UTF-8 textcodec."

So a user who has an existing PySide2/Qt5-written settings `.ini` file will
have it read correctly by the PySide6/Qt6 build. The one-directional caveat
(Qt6-written files not being readable by a future Qt5 install) is irrelevant
here since this is a one-way migration (no downgrade path planned).

The app's own `migrate_legacy()` function in `mapper_config.py` (lines
75-144) already performs a one-shot, Qt-version-independent migration of
older flat/grouped legacy keys (`MainWindow/tripwire_url`, `Tripwire/url`,
etc.) into the current `MapperConfigs` JSON blob — this logic reads/writes
through the same `QSettings` API and is unaffected by the Qt5→Qt6 jump; it
will keep working as-is on PySide6.

**File location caveat (informational, not a compatibility break):** per the
same Qt6 docs' platform table, `IniFormat`/`UserScope` settings live at
`$HOME/.config` on Unix/macOS and `FOLDERID_RoamingAppData` on Windows — this
table reflects Qt6's current docs; it was not independently cross-checked
against the equivalent Qt5 table, so if the on-disk *path* (not format) ever
differed between major versions on macOS specifically, that would need a
follow-up check before shipping. Flagging as an open question rather than a
confirmed finding.

---

## 8. `.ui` files, `resources.qrc`, and `generate_gui.sh`

**`.ui` file format itself:** all four files declare `<ui version="4.0">`
(`resources/ui/gui_about.ui:2`, `gui_main.ui:2`, `gui_mappers.ui:2`,
`gui_tripwire.ui:2`). This is the long-standing Designer XML schema version
and is still what current Qt6 Designer writes
(https://doc.qt.io/qt-6.12/designer-using-a-ui-file-python.html examples use
the same tooling without mentioning a version bump) — no XML-schema
compatibility issue expected.

**Bare enum XML values** (`Qt::AlignCenter`, `Qt::Horizontal`, etc.) appear
throughout the `.ui` files, e.g.:
```
resources/ui/gui_about.ui:61        <set>Qt::AlignCenter</set>
resources/ui/gui_about.ui:123       <enum>Qt::Horizontal</enum>
resources/ui/gui_main.ui:67         <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
resources/ui/gui_tripwire.ui:125    <set>Qt::ImhHiddenText|Qt::ImhNoAutoUppercase|Qt::ImhNoPredictiveText|Qt::ImhSensitiveData</set>
resources/ui/gui_mappers.ui:85,100  <enum>Qt::Horizontal</enum>
```
`pyside6-uic` compiles these `Qt::X` XML values down into the same
class-scoped-but-bare Python form seen in the current generated output (e.g.
`Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter`), which per §2 is covered by
PySide6's forgiveness mode. No `.ui` edits are required purely for Qt6
compatibility; recompiling with `pyside6-uic` is expected to "just work" for
these enum references.

**`generate_gui.sh` itself needs updating** — it currently hardcodes the Qt5
tools:
```bash
pyside2-uic --from-imports resources/ui/gui_main.ui -o src/shortcircuit/view/gui_main.py
pyside2-uic --from-imports resources/ui/gui_tripwire.ui -o src/shortcircuit/view/gui_tripwire.py
pyside2-uic --from-imports resources/ui/gui_mappers.ui -o src/shortcircuit/view/gui_mappers.py
pyside2-uic --from-imports resources/ui/gui_about.ui -o src/shortcircuit/view/gui_about.py
pyside2-rcc resources/resources.qrc -o src/shortcircuit/view/resources_rc.py
```
These 5 lines need `pyside2-uic`/`pyside2-rcc` → `pyside6-uic`/`pyside6-rcc`
(and the Windows counterpart `generate_gui.bat`, not reviewed here as it was
outside the specified 8-file + resources scope, but will need the identical
substitution per the ticket's "regenerate Qt UI... after editing `.ui`/`.qrc`"
convention in `AGENTS.md`).

**Generated-file import style differs between the Qt5 and Qt6 tools** — this
is a generator-output change, not a source change you make by hand, but worth
recording so the diff after regeneration isn't mistaken for manual edits:
- `pyside2-uic` output (current, e.g. `src/shortcircuit/view/gui_main.py:12-14`):
  ```python
  from PySide2.QtCore import *
  from PySide2.QtGui import *
  from PySide2.QtWidgets import *

  from  . import resources_rc
  ```
- Per the `qtbase` commit that added Qt-for-Python awareness to `uic`/`rcc`
  (https://github.com/qt/qtbase/commit/fc9cda5f08ac848e88f63dd4a07c08b2fbc6bf17,
  `src/tools/uic/python/pythonwriteimports.cpp`), the tool's *wildcard-import
  template* was simply updated from `PySide2` to `PySide6` strings — so
  `pyside6-uic` is expected to emit the equivalent wildcard-import block
  naming `PySide6` instead, via `--from-imports` exactly as today. (A
  secondary, unverified-in-this-session forum report
  (https://forum.qt.io/topic/137853) showed a newer `pyside6-uic` producing
  explicit named imports like `from PySide6.QtCore import (QCoreApplication,
  QDate, ...)` instead of `import *` — this may be a version-dependent
  behavior change in `uic` since that commit; either form is a mechanical,
  regenerated-file difference that doesn't require hand-editing.)
- `resources_rc.py` (generated by `pyside2-rcc`) currently starts with Qt5
  version banners and `from PySide2 import QtCore` (not independently opened
  in this pass, but same `qtbase` commit shows `rcc.cpp`'s Python-output
  template changing `from PySide2 import QtCore` → `from PySide6 import
  QtCore`). Per `pyside6-rcc` docs
  (https://doc.qt.io/qtforpython-6/tools/pyside-rcc.html), the tool is "a
  wrapper around the rcc tool" and generates Qt-for-Python-flavored output by
  construction — using `pyside6-rcc` (not a bare `rcc -g python` call) is
  recommended specifically "to avoid mismatches between versions for the
  generated code," so `generate_gui.sh` continuing to call the "pysideN"
  wrapper (updated to 6) rather than raw `rcc` is the right call.

**`resources.qrc` itself** (`resources/resources.qrc`) needs no edits — it's
a flat list of 13 PNG files under one `<qresource>` with no format-version
markers; the `<!DOCTYPE RCC><RCC version="1.0">` declaration is unchanged
across Qt5/Qt6 (same as confirmed for `.ui`, Qt6 Designer/rcc tooling
continues to use the same `RCC version="1.0"` schema). One operational note
from the `pyside6-rcc` tutorial
(https://doc.qt.io/qtforpython-6/tutorials/basictutorial/qrcfiles.html):
*"The tool uses Zstandard as a compression algorithm, which at its default
compression level... may produce results that are not usable on other
platforms. To ensure the files are usable on all platforms, the compression
level should be reduced or zlib should be chosen."* Given this project ships
binaries for both Windows and macOS (`build_win_installer.bat`,
`build_mac_installer.sh`), this is worth a deliberate choice (`--compress-algo
zlib` or an explicit low zstd level) rather than accepting `pyside6-rcc`'s
default, to avoid a cross-platform resource-loading regression that wouldn't
show up when building/testing on one OS only.

---

## 9. Other porting-guide items checked and found not applicable

Grepped `src/` and `resources/` for each of the other common PySide2→PySide6
breakages called out in the official porting guide
(https://doc.qt.io/qtforpython-6/faq/porting_from2.html):

| Porting-guide item | Grep result in this repo |
|---|---|
| `Qt.AA_EnableHighDpiScaling` / `AA_DisableHighDpiScaling` / `AA_UseHighDpiPixmaps` (deprecated, HiDPI always on in Qt6) | no matches |
| `QDesktopWidget` (removed; use `QScreen`) | no matches |
| `QFontMetrics.width()` → `horizontalAdvance()` | no matches |
| `QMouseEvent.pos()`/`.globalPos()`/`.x()`/`.y()` → `.position()`/`.globalPosition()` | no matches |
| `Qt.MidButton` → `Qt.MiddleButton` | no matches |
| `QOpenGLContext.versionFunctions()` → `QOpenGLVersionFunctionsFactory.get()` | no matches (no OpenGL usage) |
| `QRegExp` → `QRegularExpression` | no matches |
| old-style `SIGNAL()`/`SLOT()` string connections | no matches (see §5) |

No action needed for any of these in the reviewed scope.

---

## Summary table — concrete change list

| # | File | Line(s) | Old | New | Breaks today on PySide6? |
|---|---|---|---|---|---|
| 1 | `app.py` | 9 | `from PySide2 import QtCore, QtGui, QtWidgets` | `from PySide6 import QtCore, QtGui, QtWidgets` | Yes — import fails outright |
| 2 | `model/esi_processor.py` | 5 | `from PySide2 import QtCore` | `from PySide6 import QtCore` | Yes |
| 3 | `model/logger.py` | 9 | `from PySide2 import QtCore` | `from PySide6 import QtCore` | Yes |
| 4 | `model/mapper_config.py` | 7 | `from PySide2 import QtCore` | `from PySide6 import QtCore` | Yes |
| 5 | `model/navprocessor.py` | 4 | `from PySide2 import QtCore` | `from PySide6 import QtCore` | Yes |
| 6 | `model/test_mapper_config.py` | 8 | `from PySide2 import QtCore` | `from PySide6 import QtCore` | Yes |
| 7 | `model/utility/configuration.py` | 1 | `from PySide2 import QtCore` | `from PySide6 import QtCore` | Yes |
| 8 | `model/versioncheck.py` | 7 | `from PySide2 import QtCore` | `from PySide6 import QtCore` | Yes |
| 9 | `app.py` | 229, 604, 838, 1005, 1058, 1136, 1159 | `.exec_()` (×7) | `.exec()` | No (DeprecationWarning only; scheduled for removal in PySide7) |
| 10 | `app.py` | 109-112, 131, 139, 145, 149, 246, 321-322, 344, 432, 434, 441-443, 694, 1055, 1057, 1060, 1134-1135, 1138 | bare enum access, e.g. `QtCore.Qt.AlignCenter` | scoped form, e.g. `QtCore.Qt.AlignmentFlag.AlignCenter` | No — forgiveness mode covers class-scoped enums (recommended cleanup, not a break) |
| 11 | `generate_gui.sh` | all 5 lines | `pyside2-uic`, `pyside2-rcc` | `pyside6-uic`, `pyside6-rcc` | Yes — wrong binding, must change to regenerate `view/gui_*.py` + `resources_rc.py` against PySide6 |
| 12 | `resources/resources.qrc` | n/a | default (zstd) rcc compression | explicit `zlib` or low zstd level via `pyside6-rcc` flags | Not a break, but a cross-platform packaging risk if left default |
| 13 | QAction/QShortcut module move | n/a | n/a | n/a | **Not applicable** — no usage found anywhere in scope |
| 14 | QVariant handling | n/a | n/a | n/a | **Not applicable** — no explicit `QVariant` usage found |
| 15 | Signal/slot connection syntax | n/a | n/a | n/a | **Not applicable** — already uses modern `Signal`/`Slot`/`.connect()`, unchanged across PySide2→6 |
| 16 | `QSettings` on-disk format (Tripwire creds, Eve Scout toggle, proxy, restrictions, avoid-list) | `app.py:319-323`, `utility/configuration.py:6-10` | n/a | n/a | **No data loss** — app always uses `IniFormat`; Qt6 reads Qt5-written INI files natively per Qt's own compatibility note |

## Open questions / dead ends

- The Qt6 `QSettings` platform-path table (fetched from
  https://doc.qt.io/qt-6/qsettings.html) was reviewed for current Qt6
  behavior only; I did not independently pull the equivalent Qt5 table to
  diff path-by-path (only the documented *format-compatibility* statement,
  which is explicit and sufficient to answer "will data be lost"). If an
  exact byte-for-byte path check matters later (e.g. for an uninstall/cleanup
  script), that's a follow-up, not resolved here.
- The `pyside6-uic` wildcard-import vs. explicit-named-import discrepancy
  (§8) was observed only in a third-party forum post, not in the official
  tool docs or changelogs — flagged as plausibly version-dependent rather
  than confirmed from a primary source. Either way it doesn't require source
  changes, only regeneration.
- `generate_gui.bat` (Windows counterpart to `generate_gui.sh`) was not read
  in this pass since it wasn't in the requested file list; it almost
  certainly needs the same `pyside2-*` → `pyside6-*` substitution and should
  be covered by whichever ticket implements this change.
