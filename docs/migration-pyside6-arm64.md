# Migrating Short Circuit from PySide2/Qt5 to PySide6/Qt6 (native Apple Silicon)

> **Superseded in part.** [ADR-0002](adr/0002-both-macos-arches-and-fork-release-channel.md)
> retains Intel support, so both macOS architectures now build. The arm64-only
> instructions below describe the original, narrower plan.

Consolidated execution spec produced by the [Migrate PySide2 to PySide6: native Apple Silicon support](https://github.com/mgoodness/shortcircuit/issues/1) wayfinder map. Every decision below was resolved on that map's child tickets; this document synthesizes them into a top-to-bottom checklist so an implementer (human or `/implement-spec`) doesn't need to re-read the tracker. Links back to each ticket are included for the full reasoning/evidence trail.

## Platform support statement (the destination)

- **macOS: arm64 and x86_64.** Both build. [ADR-0001](adr/0001-arm64-only-macos-no-rosetta.md) dropped Intel, but [ADR-0002](adr/0002-both-macos-arches-and-fork-release-channel.md) supersedes it: PySide6's universal2 wheel makes the second slice cheap enough to keep.
- **Windows / Linux: unchanged**, still x86_64. This migration does not touch their build or CI legs.
- **Codesigning / notarization: unchanged (still unsigned).** Explicitly out of scope — see "Out of scope" below.
- **Python: bump 3.10 → 3.13.** Python 3.10 reached end-of-life October 1, 2026.

## 1. Dependency changes (`Pipfile`)

Source: [Decide target Python version](https://github.com/mgoodness/shortcircuit/issues/6), [Decide CI runner and build-script changes](https://github.com/mgoodness/shortcircuit/issues/4), [Research: PySide6 packaging facts](https://github.com/mgoodness/shortcircuit/issues/2).

```diff
 [dev-packages]
-pyinstaller = "*"
+pyinstaller = ">=6.4"
 pylint = "*"
 yapf = "*"
 pytest = "*"
 debugpy = "*"

 [packages]
 requests = {extras = ["socks"], version = "*"}
 semver = "*"
 python-dateutil = "*"
-pyside2 = "*"
+pyside6 = "*"
 typing-extensions = "*"
-importlib-resources = "*"
 appdirs = "*"

 [requires]
-python_version = "3.10"
+python_version = "3.13"
```

- `pyinstaller = ">=6.4"`: floor needed for the macOS/arm64 `.framework`-bundle-preservation and `QtNetwork`/OpenSSL fixes (PyInstaller 6.0.0 and 6.4.0 respectively); current stable is `6.22.3`, comfortably clears it.
- `pyside2` → `pyside6`: the actual migration. No arm64-only wheel exists — PySide6 ships one universal2 wheel on PyPI regardless of target; the arm64-only *build* win comes entirely from PyInstaller's `--target-arch` thinning (§4), not from the installed package.
- `importlib-resources` dropped entirely: zero usage found anywhere in `src/` (confirmed by grep), unrelated dead weight.
- No other dependency needs a floor bump — `typing-extensions`, `appdirs`, `requests`, `semver`, `python-dateutil` already lock to versions that support Python 3.13 cleanly. Just regenerate `Pipfile.lock` after the above changes (`pipenv lock`), consistent with this repo's existing unpinned (`"*"`) style for those packages.

## 2. Regenerate Qt UI/resource modules

Source: [Research: Qt5-to-Qt6 API diff inventory](https://github.com/mgoodness/shortcircuit/issues/3).

Update both `generate_gui.sh` and `generate_gui.bat`, swapping the Qt5 tool names for their Qt6 equivalents (5 lines in each file):

```diff
-pyside2-uic --from-imports resources/ui/gui_main.ui -o src/shortcircuit/view/gui_main.py
-pyside2-uic --from-imports resources/ui/gui_tripwire.ui -o src/shortcircuit/view/gui_tripwire.py
-pyside2-uic --from-imports resources/ui/gui_mappers.ui -o src/shortcircuit/view/gui_mappers.py
-pyside2-uic --from-imports resources/ui/gui_about.ui -o src/shortcircuit/view/gui_about.py
-pyside2-rcc resources/resources.qrc -o src/shortcircuit/view/resources_rc.py
+pyside6-uic --from-imports resources/ui/gui_main.ui -o src/shortcircuit/view/gui_main.py
+pyside6-uic --from-imports resources/ui/gui_tripwire.ui -o src/shortcircuit/view/gui_tripwire.py
+pyside6-uic --from-imports resources/ui/gui_mappers.ui -o src/shortcircuit/view/gui_mappers.py
+pyside6-uic --from-imports resources/ui/gui_about.ui -o src/shortcircuit/view/gui_about.py
+pyside6-rcc resources/resources.qrc -o src/shortcircuit/view/resources_rc.py
```

(`generate_gui.bat` has the identical 5 lines with Windows-style backslash paths — same tool-name substitution, no path changes.)

Then **run it** (`./generate_gui.sh`) to regenerate `src/shortcircuit/view/gui_main.py`, `gui_tripwire.py`, `gui_mappers.py`, `gui_about.py`, and `resources_rc.py` against PySide6. Per `AGENTS.md`, these files are generated — never hand-edit them; the regeneration is the fix.

No `.ui`/`.qrc` *source* edits are required for Qt6 compatibility — the `<ui version="4.0">` schema and `RCC version="1.0"` schema are both unchanged in Qt6, and `pyside6-uic` compiles the existing bare-enum XML (`Qt::AlignCenter`, etc.) into forgiveness-mode-compatible Python (see §3.2).

**One packaging decision folded in here**: `pyside6-rcc` defaults to Zstandard compression, which the tool's own docs warn "may produce results that are not usable on other platforms" at default compression level. Since this project ships both Windows and macOS binaries, pass an explicit `--compress-algo zlib` (or a low zstd level) when regenerating, rather than accepting the default — otherwise this is a latent cross-platform resource-loading regression that wouldn't surface testing on one OS alone.

## 3. Source code changes — 8 hand-edited files

Source: [Research: Qt5-to-Qt6 API diff inventory](https://github.com/mgoodness/shortcircuit/issues/3) (full file: `research/qt5-to-qt6-api-diff` branch).

### 3.1 Import rename — required, all 8 files (hard break without this)

| File | Line | Change |
|---|---|---|
| `src/shortcircuit/app.py` | 9 | `from PySide2 import QtCore, QtGui, QtWidgets` → `from PySide6 import QtCore, QtGui, QtWidgets` |
| `src/shortcircuit/model/esi_processor.py` | 5 | `from PySide2 import QtCore` → `from PySide6 import QtCore` |
| `src/shortcircuit/model/logger.py` | 9 | same substitution |
| `src/shortcircuit/model/mapper_config.py` | 7 | same substitution |
| `src/shortcircuit/model/navprocessor.py` | 4 | same substitution |
| `src/shortcircuit/model/test_mapper_config.py` | 8 | same substitution |
| `src/shortcircuit/model/utility/configuration.py` | 1 | same substitution |
| `src/shortcircuit/model/versioncheck.py` | 7 | same substitution |

None of these 8 files use `QAction`/`QShortcut` (which move from `QtWidgets` to `QtGui` in Qt6), so this is a straight string substitution — no module re-routing needed.

### 3.2 `.exec_()` → `.exec()` — required cleanup, not a hard break today

7 call sites, all in `app.py`: lines **229, 604, 838, 1005, 1058, 1136, 1159**. PySide6 keeps `.exec_()` working as a deprecation-warning alias (unlike PyQt6, which removed it outright) — but it's confirmed, in the `pyside-setup` source history, scheduled for removal in **PySide7**. Treat as required for this migration, not optional polish.

### 3.3 Scoped enum access — recommended cleanup, not a hard break

~20 call sites in `app.py` (`QHeaderView.ResizeToContents` → `.ResizeMode.ResizeToContents`, `Qt.AlignCenter` → `Qt.AlignmentFlag.AlignCenter`, `QMessageBox.Yes` → `.StandardButton.Yes`, etc. — full line-by-line list in the research artefact's §2 summary table). PySide6's "forgiveness mode" silently translates every one of these because they're all accessed through an enclosing Qt class — confirmed no bare/global-enum usage (the one case forgiveness mode doesn't cover) exists anywhere in this codebase. **Not required to ship**, but worth doing in the same pass since IDE/type-stub completion only shows the new scoped form.

One enum *rename* (not just rescoping) to double check during this pass: `Qt.MidButton` → `Qt.MiddleButton` is unconditional in Qt6 — confirmed **not present** in this codebase, no action needed, just flagging so it isn't missed if new code adds it later.

### 3.4 Not applicable — confirmed, no action needed

- **QAction/QShortcut relocation**: no usage anywhere in `src/` or `resources/`.
- **QVariant handling**: no explicit `QVariant` usage; `QSettings.value()` calls throughout already read back as plain `str`.
- **Signal/slot syntax**: already uses modern `QtCore.Signal`/`@QtCore.Slot`/`.connect()` — identical across PySide2 and PySide6.
- **`QRegExp`, `QDesktopWidget`, `QFontMetrics.width()`, `QMouseEvent.pos()`, HiDPI `AA_*` flags, OpenGL version-functions API**: none present in this codebase (full negative-match table in the research artefact §9).

### 3.5 `QSettings` — confirmed no data loss for existing users

This app persists Tripwire credentials, the Eve Scout toggle, proxy settings, restrictions, and the avoid-list via `QSettings`, always constructed with `IniFormat`/`UserScope` (`app.py:319-323`, `model/utility/configuration.py:6-10`) — never `NativeFormat` (Windows registry / macOS plist). Qt6's own `QSettings` docs confirm INI files written by Qt5 are fully readable by Qt6. **No migration script needed for user settings.** The app's existing `migrate_legacy()` function in `mapper_config.py` (one-shot legacy-key migration, unrelated to the Qt5→Qt6 jump) is unaffected and keeps working as-is.

## 4. CI and build-script changes

Source: [Decide CI runner and build-script changes for arm64-only macOS](https://github.com/mgoodness/shortcircuit/issues/4).

### `.github/workflows/main.yml`

```diff
       matrix:
-        os: [windows-latest, macos-15-intel]
+        os: [windows-latest, macos-15]
```

Pin to `macos-15` (arm64, GA) for now — **not** a permanent choice. Fast-follow: once `macos-latest` has settled past GitHub's macos-26 migration (expected mid-2026), switch to `macos-latest` so this repo stops needing to manually track GitHub's OS deprecation calendar.

Drop the explicit `macholib` install step, **conditionally**:

```diff
-      - name: Additional dependencies [macos-15-intel]
-        if: ${{ matrix.os == 'macos-15-intel' }}
-        run: python -m pipenv install macholib
-
```

PyInstaller already declares `macholib>=1.8; sys_platform == "darwin"` as its own dependency (confirmed via PyPI metadata), so this step should be redundant on the pinned `>=6.4` floor. **Verify the macOS CI leg still builds after removing this step before merging** — if it fails for lack of `macholib`, re-add the step rather than assuming the removal was safe. Remember to update the matching `if: matrix.os == 'macos-15-intel'` conditionals elsewhere in the workflow (the build step, artifact upload step) to `macos-15`.

### `build_mac_installer.sh`

Add `--target-arch arm64` explicitly, rather than relying on the CI runner's native architecture to produce a thin arm64 build implicitly:

```diff
 python -O -m PyInstaller \
     --clean \
     --windowed \
     --icon resources/images/app_icon.icns \
     --add-data 'src/database/*:database' \
     --noconfirm \
     --name shortcircuit src/main.py \
     --noupx \
+    --target-arch arm64 \
     --osx-bundle-identifier ru.secondfry.shortcircuit
```

This makes arm64-only a stated, enforced property of the build (PyInstaller's architecture validation will abort the *build*, not silently ship a broken binary, if a dependency lacks the arm64 slice) instead of an accident of which machine happened to run it.

### `shortcircuit.spec` — delete

Confirmed dead at migration time: neither `build_mac_installer.sh` nor
`build_win_installer.bat` referenced it (both passed PyInstaller flags via CLI
directly), so it was removed.

> **Reversed later.** The spec is back and is now the macOS build's source of
truth. PyInstaller's CLI cannot set the bundle version or arbitrary
`Info.plist` keys — `version=` and `info_plist=` exist only on `BUNDLE` in a
spec file — so the `.app` was reporting PyInstaller's hardcoded `0.0.0` for
`CFBundleShortVersionString` instead of the released `__version__`. See
`shortcircuit.spec` and `build_mac_installer.sh`.

### Unaffected, confirmed

- `build_win_installer.bat`: no changes.
- Windows/Linux CI legs: no changes (architecture change is macOS-only). Note for context: this repo's CI has no Linux leg at all today, only `windows-latest` and the macOS leg — unrelated to this migration, just worth knowing going in.
- `--osx-bundle-identifier`, app icon, and other packaging metadata: no reason to expect changes, unaffected by the Qt5→Qt6 jump.

## 5. Validation checklist for the implementer

1. `pipenv install --dev` with the updated `Pipfile` resolves cleanly on Python 3.13.
2. `./generate_gui.sh` regenerates all 5 generated files against PySide6 without errors.
3. `pipenv run pytest src/shortcircuit/model` passes (covers `test_mapper_config.py`, which also needs its import rename).
4. App launches locally (`cd src && python main.py`) on an Apple Silicon Mac — exercise the main window, Tripwire dialog, Mappers dialog, About dialog (the 4 generated `.ui`-backed surfaces) and confirm no `.exec_()` deprecation warnings remain.
5. Confirm an existing Qt5-written settings `.ini` (if available from a pre-migration install) is read correctly by the PySide6 build — no reset of saved Tripwire credentials/avoid-list/etc.
6. CI green on both `windows-latest` and `macos-15` legs; confirm the `macholib`-step removal didn't break the macOS build (§4) before merging.
7. Resulting `.app` is arm64-only (`lipo -archs dist/shortcircuit.app/Contents/MacOS/shortcircuit` should report `arm64` only, not `x86_64` or both).

## Out of scope (unchanged by this migration)

- **Rosetta 2 / x86_64-under-Rosetta fallback** — ruled out; see [ADR-0001](adr/0001-arm64-only-macos-no-rosetta.md).
- **Codesigning / notarization** — distribution stays unsigned, exactly as today.

## Decision trail

- [Research: PySide6 packaging facts for arm64 macOS](https://github.com/mgoodness/shortcircuit/issues/2) — `research/pyside6-packaging-arm64` branch
- [Research: Qt5-to-Qt6 API diff inventory](https://github.com/mgoodness/shortcircuit/issues/3) — `research/qt5-to-qt6-api-diff` branch
- [Decide CI runner and build-script changes for arm64-only macOS](https://github.com/mgoodness/shortcircuit/issues/4)
- [Decide target Python version for the PySide6 migration](https://github.com/mgoodness/shortcircuit/issues/6)
- [ADR-0001: Drop Intel Mac support; ship arm64-only, no Rosetta fallback](adr/0001-arm64-only-macos-no-rosetta.md)
- Map: [Migrate PySide2 to PySide6: native Apple Silicon support](https://github.com/mgoodness/shortcircuit/issues/1)
