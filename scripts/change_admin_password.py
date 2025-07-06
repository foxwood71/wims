# change_admin_password.py

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

# SQLModel 및 SQLAlchemy 관련 임포트
from sqlmodel import Session, select, SQLModel, Field, Column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 비밀번호 해싱을 위한 passlib
from passlib.context import CryptContext

# Pydantic 설정 로드를 위한 pydantic_settings
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

# 애플리케이션의 실제 모델을 임포트하여 데이터베이스 스키마와 일치시킵니다.
# 이렇게 하면 updated_at 컬럼 처리 등에서 발생할 수 있는 잠재적 오류를 방지합니다.
# 주의: 이 스크립트를 실행하기 전에 'app' 모듈이 Python 경로에 접근 가능해야 합니다.
# 일반적으로 프로젝트 루트(backend 폴더의 상위)에서 실행해야 합니다.
import app.domains.usr.models as usr_models_module
import app.domains.shared.models  # 필요에 따라 다른 모델들도 임포트하여 metadata에 등록
import app.domains.loc.models
import app.domains.ven.models
import app.domains.fms.models
import app.domains.inv.models
import app.domains.lims.models
import app.domains.ops.models

# 실제 User 모델을 참조
User = usr_models_module.User


# --- 1. 설정 로드 (app/core/config.py와 동일하게 .env 파일 경로 설정) ---
# 스크립트의 BASE_DIR을 프로젝트의 루트 디렉토리로 설정합니다.
# 예를 들어, 스크립트가 'backend' 폴더와 같은 레벨에 있다면, BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 만약 스크립트가 'backend' 폴더 안에 있다면 (예: backend/scripts/change_admin_password.py),
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 와 같이 조정해야 합니다.
# 현재 예시에서는 스크립트가 'backend' 폴더와 같은 레벨에 있다고 가정합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, '.env'),  # .env 파일 경로 지정
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True
    )
    DATABASE_URL: SecretStr = Field(..., description="PostgreSQL database connection URL")  #
    SECRET_KEY: SecretStr = Field("default-secret-key", description="JWT secret key (비밀번호 해싱에는 직접 사용 안됨)")  #
    ALGORITHM: str = Field("HS256", description="JWT algorithm")  #
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="JWT expiration")  #


settings = Settings()

# --- 2. 비밀번호 해싱 설정 (app/core/security.py에서 가져옴) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    주어진 비밀번호를 해싱합니다.
    """
    return pwd_context.hash(password)


# --- 3. 데이터베이스 엔진 및 세션 설정 ---
engine = create_async_engine(
    settings.DATABASE_URL.get_secret_value(),  # DB URL 참조
    echo=False,  # 스크립트 실행 시 SQL 쿼리 출력 여부
    future=True
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- 4. 비밀번호 변경 로직 ---
async def change_admin_password(new_password: str):
    hashed_password = get_password_hash(new_password)
    print(f"DEBUG: New hashed password for 'admin': {hashed_password[:20]}...")

    async with AsyncSessionLocal() as session:
        try:
            # admin 사용자 조회
            user_to_update = await session.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = user_to_update.scalars().one_or_none()

            if admin_user:
                admin_user.password_hash = hashed_password
                # updated_at 필드를 현재 시간(UTC)으로 업데이트합니다.
                # models.py에서 datetime.now(timezone.utc)를 사용하므로 여기도 통일합니다.
                admin_user.updated_at = datetime.now(timezone.utc)

                session.add(admin_user)
                await session.commit()
                await session.refresh(admin_user)
                print(f"SUCCESS: Admin password for '{admin_user.username}' successfully updated.")
            else:
                print("ERROR: Admin user not found in the database. Please ensure 'admin' user exists.")
        except Exception as e:
            await session.rollback()
            print(f"ERROR: Failed to update admin password: {e}")
        finally:
            await engine.dispose()  # 엔진 연결 풀 정리

# --- 5. 스크립트 실행 부분 ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Change the password for the 'admin' user.")
    parser.add_argument("new_password", type=str, help="The new password for the admin user.")
    args = parser.parse_args()

    # 모든 SQLModel 모델이 SQLAlchemy metadata에 등록되도록 애플리케이션 모델 모듈을 임포트합니다.
    # 이렇게 해야 User 모델의 테이블 정의가 올바르게 인식됩니다.
    # 이 스크립트가 실행되기 전에 해당 테이블이 이미 존재한다고 가정합니다.
    # (이미 상단에서 모든 도메인 모델 모듈을 임포트했으므로 여기서는 추가적인 작업이 필요 없습니다.)

    asyncio.run(change_admin_password(args.new_password))
