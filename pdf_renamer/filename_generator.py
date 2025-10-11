"""LLM-based filename generator for PDF files."""

from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI
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

Your task is to analyze PDF metadata and content excerpts, then suggest a clear, descriptive filename.

Guidelines:
- Create filenames in the format: Author-Topic-Year (e.g., Smith-Kalman-Filtering-2020)
- If multiple authors, use first author's last name only
- Keep topic description concise but informative (2-4 words)
- Always include year if available
- Use hyphens to separate words (no spaces or underscores)
- Keep total length under 60 characters if possible
- For well-known papers, use recognizable short forms
- Only use information you can confirm from the content
- If year is uncertain, omit it rather than guess

Return high confidence only when you can clearly identify author, topic, and year.
Return medium confidence if some elements are unclear but you can infer the topic.
Return low confidence if the content is unclear or ambiguous.""",
        )

    async def generate_filename(
        self,
        original_filename: str,
        text_excerpt: str,
        metadata: dict
    ) -> SuggestedFilename:
        """
        Generate a filename suggestion based on PDF content.

        Args:
            original_filename: Current filename
            text_excerpt: Excerpt from the PDF
            metadata: PDF metadata dictionary

        Returns:
            SuggestedFilename with suggestion and confidence
        """
        # Prepare context for the LLM
        context_parts = [f"Original filename: {original_filename}"]

        if metadata:
            if title := metadata.get("title"):
                context_parts.append(f"PDF Title metadata: {title}")
            if author := metadata.get("author"):
                context_parts.append(f"PDF Author metadata: {author}")
            if subject := metadata.get("subject"):
                context_parts.append(f"PDF Subject metadata: {subject}")

        context_parts.append(f"\nContent excerpt:\n{text_excerpt[:2000]}")

        context = "\n".join(context_parts)

        result = await self.agent.run(context)
        return result.output

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
