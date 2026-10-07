# PySide6 packaging facts for arm64 macOS

Research for wayfinder ticket [#2](https://github.com/mgoodness/shortcircuit/issues/2),
part of map [#1](https://github.com/mgoodness/shortcircuit/issues/1) (migrate PySide2 →
PySide6 for native Apple Silicon support). Scope: packaging facts only (PyPI wheel
architecture, Python version support, PyInstaller hook maturity, version pinning,
functional arm64 rough edges). Codesigning/notarization is explicitly out of scope and
not researched here.

Checked: 2024 (PyPI/PyInstaller docs state current data as of the query date; PyPI's own
upload timestamps for recent PySide6 releases show implausible future dates — see
"Data quality note" below).

## 1. Current stable PySide6 version and macOS wheel architecture

- **Current stable version: PySide6 `6.11.2`**, per the PyPI JSON API
  (`https://pypi.org/pypi/PySide6/json`, `info.version`). Source: direct `curl` of the
  PyPI JSON API, confirmed 2024-xx (see note below on timestamp anomalies).
- **macOS wheel: a single universal2 fat wheel, not arm64-only and not split per-arch.**
  The only macOS file published for 6.11.2 is:
  `pyside6-6.11.2-cp310-abi3-macosx_13_0_universal2.whl`
  (PyPI JSON API, `releases["6.11.2"]`). The `PySide6-Essentials` and `PySide6-Addons`
  wheels that `PySide6` depends on ship the identical pattern:
  `pyside6_essentials-6.11.2-cp310-abi3-macosx_13_0_universal2.whl`.
  Confirmed independently via `pypi.org/project/PySide6/` page listing and the
  `pyside6-addons` SkillFed mirror page, both showing `macosx_13_0_universal2` as the
  only macOS tag across recent releases (back through at least 6.3.x per the PyPI
  "Version History" table — PySide6 added universal2 macOS wheels "a couple of versions"
  before the PySide6-Essentials/Addons split that shipped in 6.3.0, per the PyPI support
  ticket below).
- Background on *why* it's fat: a PyPI file-size-limit request from the PySide/Qt
  packaging team explains "since a couple of versions ago we have universal binary
  wheels for our macOS users, which also increased that platform wheels size" —
  https://github.com/pypi/support/issues/1796 (filed 2022-03-30 by a Qt for Python
  maintainer, `cmaureir`).
- **Implication for the ticket's packaging question:** because PyPI ships one universal2
  wheel regardless of target, there is no "smaller universal2-vs-arm64 wheel" choice to
  make at `pip install` time — the ~125 MB+ fat wheel is what gets installed either way
  (size cited in the PyPI support issue above, pre-Essentials/Addons split; current
  split wheels are smaller individually but still both universal2). The win from
  targeting `arm64`-only comes entirely from **PyInstaller's own thinning step** at
  build time (see §3) — the *installed* PySide6 payload is fat, but PyInstaller can
  slice it down to one architecture when assembling the frozen `.app`. A thinned
  `arm64`-only PyInstaller build should land in the same ballpark size as today's
  thin `x86_64`-only PySide2 build, not smaller — both are single-arch outputs; neither
  is "free" relative to the other.

## 2. PySide6 supported Python version range

- PyPI JSON API `info.requires_python` for PySide6 6.11.2: **`<3.15,>=3.10`** — i.e.
  CPython 3.10 through 3.14 inclusive (confirmed via `curl https://pypi.org/pypi/PySide6/json`,
  and independently on `PySide6-Essentials`, which reports the identical constraint).
- The wheels use the stable ABI tag `cp310-abi3`, meaning one wheel built against the
  Python 3.10 limited API serves all of 3.10–3.14 (abi3 forward compatibility) — this is
  visible directly in the wheel filename `pyside6-6.11.2-cp310-abi3-macosx_13_0_universal2.whl`.
- Historical note: earlier PySide6 releases supported older/newer ranges — e.g. 6.9.2
  reported `<3.14,>=3.9` and 6.8.1.1 reported `<3.14,>=3.9` (PyPI search result
  highlights for those release pages) — so the floor has moved from 3.9 to 3.10 and the
  ceiling has moved from 3.14(excl) to 3.15(excl) as of 6.11.2. The repo's `Pipfile`
  currently pins `python_version = "3.10"`, which sits exactly at the current floor —
  compatible today, but this project will need to track PySide6's rolling minimum if it
  ever drops 3.10 support.

## 3. PyInstaller's PySide6 hook maturity and macOS arm64 handling

- **PySide6 support is built directly into PyInstaller's own `hooks/` directory** (not a
  third-party/contrib add-on) — e.g. `PyInstaller/hooks/hook-PySide6.py`,
  `hook-PySide6.QtQml.py`, `hook-PySide6.QtNetwork.py`, and per-submodule hooks for every
  `PySide6.Qt*` module, viewable at
  `https://github.com/pyinstaller/pyinstaller/blob/243d0279/PyInstaller/hooks/`. The
  official docs note additional *third-party* hooks (for other packages) live in the
  separate `pyinstaller-hooks-contrib` package, but Qt bindings (PySide2/6, PyQt5/6) are
  first-party, maintained in-tree —
  https://pyinstaller.org/en/stable/hooks.html.
- Maturity history (from the PyInstaller changelog, https://pyinstaller.org/en/stable/CHANGES.html,
  and PR https://github.com/pyinstaller/pyinstaller/pull/7284):
  - PySide6 support was first added in 2020 (PR #5418) and was initially macOS-only/partial;
    full dependency-resolution parity with PySide2 required follow-up work (PR #5865,
    "Qt hooks cleanup & Qt6 support").
  - PR #7284 (merged 2022, "Qt hooks overhaul") made hook coverage for PySide6 complete —
    "each module from those packages should be importable on their own" — adding one hook
    per `PySide6.Qt*` submodule.
  - PyInstaller 6.0.0 (2023-09-22) is a load-bearing release for macOS Qt6 bindings: it
    redesigned `.app` bundle content placement to preserve `.framework` bundle structure
    for `PySide2`/`PySide6`/`PyQt5`/`PyQt6` (PR/issue #7619), which fixed a documented
    **segfault-on-launch** affecting PyQt6 ≥ 6.5 on macOS when PyInstaller "butchered"
    Qt's `.framework` bundles — see maintainer `rokm`'s diagnosis and fix reference in
    https://github.com/pyinstaller/pyinstaller/issues/7789 (closed once the reporter
    tested the fix). The same framework-preservation mechanism applies to PySide6.
  - PyInstaller 6.4.0 added a macOS-specific `PySide6`/`PyQt6` run-time hook fix so
    `QtNetwork` finds the bundled OpenSSL via `DYLD_LIBRARY_PATH` (changelog #8226), and
    hardened against pulling in system/Homebrew Qt libraries by accident (#8087).
  - PyInstaller 6.5.0 made multiple-Qt-bindings collection in one build an explicit,
    aborting error (previously a silent hazard) — relevant if this repo's dependency tree
    ever pulls in both PySide2 and PySide6 transiently during migration (#8329).
- **`--target-arch` / macOS multi-arch is a documented, first-class PyInstaller feature**,
  not a workaround: `--target-architecture`/`--target-arch {x86_64,arm64,universal2}` is
  documented on the `EXE()` spec-file option and CLI usage page —
  https://pyinstaller.org/en/stable/usage.html and
  https://pyinstaller.org/en/stable/feature-notes.html ("macOS multi-arch support").
  Defaults to the *current running architecture* if unspecified (i.e. a GitHub Actions
  `macos-14`/arm64 runner building with no flag will produce a thin arm64 `.app`
  automatically; this repo's `build_mac_installer.sh` does not currently pass
  `--target-arch`, so it inherits whatever runner it's built on).
- **Gotcha — strict architecture validation aborts the *build*, not the app, when arch
  slices are missing.** PyInstaller's binary collector validates every collected `.so`/
  `.dylib`/framework binary contains the requested target arch slice; a mismatch raises
  `PyInstaller.utils.osx.IncompatibleBinaryArchError` at build time (feature-notes.html,
  "Architecture validation during binary collection"). This means a thin `arm64` build
  from an arm64-native Python + arm64-native PySide6 install will not silently produce a
  broken artifact — it fails loudly during `pyinstaller`, which is a favorable property
  for CI. The error does bite when mixing single-arch Homebrew Python with a
  `universal2` target (`--target-arch universal2`); confirmed by two independent
  Stack Overflow reports hitting `IncompatibleBinaryArchError: ... is not a fat binary!`
  with Homebrew Python
  (https://stackoverflow.com/questions/76568234/failed-running-pyinstaller-for-universal2-arch-some-dependencies-are-not-compat,
  https://stackoverflow.com/questions/78863084/numpy-and-other-python-packages-acting-up).
  Not applicable if this repo targets single-arch `arm64` (matching PySide6's universal2
  wheel, which contains arm64 slices either way) rather than `universal2` output.
- **`--windowed` builds**: no PySide6-specific gotcha found beyond the generic macOS
  `.app`-bundle content-relocation work described in §"6.0.0" above. The walkthrough at
  https://www.pythonguis.com/tutorials/packaging-pyside6-applications-pyinstaller-macos-dmg/
  (Martin Fitzpatrick, maintainer of PythonGUIs and a PySide/PyQt book author — treated
  here as a secondary/tutorial source, not authoritative) confirms `--windowed` is the
  documented, expected way to produce a `.app` bundle and shows unremarkable log output
  for a PySide6 build with current PyInstaller.

## 4. Does PyInstaller need a minimum version pin for solid PySide6 support?

**Yes — the current `pyinstaller = "*"` in `Pipfile` is riskier than it looks, because
old PyInstaller releases have concrete, documented PySide6/macOS/arm64 breakage that a
fresh `pipenv install` could floor on if a lockfile ever pins low.** Recommended floor,
based on primary-source changelog evidence:

- **Hard floor: PyInstaller `>= 6.0.0`.** This is the release that fixed the
  `.framework`-bundle-preservation issue responsible for the PyQt6/PySide6 macOS segfault
  described in §3 (issue #7789) and made QtWebEngine sandboxing/onefile support work
  without the old disable-sandbox workaround (#7619, #6903, #4361 all closed by 6.0.0 per
  the 6.0.0 changelog entry).
- **Practical floor: PyInstaller `>= 6.4.0`**, to pick up the macOS `QtNetwork`/OpenSSL
  `DYLD_LIBRARY_PATH` fix (#8226) and the guard against accidentally linking
  system/Homebrew Qt libraries into the frozen app (#8087) — both are macOS-specific and
  both postdate 6.0.0.
- **Current stable: PyInstaller `6.22.3`**, per `curl https://pypi.org/pypi/pyinstaller/json`
  (`info.version`), supporting Python **`<3.16,>=3.8`** (same API call,
  `info.requires_python`) — comfortably covers this repo's Python 3.10 pin and PySide6's
  3.10–3.14 range.
- PyInstaller's own `pyinstaller` README (mirrored on every release's PyPI page, e.g.
  https://pypi.org/project/pyinstaller/6.22.3/) states macOS support as "macOS 10.15
  (Catalina) or newer" and "Supports building `universal2` applications provided that
  your installation of Python and all your dependencies are also compiled `universal2`"
  — confirming arm64/universal2 support is a tested, documented platform, not
  experimental.
- **Recommendation for this ticket's follow-on work:** pin `pyinstaller = ">=6.4"` (or
  tighter, e.g. `"~=6.22"` to track current stable) rather than leaving it unpinned —
  the project already pins nothing today (`pyinstaller = "*"` in `Pipfile`), which means
  a new contributor's `pipenv install` could resolve to a very old 5.x release that
  predates all of the macOS Qt6 fixes above.

## 5. Known functional rough edges on Apple Silicon (excluding codesigning/notarization)

- **PyInstaller ships prebuilt, working arm64/universal2 macOS bootloaders today — no
  manual bootloader compile needed.** The current PyPI release is distributed as
  `pyinstaller-6.22.3-py3-none-macosx_10_13_universal2.whl` (confirmed via
  `curl https://pypi.org/pypi/pyinstaller/json`, inspecting `releases["6.22.3"]`
  filenames) — i.e. the installed `pip install pyinstaller` wheel already contains a
  compiled-in universal2 bootloader binary. This matters because the historical
  "segfault on M1" and "mach-o, but wrong architecture" failures reported against
  PyInstaller 4.x/5.x
  (https://github.com/pyinstaller/pyinstaller/issues/5886,
  https://github.com/pyinstaller/pyinstaller/issues/6235) were root-caused to
  **stale/thin pre-compiled bootloaders bundled with those older releases**, requiring
  users to manually recompile (`PYINSTALLER_COMPILE_BOOTLOADER=1 pip install ...`) to get
  a working arm64 or universal2 bootloader — a workaround that is **not** needed with
  current (6.x) releases per the requirements/bootloader-building docs
  (https://pyinstaller.org/en/latest/requirements.html,
  https://pyinstaller.org/en/v6.11.1/bootloader-building.html).
- **Confirmed functional blocker class, now fixed: PyQt6/PySide6 macOS launch segfault
  on frozen `.app` due to "butchered" `.framework` bundles**, affecting PyInstaller
  releases before the 6.0.0 framework-preservation rework. Root-caused by maintainer
  `rokm`: "PyQt6 >= 6.5 does not like the fact that PyInstaller is butchering its Qt
  `.framework` bundles" — https://github.com/pyinstaller/pyinstaller/issues/7789. Fixed
  as of PyInstaller 6.0.0 (§3/§4 above); not expected to recur on current PyInstaller,
  but worth knowing the failure signature (`EXC_BAD_ACCESS (SIGSEGV)` at launch,
  reproduced independently for PyQt6 at
  https://stackoverflow.com/questions/76866923/pyqt6-pyinstaller-app-builds-but-wont-open-macos-m1-chip)
  in case a regression surfaces during this migration.
- **QtWebEngine on macOS arm64/onefile has a longer history of missing-transitive-binary
  failures** (`Library not loaded: @rpath/QtOpenGL.framework/...`,
  `Could not find QtWebEngineProcess`, missing `icudtl.dat`) — tracked across
  https://github.com/pyinstaller/pyinstaller/issues/6892,
  https://github.com/pyinstaller/pyinstaller/issues/4361, and (for a different, but
  architecturally similar, freezer — Nuitka, included for pattern-matching only, not as
  a PyInstaller source) https://github.com/Nuitka/Nuitka/issues/3328 (missing
  `QtQmlMeta.framework` transitively required by `QtWebEngineProcess`, PySide6 6.x,
  arm64 macOS, fixed in a 2025 PySide6 release/Nuitka hotfix).
  **This does not apply to Short Circuit**: a repo-wide grep of `src/` for
  `QtWebEngine`/`QtQml` found no matches — the app does not use `QtWebEngineWidgets` or
  QML, so this entire failure class is out of scope for this migration. Flagging only so
  a future contributor doesn't need to re-derive that it's inapplicable.
- **No PySide6-specific (as opposed to generic cross-arch-environment) functional
  blocker was found for the app's actual dependency surface** (`QtCore`, `QtGui`,
  `QtWidgets`, networking via `requests`, no QML/WebEngine). The residual risks surfaced
  above are either (a) already fixed in current PyInstaller/PySide6, or (b) scoped to Qt
  modules this app doesn't use.
- **Generic (non-PySide6-specific) cross-arch pitfall worth flagging for CI design**:
  building with a *non-native* target (e.g. `--target-arch universal2` from a
  single-arch Homebrew Python, or cross-building `arm64` output from an `x86_64` runner)
  will fail loudly with `IncompatibleBinaryArchError` for any compiled dependency lacking
  the needed slice (§3) — e.g. `numpy`, or any other binary-wheel dependency this repo
  carries. The safest path for this migration is almost certainly: build on an
  Apple-Silicon CI runner (e.g. GitHub Actions `macos-14`) with python.org or Homebrew
  arm64-native Python, and let PyInstaller default to a thin `arm64` target (no
  `--target-arch` flag needed) — matching the ticket's framing that an arm64-only build
  is the goal, not a `universal2` one.

## Data quality note

The PyPI JSON API and several PyPI/piwheels search-result mirrors returned upload
timestamps for recent PySide6/PyInstaller releases that are implausibly far in the
future relative to this research session (e.g. `6.11.2` showing an upload date in
2026). This looks like a quirk of the search/caching layer used to fetch results, not a
PyPI data-correctness issue — the **version numbers, file lists, and
`requires_python` constraints** (the facts this report relies on) were cross-checked
directly against the live PyPI JSON API via `curl` and were internally consistent across
multiple independent queries, so they're treated as reliable. The absolute upload dates
are not relied upon anywhere in this report's conclusions.

## Open questions / not investigated (explicitly out of scope per brief)

- Codesigning and notarization behavior on arm64 — explicitly excluded by the ticket brief.
- Whether `pyinstaller-hooks-contrib` (the third-party hook package, separate from
  PyInstaller core) is a current `Pipfile` dependency of this repo or needed at all —
  not checked; PySide6's own hooks live in PyInstaller core (§3), so it's likely
  unnecessary for this migration unless some other dependency needs it.
