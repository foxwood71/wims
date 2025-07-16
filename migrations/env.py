# migrations/env.py

import os
import sys
import asyncio
from logging.config import fileConfig

from alembic import context
from alembic_utils.replaceable_entity import register_entities  # noqa: F401, E402

from sqlalchemy import pool, text  # , inspect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel

# --- 1. 프로젝트 루트 경로 설정 ---
# alembic.ini의 python_path 설정이 가장 좋은 방법이지만,
# env.py에 두는 경우를 위해 최종 코드를 유지합니다.
# 이 코드는 env.py가 어디에서 실행되든 'app' 모듈을 찾을 수 있게 합니다.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 2. 애플리케이션의 핵심 설정 및 모든 모델 임포트 ---
# Alembic이 데이터베이스와 모델을 비교할 수 있으려면,
# 모든 SQLModel 클래스가 metadata에 등록되어야 합니다.
from app.core.config import settings        # noqa: F401, E402
from app.core.database import SCHEMA        # noqa: F401, E402

# ⭐️ pgsql_scripts에서 자동으로 탐색된 DB 객체 리스트를 가져옵니다.
from pgsql_scripts import all_db_objects    # noqa: F401, E402

#  모든 SQLModel 모델을 임포트하여 Alembic의 metadata에 등록되도록 합니다.
#  이 부분이 매우 중요합니다. 모든 SQLModel 클래스가 SQLModel.metadata에 등록되도록
#  명시적으로 임포트해야 합니다.
import app.domains.corp.models              # noqa: F401, E402
import app.domains.fms.models               # noqa: F401, E402
import app.domains.inv.models               # noqa: F401, E402
import app.domains.lims.models              # noqa: F401, E402
import app.domains.loc.models               # noqa: F401, E402
import app.domains.ops.models               # noqa: F401, E402
import app.domains.rpt.models               # noqa: F401, E402
import app.domains.shared.models            # noqa: F401, E402
import app.domains.usr.models               # noqa: F401, E402
import app.domains.ven.models               # noqa: F401, E402

# --- 3. Alembic 기본 설정 ---
# Alembic Config 객체이며, alembic.ini 파일의 값들에 접근할 수 있습니다..
config = context.config

#  .ini 파일에 설정된 로깅 설정을 해석합니다.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ⭐️ Alembic-utils에 우리가 정의한 모든 함수/트리거 객체를 등록합니다.
# ⭐️ 1회차 - 코멘트 후 실행 : 테이블 우선생성
# ⭐️ 2회차 이후 - 코멘트 제거 실행
# register_entities(all_db_objects)

# target_metadata는 autogenerate 지원을 위해 SQLModel의 메타데이터를 사용합니다.
# Alembic-utils는 alembic.ini의 'user_module_prefix' 설정을 통해
# 자동으로 함수/트리거/뷰를 인식하므로, 여기서는 별도 등록이 필요 없습니다..
target_metadata = SQLModel.metadata

# alembic.ini에 sqlalchemy.url이 설정되지 않았다면, settings에서 값을 가져와 설정합니다.
if config.get_main_option("sqlalchemy.url") is None:
    db_url = settings.DATABASE_URL.get_secret_value()
    config.set_main_option("sqlalchemy.url", db_url)


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name == "alembic_version":
        return False
    return True


def do_run_migrations(connection) -> None:
    """
    실제 마이그레이션을 실행하는 동기 로직입니다.
    Alembic 컨텍스트를 데이터베이스 연결로 구성하고 마이그레이션을 실행합니다.
    """
    # alembic_version 테이블이 이미 존재할 때만 (즉, 초기화 이후)
    # 함수/트리거를 autogenerate 대상에 포함시킴
    # 데이터베이스 Inspector를 사용하여 alembic_version 테이블 존재 여부 확인
    # inspector = inspect(connection)
    # has_alembic_version_table = inspector.has_table("alembic_version", schema="public")

    # if has_alembic_version_table:
    #     print("--- DB is already initialized. Registering functions/triggers for comparison. ---")
    #     register_entities(all_db_objects)

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,  # 여러 스키마를 사용하는 프로젝트에서는 필수
        version_table_schema='public',  # alembic_version 테이블 위치
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """오프라인 모드는 지원하지 않습니다."""
    raise NotImplementedError("Offline mode is not supported in this configuration.")


async def run_migrations_online() -> None:
    """'온라인' 모드에서 마이그레이션을 실행합니다.

    이 시나리오에서는 실제 데이터베이스에 연결하여 마이그레이션을 실행합니다.
    """
    engine: AsyncEngine = create_async_engine(
        settings.DATABASE_URL.get_secret_value(),  # SecretStr 값에 접근
        echo=settings.DEBUG_MODE,  # 디버그 모드 설정에 따라 SQL 쿼리 출력
        future=True,
        poolclass=pool.NullPool,  # 마이그레이션 시에는 풀을 사용하지 않아 즉시 연결/해제
    )

    #  AsyncEngine으로 생성된 비동기 connection 객체의 run_sync 메서드를 사용합니다.
    #  이 메서드는 비동기 연결 위에서 동기 함수(do_run_migrations)를 안전하게 실행합니다.

    # --- 1단계: 스키마 생성 전용 연결 ---
    # 마이그레이션을 시작하기 전에, 모든 스키마가 존재하는 것을 보장합니다.
    async with engine.connect() as connection:
        print("--- Ensuring all schemas exist before migration... ---")
        # 이 트랜잭션은 스키마 생성만 책임지고 바로 커밋됩니다.
        async with connection.begin():
            for schema_name in SCHEMA:
                await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        print("--- Schema check/creation complete. ---")

    # --- 2단계: Alembic 마이그레이션 전용 연결 ---
    # 이제 스키마가 준비된 상태에서 마이그레이션을 실행합니다.
    async with engine.connect() as connection:
        print("\n--- Running Alembic migrations... ---")
        await connection.run_sync(do_run_migrations)

    # 모든 작업이 끝나면 엔진 리소스를 정리합니다.
    await engine.dispose()
    print("\n--- Alembic migrations finished. ---")

# def run_migrations_offline() -> None:
#     """'오프라인' 모드에서 마이그레이션을 실행합니다.
#     이 시나리오에서는 데이터베이스 연결 없이 마이그레이션 스크립트를 생성합니다.
#     """
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#         include_schemas=True,  # 여러 스키마 포함 설정
#         version_table_schema='public',  # Alembic 버전 테이블 스키마
#         include_object=include_object,
#     )

#     with context.begin_transaction():
#         context.run_migrations()


# def run_async_migrations():
#     """
#     실행 중인 이벤트 루프를 확인하고, 없으면 새로 만들어 비동기 마이그레이션을 실행합니다.
#     """
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:  # 'RuntimeError: There is no current event loop...'
#         loop = None

#     if loop and loop.is_running():
#         task = loop.create_task(run_migrations_online())  # noqa: F841, 비동기 마이그레이션 실행
#     else:
#         asyncio.run(run_migrations_online())


if context.is_offline_mode():
    print("Offline mode is not supported.")
    # run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
