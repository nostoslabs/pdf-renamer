"""LLM-based filename generator for PDF files."""

from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError
import re


class SuggestedFilename(BaseModel):
    """Model for the suggested filename."""

    filename: str = Field(
        description="A descriptive filename without extension, using hyphens between words"
    )
    confidence: str = Field(
        description="Confidence level: high, medium, or low"
    )
    reasoning: str = Field(
        description="Brief explanation of why this filename was chosen"
    )


class FilenameGenerator:
    """Generator that uses LLM to suggest filenames based on PDF content."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None
    ):
        """
        Initialize the filename generator.

        Args:
            model_name: Model to use (default: gpt-4o-mini for cost efficiency)
            api_key: API key (if not provided, reads from OPENAI_API_KEY env var)
            base_url: Custom base URL for OpenAI-compatible APIs (e.g., Ollama, LM Studio)
        """
        # If base_url is provided, create a custom provider
        if base_url:
            client = AsyncOpenAI(base_url=base_url, api_key=api_key or "dummy-key")
            provider = OpenAIProvider(openai_client=client)
            model = OpenAIModel(model_name, provider=provider)
        else:
            # Use default OpenAI provider
            if api_key:
                client = AsyncOpenAI(api_key=api_key)
                provider = OpenAIProvider(openai_client=client)
                model = OpenAIModel(model_name, provider=provider)
            else:
                model = OpenAIModel(model_name)

        self.agent = Agent(
            model=model,
            output_type=SuggestedFilename,
            system_prompt="""You are an expert at creating concise, descriptive filenames for academic papers and technical documents.

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

IMPORTANT: When metadata contradicts document text, TRUST THE DOCUMENT TEXT. Explain your reasoning briefly.""",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((APIError, APIConnectionError, RateLimitError, APITimeoutError)),
        reraise=True
    )
    async def generate_filename(
        self,
        original_filename: str,
        text_excerpt: str,
        metadata: dict
    ) -> SuggestedFilename:
        """
        Generate a filename suggestion based on PDF content.
        Automatically retries up to 3 times on API errors with exponential backoff.
        Also uses a multi-pass approach for low confidence results.

        Args:
            original_filename: Current filename
            text_excerpt: Excerpt from the PDF
            metadata: PDF metadata dictionary

        Returns:
            SuggestedFilename with suggestion and confidence
        """
        # Prepare context for the LLM
        context_parts = [f"Original filename: {original_filename}"]

        # Add PDF metadata (if available, but note it may be unreliable)
        if metadata:
            if title := metadata.get("title"):
                context_parts.append(f"PDF Title metadata (may be unreliable): {title}")
            if author := metadata.get("author"):
                context_parts.append(f"PDF Author metadata (may be unreliable): {author}")
            if subject := metadata.get("subject"):
                context_parts.append(f"PDF Subject metadata (may be unreliable): {subject}")

            # Add focused metadata hints if available
            if focused := metadata.get("focused"):
                if year_hints := focused.get("year_hints"):
                    context_parts.append(f"Years found in document: {', '.join(map(str, year_hints))}")
                if email_hints := focused.get("email_hints"):
                    context_parts.append(f"Email addresses found (often near authors): {', '.join(email_hints[:2])}")
                if author_hints := focused.get("author_hints"):
                    context_parts.append(f"Possible author sections:\n" + "\n".join(author_hints))
                if header_text := focused.get("header_text"):
                    context_parts.append(f"First 500 chars (likely title/author area):\n{header_text}")

        # Send full extracted text to LLM
        context_parts.append(f"\nFull content excerpt (first ~5 pages):\n{text_excerpt}")

        context = "\n".join(context_parts)

        # First pass
        result = await self.agent.run(context)
        suggestion = result.output

        # If confidence is low, try a second pass with more focused extraction
        if suggestion.confidence.lower() == "low":
            # Second pass: Focus on first 2 pages more carefully
            first_pages = text_excerpt[:4000]  # Roughly first 2 pages

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
            suggestion = result.output

        return suggestion

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to be filesystem-safe.

        Args:
            filename: The filename to sanitize

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace multiple spaces/hyphens with single hyphen
        filename = re.sub(r'[\s\-]+', '-', filename)
        # Remove leading/trailing hyphens
        filename = filename.strip('-')
        # Limit length
        if len(filename) > 100:
            filename = filename[:100].rstrip('-')
        return filename
