"""Explicit runtime modes: no silent replacement of real models with mocks."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr | None = None
    mock_llm: bool = False
    retrieval_backend: Literal["fastembed", "mock"] | None = None
    qdrant_mode: Literal["local", "memory", "server"] = "local"
    qdrant_url: str = "http://localhost:6333"
    qdrant_path: Path = Path(".sentinel/qdrant")
    checkpoint_path: str = ".sentinel/checkpoints.sqlite"
    runbook_dir: Path = Path(__file__).resolve().parents[1] / "data/runbooks"
    model_cache: str = ".cache/models"
    collection_name: str = "sentinel_runbooks_v1"
    fast_model: str = "gpt-4o-mini"
    reasoning_model: str = "gpt-4o"
    api_token: SecretStr | None = None
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    use_presidio: bool = True

    @model_validator(mode="after")
    def validate_modes(self):
        if self.retrieval_backend is None:
            self.retrieval_backend = "mock" if self.mock_llm else "fastembed"
        if not self.mock_llm and not (
            self.openai_api_key and self.openai_api_key.get_secret_value()
        ):
            raise ValueError("Set OPENAI_API_KEY or use MOCK_LLM=true for the free offline demo")
        return self
