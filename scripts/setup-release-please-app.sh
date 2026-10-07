#!/usr/bin/env bash
#
# Thin pointer to the shared, cross-repo tool, which lives in dotfiles at
# dot_local/bin/executable_setup-release-please-app and deploys to
# ~/.local/bin/setup-release-please-app. Keeping a pointer here means this
# repo's documented command still works without carrying a copy that drifts.
#
# The tool installs the shared App (mgoodness-release-please) on the repo and
# sets RELEASE_PLEASE_APP_CLIENT_ID and RELEASE_PLEASE_APP_PRIVATE_KEY.
set -euo pipefail

if ! command -v setup-release-please-app >/dev/null 2>&1; then
    cat >&2 <<'EOF'
setup-release-please-app is not on PATH.
It ships with dotfiles (dot_local/bin/executable_setup-release-please-app)
and deploys to ~/.local/bin. Install dotfiles, then re-run this script.
EOF
    exit 1
fi

exec setup-release-please-app --app mgoodness-release-please "$@"
