# app/core/config.py

from typing import Any
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# 프로젝트의 루트 디렉토리 경로를 계산합니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    """
    애플리케이션의 모든 설정을 정의하는 Pydantic BaseSettings 모델입니다.
    환경 변수 및 .env 파일에서 값을 자동으로 로드합니다.
    """

    # --- Pydantic Settings 설정 ---
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, '.env'),  # 프로젝트 루트의 .env 파일을 명시적으로 지정
        env_file_encoding='utf-8',           # .env 파일 인코딩
        extra='ignore',                      # .env 파일에 정의되었지만 모델에 없는 변수는 무시
        case_sensitive=True                  # 환경 변수 이름 대소문자 구분
    )

    # --- 애플리케이션 기본 설정 ---
    APP_NAME: str = "WIMS FastAPI API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Wastewater Information Management System (WIMS) API"
    # 애플리케이션 환경 (예: "development", "production", "testing")
    APP_ENV: str = Field("development", description="Application environment (e.g., development, production, testing)")
    # 디버그 모드 활성화 여부
    DEBUG_MODE: bool = Field(False, description="Enable debug mode for detailed logging and error messages")

    # --- 데이터베이스 설정 ---
    DATABASE_URL: SecretStr = Field(..., description="PostgreSQL database connection URL")

    # --- JWT (JSON Web Token) 설정 ---
    SECRET_KEY: SecretStr = Field(..., description="Secret key for JWT token signing. Keep this highly secure!")
    ALGORITHM: str = Field("HS256", description="Algorithm used for JWT signing (e.g., HS256)")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="Access token expiration time in minutes")

    # --- 파일 업로드 설정 ---
    # UPLOAD_DIR: 개발 환경과 프로덕션 환경에 따라 다르게 설정
    UPLOAD_DIR: str = Field(..., description="Directory for uploaded files.")

    # Post-initialization validation (Pydantic v2 BaseSettings)
    def model_post_init(self, __context: Any) -> None:  # noqa: ANN001
        # APP_ENV가 development이고, UPLOAD_DIR이 기본값인 경우 로컬 경로로 변경
        if self.APP_ENV == "development" and self.UPLOAD_DIR == "/app/data/uploads":
            # BASE_DIR을 기준으로 로컬 경로 설정
            self.UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
            # print(f"DEBUG: Development UPLOAD_DIR set to: {self.UPLOAD_DIR}")


settings = Settings()