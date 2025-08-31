from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal
import os
import rootutils
from pydantic import SecretStr, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

rootutils.setup_root(__file__, indicator=".env", pythonpath=True)

ChatModel = Literal["gpt-5", "gpt-5-mini", "gpt-5-nano", "gemini-2.0-flash", "gemini-2.5-flash"]
EmbedModel = Literal["text-embedding-3-small", "text-embedding-3-large"]
Dist = Literal["cosine", "l2", "ip"]

# Mapping of embedding models to their dimensions
EMBED_MODEL_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


@dataclass
class VectorConfig:
    """Configuration for vector store (pgvector)."""

    dim: int = 1536  # Dimension of the embedding vector
    distance: Dist = "cosine"  # Distance metric for vector search
    hsnw_m: int = 16  # HNSW max connections per layer
    hsnw_ef_construction: int = 64  # HNSW construction-time exploration factor
    hsnw_ef_search: int = 64  # HNSW search-time exploration factor
    ivf_lists: int = 1000  # Number of IVF lists
    ivf_probes: int = 10  # Number of IVF probes during search

    def update_dim(self, new_dim: int):
        """Return a new VectorConfig with updated dimension."""
        return VectorConfig(
            dim=new_dim,
            distance=self.distance,
            hsnw_m=self.hsnw_m,
            hsnw_ef_construction=self.hsnw_ef_construction,
            hsnw_ef_search=self.hsnw_ef_search,
            ivf_lists=self.ivf_lists,
            ivf_probes=self.ivf_probes,
        )


def _as_list(v: str | list[str] | None) -> list[str]:
    """Convert input to a list of stripped strings, defaulting to empty list."""
    if v is None or v == "":
        return []
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return [s.strip() for s in v if s.strip()]


class Settings(BaseSettings):
    """Application configuration settings."""

    # --- App ---
    APP_NAME: str = "AmiAgent"
    APP_ENV: Literal["dev", "staging", "prod"] = "dev"
    DEBUG: bool = True
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 1912

    # --- Providers ---
    OPENAI_API_KEY: SecretStr | None = None  # Required in production
    GOOGLE_API_KEY: SecretStr | None = None  

    # --- Models ---
    DEFAULT_CHAT_MODEL_ID: ChatModel = "gpt-5-nano"
    THINKING_CHAT_MODEL_ID: ChatModel = "gemini-2.5-flash"  # Model worked well with BuiltInPlanner
    GENERAL_CHAT_MODEL_ID: ChatModel = "gemini-2.0-flash"  # Model for general task
    DEFAULT_EMBED_MODEL_ID: EmbedModel = "text-embedding-3-small"
    
    # --- Infra ---
    DATABASE_URL: str = "postgresql+psycopg://rag:ragpass@localhost:5432/ragdb"
    REDIS_URL: str = "redis://localhost:6379/0"
    MONGO_URI_LEARNING: str = os.getenv("MONGO_URI_LEARNING") # mongoDB config for learning agent to store learning data
    # --- Vector Store Configuration ---
    # Individual vector config fields from .env
    PGVECTOR_DIM: int = 1536
    VECTOR_DISTANCE: Dist = "cosine"
    HNSW_M: int = 16
    HNSW_EF_CONSTRUCTION: int = 64
    HNSW_EF_SEARCH: int = 64
    IVF_LISTS: int = 1000
    IVF_PROBES: int = 10

    # --- Monitoring ---
    LANGFUSE_PUBLIC_KEY: SecretStr | None = None
    LANGFUSE_SECRET_KEY: SecretStr | None = None
    LANGFUSE_BASE_URL: str | None = None
    DEEPEVAL_API_KEY: SecretStr | None = None  # Optional evaluation API key

    # --- Misc ---
    ALLOWED_ORIGINS: list[str] = []

    @property
    def VECTOR_CONFIG(self) -> VectorConfig:
        """Build VectorConfig from individual settings."""
        return VectorConfig(
            dim=self.PGVECTOR_DIM,
            distance=self.VECTOR_DISTANCE,
            hsnw_m=self.HNSW_M,
            hsnw_ef_construction=self.HNSW_EF_CONSTRUCTION,
            hsnw_ef_search=self.HNSW_EF_SEARCH,
            ivf_lists=self.IVF_LISTS,
            ivf_probes=self.IVF_PROBES,
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v: Any) -> list[str]:
        return _as_list(v)

    @field_validator("OPENAI_API_KEY", "GOOGLE_API_KEY", mode="before")
    @classmethod
    def _validate_api_key(cls, v: Any, info: ValidationInfo) -> SecretStr | None:
        """
        Xác thực API key: loại bỏ khoảng trắng và yêu cầu key
        trong môi trường production.
        """
        # Lấy tên của trường đang được xác thực (ví dụ: 'OPENAI_API_KEY')
        current_field_name = info.field_name.upper()

        if not v or str(v).strip() == "":
            app_env = info.data.get("APP_ENV", "dev")
            if app_env == "prod":
                # Tạo thông báo lỗi động, chính xác cho từng trường
                raise ValueError(f"{current_field_name} is required in production")
            return None
            
        return SecretStr(str(v).strip())


    @field_validator("PGVECTOR_DIM", mode="after")
    @classmethod
    def _validate_vector_dim(cls, v: int, info: ValidationInfo) -> int:
        """Ensure vector dimension matches the embedding model."""
        embed_model = info.data.get("DEFAULT_EMBED_MODEL_ID", "text-embedding-3-small")
        expected_dim = EMBED_MODEL_DIMS.get(embed_model)
        if expected_dim is not None and v != expected_dim:
            return expected_dim
        return v

    @field_validator("DEBUG", mode="after")
    @classmethod
    def _set_debug(cls, v: bool, info: ValidationInfo) -> bool:
        """Set DEBUG based on APP_ENV if not explicitly set."""
        if "DEBUG" not in info.data:
            app_env: str = info.data.get("APP_ENV", "dev")
            return bool(app_env != "prod")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached settings instance."""
    return Settings()


settings = get_settings()
