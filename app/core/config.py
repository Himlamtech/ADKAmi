# app/config.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import (
    AnyUrl,
    Field,
    SecretStr,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# ===== Enums =====
class ChatModelID(str, Enum):
    GPT41NANO = "gpt-4.1-nano"
    GPT5 = "gpt-5"
    GPT5_MINI = "gpt-5-mini"
    GPT5_NANO = "gpt-5-nano"
    GEMINI_FLASH_25 = "gemini-2.5-flash"


class EmbedModelID(str, Enum):
    E3_SMALL = "text-embedding-3-small"
    E3_LARGE = "text-embedding-3-large"


class Distance(str, Enum):
    COSINE = "cosine"
    L2 = "l2"
    IP = "ip"


# ===== Embedding dims (single source of truth) =====
EMBED_MODEL_DIMS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


# ===== Vector config (immutable) =====
@dataclass(frozen=True)
class VectorConfig:
    dim: int
    distance: str = "cosine"
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64
    hnsw_ef_search: int = 64
    ivf_lists: int = 1000
    ivf_probes: int = 10


def _parse_listish(v: str | list[str] | None) -> list[str]:
    """Accept JSON-list or CSV; normalize to list[str]."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(i).strip() for i in v if str(i).strip()]
    s = v.strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        import json

        try:
            arr = json.loads(s)
            return [str(i).strip() for i in arr if str(i).strip()]
        except Exception:
            pass
    return [i.strip() for i in s.split(",") if i.strip()]


# ===== Settings (Pydantic v2) =====
class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "AmiAgent"
    APP_ENV: str = "dev"  # dev|staging|prod
    DEBUG: bool | None = None
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 1912

    # --- Providers ---
    OPENAI_API_KEY: SecretStr | None = None
    GOOGLE_API_KEY: SecretStr | None = None

    # --- Models ---
    DEFAULT_CHAT_MODEL_ID: ChatModelID = ChatModelID.GPT41NANO
    GENERAL_CHAT_MODEL_ID: ChatModelID = ChatModelID.GPT5_MINI
    DEFAULT_EMBED_MODEL_ID: EmbedModelID = EmbedModelID.E3_SMALL

    # --- Vector Store ---
    VECTOR_STORE_DIR: str = "vectorstore"
    VECTOR_STORE_COLLECTION_NAME: str = "ami_collection"
    DEFAULT_DATA_PATH: str = "assets/data/processed/qa.csv"
    # --- Infra (use AnyUrl to accept SQLAlchemy schemes like postgresql+psycopg) ---
    DATABASE_URL: AnyUrl = "postgresql+psycopg://rag:ragpass@localhost:5432/ragdb"
    REDIS_URL: AnyUrl = "redis://localhost:6379/0"

    # --- Vector knobs (override only if needed) ---
    VECTOR_DISTANCE: Distance = Distance.COSINE
    HNSW_M: int = 16
    HNSW_EF_CONSTRUCTION: int = 64
    HNSW_EF_SEARCH: int = 64
    IVF_LISTS: int = 1000
    IVF_PROBES: int = 10

    # --- Monitoring ---
    LANGFUSE_PUBLIC_KEY: SecretStr | None = None
    LANGFUSE_SECRET_KEY: SecretStr | None = None
    LANGFUSE_BASE_URL: str | None = None
    DEEPEVAL_API_KEY: SecretStr | None = None

    # --- Misc ---
    ALLOWED_ORIGINS: list[str] = Field(default_factory=list)

    # --- Model config ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
        # env_prefix="AMI_",  # uncomment nếu muốn prefix env rõ ràng
    )

    # ===== Derived fields =====
    @computed_field  # type: ignore[misc]
    @property
    def VECTOR_DIM(self) -> int:
        return EMBED_MODEL_DIMS[self.DEFAULT_EMBED_MODEL_ID.value]

    @computed_field  # type: ignore[misc]
    @property
    def VECTOR_CONFIG(self) -> VectorConfig:
        return VectorConfig(
            dim=self.VECTOR_DIM,
            distance=self.VECTOR_DISTANCE.value,
            hnsw_m=self.HNSW_M,
            hnsw_ef_construction=self.HNSW_EF_CONSTRUCTION,
            hnsw_ef_search=self.HNSW_EF_SEARCH,
            ivf_lists=self.IVF_LISTS,
            ivf_probes=self.IVF_PROBES,
        )

    # ===== Validators / Normalizers =====
    @model_validator(mode="after")
    def _prod_guardrails(self) -> "Settings":
        # Fail-fast ở production
        if self.APP_ENV == "prod":
            # Provider keys
            if not (
                self.OPENAI_API_KEY and self.OPENAI_API_KEY.get_secret_value().strip()
            ):
                raise ValueError("OPENAI_API_KEY is required in production")
            # CORS phải explicit
            if not self.ALLOWED_ORIGINS or self.ALLOWED_ORIGINS == ["*"]:
                raise ValueError(
                    "In production, ALLOWED_ORIGINS must be explicit (no '*')."
                )
        return self

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v: Any) -> list[str]:
        arr = _parse_listish(v)
        # "*" allowed only outside prod (prod is guarded above)
        return arr

    @field_validator(
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "DEEPEVAL_API_KEY",
        mode="before",
    )
    @classmethod
    def _trim_secret(cls, v: Any) -> SecretStr | None:
        if v is None:
            return None
        s = str(v).strip()
        return SecretStr(s) if s else None

    @field_validator("DEBUG", mode="after")
    @classmethod
    def _default_debug(cls, v: bool | None, info: ValidationInfo) -> bool:
        return (info.data.get("APP_ENV", "dev") != "prod") if v is None else bool(v)


# ===== Accessor (singleton) =====
@lru_cache(maxsize=1)
def get_config() -> Settings:
    return Settings()


# Optional: convenience binding
config = get_config()
