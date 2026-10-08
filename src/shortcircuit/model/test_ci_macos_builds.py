# test_ci_macos_builds.py
"""Regression tests for the macOS CI and build contract.

The packaging decisions from the PySide2 -> PySide6 migration live in CI
configuration and a shell script, not in Python, so these tests lock the
observable contract of those artefacts rather than unit-testing logic:

  * the macOS matrix builds both slices of PySide6's universal2 wheel -- arm64
    on the ``macos-15`` runner, x86_64 on ``macos-15-intel`` -- and the two
    uploads are named apart so neither clobbers the other;
  * the per-mapper ``macholib`` install step is gone (PyInstaller carries it
    itself on darwin);
  * the workflow tracks the Pipfile's Python 3.13 and does not force an x64
    interpreter, so the arm64 runner gets arm64 Python;
  * ``build_mac_installer.sh`` builds from the committed ``shortcircuit.spec``,
    which owns the packaging metadata (windowed mode, icon, datas, bundle
    identifier, target architecture) and derives the bundle version from
    ``shortcircuit.__version__`` so ``CFBundleShortVersionString`` is the real
    release version rather than PyInstaller's hardcoded ``0.0.0`` default;
  * ``Pipfile.lock`` stays cross-platform, carrying the Windows-only deps that
    a single-platform ``pipenv lock`` would drop and the Windows CI leg needs.

They live beside the model tests, per the repo convention that tests are
collocated with the code they cover rather than in a top-level ``tests/``
directory. They exercise build/CI configuration, which already lives at the
repo root, so they read those artefacts relative to the repo root.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / '.github' / 'workflows' / 'build.yml'
_BUILD_SCRIPT = _REPO_ROOT / 'build_mac_installer.sh'
_SPEC = _REPO_ROOT / 'shortcircuit.spec'
_WIN_BUILD_SCRIPT = _REPO_ROOT / 'build_win_installer.bat'
_PIPFILE_LOCK = _REPO_ROOT / 'Pipfile.lock'
_REQUIREMENTS = _REPO_ROOT / 'requirements.txt'

# pipenv resolves the lock for the running platform only, so a lock generated on
# macOS silently drops the Windows-only dependencies PyInstaller needs there.
# pipenv installs from the lock with ``--no-deps``, so those entries must be
# present for the Windows CI leg to install and build.
_WIN32_ONLY_PYINSTALLER_DEPS = {
  'pefile': '==2024.8.26',
  'pywin32-ctypes': '==0.2.3',
  'colorama': '==0.4.6',
}

_needs_bash = pytest.mark.skipif(
  sys.platform == 'win32' or shutil.which('bash') is None,
  reason='needs a real bash; Windows has only a WSL stub without a distro',
)


def _workflow_text():
  return _WORKFLOW.read_text(encoding='utf-8')


def test_macos_legs_build_both_architectures():
  """arm64 on ``macos-15`` and x86_64 on ``macos-15-intel``, both wired up."""
  text = _workflow_text()
  assert '- os: macos-15\n' in text
  assert '- os: macos-15-intel\n' in text
  assert 'arch: arm64' in text
  assert 'arch: x86_64' in text
  assert 'build_mac_installer.sh ${{ matrix.arch }}' in text


def test_macos_artifacts_are_named_per_architecture():
  """Two macOS legs upload the same app; distinct names keep both artifacts."""
  text = _workflow_text()
  assert 'shortcircuit-arm64.app.tar.gz' in text
  assert 'shortcircuit-x86_64.app.tar.gz' in text


def test_macholib_install_step_is_gone():
  """PyInstaller declares macholib for darwin itself; no CI step reinstalls it."""
  assert 'macholib' not in _workflow_text()


def test_workflow_tracks_python_3_13_without_forcing_x64():
  """Match the Pipfile's ``python_version = "3.13"`` and let each runner win."""
  text = _workflow_text()
  assert 'python-version: "3.13"' in text
  assert 'architecture: x64' not in text


def test_spec_derives_the_bundle_version_from_the_package():
  """The ``.app`` reports the real version, from release-please's one source.

  PyInstaller's default is a hardcoded ``0.0.0``, so without an explicit
  ``version``/``info_plist`` the published bundle lies about its version. A
  second, hardcoded copy in the spec would drift from ``__version__``.
  """
  from shortcircuit import __version__

  bundle = _capture_spec_stages()['bundle']
  assert bundle['version'] == __version__
  assert bundle['info_plist']['CFBundleShortVersionString'] == __version__
  assert bundle['info_plist']['CFBundleVersion'] == __version__


def test_spec_forwards_the_target_arch_to_the_executable():
  """A spec argument sets ``EXE.target_arch``; with none, PyInstaller infers."""
  assert _capture_spec_stages()['exe']['target_arch'] is None
  assert _capture_spec_stages(['arm64'])['exe']['target_arch'] == 'arm64'
  assert _capture_spec_stages(['x86_64'])['exe']['target_arch'] == 'x86_64'


def test_spec_defers_bytecode_optimization_to_the_interpreter():
  """``python -O`` must still set the frozen code's optimization level.

  A hardcoded ``optimize=0`` silently retains asserts, differing from the
  pre-spec CLI build, which inferred ``sys.flags.optimize``.
  """
  assert _capture_spec_stages()['analysis']['optimize'] in (None, -1)


def test_macos_spec_is_tracked_build_source():
  """The spec is committed, not a throwaway PyInstaller regenerates per run."""
  tracked = subprocess.run(
    ['git', 'ls-files', '--error-unmatch', 'shortcircuit.spec'],
    cwd=_REPO_ROOT,
    capture_output=True,
    text=True,
  )
  assert tracked.returncode == 0, 'shortcircuit.spec is not tracked by git'


@_needs_bash
def test_build_script_is_valid_bash():
  subprocess.run(['bash', '-n', str(_BUILD_SCRIPT)], check=True)


def test_windows_build_still_uses_direct_flags():
  """The onefile Windows build has no bundle metadata to set; leave it alone."""
  assert 'shortcircuit.spec' not in _WIN_BUILD_SCRIPT.read_text(encoding='utf-8')


@_needs_bash
def test_build_script_builds_from_the_spec_and_forwards_the_arch(tmp_path):
  """The spec owns packaging metadata; the arch is forwarded after ``--``.

  ``--target-arch`` is a makespec-only option that PyInstaller rejects when a
  spec file is given, so the script must pass the arch as a spec argument.
  """
  args = _record_macos_build_invocation(tmp_path, 'arm64')
  assert 'shortcircuit.spec' in args
  assert _spec_args(args) == ['--', 'arm64']


@_needs_bash
def test_build_script_omits_the_arch_by_default(tmp_path):
  """No arch argument means no spec argument; PyInstaller uses the host's."""
  args = _record_macos_build_invocation(tmp_path)
  assert _spec_args(args) == []


def test_lock_keeps_win32_only_pyinstaller_deps():
  """The lock stays cross-platform: a macOS ``pipenv lock`` drops these."""
  develop = json.loads(_PIPFILE_LOCK.read_text(encoding='utf-8'))['develop']
  for name, version in _WIN32_ONLY_PYINSTALLER_DEPS.items():
    assert name in develop, f'{name} missing from the develop lock section'
    assert develop[name]['version'] == version, name
    assert develop[name]['markers'] == "sys_platform == 'win32'", name


def test_requirements_export_includes_win32_only_deps():
  """The generated requirements.txt mirrors the lock's win32 entries."""
  text = _REQUIREMENTS.read_text(encoding='utf-8')
  for name in _WIN32_ONLY_PYINSTALLER_DEPS:
    assert re.search(rf'^{re.escape(name)}\S*==', text, re.MULTILINE), name


def _record_macos_build_invocation(tmp_path, *arch):
  """Run ``build_mac_installer.sh`` with a recording stand-in for ``python``.

  Returns the argv the script handed to PyInstaller. The stand-in also lays
  down the ``dist/shortcircuit.app`` the script archives, so the script runs to
  completion without a real (minutes-long) build.
  """
  bin_dir = tmp_path / 'bin'
  bin_dir.mkdir()
  argv_file = tmp_path / 'pyinstaller-argv.txt'
  stub = bin_dir / 'python'
  stub.write_text(
    '#!/bin/bash\n'
    'printf "%s\\n" "$@" > "$ARGV_FILE"\n'
    'mkdir -p dist/shortcircuit.app\n',
    encoding='utf-8',
  )
  stub.chmod(0o755)

  env = {
    **os.environ,
    'PATH': f'{bin_dir}:{os.environ["PATH"]}',
    'ARGV_FILE': str(argv_file),
  }
  subprocess.run(
    ['bash', str(_BUILD_SCRIPT), *arch],
    cwd=tmp_path,
    env=env,
    check=True,
  )
  return argv_file.read_text(encoding='utf-8').splitlines()


def _spec_args(argv):
  """The arguments the build script forwards to the spec, after ``--``."""
  return argv[argv.index('shortcircuit.spec') + 1:]


def _capture_spec_stages(spec_args=()):
  """Execute ``shortcircuit.spec`` with PyInstaller's build classes stubbed.

  A real build takes minutes and a macOS host, so the spec's contract -- the
  kwargs it hands to ``EXE`` and ``BUNDLE`` -- is observed by exec'ing it the
  way PyInstaller does: build classes and ``SPECPATH`` in the namespace, extra
  command-line arguments in ``sys.argv``.
  """
  captured = {}

  class _Stub:
    def __init__(self, *args, **kwargs):
      self.pure = []
      self.scripts = []
      self.binaries = []
      self.datas = []

  def _record(stage):
    def _factory(*args, **kwargs):
      captured[stage] = kwargs
      return _Stub(*args, **kwargs)
    return _factory

  namespace = {
    'SPECPATH': str(_REPO_ROOT),
    'Analysis': _record('analysis'),
    'PYZ': _Stub,
    'EXE': _record('exe'),
    'COLLECT': _Stub,
    'BUNDLE': _record('bundle'),
  }

  original_argv = sys.argv
  sys.argv = [str(_SPEC), *spec_args]
  try:
    exec(compile(_SPEC.read_text(encoding='utf-8'), str(_SPEC), 'exec'), namespace)
  finally:
    sys.argv = original_argv
  return captured
