from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")

    app_name: str = "ai-next-book-rag"
    chroma_path: Path = Path(__file__).resolve().parents[1] / "data" / "chroma"
    chroma_collection: str = "library_books"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    opac_base_url: str = "https://opac.provincia.re.it"
    request_timeout_seconds: int = 30
    headless_browser: bool = True
    user_agent: str = "ai-next-book-rag/0.1"


settings = Settings()
