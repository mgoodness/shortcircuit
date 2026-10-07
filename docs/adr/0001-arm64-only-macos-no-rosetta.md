---
status: superseded by [ADR-0002](0002-both-macos-arches-and-fork-release-channel.md)
---

# Drop Intel Mac support; ship arm64-only, no Rosetta fallback

> Superseded by [ADR-0002](0002-both-macos-arches-and-fork-release-channel.md):
> the fork now builds both macOS architectures. The reasoning here — PySide2/Qt5
> is EOL, and Rosetta is a tax rather than a fix — still holds.

Short Circuit moved from PySide2/Qt5 to PySide6/Qt6 to get native Apple Silicon
support (see [`docs/migration-pyside6-arm64.md`](../migration-pyside6-arm64.md)
for the full migration). While deciding *how* to support Apple Silicon, two
cheaper alternatives to a full Qt6 port were considered and rejected:

- **Run the existing PySide2 build under Rosetta 2** (x86_64 Python + x86_64
  PySide2 wheel, translated at runtime). Rejected: PySide2/Qt5 is EOL
  upstream, so this just defers the real migration while paying a permanent
  Rosetta performance tax and keeping Intel-only tooling (x86_64 Homebrew/
  pyenv) in the dev loop indefinitely.
- **Ship a universal2 macOS build** (both x86_64 and arm64 in one `.app`).
  Rejected as the default target: PySide6's own PyPI wheel is already
  universal2, but the *installed* app size and complexity roughly doubles
  for a user base that, developer-judgment call, skews overwhelmingly
  Apple Silicon at this point. Revisit if Intel Mac user reports surface.

Decided instead: **arm64-only**, built with PyInstaller's `--target-arch arm64`
on an arm64-hosted CI runner (`macos-15`). Intel Mac users are not supported
by this build; they would need to build from source themselves. This is a
real trade-off made consciously, not an oversight — recorded here because the
reasoning (PySide2 being EOL, Rosetta being a tax not a fix, universal2's
cost/benefit skew) isn't visible from the code or the CI config alone, and a
future reader re-adding Intel support should know this was already weighed
once.

Codesigning/notarization status is unchanged by this decision — the `.app`
ships unsigned both before and after, tracked separately (see the migration
spec's scope notes).
