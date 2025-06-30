# migrations/env.py

# migrations/env.py
import os
import sys
from pathlib import Path

# migrations 디렉터리의 부모 디렉터리(프로젝트 루트)를 sys.path에 추가
sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
from logging.config import fileConfig
from alembic import context  # flake8: noqa
from sqlalchemy import pool  # flake8: noqa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine  # flake8: noqa
from sqlmodel import SQLModel  # flake8: noqa

#  애플리케이션의 핵심 설정을 임포트합니다.
from app.core.config import settings  # flake8: noqa

#  모든 SQLModel 모델을 임포트하여 Alembic의 metadata에 등록되도록 합니다.
#  이 부분이 매우 중요합니다. 모든 SQLModel 클래스가 SQLModel.metadata에 등록되도록
#  명시적으로 임포트해야 합니다.
#  flake8: noqa
import app.domains.fms.models
import app.domains.inv.models
import app.domains.lims.models
import app.domains.loc.models
import app.domains.ops.models
import app.domains.shared.models
import app.domains.usr.models
import app.domains.ven.models


#  프로젝트 루트 디렉토리(backend)를 Python 경로에 추가합니다.
#  이렇게 하면 env.py가 어디에서 실행되든 'app' 모듈을 찾을 수 있습니다.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

#  Alembic Config 객체이며, .ini 파일의 값들에 접근할 수 있습니다.
config = context.config

#  .ini 파일에 설정된 로깅 설정을 해석합니다.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

#  target_metadata는 autogenerate 지원을 위해 필요합니다.
target_metadata = SQLModel.metadata

# alembic.ini에 sqlalchemy.url이 설정되지 않았다면, settings에서 값을 가져와 설정합니다.
if config.get_main_option("sqlalchemy.url") is None:
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.get_secret_value())


def include_object(object, name, type_, reflected, compare_to):
    """
    autogenerate가 'alembic_version' 테이블을 무시하도록 설정합니다.
    """
    if type_ == "table" and name == "alembic_version":
        return False
    return True


def run_migrations_offline() -> None:
    """'오프라인' 모드에서 마이그레이션을 실행합니다.

    이 시나리오에서는 데이터베이스 연결 없이 마이그레이션 스크립트를 생성합니다.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,  # 여러 스키마 포함 설정
        version_table_schema='public',  # Alembic 버전 테이블 스키마
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """
    실제 마이그레이션을 실행하는 동기 로직입니다.
    Alembic 컨텍스트를 데이터베이스 연결로 구성하고 마이그레이션을 실행합니다.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,  # 여러 스키마 포함 설정
        version_table_schema='public',  # Alembic 버전 테이블 스키마
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """'온라인' 모드에서 마이그레이션을 실행합니다.

    이 시나리오에서는 실제 데이터베이스에 연결하여 마이그레이션을 실행합니다.
    """
    connectable: AsyncEngine = create_async_engine(
        settings.DATABASE_URL.get_secret_value(),  # SecretStr 값에 접근
        echo=settings.DEBUG_MODE,  # 디버그 모드 설정에 따라 SQL 쿼리 출력
        future=True,
        poolclass=pool.NullPool,  # 마이그레이션 시에는 풀을 사용하지 않아 즉시 연결/해제
    )

    #  AsyncEngine으로 생성된 비동기 connection 객체의 run_sync 메서드를 사용합니다.
    #  이 메서드는 비동기 연결 위에서 동기 함수(do_run_migrations)를 안전하게 실행합니다.
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    #  작업이 끝나면 엔진의 리소스를 정리합니다.
    await connectable.dispose()


def run_async_migrations():
    """
    실행 중인 이벤트 루프를 확인하고, 없으면 새로 만들어 비동기 마이그레이션을 실행합니다.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = None

    if loop and loop.is_running():
        task = loop.create_task(run_migrations_online())
    else:
        asyncio.run(run_migrations_online())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_async_migrations()
