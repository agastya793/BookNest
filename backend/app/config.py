import json
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/booknest"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # JWT Token Configuration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: str = '["http://localhost:5173"]'
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return json.loads(self.CORS_ORIGINS)
    
    # Cookie Security Configuration (False for local HTTP, True for production HTTPS)
    COOKIE_SECURE: bool = False

    # Password Rules (documented for the assessment)
    # - Minimum 8 characters
    # - Maximum 72 bytes (bcrypt truncation safety limit)
    # - At least 1 uppercase letter
    # - At least 1 lowercase letter
    # - At least 1 digit
    # - At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_BYTES: int = 72

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
