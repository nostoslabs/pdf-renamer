# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.3] - 2025-10-14

### Fixed
- Fixed critical bug where pdf2doi extracted DOIs from citations instead of the paper's own DOI
- Added DOI validation to verify metadata matches PDF content before accepting DOI
- Prevents incorrect naming when papers don't have their own DOI but cite other papers

### Added
- DOI metadata validation against PDF first page content
- Title similarity checking using SequenceMatcher
- Configurable validation thresholds for DOI matching
- Fallback to LLM-based naming when DOI validation fails

### Changed
- DOI extraction now validates that extracted metadata matches the actual PDF content
- Improved accuracy by rejecting citation DOIs that don't match the paper's title
- DOI validation checks title area (first ~300 characters) instead of full document

## [0.6.2] - 2025-10-14

### Added
- Demo GIF showing pdf-renamer in action with live TUI
- VHS recording infrastructure (demo.tape)
- Automated demo creation scripts (create_demo_gif.py, record_demo.sh)
- Comprehensive PyPI metadata and classifiers
- Table of contents in README for better navigation
- Architecture, Development, and Contributing sections in README
- Project URLs for homepage, repository, issues, and changelog

### Changed
- Enhanced README with animated demo, better badges, and emoji icons
- Improved PyPI discoverability with keywords and proper categorization
- Updated description to highlight DOI-first approach and interactive mode

## [0.6.1] - 2025-10-14

### Fixed
- Fixed DOI extractor incorrectly expecting list instead of dict from pdf2doi
- Fixed JSON parsing for CrossRef API metadata instead of incorrect bibtex parsing
- Fixed confidence enum handling causing AttributeError in workflow and formatters
- Fixed linting errors (SIM105 - use contextlib.suppress)
- Fixed mypy type checking errors in author extraction
- Fixed code formatting issues

### Changed
- Improved DOI metadata extraction from CrossRef JSON structure
- Enhanced type safety with explicit type annotations

## [0.6.0] - 2025-10-14

### Added
- DOI-based naming feature using pdf2doi library
- Automatic DOI extraction from academic papers
- CrossRef API integration for rich metadata (title, authors, year, journal, publisher)
- Hybrid naming strategy: DOI-first with LLM fallback
- DOI metadata display in interactive prompts
- Enhanced status display showing "DOI found" during processing

### Changed
- Improved filename generation with VERY_HIGH confidence for DOI-based names
- Updated workflow to prioritize DOI extraction before LLM analysis
- Enhanced reasoning messages to indicate DOI-based naming

## [0.5.0] - 2025-10-12

### Changed
- Reorganized project to src layout structure (src/pdf_file_renamer)
- Improved package organization following Python best practices
- Updated all imports and references to new structure

## [0.4.2] - 2025-10-12

### Changed
- Renamed package from `pdf_renamer` to `pdf-file-renamer` for PyPI
- Updated package name across all configurations
- Improved PyPI package metadata

## [0.4.1] - 2025-10-12

### Added
- Initial PyPI publishing workflow
- Automated releases via GitHub Actions

## [0.4.0] - 2025-10-12

### Added
- Complete refactoring to Clean Architecture
- Comprehensive unit tests with pytest
- Type checking with mypy (strict mode)
- Code quality with ruff linting and formatting
- GitHub Actions CI/CD pipeline
- Code coverage reporting with pytest-cov
- Domain-driven design with clear separation of concerns
- Port and adapter pattern for external dependencies

### Changed
- Reorganized codebase into domain, application, infrastructure, and presentation layers
- Improved testability and maintainability
- Enhanced documentation with architecture notes

## [0.3.0] - 2025-10-11

### Added
- Enhanced interactive mode with retry, edit, and skip options
- Multi-pass analysis for better accuracy
- Focused metadata extraction for improved LLM context
- Better error handling and recovery

### Changed
- Improved LLM prompting strategy
- Enhanced user experience with clearer prompts
- Better handling of edge cases

## [0.2.0] - 2025-10-10

### Added
- Interactive mode for rename confirmation
- Rich terminal UI with tables and colored output
- Batch processing with progress tracking
- Live status updates during processing

### Changed
- Simplified CLI by removing subcommand requirement
- Improved PDF processing pipeline
- Enhanced error messages

## [0.1.0] - 2025-10-09

### Added
- Initial release
- PDF text extraction using PyMuPDF
- LLM-based filename generation (OpenAI and Ollama support)
- Dry-run mode for safe testing
- Basic CLI interface
- Configuration via environment variables
- Confidence scoring for suggestions
- Support for custom output directories

[0.6.3]: https://github.com/nostoslabs/pdf-renamer/compare/v0.6.2...v0.6.3
[0.6.2]: https://github.com/nostoslabs/pdf-renamer/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/nostoslabs/pdf-renamer/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/nostoslabs/pdf-renamer/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/nostoslabs/pdf-renamer/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/nostoslabs/pdf-renamer/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/nostoslabs/pdf-renamer/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/nostoslabs/pdf-renamer/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/nostoslabs/pdf-renamer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/nostoslabs/pdf-renamer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nostoslabs/pdf-renamer/releases/tag/v0.1.0
