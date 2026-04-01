from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")

    app_name: str = "ai-next-book-rag"
    opac_base_url: str = "https://opac.provincia.re.it"
    request_timeout_seconds: int = 12
    llm_timeout_seconds: int = 8
    headless_browser: bool = True
    user_agent: str = "ai-next-book-rag/0.1"


settings = Settings()
