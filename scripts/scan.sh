#!/usr/bin/env bash
# Secret scan of the full git history plus a canary: a fake credential is planted in a throw-away folder
# outside this repository, and gitleaks must report it. If the canary is not found, the scan counts as failed.
# Optional scanners run when installed: zizmor (workflows), osv-scanner (uv.lock).
set -euo pipefail
cd "$(dirname "$0")/.."
command -v gitleaks >/dev/null || { echo "gitleaks not installed"; exit 1; }

echo "== gitleaks: full history"
gitleaks git . --config .gitleaks.toml --redact --no-banner

echo "== gitleaks: canary"
# The canary is scanned as a directory (not committed): local commit hooks may block committing it, and the
# same default rules apply to both scan modes.
canary="$(mktemp -d)"
trap 'rm -rf "$canary"' EXIT
# Built at run time so that no credential-shaped string is stored in this repository.
key="AKIA$(python3 -c 'import secrets; print("".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567") for _ in range(16)))')"
printf 'aws_access_key_id = %s\n' "$key" > "$canary/config.txt"
if gitleaks dir "$canary" --config .gitleaks.toml --redact --no-banner >/dev/null 2>&1; then
  echo "FAIL: gitleaks did not report the planted canary credential"; exit 1
fi
echo "canary detected (expected)"

if command -v zizmor >/dev/null; then echo "== zizmor"; zizmor .github/workflows; else echo "zizmor not installed (skipped)"; fi
if command -v osv-scanner >/dev/null; then echo "== osv-scanner"; osv-scanner scan source --lockfile=uv.lock; else echo "osv-scanner not installed (skipped)"; fi
