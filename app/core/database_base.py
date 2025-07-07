# app/core/db_base.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# 애플리케이션 설정을 임포트합니다.
from app.core.config import settings

# SQLModel 엔진을 생성합니다.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL.get_secret_value(),  # SecretStr 값에 접근
    echo=settings.DEBUG_MODE,  # 디버그 모드일 때만 SQL 쿼리 출력
    future=True,
    pool_recycle=3600,  # 1시간마다 연결 재활용 (PostgreSQL 기본 유휴 타임아웃 8시간)
    pool_size=10,  # 최소 10개의 연결 유지
    max_overflow=20  # 최대 20개의 추가 연결 허용 (총 30개)
)

# 비동기 세션을 생성하는 '세션 공장'을 정의합니다.
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
