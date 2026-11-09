# Sourced by the start scripts. Uses ANTHROPIC_API_KEY if it's set, otherwise the macOS Keychain, so the key is never in a file.
# To store or replace it: security add-generic-password -a chamber -s chamber-anthropic-key -U -w
if [ -z "${ANTHROPIC_API_KEY:-}" ] && command -v security >/dev/null; then
  ANTHROPIC_API_KEY="$(security find-generic-password -a chamber -s chamber-anthropic-key -w 2>/dev/null || true)"
  export ANTHROPIC_API_KEY
fi
