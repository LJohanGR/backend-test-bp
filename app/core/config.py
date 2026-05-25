from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    MAX_FILE_SIZE_MB: int = 50
    SESSION_TTL_MINUTES: int = 60
    CATALOGOS_PATH: str = "Catalogos"

    model_config = {"env_file": ".env"}


settings = Settings()
