#!/usr/bin/env python
"""Generate the Windows VERSIONINFO resource PyInstaller embeds in the exe.

PyInstaller ``eval``s a version file against its own
``PyInstaller.utils.win32.versioninfo`` classes, so the file is Python source.
This emits that source directly rather than importing PyInstaller -- which
needs the Windows-only ``pefile`` -- so it runs anywhere, including the macOS
dev machine and the test suite.

The executable stays slugged (``shortcircuit.exe``), per the Windows
convention of a space-free filename. ``FileDescription`` and ``ProductName``
are what Explorer's Properties, Task Manager, and the taskbar jump list read,
so the app still shows as "Short Circuit" to the user.

Usage: ``windows_version_info.py [output_path]``; writes to stdout with no
path. The build script passes a path under ``%TEMP%`` because PyInstaller's
``--clean`` empties the workpath (``build/``) before the resource is read.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from shortcircuit import __appname__, __version__  # noqa: E402

COMPANY_NAME = 'mgoodness'
INTERNAL_NAME = 'shortcircuit'
ORIGINAL_FILENAME = 'shortcircuit.exe'


def version_tuple(version: str) -> tuple:
  """Semver -> the four integers a VERSIONINFO's filevers/prodvers needs.

  Pre-release and build metadata are dropped: 2.1.0-rc.1 becomes (2, 1, 0, 0).
  """
  core = re.split(r'[-+]', version, maxsplit=1)[0]
  numbers = [int(part) if part.isdigit() else 0 for part in core.split('.')[:4]]
  return tuple(numbers + [0] * (4 - len(numbers)))


def version_file(version: str = __version__, name: str = __appname__) -> str:
  """The version-file text PyInstaller consumes for this app and version."""
  numbers = version_tuple(version)
  strings = [
    ('CompanyName', COMPANY_NAME),
    ('FileDescription', name),
    ('FileVersion', version),
    ('InternalName', INTERNAL_NAME),
    ('OriginalFilename', ORIGINAL_FILENAME),
    ('ProductName', name),
    ('ProductVersion', version),
  ]
  structs = ',\n'.join(
    "            StringStruct('{}', '{}')".format(key, value)
    for key, value in strings
  )
  return (
    'VSVersionInfo(\n'
    '  ffi=FixedFileInfo(\n'
    '    filevers={numbers},\n'
    '    prodvers={numbers},\n'
    '    mask=0x3f,\n'
    '    flags=0x0,\n'
    '    OS=0x40004,\n'
    '    fileType=0x1,\n'
    '    subtype=0x0,\n'
    '    date=(0, 0)\n'
    '  ),\n'
    '  kids=[\n'
    '    StringFileInfo(\n'
    '      [\n'
    '        StringTable(\n'
    "          '040904b0',\n"
    '          [\n'
    '{structs}\n'
    '          ]\n'
    '        )\n'
    '      ]\n'
    '    ),\n'
    "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
    '  ]\n'
    ')\n'
  ).format(numbers=numbers, structs=structs)


def main(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  text = version_file()
  if argv:
    Path(argv[0]).write_text(text, encoding='utf-8')
  else:
    sys.stdout.write(text)
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
