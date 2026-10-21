"""App configuration, read from environment variables / backend/.env.

These are start-up defaults. A few of them (LLM provider, similarity
threshold, max follow-up questions) can be changed at runtime on the
Settings page; those overrides are stored in the database.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Paths
    data_dir: Path = PROJECT_ROOT / "data"
    storage_dir: Path = BACKEND_DIR / "storage"
    database_url: str = ""  # empty -> sqlite file in storage_dir

    # Retrieval
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    similarity_threshold: float = 0.40
    max_followups: int = 2
    # Short pause between workflow steps so the "Checking..." labels are visible in demos (0 in tests)
    step_delay_seconds: float = 0.5

    # LLM provider: "mock" (default, offline) or "openai"
    llm_provider: str = "mock"

    # OpenAI (used when AZURE_OPENAI_ENDPOINT is empty)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Azure OpenAI (used when AZURE_OPENAI_ENDPOINT is set)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-06-01"

    @property
    def kb_dir(self) -> Path:
        return self.data_dir / "knowledge_base"

    @property
    def eval_dir(self) -> Path:
        return self.data_dir / "eval"

    @property
    def chroma_dir(self) -> Path:
        return self.storage_dir / "chroma"

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{(self.storage_dir / 'qai.db').as_posix()}"


settings = Settings()
