#!/usr/bin/env python3
"""
Create a demo GIF showing pdf-renamer in action.

This script uses subprocess to run pdf-renamer and capture the output,
then can optionally convert to GIF using available tools.

Requirements:
- Install one of: vhs, asciinema+agg, or terminalizer
"""

import subprocess
import sys
from pathlib import Path


def check_command(cmd: str) -> bool:
    """Check if a command is available."""
    try:
        subprocess.run(
            ["which", cmd], capture_output=True, check=True, text=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def install_vhs():
    """Install VHS using Homebrew."""
    print("Installing VHS (recommended)...")
    print("Running: brew install vhs")
    try:
        subprocess.run(["brew", "install", "vhs"], check=True)
        return True
    except subprocess.CalledProcessError:
        print("Failed to install VHS via Homebrew")
        return False
    except FileNotFoundError:
        print("Homebrew not found. Please install from https://brew.sh/")
        return False


def record_with_vhs():
    """Record demo using VHS."""
    print("Recording demo with VHS...")
    tape_file = Path(__file__).parent.parent / "demo.tape"

    if not tape_file.exists():
        print(f"Error: {tape_file} not found")
        return False

    try:
        subprocess.run(["vhs", str(tape_file)], check=True)
        print("✓ Demo GIF created: demo.gif")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error recording with VHS: {e}")
        return False


def main():
    """Main function to create demo GIF."""
    print("PDF Renamer Demo GIF Creator")
    print("=" * 50)
    print()

    # Check for VHS
    if check_command("vhs"):
        print("✓ VHS is installed")
        if record_with_vhs():
            print()
            print("Success! Demo GIF created.")
            print("Add to README.md with:")
            print("  ![Demo](demo.gif)")
            return 0
    else:
        print("VHS not found.")
        print()
        response = input("Would you like to install VHS? (y/n): ").strip().lower()
        if response == 'y':
            if install_vhs():
                print()
                if record_with_vhs():
                    print()
                    print("Success! Demo GIF created.")
                    print("Add to README.md with:")
                    print("  ![Demo](demo.gif)")
                    return 0
            else:
                print("Installation failed.")
        else:
            print()
            print("To create the demo manually:")
            print()
            print("Option 1 - Install VHS (recommended):")
            print("  brew install vhs")
            print("  vhs demo.tape")
            print()
            print("Option 2 - Install asciinema + agg:")
            print("  brew install asciinema")
            print("  cargo install agg")
            print("  ./scripts/record_demo.sh")
            print()
            print("Option 3 - Manual recording:")
            print("  Run: uv run pdf-file-renamer --dry-run tests/data/")
            print("  Use screen recording software to capture")
            print("  Convert to GIF with online tools or ffmpeg")
            return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
