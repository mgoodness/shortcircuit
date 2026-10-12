---
status: accepted
---

# Ship one universal2 macOS app on `macos-latest`

Supersedes [ADR-0002](0002-both-macos-arches-and-fork-release-channel.md) section 1
on macOS architecture. ADR-0002 section 2 — the fork owning its release channel and
identity — still stands.

ADR-0002 chose two thin per-architecture builds (arm64 on `macos-15`, x86_64 on
`macos-15-intel`) and rejected a universal2 app for the installed-size cost.
Upstream, after merging the same PySide6 migration, reached the opposite
conclusion and shipped one universal2 app on `macos-latest`
([secondfry/shortcircuit#51](https://github.com/secondfry/shortcircuit/pull/51)).
This fork now follows upstream.

## Why the reversal

- **Size was the only argument against universal2, and it is smaller than
  ADR-0002 assumed.** Upstream's concurrent Qt-module pruning
  ([#54](https://github.com/secondfry/shortcircuit/pull/54)) roughly halves the
  bundle, offsetting the second slice. Upstream's universal2 build (51.7 MB,
  double-compressed) lands within about 10–20% of this fork's *unpruned*
  single-arch builds (42.7 MB arm64, 46.3 MB x86_64); a pruned per-arch build
  would be smaller still, but the gap is not the ~2× ADR-0002's framing implied.
- **The per-arch matrix depended on a dying runner.** `macos-15-intel` is
  GitHub's last x86_64 image, and the migration spec already flagged switching
  to `macos-latest` as a fast-follow so the repo would stop tracking GitHub's
  OS-deprecation calendar by hand. A single `macos-latest` leg removes that
  maintenance entirely.
- **One download cannot be picked wrong.** The app is unsigned and gated by
  Gatekeeper, so a single artifact is worth a few megabytes to a non-developer
  audience; the per-arch release page made the user choose an architecture.

## Consequences

CI builds the universal2 bundle on an Apple Silicon runner, so the x86_64 slice
is built but never executed in CI — the same coverage gap upstream accepted in
#51. A manual smoke test on an Intel Mac closes it. PyInstaller aborts a
universal2 build if any collected binary lacks a slice, so a future arm64-only
dependency fails the build loudly rather than shipping a broken app.

PySide6 is pinned to `>=6.8.0.2,<6.10`, the last series built for macOS 12
Monterey (EVE Online's own floor). Both slices share that floor.

ADR-0002's claim that "a merged upstream and this fork build identically" was an
assumption when it was written; upstream then chose universal2 and this fork has
now adopted it, so the two build the same way — for the reason recorded here.
