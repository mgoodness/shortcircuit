#!/bin/bash
#
# Build the macOS .app from shortcircuit.spec. Pass the target architecture
# (arm64, x86_64, or universal2); the default is the architecture of the running
# Python. PySide6 ships a single universal2 wheel, so either slice builds from
# the same dependency set -- this argument only tells PyInstaller which slice to
# keep.
#
# The arch is forwarded to the spec after `--`. `--target-arch` is a
# makespec-only option and PyInstaller rejects it when building from a spec
# file, so the spec parses the value itself.

target_arch="${1:-}"

spec_args=()
if [ -n "$target_arch" ]; then
    spec_args=(-- "$target_arch")
fi

python -O -m PyInstaller \
    --clean \
    --noconfirm \
    shortcircuit.spec \
    "${spec_args[@]}"

cd dist || exit 1
# The tarball keeps the slugged name so release asset URLs stay clean; the app
# inside it is the user-visible "Short Circuit.app".
tar cfz shortcircuit.app.tar.gz "Short Circuit.app"
