"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    llm_provider: Literal["openai"] = Field(
        default="openai",
        description="LLM provider to use",
    )
    llm_model: str = Field(
        default="llama3.2",
        description="Model name to use",
    )
    llm_base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for OpenAI-compatible API",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key (optional for local models)",
    )

    # PDF Extraction Configuration
    pdf_max_pages: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum pages to extract from PDF",
    )
    pdf_max_chars: int = Field(
        default=8000,
        ge=1000,
        le=50000,
        description="Maximum characters to extract from PDF",
    )
    pdf_extractor: Literal["docling", "pymupdf"] = Field(
        default="docling",
        description="PDF extractor to use (docling for better structure, pymupdf for speed)",
    )

    # Processing Configuration
    max_concurrent_api: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum concurrent API calls",
    )
    max_concurrent_pdf: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum concurrent PDF extractions",
    )

    # Retry Configuration
    retry_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for API calls",
    )
    retry_min_wait: int = Field(
        default=4,
        ge=1,
        le=60,
        description="Minimum wait time for exponential backoff (seconds)",
    )
    retry_max_wait: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum wait time for exponential backoff (seconds)",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()
