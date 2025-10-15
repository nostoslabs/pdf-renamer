#!/bin/bash
# Script to record a demo GIF of pdf-renamer in action
#
# Requirements (choose one):
# 1. VHS: brew install vhs (recommended - creates beautiful GIFs)
# 2. asciinema + agg: brew install asciinema && cargo install agg
# 3. terminalizer: npm install -g terminalizer

set -e

echo "PDF Renamer Demo Recording Script"
echo "=================================="
echo ""

# Check which tool is available
if command -v vhs &> /dev/null; then
    echo "Using VHS to record demo..."
    vhs demo.tape
    echo "✓ Demo GIF created: demo.gif"

elif command -v asciinema &> /dev/null; then
    echo "Using asciinema to record demo..."
    echo "Press Ctrl+D when done recording"

    # Record to asciinema format
    asciinema rec demo.cast -c "bash -c 'echo \"PDF Renamer Demo\" && echo \"\" && uv run pdf-file-renamer --dry-run --url http://localhost:11434/v1 --model llama3.2 tests/data/'"

    # Convert to GIF if agg is available
    if command -v agg &> /dev/null; then
        agg demo.cast demo.gif
        echo "✓ Demo GIF created: demo.gif"
    else
        echo "✓ Demo recording saved: demo.cast"
        echo "  Install agg to convert to GIF: cargo install agg"
        echo "  Then run: agg demo.cast demo.gif"
    fi

elif command -v terminalizer &> /dev/null; then
    echo "Using terminalizer to record demo..."
    terminalizer record demo -c "uv run pdf-file-renamer --dry-run --url http://localhost:11434/v1 --model llama3.2 tests/data/"
    terminalizer render demo
    echo "✓ Demo GIF created: demo.gif"

else
    echo "❌ No recording tool found. Please install one of:"
    echo ""
    echo "Option 1 (Recommended): VHS"
    echo "  brew install vhs"
    echo ""
    echo "Option 2: asciinema + agg"
    echo "  brew install asciinema"
    echo "  cargo install agg"
    echo ""
    echo "Option 3: terminalizer"
    echo "  npm install -g terminalizer"
    exit 1
fi

echo ""
echo "To add the GIF to README.md, add this line:"
echo ""
echo "![Demo](demo.gif)"
