# PDF Renamer

[![PyPI version](https://img.shields.io/pypi/v/pdf-file-renamer.svg)](https://pypi.org/project/pdf-file-renamer/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pdf-file-renamer.svg)](https://pypi.org/project/pdf-file-renamer/)
[![Python](https://img.shields.io/pypi/pyversions/pdf-file-renamer.svg)](https://pypi.org/project/pdf-file-renamer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/nostoslabs/pdf-renamer/workflows/CI/badge.svg)](https://github.com/nostoslabs/pdf-renamer/actions)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

**Intelligent PDF file renaming using LLMs and DOI metadata.** Automatically generate clean, descriptive filenames for your PDF library.

> 🚀 Works with **OpenAI**, **Ollama**, **LM Studio**, and any OpenAI-compatible API
> 📚 **DOI-first** approach for academic papers - no API costs!
> 🎯 **Interactive mode** with retry, edit, and skip options

## Table of Contents

- [Quick Example](#quick-example)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Interactive Mode](#interactive-mode)
- [How It Works](#how-it-works)
- [Cost Considerations](#cost-considerations)
- [Architecture](#architecture)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Quick Example

![Demo](demo.gif)

Transform messy filenames into clean, organized ones:

```
Before:                               After:
📄 paper_final_v3.pdf          →     Leroux-Analog-In-memory-Computing-2025.pdf
📄 download (2).pdf            →     Ruiz-Why-Don-Trace-Requirements-2023.pdf
📄 document.pdf                →     Raspail-Camp_of_the_Saints.pdf
```

**Live Progress Display:**
```
Processing 3 PDFs with max 3 concurrent API calls and 10 concurrent extractions

╭─────────────────────────── 📊 Progress ───────────────────────────╮
│ Total: 3 | Pending: 0 | Extracting: 0 | Analyzing: 0 | Complete: 3 │
╰───────────────────────────────────────────────────────────────────╯
╭───────────────────────────────────────────────────────────────────╮
│ [██████████████████████████████████████████████] 100.0%           │
╰───────────────────────────────────────────────────────────────────╯
                          Processing Status
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ File               ┃ Stage ┃ Status   ┃ Details             ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ paper_final_v3.pdf │   ✓   │ Complete │ very_high           │
│ download (2).pdf   │   ✓   │ Complete │ very_high (DOI)     │
│ document.pdf       │   ✓   │ Complete │ high                │
└────────────────────┴───────┴──────────┴─────────────────────┘
```

## Features

- **🎓 DOI-based naming** - Automatically extracts DOI and fetches authoritative metadata for academic papers
- **🧠 Advanced PDF parsing** using docling-parse for better structure-aware extraction
- **👁️ OCR fallback** for scanned PDFs with low text content
- **🎯 Smart LLM prompting** with multi-pass analysis for improved accuracy
- **⚡ Hybrid approach** - Uses DOI metadata when available, falls back to LLM analysis for other documents
- **📝 Standardized format** - Generates filenames like `Author-Topic-Year.pdf`
- **🔍 Dry-run mode** to preview changes before applying
- **💬 Enhanced interactive mode** with options to accept, manually edit, retry, or skip each file
- **📊 Live progress display** with concurrent processing for speed
- **⚙️ Configurable concurrency** limits for API calls and PDF extraction
- **📦 Batch processing** of multiple PDFs with optional output directory

## Installation

### Quick Start (No Installation Required)

```bash
# Run directly with uvx
uvx pdf-renamer --dry-run /path/to/pdfs
```

### Install from PyPI

```bash
# Using pip
pip install pdf-file-renamer

# Using uv
uv pip install pdf-file-renamer
```

### Install from Source

```bash
# Clone and install
git clone https://github.com/nostoslabs/pdf-renamer.git
cd pdf-renamer
uv sync
```

## Configuration

Configure your LLM provider:

**Option A: OpenAI (Cloud)**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

**Option B: Ollama or other local models**
```bash
# No API key needed for local models
# Either set LLM_BASE_URL in .env or use --url flag
echo "LLM_BASE_URL=http://patmos:11434/v1" > .env
```

## Usage

### Quick Start

```bash
# Preview renames (dry-run mode)
pdf-renamer --dry-run /path/to/pdf/directory

# Actually rename files
pdf-renamer --no-dry-run /path/to/pdf/directory

# Interactive mode - review each file
pdf-renamer --interactive --no-dry-run /path/to/pdf/directory
```

### Using uvx (No Installation)

```bash
# Run directly without installing
uvx pdf-renamer --dry-run /path/to/pdfs

# Run from GitHub
uvx https://github.com/nostoslabs/pdf-renamer --dry-run /path/to/pdfs
```

### Options

- `--dry-run/--no-dry-run`: Show suggestions without renaming (default: True)
- `--interactive, -i`: Interactive mode with rich options:
  - **Accept** - Use the suggested filename
  - **Edit** - Manually modify the filename
  - **Retry** - Ask the LLM to generate a new suggestion
  - **Skip** - Skip this file and move to the next
- `--model`: Model to use (default: llama3.2, works with any OpenAI-compatible API)
- `--url`: Custom base URL for OpenAI-compatible APIs (default: http://localhost:11434/v1)
- `--pattern`: Glob pattern for files (default: *.pdf)
- `--output-dir, -o`: Move renamed files to a different directory
- `--max-concurrent-api`: Maximum concurrent API calls (default: 3)
- `--max-concurrent-pdf`: Maximum concurrent PDF extractions (default: 10)

### Examples

**Using OpenAI:**
```bash
# Preview all PDFs in current directory
uvx pdf-renamer --dry-run .

# Rename PDFs in specific directory
uvx pdf-renamer --no-dry-run ~/Documents/Papers

# Use a different OpenAI model
uvx pdf-renamer --model gpt-4o --dry-run .
```

**Using Ollama (or other local models):**
```bash
# Using Ollama on patmos server with gemma model
uvx pdf-renamer --url http://patmos:11434/v1 --model gemma3:latest --dry-run .

# Using local Ollama with qwen model
uvx pdf-renamer --url http://localhost:11434/v1 --model qwen2.5 --dry-run .

# Set URL in environment and just use model flag
export LLM_BASE_URL=http://patmos:11434/v1
uvx pdf-renamer --model gemma3:latest --dry-run .
```

**Other examples:**
```bash
# Process only specific files
uvx pdf-renamer --pattern "*2020*.pdf" --dry-run .

# Interactive mode with local model
uvx pdf-renamer --url http://patmos:11434/v1 --model gemma3:latest --interactive --no-dry-run .

# Run directly from GitHub
uvx https://github.com/nostoslabs/pdf-renamer --no-dry-run ~/Documents/Papers
```

## Interactive Mode

When using `--interactive` mode, you'll be presented with each file one at a time with detailed options:

```
================================================================================
Original: 2024-research-paper.pdf
Suggested: Smith-Machine-Learning-Applications-2024.pdf
Confidence: high
Reasoning: Clear author and topic identified from abstract
================================================================================

Options:
  y / yes / Enter - Accept suggested name
  e / edit - Manually edit the filename
  r / retry - Ask LLM to generate a new suggestion
  n / no / skip - Skip this file

What would you like to do? [y]:
```

This mode is perfect for:
- **Reviewing suggestions** before applying them
- **Fine-tuning filenames** that are close but not quite right
- **Retrying** when the LLM suggestion isn't good enough
- **Building confidence** in the tool before batch processing

You can use interactive mode with `--dry-run` to preview without actually renaming files, or with `--no-dry-run` to apply changes immediately after confirmation.

## How It Works

### Intelligent Hybrid Approach

The tool uses a multi-strategy approach to generate accurate filenames:

1. **DOI Detection** (for academic papers)
   - Searches PDF for DOI identifiers using [pdf2doi](https://github.com/MicheleCotrufo/pdf2doi)
   - **Validates DOI metadata** against PDF content to prevent citation DOI mismatches
   - If found and validated, queries authoritative metadata (title, authors, year, journal)
   - Generates filename with **very high confidence** from validated metadata
   - **Saves API costs** - no LLM call needed for papers with DOIs

2. **LLM Analysis** (fallback for non-academic PDFs)
   - **Extract**: Uses docling-parse to read first 5 pages with structure-aware parsing, falls back to PyMuPDF if needed
   - **OCR**: Automatically applies OCR for scanned PDFs with minimal text
   - **Metadata Enhancement**: Extracts focused hints (years, emails, author sections) to supplement unreliable PDF metadata
   - **Analyze**: Sends full content excerpt to LLM with enhanced metadata and detailed extraction instructions
   - **Multi-pass Review**: Low-confidence results trigger a second analysis pass with focused prompts
   - **Suggest**: LLM returns filename in `Author-Topic-Year` format with confidence level and reasoning

3. **Interactive Review** (optional): User can accept, edit, retry, or skip each suggestion
4. **Rename**: Applies suggestions (if not in dry-run mode)

### Benefits of DOI Integration

- **Accuracy**: DOI metadata is canonical and verified
- **Speed**: Instant lookup vs. LLM processing time
- **Cost**: Free DOI lookups save on API costs for academic papers
- **Reliability**: Works even when PDF text extraction is poor

## Cost Considerations

**DOI-based Naming (Academic Papers):**
- **Completely free** - No API costs
- **No LLM needed** - Direct metadata lookup
- Works for most academic papers with embedded DOIs

**OpenAI (Fallback):**
- Uses `gpt-4o-mini` by default (very cost-effective)
- Only called when DOI not found
- Processes first ~4500 characters per PDF
- Typical cost: ~$0.001-0.003 per PDF

**Ollama/Local Models:**
- Completely free (runs on your hardware)
- Works with any Ollama model (llama3, qwen2.5, mistral, etc.)
- Also compatible with LM Studio, vLLM, and other OpenAI-compatible endpoints

## Filename Format

The tool generates filenames in this format:
- `Smith-Kalman-Filtering-Applications-2020.pdf`
- `Adamy-Electronic-Warfare-Modeling-Techniques.pdf`
- `Blair-Monopulse-Processing-Unresolved-Targets.pdf`

Guidelines:
- First author's last name
- 3-6 word topic description (prioritizes clarity over brevity)
- Year (if identifiable)
- Hyphens between words
- Target ~80 characters (can be longer if needed for clarity)

## Architecture

This project follows **Clean Architecture** principles with clear separation of concerns:

```
src/pdf_file_renamer/
├── domain/          # Core business logic (models, ports)
├── application/     # Use cases and workflows
├── infrastructure/  # External integrations (PDF, LLM, DOI)
└── presentation/    # CLI and UI components
```

**Key Design Patterns:**
- **Ports and Adapters** - Clean interfaces for external dependencies
- **Dependency Injection** - Flexible component composition
- **Single Responsibility** - Each module has one clear purpose
- **Type Safety** - Full mypy strict mode compliance

See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for detailed architecture notes.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/nostoslabs/pdf-renamer.git
cd pdf-renamer

# Install dependencies with uv
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/
```

### Code Quality

- **Tests**: pytest with async support and coverage reporting
- **Linting**: ruff for fast, comprehensive linting
- **Formatting**: ruff format for consistent code style
- **Type Checking**: mypy in strict mode
- **CI/CD**: GitHub Actions for automated testing and releases

### Running Locally

```bash
# Run with local changes
uv run pdf-file-renamer --dry-run /path/to/pdfs

# Run specific module
uv run python -m pdf_file_renamer.main --help
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`uv run pytest && uv run ruff check src/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Follow PEP 8 (enforced by ruff)
- Use type hints for all functions
- Write tests for new features
- Update documentation as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [pdf2doi](https://github.com/MicheleCotrufo/pdf2doi) for DOI extraction
- [pydantic-ai](https://ai.pydantic.dev/) for LLM integration
- [docling-parse](https://github.com/DS4SD/docling-parse) for advanced PDF parsing
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF text extraction
- [rich](https://rich.readthedocs.io/) for beautiful terminal UI

## Support

- **Issues**: [GitHub Issues](https://github.com/nostoslabs/pdf-renamer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nostoslabs/pdf-renamer/discussions)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

**Made with ❤️ by [Nostos Labs](https://github.com/nostoslabs)**
