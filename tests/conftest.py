# tests/conftest.py

import sys
import os
from typing import AsyncGenerator, Callable, Awaitable  # , Any, Generator
from contextlib import asynccontextmanager
# from datetime import date, datetime, timedelta, UTC, time

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from sqlmodel import SQLModel  # , Session

# pgsql_scripts 패키지에서 __init__.py를 통해
# sqlmodel에서 관리하고 있는 않는 DB 객체(views, function, trigger) import
from pgsql_scripts import all_db_objects

# app.main을 임포트하여 FastAPI 앱 인스턴스에 접근합니다.
from app.main import app as main_app
from app.core import dependencies as deps
# app.core.database에서 get_session 임포트
from app.core.database import get_session
# app.core.security에서 get_password_hash 임포트
from app.core.security import get_password_hash

# --- 모든 모델 임포트 ---
#  설명: SQLModel.metadata.create_all()이 모든 테이블을 인식하려면,
#  아래처럼 모든 모델 클래스가 한 번 이상 임포트되어야 합니다.
#  app/domains/models/__init__.py에서 모든 모델 클래스 임포트
# from app.domains.models import *    # noqa: F401, F403 (와일드카드 임포트는 LIMS 모델이 많아 편의상 사용)
from app.domains.fms import models  # noqa: F401


# --- 사용자 모델 임포트 ---
from app.domains.usr import models as usr_models
from app.domains.loc import models as loc_models
from app.domains.inv import models as inv_models
from app.domains.fms import models as fms_models


# --- 경로 설정 (기존 유지) ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# --- 테스트용 데이터베이스 설정 ---
# 실제 운영 DB와 분리된 테스트 전용 DB URL을 사용합니다.
TEST_DATABASE_URL = "postgresql+asyncpg://wims:wims1234@localhost:5432/test_wims_dbv1"
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,             # 테스트 시 SQL 쿼리 출력하지 않음
    future=True,
    poolclass=NullPool,     # 각 연결이 독립적으로 사용되고 바로 닫히도록 함
)

# 테스트용 세션 팩토리 생성 (AsyncSession)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

SCHEMA = ["shared", "usr", "loc", "ven", "fms", "inv", "lims", "ops", "corp", "rpt"]


# --- 데이터베이스 픽스처 ---
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """
    [통합 Fixture] 테스트 세션 시작 시 다음 순서로 DB를 완벽하게 설정합니다.
    1. 모든 테이블 삭제
    2. 모든 스키마 생성
    3. 모든 테이블 생성
    4. 공유 DB 객체(함수, 트리거 등) 적용
    """
    print("\nDEBUG: Setting up database for session...")

    # 트랜잭션을 사용하여 전체 DB 설정을 하나의 작업 단위로 묶습니다.
    async with test_engine.begin() as conn:
        # --- 1. 테이블 전체 삭제 ---
        # DROP SCHEMA ... CASCADE는 의존성에 상관없이 모든 것을 삭제
        print("--- Dropping all tables... ---")
        for schema_name in SCHEMA:
            # 존재하지 않는 스키마를 삭제하려 할 때 오류가 나지 않도록 IF EXISTS 사용
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))

        # --- 2. 스키마 생성 ---
        print("--- Creating schemas... ---")
        for schema_name in SCHEMA:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

        # --- 3. 테이블 전체 생성 ---
        print("--- Creating all tables... ---")
        await conn.run_sync(SQLModel.metadata.create_all)

        # --- 4. 공유 DB 객체(함수, 트리거 등) 적용 ---
        print("--- Applying shared DB objects (Functions, Triggers, etc.)... ---")
        for db_object in all_db_objects:
            sql_statement_generator = db_object.to_sql_statement_create_or_replace()
            for statement in sql_statement_generator:
                await conn.execute(statement)  # 여기도 conn을 사용

    print("--- Database setup complete. Running tests... ---")

    # 모든 준비가 끝난 후, 테스트를 실행합니다.
    yield

    # --- 테스트 세션 종료 후 정리 ---
    print("\n--- Tearing down database for session... ---")
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    각 테스트 함수마다 트랜잭션을 시작하고, 테스트 완료 후 롤백하여
    테스트 간의 격리를 보장하는 비동기 데이터베이스 세션을 제공합니다.
    """
    # 권장되는 비동기 트랜잭션 관리 패턴을 사용합니다.
    async with test_engine.begin() as connection:  # connection 내에서 트랜잭션 시작
        async with TestingSessionLocal(bind=connection) as session:  # 세션 생성 및 바인딩
            yield session
            # `async with` 블록을 벗어날 때 SQLAlchemy가 자동으로 트랜잭션을 관리합니다.
            # 테스트가 실패하면 pytest_asyncio가 예외를 전파하고,
            # connection.begin() 컨텍스트가 해당 트랜잭션을 롤백합니다.
            # 명시적인 rollback 호출은 필요하지 않거나,
            # connection.rollback()은 트랜잭션이 이미 종료된 경우 경고를 발생시킬 수 있습니다.
            # 테스트 격리를 위해 yield 이후 connection을 롤백하는 것이 일반적입니다.
            await connection.rollback()  # 트랜잭션을 명시적으로 롤백하여 테스트 격리 보장

    # connection = await test_engine.connect()
    # transaction = await connection.begin()
    # session = TestingSessionLocal(bind=connection)

    # try:
    #     yield session
    # finally:
    #     await session.close()
    #     await transaction.rollback()
    #     await connection.close()


@pytest_asyncio.fixture(scope="session")
def get_password_hash_fixture():
    """
    비밀번호 해싱 함수를 픽스처로 제공합니다.
    """
    return get_password_hash


# --- 역할별 사용자 픽스처 (팩토리 사용으로 간결화) ---
# 역할: 데이터베이스(test_wims_dbv1)의 user 테이블에 테스트용 사용자 레코드 하나를 생성하고, 그 User 모델 객체를 반환합니다.
# 기능:
#   user_factory를 호출하여 사용자 이름, 해시된 비밀번호, 역할 등을 가진 사용자 데이터를 만듭니다.
#   생성된 사용자를 DB에 저장(commit)합니다.
# 목적:
#   다른 데이터를 생성할 때 외래 키(Foreign Key) 값으로 사용하기 위해 (예: requester_login_id=test_user.id).
#   API 호출 후, 응답 값과 DB에 저장된 사용자의 정보(이메일, 역할 등)를 직접 비교할 때.
#   사용자 정보 수정 같은 CRUD 로직을 테스트할 때.
# --- 부서 픽스처 추가 ---
@pytest_asyncio.fixture(scope="function")
async def test_department_a(db_session: AsyncSession) -> usr_models.Department:
    """테스트용 부서A를 데이터베이스에 생성하고 반환합니다."""
    department = usr_models.Department(code="DEP0", name="테스트 부서A")
    db_session.add(department)
    await db_session.commit()
    await db_session.refresh(department)
    return department


@pytest_asyncio.fixture(scope="function")
async def test_department_b(db_session: AsyncSession) -> usr_models.Department:
    """테스트용 부서B를 데이터베이스에 생성하고 반환합니다."""
    department = usr_models.Department(code="DEP1", name="테스트 부서B")
    db_session.add(department)
    await db_session.commit()
    await db_session.refresh(department)
    return department


@pytest_asyncio.fixture(scope="function")
def user_factory(db_session: AsyncSession) -> Callable[..., Awaitable[usr_models.User]]:
    """
    [수정] 역할과 속성을 지정하여 테스트 사용자를 생성하는 팩토리 함수를 반환합니다.
    **kwargs를 User 모델 생성자에 전달하도록 수정되었습니다.
    """
    async def _create_user(
        login_id: str,
        password: str,
        role: usr_models.UserRole,
        department_id: int,
        is_active: bool = True,
        **kwargs,
    ) -> usr_models.User:
        user_data = {
            "login_id": login_id,
            "password_hash": get_password_hash(password),
            "email": f"{login_id}@example.com",
            "role": role,
            "department_id": department_id,
            "is_active": is_active,
            **kwargs,  # name, notes 등 추가 인자를 여기서 전달합니다.
        }
        user = usr_models.User(**user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    return _create_user


@pytest_asyncio.fixture(scope="function")
async def test_admin_user(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """관리자(ADMIN) 사용자를 생성합니다."""
    return await user_factory(
        "sysadm", "sysadmpass123",
        role=usr_models.UserRole.ADMIN,
        department_id=test_department_a.id,  # [수정] 부서 ID 전달
        notes="Admin Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_lab_manager(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """실험실 관리자(LAB_MANAGER)를 생성합니다."""
    return await user_factory(
        "labmgr", "labmgrpass123",
        role=usr_models.UserRole.LAB_MANAGER,
        department_id=test_department_a.id,
        notes="Lab manager Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_lab_analyst(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """실험실 분석자(LAB_ANALYST)를 생성합니다."""
    return await user_factory(
        "labanalyst", "labanalystpass123",
        role=usr_models.UserRole.LAB_ANALYST,
        department_id=test_department_a.id,
        notes="Lab analyst Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_facility_manager(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """설비 관리자(FACILITY_MANAGER)를 생성합니다."""
    return await user_factory(
        "fmsmgr", "fmspass123",
        role=usr_models.UserRole.FACILITY_MANAGER,
        department_id=test_department_a.id,
        notes="Facility manager Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_inventory_manager(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """자재 관리자(INVENTORY_MANAGER)를 생성합니다."""
    return await user_factory(
        "invmgr", "invpass123",
        role=usr_models.UserRole.INVENTORY_MANAGER,
        department_id=test_department_a.id,
        notes="Inventory manager Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_user(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """일반 사용자(GENERAL_USER)를 생성합니다."""
    return await user_factory(
        "testuser", "testpass123",
        role=usr_models.UserRole.GENERAL_USER,
        department_id=test_department_a.id,
        notes="General Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_dep_a_user_a(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """일반 사용자(GENERAL_USER)를 생성합니다."""
    return await user_factory(
        "testuser_a", "testpass123",
        role=usr_models.UserRole.GENERAL_USER,
        department_id=test_department_a.id,
        notes="General Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_dep_a_user_b(user_factory: Callable, test_department_a: usr_models.Department) -> usr_models.User:
    """일반 사용자(GENERAL_USER)를 생성합니다."""
    return await user_factory(
        "testuser_b", "testpass123",
        role=usr_models.UserRole.GENERAL_USER,
        department_id=test_department_a.id,
        notes="General Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_dep_b_user_c(user_factory: Callable, test_department_b: usr_models.Department) -> usr_models.User:
    """일반 사용자(GENERAL_USER)를 생성합니다."""
    return await user_factory(
        "testuser_c", "testpass123",
        role=usr_models.UserRole.GENERAL_USER,
        department_id=test_department_b.id,
        notes="General Test User"
    )


@pytest_asyncio.fixture(scope="function")
async def test_dep_b_user_d(user_factory: Callable, test_department_b: usr_models.Department) -> usr_models.User:
    """일반 사용자(GENERAL_USER)를 생성합니다."""
    return await user_factory(
        "testuser_d", "testpass123",
        role=usr_models.UserRole.GENERAL_USER,
        department_id=test_department_b.id,
        notes="General Test User"
    )


# --- 역할별 인증 클라이언트 픽스처 (팩토리 사용으로 간결화) ---
# 역할: test_user를 이용해 미리 로그인 과정을 마친 AsyncClient 객체를 반환합니다.
# 기능:
#   내부적으로 test_user 픽스처를 먼저 호출하여 사용자 데이터를 준비합니다.
#   authorized_client_factory를 통해 /api/v1/usr/auth/token 로그인 API를 실제로 호출합니다.
#   로그인 성공 후 받은 access_token을 Authorization 헤더에 자동으로 포함시킵니다.
# 목적:
#   @login_required처럼 인증이 필요한 API 엔드포인트를 테스트할 때.
#   API를 호출하여 특정 사용자의 권한으로 데이터를 생성, 조회, 수정, 삭제하는 기능을 테스트할 때.
@pytest_asyncio.fixture(scope="function")
def authorized_client_factory(
    db_session: AsyncSession,
) -> Callable[[usr_models.User, str], AsyncGenerator[AsyncClient, None]]:
    """
    특정 사용자로 로그인된 AsyncClient를 생성하는 팩토리 함수를 반환합니다.
    사용자 역할에 따라 의존성 오버라이드를 다르게 적용합니다.
    """
    # async def _create_client_generator(user: usr_models.User, password: str) -> AsyncGenerator[AsyncClient, None]:
    #     def override_get_session():
    #         yield db_session

    #     def override_get_current_user():
    #         return user

    #     # 테스트 시작 전 원래 의존성 상태를 저장
    #     original_overrides = main_app.dependency_overrides.copy()
    #     # 모든 클라이언트에 공통적인 의존성만 먼저 오버라이드합니다.
    #     main_app.dependency_overrides.update({
    #         get_session: override_get_session,
    #         deps.get_db_session: override_get_session,
    #         deps.get_current_active_user: override_get_current_user,
    #     })

    #     # 관리자 역할(ADMIN)일 경우에만 추가로 관리자 의존성을 오버라이드합니다.
    #     # UserRole.ADMIN 값이 1이라고 가정
    #     # if user.role <= usr_models.UserRole.ADMIN:
    #     if user.role == usr_models.UserRole.ADMIN:
    #         main_app.dependency_overrides[deps.get_current_admin_user] = override_get_current_user

    #     transport = ASGITransport(app=main_app)
    #     async with AsyncClient(transport=transport, base_url="http://test") as client:
    #         try:
    #             # API가 form data 대신 JSON을 받도록 변경되었을 수 있습니다.
    #             # OAuth2PasswordRequestForm을 계속 사용한다면 data=,
    #             # Pydantic 모델을 사용한다면 json=을 사용해야 합니다.
    #             # 현재 라우터는 OAuth2PasswordRequestForm을 사용하므로 data=가 맞습니다.
    #             login_data = {"username": user.login_id, "password": password}
    #             res = await client.post("/api/v1/usr/auth/token", data=login_data)

    #             if res.status_code != 200:
    #                 pytest.fail(f"Login failed for {user.login_id}: {res.text}")

    #             token = res.json()["access_token"]
    #             client.headers["Authorization"] = f"Bearer {token}"
    #             yield client
    #         finally:
    #             main_app.dependency_overrides = original_overrides

    # return _create_client_generator
    @asynccontextmanager
    async def _create_client_context(user: usr_models.User, password: str) -> AsyncGenerator[AsyncClient, None]:
        def override_get_session():
            yield db_session

        def override_get_current_user():
            return user

        # 이 블록 내에서만 오버라이드를 적용하기 위해 contextlib.asynccontextmanager를 사용합니다.
        # FastAPI의 app.dependency_overrides는 dict이므로, TestClient를 사용하지 않는 경우
        # 이처럼 수동으로 context manager를 구현해야 합니다.
        original_get_session_dep = main_app.dependency_overrides.get(get_session)
        original_deps_get_db_session = main_app.dependency_overrides.get(deps.get_db_session)
        original_deps_get_current_active_user = main_app.dependency_overrides.get(deps.get_current_active_user)
        original_deps_get_current_admin_user = main_app.dependency_overrides.get(deps.get_current_admin_user)

        try:
            main_app.dependency_overrides[get_session] = override_get_session
            main_app.dependency_overrides[deps.get_db_session] = override_get_session
            main_app.dependency_overrides[deps.get_current_active_user] = override_get_current_user

            # 관리자 역할일 경우에만 get_current_admin_user 오버라이드
            if user.role == usr_models.UserRole.ADMIN:
                main_app.dependency_overrides[deps.get_current_admin_user] = override_get_current_user

            transport = ASGITransport(app=main_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                login_data = {"username": user.login_id, "password": password}
                res = await client.post("/api/v1/usr/auth/token", data=login_data)

                if res.status_code != 200:
                    pytest.fail(f"Login failed for {user.login_id}: {res.text}")

                token = res.json()["access_token"]
                client.headers["Authorization"] = f"Bearer {token}"
                yield client

        finally:
            # 오버라이드된 의존성을 원래대로 복원합니다.
            if original_get_session_dep is not None:
                main_app.dependency_overrides[get_session] = original_get_session_dep
            elif get_session in main_app.dependency_overrides:
                del main_app.dependency_overrides[get_session]

            if original_deps_get_db_session is not None:
                main_app.dependency_overrides[deps.get_db_session] = original_deps_get_db_session
            elif deps.get_db_session in main_app.dependency_overrides:
                del main_app.dependency_overrides[deps.get_db_session]

            if original_deps_get_current_active_user is not None:
                main_app.dependency_overrides[deps.get_current_active_user] = original_deps_get_current_active_user
            elif deps.get_current_active_user in main_app.dependency_overrides:
                del main_app.dependency_overrides[deps.get_current_active_user]

            if original_deps_get_current_admin_user is not None:
                main_app.dependency_overrides[deps.get_current_admin_user] = original_deps_get_current_admin_user
            elif deps.get_current_admin_user in main_app.dependency_overrides:
                del main_app.dependency_overrides[deps.get_current_admin_user]

    return _create_client_context


@pytest_asyncio.fixture(scope="function")
async def admin_client(
    authorized_client_factory: Callable[..., AsyncGenerator[AsyncClient, None]],
    test_admin_user: usr_models.User,
) -> AsyncGenerator[AsyncClient, None]:
    """관리자로 인증된 클라이언트를 반환합니다."""
    async with authorized_client_factory(test_admin_user, "sysadmpass123") as client:
        yield client
# @pytest_asyncio.fixture(scope="function")
# async def admin_client(
#     db_session: AsyncSession,
#     test_admin_user: usr_models.User,
# ) -> AsyncGenerator[AsyncClient, None]:
#     """관리자로 인증된 AsyncClient를 반환합니다."""
#     def override_get_session():
#         yield db_session

#     def override_get_current_user():
#         return test_admin_user

#     original_overrides = main_app.dependency_overrides.copy()  # 원본 오버라이드 저장
#     try:
#         main_app.dependency_overrides.update({
#             get_session: override_get_session,
#             deps.get_db_session: override_get_session,
#             deps.get_current_active_user: override_get_current_user,
#             deps.get_current_admin_user: override_get_current_user,  # 관리자 클라이언트이므로 이 의존성도 오버라이드
#         })

#         transport = ASGITransport(app=main_app)
#         async with AsyncClient(transport=transport, base_url="http://test") as client:
#             login_data = {"username": test_admin_user.login_id, "password": "sysadmpass123"}
#             res = await client.post("/api/v1/usr/auth/token", data=login_data)
#             assert res.status_code == 200, f"Admin login failed: {res.text}"
#             token = res.json()["access_token"]
#             client.headers["Authorization"] = f"Bearer {token}"
#             yield client
#     finally:
#         main_app.dependency_overrides.clear()  # 모든 오버라이드 제거
#         main_app.dependency_overrides.update(original_overrides)  # 원본 오버라이드 복원


@pytest_asyncio.fixture(scope="function")
async def lab_manager_client(
    authorized_client_factory: Callable[..., AsyncGenerator[AsyncClient, None]],
    test_lab_manager: usr_models.User,
) -> AsyncGenerator[AsyncClient, None]:
    """실험실 관리자로 인증된 클라이언트를 반환합니다."""
    async with authorized_client_factory(test_lab_manager, "labmgrpass123") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def lab_analyst_client(
    authorized_client_factory: Callable[..., AsyncGenerator[AsyncClient, None]],
    test_lab_analyst: usr_models.User,
) -> AsyncGenerator[AsyncClient, None]:
    """실험실 분석자로 인증된 클라이언트를 반환합니다."""
    async with authorized_client_factory(test_lab_analyst, "labanalystpass123") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def facility_manager_client(
    authorized_client_factory: Callable[..., AsyncGenerator[AsyncClient, None]],
    test_facility_manager: usr_models.User,
) -> AsyncGenerator[AsyncClient, None]:
    """설비 관리자로 인증된 클라이언트를 반환합니다."""
    async with authorized_client_factory(test_facility_manager, "fmspass123") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def inventory_manager_client(
    authorized_client_factory: Callable[..., AsyncGenerator[AsyncClient, None]],
    test_inventory_manager: usr_models.User,
) -> AsyncGenerator[AsyncClient, None]:
    """자재 관리자로 인증된 클라이언트를 반환합니다."""
    async with authorized_client_factory(test_inventory_manager, "invpass123") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def authorized_client(
    authorized_client_factory: Callable[..., AsyncGenerator[AsyncClient, None]],
    test_user: usr_models.User,
) -> AsyncGenerator[AsyncClient, None]:
    """일반 사용자로 인증된 클라이언트를 반환합니다."""
    # [수정] async for 구문으로 제너레이터에서 클라이언트를 받아옵니다.
    async with authorized_client_factory(test_user, "testpass123") as client:
        yield client
# @pytest_asyncio.fixture(scope="function")
# async def authorized_client(
#     db_session: AsyncSession,
#     test_user: usr_models.User,
# ) -> AsyncGenerator[AsyncClient, None]:
#     """일반 사용자로 인증된 AsyncClient를 반환합니다."""
#     def override_get_session():
#         yield db_session

#     def override_get_current_user():
#         print(f"DEBUG: override_get_current_user returning user: {test_user.login_id}, role: {test_user.role.value}")
#         return test_user

#     original_overrides = main_app.dependency_overrides.copy()  # 원본 오버라이드 저장
#     try:
#         main_app.dependency_overrides.update({
#             get_session: override_get_session,
#             deps.get_db_session: override_get_session,
#             deps.get_current_active_user: override_get_current_user,
#         })
#         # 일반 사용자의 경우 deps.get_current_admin_user는 오버라이드하지 않습니다.
#         # 이렇게 해야 security.py의 원본 get_current_admin_user 함수가 호출되어 권한 검사를 수행합니다.

#         transport = ASGITransport(app=main_app)
#         async with AsyncClient(transport=transport, base_url="http://test") as client:
#             login_data = {"username": test_user.login_id, "password": "testpass123"}
#             res = await client.post("/api/v1/usr/auth/token", data=login_data)
#             assert res.status_code == 200, f"User login failed: {res.text}"
#             token = res.json()["access_token"]
#             client.headers["Authorization"] = f"Bearer {token}"
#             yield client
#     finally:
#         main_app.dependency_overrides.clear()  # 모든 오버라이드 제거
#         main_app.dependency_overrides.update(original_overrides)  # 원본 오버라이드 복원


# --- 비동기 테스트 클라이언트 픽스처 ---
@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    인증되지 않은 사용자를 위한 AsyncClient 인스턴스를 생성하고,
    테스트용 비동기 DB 세션을 주입합니다.
    """

    def override_get_session_and_dependency():
        yield db_session

    original_overrides = main_app.dependency_overrides.copy()

    # # 핵심 변경: get_session과 deps.get_db_session 모두 오버라이드
    # main_app.dependency_overrides[get_session] = override_get_session_and_dependency
    # main_app.dependency_overrides[deps.get_db_session] = override_get_session_and_dependency

    # async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as async_client:
    #     yield async_client

    # async_client.headers.clear()
    # main_app.dependency_overrides.clear()

    try:  # 이 try-finally 블록 추가 확인
        # 핵심 변경: get_session과 deps.get_db_session 모두 오버라이드
        main_app.dependency_overrides[get_session] = override_get_session_and_dependency
        main_app.dependency_overrides[deps.get_db_session] = override_get_session_and_dependency
        # 여기에 deps.get_current_user_from_token, deps.get_current_active_user, deps.get_current_admin_user
        # 와 같은 인증 관련 의존성을 오버라이드하고 있지 않은지 확인해야 합니다.
        # 만약 의도치 않게 오버라이드되어 있다면, 인증되지 않은 클라이언트에도 사용자가 주입될 수 있습니다.

        async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as async_client:
            yield async_client

    finally:  # 이 finally 블록 추가 확인
        # 클라이언트 픽스처가 끝나면 오버라이드를 반드시 복원해야 합니다.
        main_app.dependency_overrides.clear()
        main_app.dependency_overrides.update(original_overrides)


# --- 도메인별 공통 픽스처 추가 ---
@pytest_asyncio.fixture(name="test_facility")
async def test_facility_fixture(db_session: AsyncSession) -> loc_models.Facility:
    """테스트용 하수처리장을 데이터베이스에 생성하고 반환합니다."""
    # code 값을 5자 이하로 변경
    plant = loc_models.Facility(code="TPLNT", name="테스트 처리장")  # 'TESTPLANT' 대신 'TPLNT' 사용
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)
    return plant


@pytest_asyncio.fixture
async def test_material_category(db_session):
    # 'code' 필드에 유효한 값을 할당합니다.
    category = inv_models.MaterialCategory(
        code="TEST-CAT-001",
        name="테스트 자재 카테고리",
        # description="어떤 설명"
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture(name="test_equipment_category")
async def test_equipment_category_fixture(db_session: AsyncSession) -> fms_models.EquipmentCategory:
    """테스트용 설비 카테고리를 데이터베이스에 생성하고 반환합니다."""
    category = fms_models.EquipmentCategory(name="테스트 설비 카테고리")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category
