import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    FRONTEND_URL: str
    KIS_BASE_URL: str
    KIS_WS_URL: str
    TWLEVEDATA_BASE_URL: str
    KAKAO_REDIRECT_URI: str
    GOOGLE_REDIRECT_URI: str

    KIS_APP_KEY: str
    KIS_SECRET_KEY: str

    TWLEVEDATA_API_KEY: str

    KAKAO_CLIENT_ID: str
    KAKAO_CLIENT_SECRET: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()