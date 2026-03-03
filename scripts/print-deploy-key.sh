#!/usr/bin/env bash
# print-deploy-key.sh — Generate (if needed) and print the VM's deploy public key.
# Paste the output into GitHub → Settings → Deploy keys, or into your personal SSH authorized_keys.
#
# Run this on the VM:
#   bash scripts/print-deploy-key.sh

set -euo pipefail

KEY_PATH="$HOME/.ssh/id_ed25519_wildleague_deploy"

if [ ! -f "$KEY_PATH" ]; then
  echo "Generating new deploy key at $KEY_PATH..."
  ssh-keygen -t ed25519 -C "wildleague-deploy@$(hostname)" -f "$KEY_PATH" -N ""
fi

echo ""
echo "=== Public key (add to GitHub Deploy keys or authorized_keys) ==="
cat "${KEY_PATH}.pub"
echo "=================================================================="
echo ""
echo "=== Private key (add as DEPLOY_SSH_KEY secret in GitHub Actions) ==="
cat "$KEY_PATH"
echo "====================================================================="
