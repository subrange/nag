#!/usr/bin/env sh
set -e

REPO="https://raw.githubusercontent.com/subrange/nag/main"
CMD="nag"
WARN_PATH=0

if [ -w "/usr/local/bin" ]; then
    DIR="/usr/local/bin"
else
    DIR="$HOME/.local/bin"
    mkdir -p "$DIR"
    WARN_PATH=1
fi

command -v python3 > /dev/null || { echo "Error: python3 not found." >&2; exit 1; }

if command -v curl > /dev/null; then
    curl -fsSL "$REPO/nag.py" -o "$DIR/$CMD"
elif command -v wget > /dev/null; then
    wget -qO "$DIR/$CMD" "$REPO/nag.py"
else
    echo "Error: curl or wget required." >&2; exit 1
fi

chmod +x "$DIR/$CMD"

echo "Done. Run 'nag' to get started."

if [ "$WARN_PATH" -eq 1 ] && ! case ":$PATH:" in *":$DIR:"*) true;; *) false;; esac; then
    echo ""
    echo "Warning: $DIR is not in your PATH."
    echo "Add this to your shell config:"
    echo "  export PATH=\"$DIR:\$PATH\""
fi
