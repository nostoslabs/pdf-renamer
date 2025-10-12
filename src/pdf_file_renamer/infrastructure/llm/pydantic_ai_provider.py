"""LLM provider using Pydantic AI for structured output generation."""

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pdf_file_renamer.domain.models import ConfidenceLevel, FilenameResult
from pdf_file_renamer.domain.ports import LLMProvider

# System prompt for filename generation
FILENAME_GENERATION_PROMPT = """You are an expert at creating concise, descriptive filenames for academic papers and technical documents.

Your task is to analyze PDF content and suggest a clear, descriptive filename that accurately captures the document's identity.

CRITICAL: PDF metadata (title, author, subject) is often UNRELIABLE or MISSING. Always prioritize what you find in the actual document text over metadata fields.

Filename Format: Author-Topic-Year
Example: Smith-Neural-Networks-Deep-Learning-2020

EXTRACTION STRATEGY:
1. AUTHOR: Look for author names in these locations (in order of reliability):
   - First page header/title area
   - After the title (often in smaller font or with affiliations)
   - Paper byline (e.g., "by John Smith" or "Authors: Smith et al.")
   - Email addresses can help confirm author names
   - If multiple authors, use ONLY the first author's last name
   - IGNORE metadata author field if it conflicts with document text

2. TOPIC/TITLE: Look for the main title in:
   - Large text at top of first page (usually biggest font)
   - Abstract section which often restates the title
   - Running headers on subsequent pages
   - Condense long titles to key terms (3-6 words)
   - Remove generic words like "A Study of", "An Analysis of", "Introduction to"
   - Keep domain-specific terminology intact

3. YEAR: Look for publication year in:
   - Copyright notice or footer on first page
   - Date near title or author information
   - Conference/journal citation info
   - Page headers/footers
   - ONLY include year if you find it clearly stated
   - Do NOT guess or estimate years

EXAMPLES OF GOOD FILENAMES:
- Hinton-Deep-Learning-Review-2015
- Vapnik-Support-Vector-Networks-1995
- Goodfellow-Generative-Adversarial-Networks-2014
- Hochreiter-Long-Short-Term-Memory-1997

FORMATTING RULES:
- Use hyphens between ALL words (no spaces or underscores)
- Use title case for all words
- Remove special characters: colons, quotes, commas, parentheses
- Target 60-100 characters total (can be shorter or slightly longer if needed)
- If title is very long, focus on the most distinctive/searchable terms

CONFIDENCE LEVELS:
- HIGH: You found author (first page), clear title, and year in the document text
- MEDIUM: You found title and either author OR year, or title is very clear but other elements missing
- LOW: Document text is unclear, heavily formatted, or you can only extract partial information

IMPORTANT: When metadata contradicts document text, TRUST THE DOCUMENT TEXT. Explain your reasoning briefly."""


class PydanticAIProvider(LLMProvider):
    """LLM provider using Pydantic AI with structured outputs."""

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        retry_max_attempts: int = 3,
        retry_min_wait: int = 4,
        retry_max_wait: int = 30,
    ) -> None:
        """
        Initialize the Pydantic AI provider.

        Args:
            model_name: Model name to use
            api_key: API key (optional for local models)
            base_url: Base URL for OpenAI-compatible API
            retry_max_attempts: Maximum retry attempts
            retry_min_wait: Minimum wait time for retries (seconds)
            retry_max_wait: Maximum wait time for retries (seconds)
        """
        self.model_name = model_name
        self.retry_max_attempts = retry_max_attempts
        self.retry_min_wait = retry_min_wait
        self.retry_max_wait = retry_max_wait

        # Create model with appropriate configuration
        if base_url:
            client = AsyncOpenAI(base_url=base_url, api_key=api_key or "dummy-key")
            provider = OpenAIProvider(openai_client=client)
            model = OpenAIModel(model_name, provider=provider)
        else:
            if api_key:
                client = AsyncOpenAI(api_key=api_key)
                provider = OpenAIProvider(openai_client=client)
                model = OpenAIModel(model_name, provider=provider)
            else:
                model = OpenAIModel(model_name)

        # Create agent with structured output
        self.agent: Agent[None, FilenameResult] = Agent(
            model=model,
            output_type=FilenameResult,
            system_prompt=FILENAME_GENERATION_PROMPT,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type(
            (APIError, APIConnectionError, RateLimitError, APITimeoutError)
        ),
        reraise=True,
    )
    async def generate_filename(
        self,
        original_filename: str,
        text_excerpt: str,
        metadata_dict: dict[str, str | list[str] | None],
    ) -> FilenameResult:
        """
        Generate filename using LLM with retry logic.

        Args:
            original_filename: Current filename
            text_excerpt: Extracted text from PDF
            metadata_dict: PDF metadata dictionary

        Returns:
            FilenameResult with suggestion

        Raises:
            RuntimeError: If generation fails after retries
        """
        try:
            # Build context for LLM
            context_parts = [f"Original filename: {original_filename}"]

            # Add metadata hints if available
            if title := metadata_dict.get("title"):
                context_parts.append(f"PDF Title metadata (may be unreliable): {title}")
            if author := metadata_dict.get("author"):
                context_parts.append(f"PDF Author metadata (may be unreliable): {author}")
            if subject := metadata_dict.get("subject"):
                context_parts.append(f"PDF Subject metadata (may be unreliable): {subject}")

            # Add focused metadata hints
            year_hints = metadata_dict.get("year_hints")
            if year_hints and isinstance(year_hints, list):
                context_parts.append(f"Years found in document: {', '.join(year_hints)}")

            email_hints = metadata_dict.get("email_hints")
            if email_hints and isinstance(email_hints, list):
                context_parts.append(
                    f"Email addresses found (often near authors): {', '.join(email_hints[:2])}"
                )

            author_hints = metadata_dict.get("author_hints")
            if author_hints and isinstance(author_hints, list):
                context_parts.append("Possible author sections:\n" + "\n".join(author_hints[:2]))
            if header_text := metadata_dict.get("header_text"):
                context_parts.append(f"First 500 chars (likely title/author area):\n{header_text}")

            # Add full text excerpt
            context_parts.append(f"\nFull content excerpt (first ~5 pages):\n{text_excerpt}")

            context = "\n".join(context_parts)

            # Generate filename
            result = await self.agent.run(context)
            suggestion = result.output

            # If confidence is low, try a focused second pass
            if suggestion.confidence == ConfidenceLevel.LOW:
                suggestion = await self._retry_with_focus(original_filename, text_excerpt)

            return suggestion

        except Exception as e:
            msg = f"Failed to generate filename: {e}"
            raise RuntimeError(msg) from e

    async def _retry_with_focus(self, original_filename: str, text_excerpt: str) -> FilenameResult:
        """
        Retry filename generation with more focused prompting.

        Args:
            original_filename: Current filename
            text_excerpt: Extracted text from PDF

        Returns:
            FilenameResult from second pass
        """
        # Focus on first portion of text
        first_pages = text_excerpt[:4000]

        focused_context = f"""SECOND PASS - The initial analysis had low confidence. Please analyze more carefully.

Original filename: {original_filename}

FOCUS ON: The first few pages contain the most important metadata (title, author, year).
Look VERY carefully at:
1. The largest text on page 1 (this is usually the title)
2. Text immediately after the title (usually authors and affiliations)
3. Any dates, copyright notices, or publication info on page 1
4. Headers and footers that might contain publication info

First pages content:
{first_pages}

Please extract whatever information you can find with certainty. If you cannot find author or year, that's OK - just provide the best title you can determine."""

        result = await self.agent.run(focused_context)
        return result.output
