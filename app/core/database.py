# app/core/db.py

"""
애플리케이션의 데이터베이스 연결 및 세션 관리를 담당하는 모듈입니다.

- SQLModel의 비동기 엔진을 설정합니다.
- 비동기 세션 생성을 위한 유틸리티 함수를 제공합니다.
- 애플리케이션 시작 시 데이터베이스 테이블을 생성하는 함수를 포함합니다 (개발용).
"""

from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine  # 비동기 엔진 생성 함수와 타입 임포트
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy import text  # 스키마 생성 시 text 함수 필요

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession  # AsyncSession은 비동기용

# 1. db_base에서 engine과 AsyncSessionLocal을 임포트합니다. (이전 코드는 삭제)
# from app.core.database_base import engine, AsyncSessionLocal

# 애플리케이션 설정을 임포트합니다.
from app.core.config import settings

# =============================================================================
# 모든 도메인 모델 임포트 -> 순환 import 때문에 main.py로 이동
# =============================================================================
# 이 부분이 매우 중요합니다. 모든 SQLModel 클래스가 SQLModel.metadata에 등록되도록
# 명시적으로 임포트해야 합니다. 이렇게 해야 SQLAlchemy 매퍼가 모든 모델과
# 그 관계를 인식하고 'configure_mappers()'가 올바르게 작동할 수 있습니다.
# 이 임포트들은 각 모델 파일 내의 TYPE_CHECKING 블록과는 별개로 런타임에 필요합니다.
from app.domains.corp import models     # noqa
from app.domains.fms import models      # noqa
from app.domains.inv import models      # noqa
from app.domains.lims import models     # noqa
from app.domains.loc import models      # noqa
from app.domains.ops import models      # noqa
from app.domains.rpt import models      # noqa
from app.domains.shared import models   # noqa
from app.domains.usr import models      # noqa
from app.domains.ven import models      # noqa


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

# SQLModel의 기본 MetaData 객체입니다.
# 모든 SQLModel 클래스는 이 MetaData에 자동으로 연결됩니다.
metadata = SQLModel.metadata

# 매퍼 구성 완료 플래그 (중복 호출 방지)
_mappers_configured = False


# =============================================================================
# 데이터베이스 초기화 및 테이블 생성 함수
# =============================================================================
async def create_db_and_tables() -> None:
    """
    데이터베이스 스키마 및 테이블을 생성합니다.
    이 함수는 개발 환경에서만 사용해야 하며, 기존 테이블을 삭제하지는 않습니다.
    """
    global _mappers_configured  # 전역 플래그를 사용합니다.
    print("DEBUG: 데이터베이스 초기화 함수 시작.")

    # 스키마 생성
    print("DEBUG: 데이터베이스 스키마 생성을 시도합니다...")
    async with engine.begin() as conn:
        # 'app' 스키마를 'shared' 스키마로 변경
        schemas_to_create = ['shared', 'usr', 'loc', 'ven', 'fms', 'inv', 'lims', 'ops', 'corp', 'rpt']  # 'app' 대신 'shared'
        for schema_name in schemas_to_create:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            print(f"  DEBUG: 스키마 '{schema_name}' 생성 완료 또는 이미 존재.")

        # SQLAlchemy 매퍼 초기화: 모든 모델 클래스가 로드된 후 호출해야 합니다.
        # 이 호출은 애플리케이션 수명 주기에서 단 한 번만 필요합니다.
        # 하지만 pytest 환경에서는 각 테스트 세션 또는 모듈 로딩 시마다 호출될 수 있습니다.
        if not _mappers_configured:
            print("DEBUG: SQLAlchemy 매퍼 초기화를 시도합니다 (최초 1회)...")
            try:
                configure_mappers()
                _mappers_configured = True
                print("DEBUG: SQLAlchemy 매퍼 초기화 완료.")
            except Exception as e:
                # 매퍼가 이미 초기화되었거나 다른 초기화 오류가 발생할 수 있습니다.
                # 이는 경고로 처리하고 계속 진행합니다.
                print(f"WARNING: SQLAlchemy 매퍼 초기화 중 오류 발생 (무시될 수 있음): {e}")

        # 모든 SQLModel 클래스가 SQLModel.metadata에 등록되어 있어야 합니다.
        print("DEBUG: 데이터베이스 테이블 생성을 시도합니다...")
        await conn.run_sync(SQLModel.metadata.create_all)
    print("DEBUG: 데이터베이스 테이블 생성이 완료되었습니다 (또는 이미 존재).")
    print("DEBUG: 데이터베이스 초기화 함수 종료.")


# =============================================================================
# 비동기 데이터베이스 세션 의존성 주입
# =============================================================================
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성 주입을 위한 비동기 데이터베이스 세션 제너레이터입니다.
    요청마다 새로운 세션을 생성하고, 요청 처리 후 세션을 자동으로 닫습니다.
    """
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    ARQ Task 등 비동기 컨텍스트에서 사용할 수 있는
    독립적인 비동기 DB 세션을 제공하는 컨텍스트 관리자입니다.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
