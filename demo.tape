# VHS tape file for creating demo GIF
# Install VHS: brew install vhs
# Run: vhs demo.tape

Output demo.gif

Set FontSize 14
Set Width 1200
Set Height 600
Set Theme "Dracula"
Set TypingSpeed 100ms

Type "# PDF Renamer - LLM-powered file renaming"
Sleep 800ms
Enter
Sleep 300ms

Type "pdf-file-renamer --dry-run --url http://localhost:11434/v1 --model llama3.2 tests/data/"
Sleep 800ms
Enter

# Wait for processing
Sleep 25s

Sleep 2s
