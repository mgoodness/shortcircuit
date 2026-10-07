# test_ci_arm64.py
"""Regression tests for the arm64-only macOS CI and build contract.

The packaging decisions from the PySide2 -> PySide6 migration live in CI
configuration and a shell script, not in Python, so these tests lock the
observable contract of those artefacts rather than unit-testing logic:

  * the macOS matrix leg runs on the arm64-native ``macos-15`` runner, and no
    ``macos-15-intel`` reference survives anywhere in the workflow;
  * the per-mapper ``macholib`` install step is gone (PyInstaller carries it
    itself on darwin);
  * the workflow tracks the Pipfile's Python 3.13 and no longer forces an
    x64 interpreter, so the arm64 runner gets arm64 Python;
  * ``build_mac_installer.sh`` asks PyInstaller for ``--target-arch arm64``
    explicitly, and the dead ``shortcircuit.spec`` is gone.

They live at the repo root, not beside the model tests: this is build/CI
configuration, and ticket #8 owns the source tree.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _REPO_ROOT / '.github' / 'workflows' / 'main.yml'
_BUILD_SCRIPT = _REPO_ROOT / 'build_mac_installer.sh'
_WIN_BUILD_SCRIPT = _REPO_ROOT / 'build_win_installer.bat'


def _workflow_text():
  return _WORKFLOW.read_text(encoding='utf-8')


def test_macos_matrix_leg_is_the_arm64_runner():
  """The macOS leg runs on ``macos-15`` (arm64), never ``macos-15-intel``."""
  text = _workflow_text()
  assert re.search(r'os:\s*\[windows-latest,\s*macos-15\]', text), text
  assert 'macos-15-intel' not in text


def test_macos_step_names_and_conditionals_use_macos_15():
  """Human-readable step names and ``if:`` guards were renamed with the leg."""
  text = _workflow_text()
  assert '[macos-15]' in text
  assert "[macos-15-intel]" not in text
  assert "matrix.os == 'macos-15'" in text
  assert "matrix.os == 'macos-15-intel'" not in text


def test_macholib_install_step_is_gone():
  """PyInstaller declares macholib for darwin itself; no CI step reinstalls it."""
  assert 'macholib' not in _workflow_text()


def test_workflow_tracks_python_3_13_without_forcing_x64():
  """Match the Pipfile's ``python_version = "3.13"`` and let the runner arch win."""
  text = _workflow_text()
  assert 'python-version: "3.13"' in text
  assert 'architecture: x64' not in text


def test_build_script_targets_arm64_explicitly():
  """arm64-only is stated in the build, not left to the runner's architecture."""
  text = _BUILD_SCRIPT.read_text(encoding='utf-8')
  assert '--target-arch arm64' in text


@pytest.mark.skipif(shutil.which('bash') is None, reason='bash not available')
def test_build_script_is_valid_bash():
  subprocess.run(['bash', '-n', str(_BUILD_SCRIPT)], check=True)


def test_dead_spec_file_is_untracked_and_unreferenced():
  """``shortcircuit.spec`` is dead packaging source from the Windows era.

  PyInstaller regenerates a throwaway ``shortcircuit.spec`` next to its
  invocation on every build, so the contract is that the repo no longer
  *tracks* it -- not that the name is absent from the filesystem.
  """
  tracked = subprocess.run(
    ['git', 'ls-files', '--error-unmatch', 'shortcircuit.spec'],
    cwd=_REPO_ROOT,
    capture_output=True,
    text=True,
  )
  assert tracked.returncode != 0, 'shortcircuit.spec is still tracked by git'
  for script in (_BUILD_SCRIPT, _WIN_BUILD_SCRIPT):
    assert 'shortcircuit.spec' not in script.read_text(encoding='utf-8')
