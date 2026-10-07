---
status: accepted
---

# Ship both macOS architectures and own the fork's release channel

This supersedes [ADR-0001](0001-arm64-only-macos-no-rosetta.md) on one point —
macOS architecture support — and records a second decision ADR-0001 did not
cover: how this fork relates to upstream when it versions releases. ADR-0001's
reasoning still holds where it argued PySide2/Qt5 is EOL and Rosetta is a tax
rather than a fix.

## 1. Build both macOS architectures (supersedes ADR-0001)

ADR-0001 dropped Intel Macs because a universal2 build roughly doubles the
installed app size. That cost is real, but it is not the whole ledger:

- PySide6 ships a single **universal2** PyPI wheel, so the dependency set is
  identical for both slices — the only difference is PyInstaller's
  `--target-arch`, plus a second CI runner (`macos-15-intel`).
- The alternative to keeping Intel is telling Intel users to build from source,
  which is a worse outcome than a larger download for a base that is cheap to
  keep.

So the fork builds both: `macos-15` → arm64 and `macos-15-intel` → x86_64, each
a thin app uploaded under its own artifact name. A single **universal2** binary
stays rejected for the same size reason ADR-0001 gave. The same change was
proposed upstream, so a merged upstream and this fork build identically.

## 2. The release channel is the contract, not the version number

The fork and upstream can both publish a `2.0.0`, and no number prevents it:
semver has no registry that reserves versions, so "use a distinct major band"
is a convention that fails the moment upstream takes that major — and chasing
it becomes a permanent race to stay ahead. The number is the wrong lever.

What routes a user to a build is the release **channel**, which is exactly two
things:

- the in-app updater's repository URL (`src/shortcircuit/model/versioncheck.py`);
- the app identity (bundle identifier, `__appname__`/`__appslug__`, config root).

Once both resolve to this fork, upstream's numbers never enter the comparison
and the collision disappears by construction. A distinct version band is
therefore decorative; the identity split is the actual fix, and this fork owns
its own line and identity.

## Fork and upstream

This fork tracks upstream opportunistically. Contributions back upstream live on
branches cut from `upstream/master` and carry only the upstreamable change;
fork-only work — the release identity, release automation, and fork docs — stays
on `master` and never enters those branches. Whether a contribution lands
upstream or not does not block work here.
