# PDF Renamer

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-0.5+-orange.svg)](https://docs.astral.sh/uv/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pydantic-ai](https://img.shields.io/badge/pydantic--ai-1.0+-green.svg)](https://ai.pydantic.dev/)
[![GitHub](https://img.shields.io/badge/github-nostoslabs%2Fpdf--renamer-blue?logo=github)](https://github.com/nostoslabs/pdf-renamer)

Intelligent PDF file renaming using LLMs. This tool analyzes PDF content and metadata to suggest descriptive, standardized filenames.

> 🚀 Works with **OpenAI**, **Ollama**, **LM Studio**, and any OpenAI-compatible API

## Features

- Extracts text and metadata from PDFs
- Uses OpenAI GPT-4o-mini for cost-efficient filename generation
- Suggests filenames in format: `Author-Topic-Year.pdf`
- Dry-run mode to preview changes before applying
- Interactive mode for manual confirmation
- Batch processing of multiple PDFs

## Setup

1. Install dependencies using `uv`:
```bash
cd pdf-renamer
```

2. Configure your LLM provider:

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

You can use this tool in two ways:

### Option 1: Using `uvx` (Recommended - No Installation)

Run the tool directly from the project directory without installation:

```bash
# Preview renames (dry-run mode)
uvx --from . pdf-rename --dry-run /path/to/pdf/directory

# Actually rename files
uvx --from . pdf-rename --no-dry-run /path/to/pdf/directory

# Interactive mode
uvx --from . pdf-rename --interactive --no-dry-run /path/to/pdf/directory
```

### Option 2: Using `uv run` (Development Mode)

If you're developing or modifying the code:

```bash
# Preview renames
uv run python -m pdf_renamer.main --dry-run /path/to/pdf/directory

# Actually rename files
uv run python -m pdf_renamer.main --no-dry-run /path/to/pdf/directory
```

### Options

- `--dry-run/--no-dry-run`: Show suggestions without renaming (default: True)
- `--interactive, -i`: Confirm each rename interactively
- `--model`: Model to use (default: gpt-4o-mini, works with any OpenAI-compatible API)
- `--url`: Custom base URL for OpenAI-compatible APIs (e.g., http://patmos:11434/v1)
- `--pattern`: Glob pattern for files (default: *.pdf)

### Examples

**Using OpenAI:**
```bash
# Preview all PDFs in current directory (using uvx)
uvx --from . pdf-rename --dry-run .

# Rename PDFs in specific directory (using uvx)
uvx --from . pdf-rename --no-dry-run ~/Documents/Papers

# Use a different OpenAI model
uvx --from . pdf-rename --model gpt-4o --dry-run .
```

**Using Ollama (or other local models):**
```bash
# Using Ollama on patmos server with gemma model
uvx --from . pdf-rename --url http://patmos:11434/v1 --model gemma3:latest --dry-run .

# Using local Ollama with qwen model
uvx --from . pdf-rename --url http://localhost:11434/v1 --model qwen2.5 --dry-run .

# Set URL in environment and just use model flag
export LLM_BASE_URL=http://patmos:11434/v1
uvx --from . pdf-rename --model gemma3:latest --dry-run .
```

**Other examples:**
```bash
# Process only specific files
uvx --from . pdf-rename --pattern "*2020*.pdf" --dry-run .

# Interactive mode with local model
uvx --from . pdf-rename --url http://patmos:11434/v1 --model gemma3:latest --interactive --no-dry-run .

# From parent directory
cd "/path/to/parent"
uvx --from ./pdf-renamer pdf-rename --dry-run .
```

## How It Works

1. **Extract**: Reads first 3 pages and metadata from each PDF
2. **Analyze**: Sends excerpt to LLM with instructions to generate filename
3. **Suggest**: LLM returns filename in `Author-Topic-Year` format with confidence level
4. **Rename**: Applies suggestions (if not in dry-run mode)

## Cost Considerations

**OpenAI:**
- Uses `gpt-4o-mini` by default (very cost-effective)
- Processes only first ~3000 characters per PDF
- Typical cost: ~$0.001-0.002 per PDF

**Ollama/Local Models:**
- Completely free (runs on your hardware)
- Works with any Ollama model (llama3, qwen2.5, mistral, etc.)
- Also compatible with LM Studio, vLLM, and other OpenAI-compatible endpoints

## Filename Format

The tool generates filenames in this format:
- `Smith-Kalman-Filtering-2020.pdf`
- `Adamy-Electronic-Warfare-Modeling.pdf`
- `Blair-Monopulse-Processing-Unresolved-Targets.pdf`

Guidelines:
- First author's last name
- 2-4 word topic description
- Year (if identifiable)
- Hyphens between words
- Max 60 characters (preferred)
