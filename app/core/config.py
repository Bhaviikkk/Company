from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost/legal_ai")
    
    # Redis / Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Storage
    s3_endpoint_url: Optional[str] = os.getenv("S3_ENDPOINT_URL")
    s3_bucket: str = os.getenv("S3_BUCKET", "legal-ai-docs")
    s3_access_key: Optional[str] = os.getenv("S3_ACCESS_KEY")
    s3_secret_key: Optional[str] = os.getenv("S3_SECRET_KEY")
    
    # LLM Configuration
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    data_gov_api_key: Optional[str] = os.getenv("DATA_GOV_API_KEY")
    indian_kanoon_api_token: Optional[str] = os.getenv("INDIAN_KANOON_API_TOKEN")
    
    # App
    debug: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    fastapi_host: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    fastapi_port: int = int(os.getenv("FASTAPI_PORT", "5000"))
    
    # Quality thresholds
    grounding_coverage_threshold: float = 0.95
    citation_resolve_rate_threshold: float = 0.90
    nli_consistency_threshold: float = 0.01
    
    class Config:
        env_file = ".env"

settings = Settings()