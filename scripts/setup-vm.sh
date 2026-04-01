#!/bin/bash
set -euo pipefail

echo "=== Gisst VM Setup ==="
echo ""

# 1. Install Bun
if command -v bun &> /dev/null; then
  echo "[✓] Bun already installed: $(bun --version)"
else
  echo "[*] Installing Bun..."
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
  echo "[✓] Bun installed: $(bun --version)"
fi

# 2. Install Claude Code
if command -v claude &> /dev/null; then
  echo "[✓] Claude Code already installed: $(claude --version 2>/dev/null || echo 'installed')"
else
  echo "[*] Installing Claude Code..."
  npm install -g @anthropic-ai/claude-code
  echo "[✓] Claude Code installed"
  echo ""
  echo "!!! IMPORTANT: You need to run 'claude login' manually in tmux to authenticate."
  echo "!!! This is a one-time interactive step that cannot be automated."
fi

# 3. Install dependencies
echo "[*] Installing project dependencies..."
cd "$(dirname "$0")/../src"
bun install
echo "[✓] Dependencies installed"

# 4. Create data directories
echo "[*] Creating data directories..."
mkdir -p data/workspace data/agents data/sessions data/staging
echo "[✓] Data directories created"

# 5. Setup .env if it doesn't exist
if [ ! -f .env ]; then
  echo "[*] Creating .env from .env.example..."
  cp .env.example .env
  echo "[!] Edit src/.env with your actual values before running the agent."
else
  echo "[✓] .env already exists"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Run 'claude login' in tmux to authenticate Claude Code"
echo "  2. Edit src/.env with your config"
echo "  3. Test the agent: cd src && bun run test-agent"
echo ""
