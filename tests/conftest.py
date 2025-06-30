# tests/conftest.py

import sys
import os
import pytest
import pytest_asyncio

# import asyncio
from typing import Any, AsyncGenerator  # , Generator

from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from datetime import date, datetime, timedelta, UTC  # , time

# app.main을 임포트하여 FastAPI 앱 인스턴스에 접근합니다.
from app.main import app as main_app

# app.core.database에서 get_session 임포트
from app.core.database import get_session
# app.core.security에서 get_password_hash 임포트
from app.core.security import get_password_hash
# app.core.dependencies에서 get_db_session_dependency, get_current_admin_user 임포트
from app.core.dependencies import get_db_session_dependency, get_current_admin_user, get_current_active_user

# 모든 도메인 모델 임포트 (SQLModel.metadata에 등록되도록)
# usr (User, Department)
from app.domains.usr.models import User as UsrUser, UserRole
from app.domains.usr.models import Department as UsrDepartment

# shared (Image, ImageType, Version, EntityImage)
from app.domains.shared.models import Image as SharedImage
from app.domains.shared.models import ImageType as SharedImageType
from app.domains.shared.models import Version as SharedVersion
from app.domains.shared.models import EntityImage as SharedEntityImage

# loc (facility, Location, LocationType)
from app.domains.loc.models import Facility as Locfacility
from app.domains.loc.models import Location as LocLocation
from app.domains.loc.models import LocationType as LocLocationType

# ven (Vendor, VendorCategory, VendorContact, VendorVendorCategory)
from app.domains.ven.models import Vendor as VenVendor
from app.domains.ven.models import VendorCategory as VenVendorCategory
from app.domains.ven.models import VendorContact as VenVendorContact
from app.domains.ven.models import VendorVendorCategory as VenVendorVendorCategory

# fms (Equipment, EquipmentCategory, EquipmentSpecDefinition, EquipmentHistory, EquipmentSpec) # EquipmentSpec 추가
from app.domains.fms.models import Equipment as FmsEquipment
from app.domains.fms.models import EquipmentCategory as FmsEquipmentCategory
from app.domains.fms.models import EquipmentSpecDefinition as FmsEquipmentSpecDefinition
from app.domains.fms.models import EquipmentHistory as FmsEquipmentHistory
from app.domains.fms.models import EquipmentSpec as FmsEquipmentSpec  # FmsEquipmentSpec 추가

# inv (Material, MaterialCategory, MaterialBatch, MaterialTransaction)
from app.domains.inv.models import Material as InvMaterial
from app.domains.inv.models import MaterialCategory as InvMaterialCategory
from app.domains.inv.models import MaterialBatch as InvMaterialBatch
from app.domains.inv.models import MaterialTransaction as InvMaterialTransaction
from app.domains.inv.models import MaterialSpec as InvMaterialSpec  # InvMaterialSpec 추가
from app.domains.inv.models import MaterialSpecDefinition as InvMaterialSpecDefinition  # InvMaterialSpecDefinition 추가
from app.domains.inv.models import MaterialCategorySpecDefinition as InvMaterialCategorySpecDefinition  # InvMaterialCategorySpecDefinition 추가

# lims (Parameter, Project, SampleContainer, SampleType, SamplingPoint, WeatherCondition, TestRequest, Sample, AliquotSample, Worksheet, WorksheetItem, WorksheetData, AnalysisResult, TestRequestTemplate, PrView, StandardSample, CalibrationRecord, QcSampleResult)
from app.domains.lims.models import Parameter as LimsParameter
from app.domains.lims.models import Project as LimsProject
from app.domains.lims.models import SampleContainer as LimsSampleContainer
from app.domains.lims.models import SampleType as LimsSampleType
from app.domains.lims.models import SamplingPoint as LimsSamplingPoint
from app.domains.lims.models import WeatherCondition as LimsWeatherCondition
from app.domains.lims.models import TestRequest as LimsTestRequest
from app.domains.lims.models import Sample as LimsSample
from app.domains.lims.models import AliquotSample as LimsAliquotSample
from app.domains.lims.models import Worksheet as LimsWorksheet
from app.domains.lims.models import WorksheetItem as LimsWorksheetItem
from app.domains.lims.models import WorksheetData as LimsWorksheetData
from app.domains.lims.models import AnalysisResult as LimsAnalysisResult
from app.domains.lims.models import TestRequestTemplate as LimsTestRequestTemplate
from app.domains.lims.models import PrView as LimsPrView
from app.domains.lims.models import StandardSample as LimsStandardSample
from app.domains.lims.models import CalibrationRecord as LimsCalibrationRecord
from app.domains.lims.models import QcSampleResult as LimsQcSampleResult

# ops (Line, DailyPlantOperation, DailyLineOperation, OpsView)
from app.domains.ops.models import Line as OpsLine
from app.domains.ops.models import DailyPlantOperation as OpsDailyPlantOperation
from app.domains.ops.models import DailyLineOperation as OpsDailyLineOperation
from app.domains.ops.models import OpsView as OpsOpsView


# --- 경로 설정 (기존 유지) ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# --- 테스트용 데이터베이스 설정 ---
# 실제 운영 DB와 분리된 테스트 전용 DB URL을 사용합니다.
TEST_DATABASE_URL = "postgresql+asyncpg://wims:wims1234@localhost:5432/test_wims_dbv1"
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,  # 테스트 시 SQL 쿼리 출력하지 않음
    future=True,
    poolclass=NullPool,  # 각 연결이 독립적으로 사용되고 바로 닫히도록 함
)

# 테스트용 세션 팩토리 생성 (AsyncSession)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- 데이터베이스 픽스처 ---
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """
    테스트 세션 시작 시 모든 테이블을 삭제하고 재생성합니다.
    테스트 종료 시 다시 테이블을 삭제합니다.
    """
    print("\nDEBUG: Setting up database for session...")
    async with test_engine.begin() as conn:
        # 모든 도메인의 스키마 이름을 명시적으로 생성합니다.
        # init.sql의 스키마 생성 순서를 고려하여 일관성을 유지합니다.
        schemas_to_create = ["shared", "usr", "loc", "ven", "fms", "inv", "lims", "ops"]
        for schema_name in schemas_to_create:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            print(f"  DEBUG: 스키마 '{schema_name}' 생성 완료 또는 이미 존재.")

        # 모든 SQLModel.metadata에 등록된 테이블을 drop_all 및 create_all 합니다.
        # 모든 모델 파일이 상단에 임포트되어 있어야 SQLModel.metadata가 모든 테이블을 인식합니다.
        await conn.run_sync(SQLModel.metadata.drop_all)
        print("DEBUG: All tables dropped.")
        await conn.run_sync(SQLModel.metadata.create_all)
        print("DEBUG: All tables created.")
    yield  # 테스트 실행

    print("DEBUG: Tearing down database after session...")
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        print("DEBUG: All tables dropped after session.")


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    각 테스트 함수마다 트랜잭션을 시작하고, 테스트 완료 후 롤백하여
    테스트 간의 격리를 보장하는 비동기 데이터베이스 세션을 제공합니다.
    """
    async with test_engine.begin() as connection:
        async with TestingSessionLocal(bind=connection) as session:
            yield session
            await connection.rollback()


@pytest_asyncio.fixture(scope="session")
def get_password_hash_fixture():
    """
    비밀번호 해싱 함수를 픽스처로 제공합니다.
    """
    return get_password_hash


# --- 비동기 테스트 클라이언트 픽스처 ---
@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    인증되지 않은 사용자를 위한 AsyncClient 인스턴스를 생성하고,
    테스트용 비동기 DB 세션을 주입합니다.
    """

    def override_get_session_and_dependency():
        yield db_session

    # 핵심 변경: get_session과 get_db_session_dependency 모두 오버라이드
    main_app.dependency_overrides[get_session] = override_get_session_and_dependency
    main_app.dependency_overrides[get_db_session_dependency] = override_get_session_and_dependency

    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as async_client:
        yield async_client

    async_client.headers.clear()
    main_app.dependency_overrides.clear()


# --- 인증 관련 사용자 픽스처 ---
@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> UsrUser:
    """일반 테스트 사용자를 데이터베이스에 생성하고 반환합니다."""
    user = UsrUser(
        username="testuser_gen",
        password_hash=get_password_hash("testpassword123"),
        email="test_gen@example.com",
        role=100,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_admin_user(db_session: AsyncSession) -> UsrUser:
    """테스트용 관리자 사용자를 데이터베이스에 생성하고 반환합니다."""
    admin_user = UsrUser(
        username="adminuser_gen",
        password_hash=get_password_hash("adminpassword123"),
        email="admin_gen@example.com",
        full_name="Admin Test User Gen",
        role=10,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user)
    return admin_user


@pytest_asyncio.fixture(scope="function")
async def test_superuser(db_session: AsyncSession) -> UsrUser:
    """테스트용 최고 관리자 사용자를 데이터베이스에 생성하고 반환합니다."""
    superuser = UsrUser(
        username="superuser_gen",
        password_hash=get_password_hash("superuserpassword123"),
        email="super_gen@example.com",
        full_name="Super Test User Gen",
        role=1,
        is_active=True,
    )
    db_session.add(superuser)
    await db_session.commit()
    await db_session.refresh(superuser)
    return superuser


# --- 역할별 테스트 사용자 픽스처 ---

# ... test_user, test_admin_user, test_superuser 픽스처 아래에 추가 ...
@pytest_asyncio.fixture(scope="function")
async def test_facility_manager(db_session: AsyncSession) -> UsrUser:
    """[신규] 테스트용 설비 관리자 사용자를 생성합니다."""
    user = UsrUser(
        username="facility_manager",
        password_hash=get_password_hash("facilitypass"),
        email="facility@example.com",
        role=UserRole.FACILITY_MANAGER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# --- 인증된 클라이언트 픽스처 ---
@pytest_asyncio.fixture(scope="function")
async def authorized_client(db_session: AsyncSession, test_user: UsrUser) -> AsyncGenerator[AsyncClient, Any]:
    """일반 사용자로 인증된 비동기 클라이언트를 반환합니다."""
    def override_get_session():
        yield db_session

    def override_get_current_active_user():
        return test_user

    main_app.dependency_overrides[get_session] = override_get_session
    main_app.dependency_overrides[get_db_session_dependency] = override_get_session
    main_app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as client_instance:
        login_data = {"username": test_user.username, "password": "testpassword123"}
        res = await client_instance.post("/api/v1/usr/auth/token", data=login_data)
        assert res.status_code == 200, f"Login failed for authorized_client: {res.json()}"
        token = res.json()["access_token"]
        client_instance.headers["Authorization"] = f"Bearer {token}"
        yield client_instance
    main_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_client(db_session: AsyncSession, test_admin_user: UsrUser) -> AsyncGenerator[AsyncClient, Any]:
    """관리자로 인증된 비동기 클라이언트를 반환합니다."""
    def override_get_session():
        yield db_session

    def override_get_current_admin_user():
        return test_admin_user

    # [핵심 수정] get_current_active_user도 관리자 유저를 반환하도록 재정의합니다.
    def override_get_current_active_user_for_admin():
        return test_admin_user

    main_app.dependency_overrides[get_session] = override_get_session
    main_app.dependency_overrides[get_db_session_dependency] = override_get_session
    main_app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
    # [핵심 수정] 아래 라인이 반드시 추가되어야 합니다.
    main_app.dependency_overrides[get_current_active_user] = override_get_current_active_user_for_admin

    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as client_instance:
        login_data = {"username": test_admin_user.username, "password": "adminpassword123"}
        res = await client_instance.post("/api/v1/usr/auth/token", data=login_data)
        assert res.status_code == 200
        token = res.json()["access_token"]
        client_instance.headers["Authorization"] = f"Bearer {token}"
        yield client_instance
    main_app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="superuser_client", scope="function")
async def superuser_client_fixture(
    db_session: AsyncSession, test_superuser: UsrUser
) -> AsyncGenerator[AsyncClient, Any]:
    """최고 관리자로 인증된 비동기 클라이언트를 반환합니다."""

    def override_get_session_and_dependency():
        yield db_session

    main_app.dependency_overrides[get_session] = override_get_session_and_dependency
    main_app.dependency_overrides[get_db_session_dependency] = override_get_session_and_dependency

    # get_current_admin_user 픽스처를 재정의 (최고관리자도 admin_user 데코레이터를 통과한다고 가정)
    def override_get_current_admin_user():
        return test_superuser

    main_app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user

    # get_current_active_user 픽스처를 재정의
    def override_get_current_active_user():
        return test_superuser

    main_app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as client_instance:
        login_data = {
            "username": test_superuser.username,
            "password": "superuserpassword123",
        }
        res = await client_instance.post("/api/v1/usr/auth/token", data=login_data)
        assert res.status_code == 200, f"Login failed in superuser_client fixture: {res.json()}"
        token = res.json()["access_token"]
        client_instance.headers["Authorization"] = f"Bearer {token}"
        yield client_instance

    client_instance.headers.clear()
    main_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def facility_manager_client(client: AsyncClient, test_facility_manager: UsrUser) -> AsyncClient:
    """[신규] 설비 관리자로 인증된 클라이언트를 반환합니다."""
    # get_current_active_user 의존성을 재정의하여, API 호출 시 설비 관리자 유저를 반환하도록 설정
    main_app.dependency_overrides[get_current_active_user] = lambda: test_facility_manager

    # 로그인 API를 통해 토큰 획득
    login_data = {"username": test_facility_manager.username, "password": "facilitypass"}
    res = await client.post("/api/v1/usr/auth/token", data=login_data)

    # 로그인이 성공했는지 확인
    if res.status_code != 200:
        # 테스트 실패 시 원인 파악을 돕기 위해 에러 내용 출력
        pytest.fail(f"Login failed for facility_manager_client: {res.text}")

    token = res.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    return client


# --- 부서 픽스처 추가 ---
@pytest_asyncio.fixture(scope="function")
async def test_department(db_session: AsyncSession) -> UsrDepartment:
    """테스트용 부서를 데이터베이스에 생성하고 반환합니다."""
    department = UsrDepartment(code="DEPT", name="테스트 부서")
    db_session.add(department)
    await db_session.commit()
    await db_session.refresh(department)
    return department


@pytest_asyncio.fixture(name="test_parameter")
async def test_parameter_fixture(db_session: AsyncSession, test_instrument: FmsEquipment) -> LimsParameter:
    """테스트에서 사용할 기본 분석 항목(Parameter)을 생성하고 반환합니다."""
    parameter = LimsParameter(
        code="pH",  # 고유한 코드로 설정
        name="수소이온농도",
        sort_order=50,
        instrument_id=test_instrument.id,
        units="-"
    )
    db_session.add(parameter)
    await db_session.commit()
    await db_session.refresh(parameter)
    return parameter


@pytest_asyncio.fixture(name="test_lims_project")
async def test_lims_project_fixture(db_session: AsyncSession) -> LimsProject:
    """테스트용 LIMS 프로젝트를 생성하고 반환합니다."""
    project = LimsProject(
        code="LIMS",
        name="기본 LIMS 프로젝트",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31)
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture(name="test_test_request")
async def test_test_request_fixture(
    db_session: AsyncSession,
    test_lims_project: LimsProject,
    test_department: UsrDepartment,
    test_user: UsrUser,
) -> LimsTestRequest:
    """테스트용 시험 의뢰(TestRequest)를 생성하고 반환합니다."""
    test_req = LimsTestRequest(
        request_date=date.today(),
        project_id=test_lims_project.id,
        department_id=test_department.id,
        requester_user_id=test_user.id,
        title="일반 테스트 의뢰",
        requested_parameters={"pH": True, "BOD": True},
    )
    db_session.add(test_req)
    await db_session.commit()
    await db_session.refresh(test_req)
    return test_req


@pytest_asyncio.fixture(name="test_sampling_point")
async def test_sampling_point_fixture(db_session: AsyncSession, test_facility: Locfacility) -> LimsSamplingPoint:
    """테스트용 채수 지점(SamplingPoint)을 생성하고 반환합니다."""
    point = LimsSamplingPoint(
        code="FINAL-EFF", name="최종방류구", facility_id=test_facility.id
    )
    db_session.add(point)
    await db_session.commit()
    await db_session.refresh(point)
    return point


@pytest_asyncio.fixture(name="test_sample_type")
async def test_sample_type_fixture(db_session: AsyncSession) -> LimsSampleType:
    """테스트용 시료 유형(SampleType)을 생성하고 반환합니다."""
    sample_type = LimsSampleType(code=1, name="일반 시료")
    # 중복을 피하기 위해 이미 존재하는지 확인
    existing = await db_session.get(LimsSampleType, 1)
    if existing:
        return existing
    db_session.add(sample_type)
    await db_session.commit()
    await db_session.refresh(sample_type)
    return sample_type


@pytest_asyncio.fixture(name="test_sample_container")
async def test_sample_container_fixture(db_session: AsyncSession) -> LimsSampleContainer:
    """테스트용 시료 용기(SampleContainer)를 생성하고 반환합니다."""
    container = LimsSampleContainer(code=1, name="1L 채수병")
    # 중복을 피하기 위해 이미 존재하는지 확인
    existing = await db_session.get(LimsSampleContainer, 1)
    if existing:
        return existing
    db_session.add(container)
    await db_session.commit()
    await db_session.refresh(container)
    return container


@pytest_asyncio.fixture(name="test_weather_condition")
async def test_weather_condition_fixture(db_session: AsyncSession) -> LimsWeatherCondition:
    """테스트용 날씨 정보(WeatherCondition)를 생성하고 반환합니다."""
    weather = LimsWeatherCondition(code=1, status="맑음")
    # 중복을 피하기 위해 이미 존재하는지 확인
    existing = await db_session.get(LimsWeatherCondition, 1)
    if existing:
        return existing
    db_session.add(weather)
    await db_session.commit()
    await db_session.refresh(weather)
    return weather


@pytest_asyncio.fixture(name="test_sample")
async def test_sample_fixture(
    db_session: AsyncSession,
    test_test_request: LimsTestRequest,
    test_sampling_point: LimsSamplingPoint,
    test_sample_type: LimsSampleType,
    test_sample_container: LimsSampleContainer,
    test_user: UsrUser,
) -> LimsSample:
    """테스트용 원시료(Sample)를 생성하고 반환합니다."""
    sample = LimsSample(
        request_id=test_test_request.id,
        sampling_point_id=test_sampling_point.id,
        sampling_date=date.today(),
        sample_type_id=test_sample_type.id,
        container_id=test_sample_container.id,
        parameters_for_analysis={"TN": True, "TP": True},
        collector_user_id=test_user.id,
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)
    return sample


# --- LIMS 관련 픽스처 추가 (test_lims.py에서 옮겨옴) ---
@pytest_asyncio.fixture(name="test_sampler_user")
async def test_sampler_user_fixture(db_session: AsyncSession) -> UsrUser:
    user = UsrUser(
        username="sampler",
        password_hash=get_password_hash("samplerpass"),
        email="sampler@example.com",
        role=100,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(name="test_analyst_user")
async def test_analyst_user_fixture(db_session: AsyncSession) -> UsrUser:
    user = UsrUser(
        username="analyst",
        password_hash=get_password_hash("analystpass"),
        email="analyst@example.com",
        role=100,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(name="test_facility")
async def test_facility_fixture(db_session: AsyncSession) -> Locfacility:
    """테스트용 하수처리장을 데이터베이스에 생성하고 반환합니다."""
    # code 값을 5자 이하로 변경
    plant = Locfacility(code="TPLNT", name="테스트 처리장")  # 'TESTPLANT' 대신 'TPLNT' 사용
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)
    return plant


@pytest_asyncio.fixture(name="test_equipment_category")
async def test_equipment_category_fixture(db_session: AsyncSession) -> FmsEquipmentCategory:
    """테스트용 설비 카테고리를 데이터베이스에 생성하고 반환합니다."""
    category = FmsEquipmentCategory(name="테스트 설비 카테고리")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def test_material_category(db_session):
    # 'code' 필드에 유효한 값을 할당합니다.
    category = InvMaterialCategory(
        code="TEST-CAT-001",
        name="테스트 자재 카테고리",
        # description="어떤 설명"
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture(name="test_instrument")
async def test_instrument_fixture(
    db_session: Session, test_facility: Locfacility, test_equipment_category: FmsEquipmentCategory
) -> FmsEquipment:
    instrument = FmsEquipment(
        facility_id=test_facility.id,  # <<< 수정된 부분
        equipment_category_id=test_equipment_category.id,
        name="테스트 분석기기",
        model_number="MODEL-X",
        serial_number="SN-INSTR-001",
    )
    db_session.add(instrument)
    await db_session.commit()
    await db_session.refresh(instrument)
    return instrument


@pytest_asyncio.fixture(name="test_aliquot_sample")
async def test_aliquot_sample_fixture(
    db_session: Session,
    test_lims_project: LimsProject,
    test_department: UsrDepartment,
    test_sampler_user: UsrUser,
    test_sampling_point: LimsSamplingPoint,
    test_sample_container: LimsSampleContainer,
    test_sample_type: LimsSampleType,
    test_instrument: FmsEquipment,
    test_weather_condition: LimsWeatherCondition,  # 추가: TestRequest 생성 시 필요할 수 있음
) -> LimsAliquotSample:
    # TestRequest 생성
    test_req = LimsTestRequest(
        request_date=date.today(),
        project_id=test_lims_project.id,
        department_id=test_department.id,
        requester_user_id=test_sampler_user.id,
        title="Test request for aliquot",
        requested_parameters={},
        sampling_weather_id=test_weather_condition.id,  # 추가: sampling_weather_id 설정
    )
    db_session.add(test_req)
    await db_session.commit()
    await db_session.refresh(test_req)

    # Sample 생성
    test_sample = LimsSample(
        request_id=test_req.id,
        sampling_point_id=test_sampling_point.id,
        sampling_date=date.today(),
        sample_type_id=test_sample_type.id,
        container_id=test_sample_container.id,
        parameters_for_analysis={},
        collector_user_id=test_sampler_user.id,  # 추가: collector_user_id 설정
    )
    db_session.add(test_sample)
    await db_session.commit()
    await db_session.refresh(test_sample)

    # Parameter 생성
    test_param = LimsParameter(
        code="TPAR", name="테스트 파라미터", sort_order=1, instrument_id=test_instrument.id
    )
    db_session.add(test_param)
    await db_session.commit()
    await db_session.refresh(test_param)

    # AliquotSample 생성
    aliquot = LimsAliquotSample(
        parent_sample_id=test_sample.id,
        parameter_id=test_param.id,
        analysis_status="Pending",
        analyst_user_id=test_sampler_user.id,  # 추가: analyst_user_id 설정
    )
    db_session.add(aliquot)
    await db_session.commit()
    await db_session.refresh(aliquot)
    return aliquot


@pytest_asyncio.fixture(name="test_worksheet")
async def test_worksheet_fixture(db_session: Session) -> LimsWorksheet:
    ws = LimsWorksheet(code="WS01", name="일일 수질 분석 워크시트", sort_order=1)
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# 추가 픽스처들 (필요에 따라 더 구체적인 데이터로 채울 수 있음)
@pytest_asyncio.fixture(name="test_worksheet_item")
async def test_worksheet_item_fixture(db_session: Session, test_worksheet: LimsWorksheet) -> LimsWorksheetItem:
    item = LimsWorksheetItem(
        worksheet_id=test_worksheet.id,
        code="ITEM01",
        priority_order=1,
        xls_cell_address="A1",
        name="항목 1",
        label="라벨 1",
        type=1,  # 숫자
        unit="mg/L",
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture(name="test_worksheet_data")
async def test_worksheet_data_fixture(
    db_session: Session, test_worksheet: LimsWorksheet, test_analyst_user: UsrUser
) -> LimsWorksheetData:
    data = LimsWorksheetData(
        worksheet_id=test_worksheet.id,
        data_date=date.today(),
        analyst_user_id=test_analyst_user.id,
        raw_data={"key1": "value1", "key2": 123},
        is_verified=False,
    )
    db_session.add(data)
    await db_session.commit()
    await db_session.refresh(data)
    return data


@pytest_asyncio.fixture(name="test_analysis_result")
async def test_analysis_result_fixture(
    db_session: Session,
    test_aliquot_sample: LimsAliquotSample,
    test_worksheet: LimsWorksheet,
    test_worksheet_data: LimsWorksheetData,
    test_analyst_user: UsrUser,
) -> LimsAnalysisResult:
    result = LimsAnalysisResult(
        aliquot_sample_id=test_aliquot_sample.id,
        parameter_id=test_aliquot_sample.parameter_id,  # test_aliquot_sample.parameter로 접근하는 대신 ID 사용
        worksheet_id=test_worksheet.id,
        worksheet_data_id=test_worksheet_data.id,
        result_value=7.2,
        unit="pH",
        analysis_date=date.today(),
        analyst_user_id=test_analyst_user.id,
        is_approved=False,
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)
    return result


@pytest_asyncio.fixture(name="test_test_request_template")
async def test_test_request_template_fixture(db_session: Session, test_user: UsrUser) -> LimsTestRequestTemplate:
    template = LimsTestRequestTemplate(
        name="General Template",
        user_id=test_user.id,
        serialized_text={"project": "Default", "parameters": ["pH", "DO"]},
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture(name="test_pr_view")
async def test_pr_view_fixture(
    db_session: Session, test_user: UsrUser, test_facility: Locfacility
) -> LimsPrView:
    pr_view = LimsPrView(
        name="My Custom View",
        user_id=test_user.id,
        plant_id=test_facility.id,
        sampling_point_ids=[],  # 더미 ID 대신 빈 리스트 또는 실제 유효한 ID
        parameter_ids=[],  # 더미 ID 대신 빈 리스트 또는 실제 유효한 ID
        memo="Custom view for daily checks",
    )
    db_session.add(pr_view)
    await db_session.commit()
    await db_session.refresh(pr_view)
    return pr_view


@pytest_asyncio.fixture(name="test_standard_sample")
async def test_standard_sample_fixture(db_session: Session, test_instrument: FmsEquipment) -> LimsStandardSample:
    param_for_std = LimsParameter(
        code="STD_PARAM", name="Standard Test Param", sort_order=1, instrument_id=test_instrument.id
    )
    db_session.add(param_for_std)
    await db_session.commit()
    await db_session.refresh(param_for_std)

    std_sample = LimsStandardSample(
        code="REF001",
        name="Reference Sample 1",
        parameter_id=param_for_std.id,
        concentration=10.5,
        preparation_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
    )
    db_session.add(std_sample)
    await db_session.commit()
    await db_session.refresh(std_sample)
    return std_sample


@pytest_asyncio.fixture(name="test_calibration_record")
async def test_calibration_record_fixture(
    db_session: Session,
    test_instrument: FmsEquipment,
    test_user: UsrUser,  # test_analyst_user 대신 test_user 사용
    test_standard_sample: LimsStandardSample,
) -> LimsCalibrationRecord:
    # test_standard_sample이 이미 parameter를 포함하므로 재사용
    param_id = test_standard_sample.parameter_id  # parameter 대신 parameter_id 사용

    cal_record = LimsCalibrationRecord(
        equipment_id=test_instrument.id,
        parameter_id=param_id,
        calibration_date=datetime.now(UTC),
        next_calibration_date=date.today() + timedelta(days=90),
        calibrated_by_user_id=test_user.id,
        standard_sample_id=test_standard_sample.id,
        acceptance_criteria_met=True,
    )
    db_session.add(cal_record)
    await db_session.commit()
    await db_session.refresh(cal_record)
    return cal_record


@pytest_asyncio.fixture(name="test_qc_sample_result")
async def test_qc_sample_result_fixture(
    db_session: Session,
    test_aliquot_sample: LimsAliquotSample,  # AliquotSample은 이미 Parameter를 포함
    test_user: UsrUser,  # test_analyst_user 대신 test_user 사용
) -> LimsQcSampleResult:
    qc_result = LimsQcSampleResult(
        aliquot_sample_id=test_aliquot_sample.id,
        parameter_id=test_aliquot_sample.parameter_id,  # AliquotSample이 가진 파라미터 ID 사용
        qc_type="Blank",
        expected_value=0.0,
        measured_value=0.005,
        recovery=None,
        rpd=None,
        acceptance_criteria={},
        passed_qc=True,
        analysis_date=date.today(),
        analyst_user_id=test_user.id,
    )
    db_session.add(qc_result)
    await db_session.commit()
    await db_session.refresh(qc_result)
    return qc_result
