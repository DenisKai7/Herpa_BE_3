from functools import lru_cache
from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "Herpa Agentic GraphRAG Backend"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_origins: str = "http://localhost:3000"
    allow_mock_services: bool = False

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwks_url: str = ""
    supabase_jwt_audience: str = "authenticated"

    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    neo4j_query_timeout_seconds: float = 15
    neo4j_max_retry_attempts: int = 2
    neo4j_retry_base_delay_ms: int = 200
    neo4j_max_transaction_retry_time_seconds: float = 8
    neo4j_connection_timeout_seconds: float = 8
    neo4j_max_connection_lifetime_seconds: float = 240
    neo4j_max_connection_pool_size: int = 20
    neo4j_connection_acquisition_timeout_seconds: float = 10

    minio_endpoint: str = "127.0.0.1:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_profile_bucket: str = "profile-images"
    minio_attachment_bucket: str = "chat-attachments"
    minio_export_bucket: str = "generated-exports"
    minio_temp_bucket: str = "processing-temp"

    llama_text_base_url: str = "http://127.0.0.1:8080/v1"
    llama_text_model_name: str = "Qwen3-4B-Instruct-2507"
    text_model_timeout_seconds: float = 180
    text_model_context_size: int = 4096
    text_model_context_safety_margin: int = 512
    text_model_auto_discover: bool = True
    text_model_metadata_cache_seconds: int = 600
    text_model_circuit_failure_threshold: int = 3
    text_model_circuit_reset_seconds: float = 20

    fast_medium_temperature: float = 0.15
    fast_medium_top_p: float = 0.80
    fast_medium_top_k: int = 20
    fast_medium_min_p: float = 0.05
    fast_medium_repeat_penalty: float = 1.05
    fast_medium_max_tokens_umum: int = 180
    fast_medium_max_tokens_pelajar: int = 260
    fast_medium_max_tokens_peneliti: int = 360
    fast_medium_max_tokens_tenaga_medis: int = 340
    fast_medium_compound_list_max_tokens_umum: int = 160
    fast_medium_compound_list_max_tokens_pelajar: int = 220
    fast_medium_compound_list_max_tokens_peneliti: int = 300
    fast_medium_compound_list_max_tokens_tenaga_medis: int = 260
    fast_medium_simple_max_tokens_umum: int = 180
    fast_medium_simple_max_tokens_pelajar: int = 260
    fast_medium_simple_max_tokens_peneliti: int = 360
    fast_medium_simple_max_tokens_tenaga_medis: int = 320
    fast_medium_retrieval_limit: int = 1
    fast_medium_compound_limit: int = 10
    fast_medium_use_limit: int = 5
    fast_medium_target_limit: int = 0
    fast_medium_source_limit: int = 2
    fast_medium_max_history_messages: int = 2
    fast_medium_max_context_tokens: int = 1800
    fast_medium_graph_cache_ttl_seconds: int = 300
    fast_medium_herb_cache_ttl_seconds: int = 600

    thinking_high_temperature: float = 0.20
    thinking_high_top_p: float = 0.88
    thinking_high_top_k: int = 30
    thinking_high_min_p: float = 0.02
    thinking_high_repeat_penalty: float = 1.07
    thinking_high_max_tokens_umum: int = 360
    thinking_high_max_tokens_pelajar: int = 520
    thinking_high_max_tokens_peneliti: int = 750
    thinking_high_max_tokens_tenaga_medis: int = 680
    thinking_high_compound_list_max_tokens_umum: int = 320
    thinking_high_compound_list_max_tokens_pelajar: int = 420
    thinking_high_compound_list_max_tokens_peneliti: int = 600
    thinking_high_compound_list_max_tokens_tenaga_medis: int = 500
    thinking_high_complex_max_tokens_umum: int = 500
    thinking_high_complex_max_tokens_pelajar: int = 650
    thinking_high_complex_max_tokens_peneliti: int = 850
    thinking_high_complex_max_tokens_tenaga_medis: int = 750
    thinking_high_refinement_max_tokens: int = 350
    thinking_high_retrieval_limit: int = 2
    thinking_high_compound_limit: int = 20
    thinking_high_use_limit: int = 12
    thinking_high_target_limit: int = 8
    thinking_high_source_limit: int = 6
    thinking_high_max_history_messages: int = 6
    thinking_high_max_context_tokens: int = 2800
    thinking_high_graph_cache_ttl_seconds: int = 180
    thinking_high_herb_cache_ttl_seconds: int = 300
    llama_vision_base_url: str = "http://llama-vlm:8080/v1"
    llama_vision_model_name: str = "Qwen3-VL-4B-Instruct"
    vision_model_timeout_seconds: float = 240

    ai_runtime_mode: Literal["text", "dual"] = "dual"
    enable_vision: bool = False
    enable_pubmed: bool = True
    enable_pubchem: bool = True
    max_agent_steps: int = 12
    max_tool_calls: int = 6
    max_retrieval_items: int = 20
    max_graph_depth: int = 3

    ncbi_api_key: str = ""
    ncbi_tool_email: str = ""
    ncbi_tool_name: str = "herpa-agentic-ai"

    max_upload_size_mb: int = 25
    max_pdf_pages: int = 50
    max_image_dimension: int = 4096
    max_document_characters: int = 200_000
    presigned_url_expiry_seconds: int = 900
    rate_limit_chat_per_minute: int = 10
    rate_limit_upload_per_minute: int = 5
    share_token_expiry_days: int = 30
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_required_services(self) -> "Settings":
        if self.app_env == "test" or self.allow_mock_services:
            return self
        missing: list[str] = []
        groups = {
            "Supabase": [self.supabase_url, self.supabase_service_role_key],
            "Neo4j": [self.neo4j_uri, self.neo4j_username, self.neo4j_password],
            "MinIO": [self.minio_endpoint, self.minio_access_key, self.minio_secret_key],
        }
        for name, values in groups.items():
            if any(not value or value.startswith("<") for value in values):
                missing.append(name)
        if missing:
            raise ValueError(
                "Konfigurasi wajib belum lengkap: "
                + ", ".join(missing)
                + ". Isi .env atau aktifkan ALLOW_MOCK_SERVICES=true untuk pengembangan."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
