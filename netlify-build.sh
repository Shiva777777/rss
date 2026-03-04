#!/usr/bin/env bash
set -euo pipefail

echo "[Netlify] Python runtime"
python --version

# Install Rust only when missing (needed by pydantic-core source builds)
if ! command -v cargo >/dev/null 2>&1; then
  echo "[Netlify] Installing Rust toolchain"
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi

export PATH="$HOME/.cargo/bin:$PATH"

echo "[Netlify] Upgrading pip/setuptools/wheel"
python -m pip install --upgrade pip setuptools wheel

echo "[Netlify] Installing Python dependencies"
python -m pip install -r requirements.txt

# Add any additional build steps below if needed.
# Example: npm ci && npm run build