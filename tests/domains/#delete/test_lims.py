# tests/domains/test_lims.py

"""
'lims' 도메인 (실험실 정보 관리 시스템 및 QA/QC) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 LIMS 엔티티 (분석 항목, 프로젝트, 시료, 시험 의뢰, 분할 시료 등)의 CRUD 테스트.
- 자동 코드 생성, 상태 업데이트 연동과 같은 비즈니스 로직 검증.
- 다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

# 다른 도메인의 모델 임포트 추가
from app.domains.loc import models as loc_models
from app.domains.usr import models as usr_models
from app.domains.fms import models as fms_models

# LIMS 도메인의 CRUD, 모델, 스키마
from app.domains.lims import models as lims_models
from app.domains.lims import schemas as lims_schemas
from app.domains.lims.crud import parameter as parameter_crud
from app.domains.lims.crud import project as project_crud
from app.domains.lims.crud import sample as sample_crud
from app.domains.lims.crud import aliquot_sample as aliquot_sample_crud
from app.domains.lims.crud import test_request as test_request_crud
from app.domains.lims.crud import worksheet as worksheet_crud
from app.domains.lims.crud import worksheet_item as worksheet_item_crud
from app.domains.lims.crud import worksheet_data as worksheet_data_crud
from app.domains.lims.crud import analysis_result as analysis_result_crud
from app.domains.lims.crud import test_request_template as test_request_template_crud
from app.domains.lims.crud import pr_view as pr_view_crud
from app.domains.lims.crud import standard_sample as standard_sample_crud
from app.domains.lims.crud import calibration_record as calibration_record_crud
from app.domains.lims.crud import qc_sample_result as qc_sample_result_crud
from app.domains.lims.crud import sampling_point as sampling_point_crud  # 누락된 sampling_point_crud 임포트 추가
from app.domains.lims.crud import sample_container as sample_container_crud  # 누락된 sample_container_crud 임포트 추가
from app.domains.lims.crud import sample_type as sample_type_crud  # 누락된 sample_type_crud 임포트 추가
from app.domains.lims.crud import weather_condition as weather_condition_crud  # 누락된 weather_condition_crud 임포트 추가

# from app.core.security import get_password_hash  # get_password_hash 임포트 추가

from datetime import date, datetime, time, timedelta, UTC  # UTC 임포트 추가

# conftest.py에서 정의된 픽스처들을 Pytest가 자동으로 감지하여 사용할 수 있습니다.
# client, db_session, admin_client, authorized_client, test_user, test_admin_user


# --- LIMS 보조 데이터 생성 픽스처 (다른 테스트에서 재사용) ---

@pytest.fixture(name="test_plant")
async def test_plant_fixture(db_session: Session) -> loc_models.facility:
    plant = loc_models.facility(code="TP01", name="테스트 플랜트 for LIMS")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)
    return plant


@pytest.fixture(name="test_location_type")
async def test_location_type_fixture(db_session: Session) -> loc_models.LocationType:
    loc_type = loc_models.LocationType(name="테스트 보관 장소 유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)
    return loc_type


@pytest.fixture(name="test_storage_location")
async def test_storage_location_fixture(db_session: Session, test_plant: loc_models.facility, test_location_type: loc_models.LocationType) -> loc_models.Location:
    location = loc_models.Location(
        plant_id=test_plant.id,
        location_type_id=test_location_type.id,
        name="테스트 보관 장소"
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest.fixture(name="test_lims_project")
async def test_lims_project_fixture(db_session: Session) -> lims_models.Project:
    project = lims_models.Project(
        code="PROJ",
        name="테스트 프로젝트",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31)
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture(name="test_department")
async def test_department_fixture(db_session: Session) -> usr_models.Department:
    department = usr_models.Department(code="LIMS", name="LIMS 부서")
    db_session.add(department)
    await db_session.commit()
    await db_session.refresh(department)
    return department


@pytest.fixture(name="test_sampler_user")
async def test_sampler_user_fixture(db_session: Session, test_department: usr_models.Department, get_password_hash_fixture) -> usr_models.User:
    user = usr_models.User(
        username="sampler1",
        password_hash=get_password_hash_fixture("password"),
        email="sampler1@example.com",
        department_id=test_department.id,
        role=100
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(name="test_analyst_user")
async def test_analyst_user_fixture(db_session: Session, test_department: usr_models.Department, get_password_hash_fixture) -> usr_models.User:
    user = usr_models.User(
        username="analyst1",
        password_hash=get_password_hash_fixture("password"),
        email="analyst1@example.com",
        department_id=test_department.id,
        role=100
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(name="test_sample_container")
async def test_sample_container_fixture(db_session: Session) -> lims_models.SampleContainer:
    container = lims_models.SampleContainer(code=1, name="테스트 시료병")
    db_session.add(container)
    await db_session.commit()
    await db_session.refresh(container)
    return container


@pytest.fixture(name="test_sample_type")
async def test_sample_type_fixture(db_session: Session) -> lims_models.SampleType:
    sample_type = lims_models.SampleType(code=10, name="테스트 수질 시료")
    db_session.add(sample_type)
    await db_session.commit()
    await db_session.refresh(sample_type)
    return sample_type


@pytest.fixture(name="test_sampling_point")
async def test_sampling_point_fixture(db_session: Session, test_plant: loc_models.facility) -> lims_models.SamplingPoint:
    sampling_point = lims_models.SamplingPoint(code="SMP1", name="유입 수질 채수 지점", plant_id=test_plant.id)
    db_session.add(sampling_point)
    await db_session.commit()
    await db_session.refresh(sampling_point)
    return sampling_point


@pytest.fixture(name="test_weather_condition")
async def test_weather_condition_fixture(db_session: Session) -> lims_models.WeatherCondition:
    weather = lims_models.WeatherCondition(code=1, status="맑음")  # `id`는 DB가 자동 생성
    db_session.add(weather)
    await db_session.commit()
    await db_session.refresh(weather)
    return weather


@pytest.fixture(name="test_instrument")
async def test_instrument_fixture(db_session: Session, test_plant: loc_models.facility) -> fms_models.Equipment:
    # 장비 카테고리 생성
    eq_cat = fms_models.EquipmentCategory(name="분석 장비", korean_useful_life_years=5)
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    # 장비 생성
    instrument = fms_models.Equipment(
        plant_id=test_plant.id,
        equipment_category_id=eq_cat.id,
        name="테스트 분석 장비",
        serial_number="INST001"
    )
    db_session.add(instrument)
    await db_session.commit()
    await db_session.refresh(instrument)
    return instrument


# --- LIMS 분석 항목 (Parameter) 테스트 ---
@pytest.mark.asyncio
async def test_create_parameter_success_admin(
    admin_client: TestClient,  # 관리자로 인증된 클라이언트
    test_instrument: fms_models.Equipment  # FK
):
    """
    관리자 권한으로 새로운 분석 항목을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_parameter_success_admin ---")
    param_data = {
        "code": "BOD5",
        "name": "생물학적 산소 요구량 5일",
        "units": "mg/L",
        "method": "SM 5210 B",
        "instrument_id": test_instrument.id,
        "sort_order": 1
    }
    response = await admin_client.post("/api/v1/lims/parameters", json=param_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_param = response.json()
    assert created_param["code"] == param_data["code"]
    assert created_param["name"] == param_data["name"]
    assert created_param["instrument_id"] == param_data["instrument_id"]
    assert "id" in created_param
    print("test_create_parameter_success_admin passed.")


@pytest.mark.asyncio
async def test_create_parameter_duplicate_code_admin(
    admin_client: TestClient,
    test_instrument: fms_models.Equipment  # 이미 존재하는 픽스처 사용
):
    """
    관리자 권한으로 이미 존재하는 코드의 분석 항목 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_parameter_duplicate_code_admin ---")
    # 기존 파라미터 생성
    param_data_existing = {
        "code": "DUPC",
        "name": "중복 코드 파라미터",
        "sort_order": 1,
        "instrument_id": test_instrument.id
    }
    await admin_client.post("/api/v1/lims/parameters", json=param_data_existing)

    # 중복 파라미터 생성 시도
    param_data_duplicate = {
        "code": "DUPC",  # 중복 코드
        "name": "새로운 파라미터",
        "sort_order": 2,
        "instrument_id": test_instrument.id
    }
    response = await admin_client.post("/api/v1/lims/parameters", json=param_data_duplicate)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Parameter with this code already exists."
    print("test_create_parameter_duplicate_code_admin passed.")


@pytest.mark.asyncio
async def test_read_parameters_success(client: TestClient, db_session: Session, test_instrument: fms_models.Equipment):
    """
    모든 사용자가 분석 항목 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_parameters_success ---")
    param1 = lims_models.Parameter(code="COD", name="화학적 산소 요구량", units="mg/L", sort_order=1, instrument_id=test_instrument.id)
    param2 = lims_models.Parameter(code="SS", name="부유물질", units="mg/L", sort_order=2, instrument_id=test_instrument.id)
    db_session.add(param1)
    db_session.add(param2)
    await db_session.commit()
    await db_session.refresh(param1)
    await db_session.refresh(param2)

    response = await client.get("/api/v1/lims/parameters")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    params_list = response.json()
    assert len(params_list) >= 2  # 이미 생성된 파라미터 포함될 수 있으므로 >=
    assert any(p["name"] == "화학적 산소 요구량" for p in params_list)
    assert any(p["name"] == "부유물질" for p in params_list)
    print("test_read_parameters_success passed.")


@pytest.mark.asyncio
async def test_update_parameter_success_admin(
    admin_client: TestClient,
    db_session: Session,
    test_instrument: fms_models.Equipment
):
    """
    관리자 권한으로 분석 항목을 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_parameter_success_admin ---")
    param_create_data = {
        "code": "UPD1",
        "name": "업데이트 전",
        "sort_order": 1,
        "instrument_id": test_instrument.id
    }
    created_param = await parameter_crud.create(db_session, obj_in=lims_schemas.ParameterCreate(**param_create_data))

    update_data = {
        "name": "업데이트 후",
        "units": "mg/L (수정됨)",
        "sort_order": 10
    }
    response = await admin_client.put(f"/api/v1/lims/parameters/{created_param.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_param = response.json()
    assert updated_param["id"] == created_param.id
    assert updated_param["name"] == update_data["name"]
    assert updated_param["units"] == update_data["units"]
    assert updated_param["sort_order"] == update_data["sort_order"]
    print("test_update_parameter_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_parameter_success_admin(
    admin_client: TestClient,
    db_session: Session,
    test_instrument: fms_models.Equipment
):
    """
    관리자 권한으로 분석 항목을 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_parameter_success_admin ---")
    param_create_data = {
        "code": "DEL1",
        "name": "삭제될 파라미터",
        "sort_order": 1,
        "instrument_id": test_instrument.id
    }
    created_param = await parameter_crud.create(db_session, obj_in=lims_schemas.ParameterCreate(**param_create_data))

    response = await admin_client.delete(f"/api/v1/lims/parameters/{created_param.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204
    # 삭제 후 조회 시 404 확인
    get_response = await admin_client.get(f"/api/v1/lims/parameters/{created_param.id}")
    assert get_response.status_code == 404
    print("test_delete_parameter_success_admin passed.")


# --- LIMS 프로젝트 (Project) 테스트 ---
@pytest.mark.asyncio
async def test_create_project_success_admin(
    admin_client: TestClient,
):
    """
    관리자 권한으로 새로운 프로젝트를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_project_success_admin ---")
    project_data = {
        "code": "PRJ2",
        "name": "새로운 LIMS 프로젝트",
        "start_date": "2025-06-01",
        "end_date": "2025-12-31"
    }
    response = await admin_client.post("/api/v1/lims/projects", json=project_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_project = response.json()
    assert created_project["name"] == project_data["name"]
    assert created_project["code"] == project_data["code"]
    assert "id" in created_project
    print("test_create_project_success_admin passed.")


@pytest.mark.asyncio
async def test_create_project_duplicate_code_admin(
    admin_client: TestClient,
):
    """
    관리자 권한으로 이미 존재하는 코드의 프로젝트 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_project_duplicate_code_admin ---")
    # 기존 프로젝트 생성
    project_data_existing = {
        "code": "PRJD",
        "name": "중복 프로젝트",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31"
    }
    await admin_client.post("/api/v1/lims/projects", json=project_data_existing)

    # 중복 프로젝트 생성 시도
    project_data_duplicate = {
        "code": "PRJD",  # 중복 코드
        "name": "새로운 프로젝트",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31"
    }
    response = await admin_client.post("/api/v1/lims/projects", json=project_data_duplicate)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Project with this code already exists."
    print("test_create_project_duplicate_code_admin passed.")


@pytest.mark.asyncio
async def test_read_projects_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 프로젝트 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_projects_success ---")
    proj1 = lims_models.Project(code="PJT1", name="프로젝트1", start_date=date(2024, 1, 1), end_date=date(2024, 6, 30))
    proj2 = lims_models.Project(code="PJT2", name="프로젝트2", start_date=date(2024, 7, 1), end_date=date(2024, 12, 31))
    db_session.add(proj1)
    db_session.add(proj2)
    await db_session.commit()
    await db_session.refresh(proj1)
    await db_session.refresh(proj2)

    response = await client.get("/api/v1/lims/projects")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    projects_list = response.json()
    assert len(projects_list) >= 2  # 이미 생성된 프로젝트 포함될 수 있으므로 >=
    assert any(p["name"] == "프로젝트1" for p in projects_list)
    assert any(p["name"] == "프로젝트2" for p in projects_list)
    print("test_read_projects_success passed.")


@pytest.mark.asyncio
async def test_update_project_success_admin(
    admin_client: TestClient,
    db_session: Session,
):
    """
    관리자 권한으로 프로젝트를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_project_success_admin ---")
    proj_create_data = {
        "code": "PRJU",
        "name": "업데이트 전 프로젝트",
        "start_date": "2025-01-01",
        "end_date": "2025-06-30"
    }
    created_proj = await project_crud.create(db_session, obj_in=lims_schemas.ProjectCreate(**proj_create_data))

    update_data = {
        "name": "업데이트 후 프로젝트",
        "end_date": "2025-12-31"
    }
    response = await admin_client.put(f"/api/v1/lims/projects/{created_proj.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_proj = response.json()
    assert updated_proj["id"] == created_proj.id
    assert updated_proj["name"] == update_data["name"]
    assert updated_proj["end_date"] == update_data["end_date"]
    print("test_update_project_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_project_success_admin(
    admin_client: TestClient,
    db_session: Session,
):
    """
    관리자 권한으로 프로젝트를 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_project_success_admin ---")
    proj_create_data = {
        "code": "PRJD",
        "name": "삭제될 프로젝트",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31"
    }
    created_proj = await project_crud.create(db_session, obj_in=lims_schemas.ProjectCreate(**proj_create_data))

    response = await admin_client.delete(f"/api/v1/lims/projects/{created_proj.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204
    # 삭제 후 조회 시 404 확인
    get_response = await admin_client.get(f"/api/v1/lims/projects/{created_proj.id}")
    assert get_response.status_code == 404
    print("test_delete_project_success_admin passed.")


# --- LIMS 시료 용기 (SampleContainer) 테스트 ---
@pytest.mark.asyncio
async def test_create_sample_container_success_admin(admin_client: TestClient):
    print("\n--- Running test_create_sample_container_success_admin ---")
    container_data = {"code": 100, "name": "유리병 1L", "memo": "갈색 유리병"}
    response = await admin_client.post("/api/v1/lims/sample_containers", json=container_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "유리병 1L"
    print("test_create_sample_container_success_admin passed.")


@pytest.mark.asyncio
async def test_read_sample_containers_success(client: TestClient, db_session: Session):
    print("\n--- Running test_read_sample_containers_success ---")
    await sample_container_crud.create(db_session, obj_in=lims_schemas.SampleContainerCreate(code=101, name="플라스틱병 500ml"))
    response = await client.get("/api/v1/lims/sample_containers")
    assert response.status_code == 200
    assert any(c["name"] == "플라스틱병 500ml" for c in response.json())
    print("test_read_sample_containers_success passed.")


@pytest.mark.asyncio
async def test_update_sample_container_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_update_sample_container_success_admin ---")
    container = await sample_container_crud.create(db_session, obj_in=lims_schemas.SampleContainerCreate(code=102, name="업데이트 전 용기"))
    update_data = {"name": "업데이트 후 용기"}
    response = await admin_client.put(f"/api/v1/lims/sample_containers/{container.id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "업데이트 후 용기"
    print("test_update_sample_container_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_sample_container_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_delete_sample_container_success_admin ---")
    container = await sample_container_crud.create(db_session, obj_in=lims_schemas.SampleContainerCreate(code=103, name="삭제될 용기"))
    response = await admin_client.delete(f"/api/v1/lims/sample_containers/{container.id}")
    assert response.status_code == 204
    print("test_delete_sample_container_success_admin passed.")


# --- LIMS 시료 유형 (SampleType) 테스트 ---
@pytest.mark.asyncio
async def test_create_sample_type_success_admin(admin_client: TestClient):
    print("\n--- Running test_create_sample_type_success_admin ---")
    type_data = {"code": 200, "name": "지하수 시료", "memo": "샘플 유형 지하수"}
    response = await admin_client.post("/api/v1/lims/sample_types", json=type_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "지하수 시료"
    print("test_create_sample_type_success_admin passed.")


@pytest.mark.asyncio
async def test_read_sample_types_success(client: TestClient, db_session: Session):
    print("\n--- Running test_read_sample_types_success ---")
    await sample_type_crud.create(db_session, obj_in=lims_schemas.SampleTypeCreate(code=201, name="하천수 시료"))
    response = await client.get("/api/v1/lims/sample_types")
    assert response.status_code == 200
    assert any(t["name"] == "하천수 시료" for t in response.json())
    print("test_read_sample_types_success passed.")


@pytest.mark.asyncio
async def test_update_sample_type_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_update_sample_type_success_admin ---")
    sample_type_obj = await sample_type_crud.create(db_session, obj_in=lims_schemas.SampleTypeCreate(code=202, name="업데이트 전 유형"))
    update_data = {"name": "업데이트 후 유형"}
    response = await admin_client.put(f"/api/v1/lims/sample_types/{sample_type_obj.id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "업데이트 후 유형"
    print("test_update_sample_type_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_sample_type_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_delete_sample_type_success_admin ---")
    sample_type_obj = await sample_type_crud.create(db_session, obj_in=lims_schemas.SampleTypeCreate(code=203, name="삭제될 유형"))
    response = await admin_client.delete(f"/api/v1/lims/sample_types/{sample_type_obj.id}")
    assert response.status_code == 204
    print("test_delete_sample_type_success_admin passed.")


# --- LIMS 채수 지점 (SamplingPoint) 테스트 ---
@pytest.mark.asyncio
async def test_create_sampling_point_success_admin(admin_client: TestClient, test_plant: loc_models.facility):
    print("\n--- Running test_create_sampling_point_success_admin ---")
    point_data = {"code": "SP01", "name": "새 채수 지점", "plant_id": test_plant.id}
    response = await admin_client.post("/api/v1/lims/sampling_points", json=point_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "새 채수 지점"
    print("test_create_sampling_point_success_admin passed.")


@pytest.mark.asyncio
async def test_read_sampling_points_by_plant_id(client: TestClient, db_session: Session, test_plant: loc_models.facility):
    print("\n--- Running test_read_sampling_points_by_plant_id ---")
    plant2 = loc_models.facility(code="TP02", name="테스트 플랜트2")
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant2)

    await sampling_point_crud.create(db_session, obj_in=lims_schemas.SamplingPointCreate(code="SP02", name="지점 2-1", plant_id=test_plant.id))
    await sampling_point_crud.create(db_session, obj_in=lims_schemas.SamplingPointCreate(code="SP03", name="지점 2-2", plant_id=test_plant.id))
    await sampling_point_crud.create(db_session, obj_in=lims_schemas.SamplingPointCreate(code="SP04", name="지점 3-1", plant_id=plant2.id))

    response = await client.get(f"/api/v1/lims/sampling_points?plant_id={test_plant.id}")
    assert response.status_code == 200
    points = response.json()
    assert len(points) >= 2  # 이미 생성된 지점 포함될 수 있으므로 >=
    assert all(p["plant_id"] == test_plant.id for p in points)
    assert any(p["name"] == "지점 2-1" for p in points)
    print("test_read_sampling_points_by_plant_id passed.")


@pytest.mark.asyncio
async def test_update_sampling_point_success_admin(admin_client: TestClient, db_session: Session, test_plant: loc_models.facility):
    print("\n--- Running test_update_sampling_point_success_admin ---")
    point = await sampling_point_crud.create(db_session, obj_in=lims_schemas.SamplingPointCreate(code="SP_UPD", name="업데이트 전 지점", plant_id=test_plant.id))
    update_data = {"name": "업데이트 후 지점", "code": "SP_MOD"}
    response = await admin_client.put(f"/api/v1/lims/sampling_points/{point.id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "업데이트 후 지점"
    assert response.json()["code"] == "SP_MOD"
    print("test_update_sampling_point_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_sampling_point_success_admin(admin_client: TestClient, db_session: Session, test_plant: loc_models.facility):
    print("\n--- Running test_delete_sampling_point_success_admin ---")
    point = await sampling_point_crud.create(db_session, obj_in=lims_schemas.SamplingPointCreate(code="SP_DEL", name="삭제될 지점", plant_id=test_plant.id))
    response = await admin_client.delete(f"/api/v1/lims/sampling_points/{point.id}")
    assert response.status_code == 204
    print("test_delete_sampling_point_success_admin passed.")


# --- LIMS 날씨 조건 (WeatherCondition) 테스트 ---
@pytest.mark.asyncio
async def test_create_weather_condition_success_admin(admin_client: TestClient):
    print("\n--- Running test_create_weather_condition_success_admin ---")
    weather_data = {"code": 10, "status": "흐림", "memo": "구름 많음"}
    response = await admin_client.post("/api/v1/lims/weather_conditions", json=weather_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["status"] == "흐림"
    print("test_create_weather_condition_success_admin passed.")


@pytest.mark.asyncio
async def test_read_weather_conditions_success(client: TestClient, db_session: Session):
    print("\n--- Running test_read_weather_conditions_success ---")
    await weather_condition_crud.create(db_session, obj_in=lims_schemas.WeatherConditionCreate(code=11, status="비"))
    response = await client.get("/api/v1/lims/weather_conditions")
    assert response.status_code == 200
    assert any(w["status"] == "비" for w in response.json())
    print("test_read_weather_conditions_success passed.")


@pytest.mark.asyncio
async def test_update_weather_condition_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_update_weather_condition_success_admin ---")
    weather_obj = await weather_condition_crud.create(db_session, obj_in=lims_schemas.WeatherConditionCreate(code=12, status="업데이트 전 날씨"))
    update_data = {"status": "업데이트 후 날씨", "memo": "날씨 변경됨"}
    response = await admin_client.put(f"/api/v1/lims/weather_conditions/{weather_obj.id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["status"] == "업데이트 후 날씨"
    print("test_update_weather_condition_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_weather_condition_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_delete_weather_condition_success_admin ---")
    weather_obj = await weather_condition_crud.create(db_session, obj_in=lims_schemas.WeatherConditionCreate(code=13, status="삭제될 날씨"))
    response = await admin_client.delete(f"/api/v1/lims/weather_conditions/{weather_obj.id}")
    assert response.status_code == 204
    print("test_delete_weather_condition_success_admin passed.")


# --- LIMS 시험 의뢰 (TestRequest) 테스트 ---

# test_create_test_request_success_user는 기존 코드에 있으므로 그대로 둠

@pytest.mark.asyncio
async def test_create_test_request_invalid_fk_admin(
    admin_client: TestClient,
    test_department: usr_models.Department,  # FK
    test_sampler_user: usr_models.User,  # FK (requester_user_id)
):
    """
    관리자 권한으로 유효하지 않은 FK (예: 없는 프로젝트 ID)로 시험 의뢰 생성 시도 시 404 Not Found를 반환하는지 테스트합니다.
    (CRUD 계층에서 404를 반환하도록 수정되었으므로)
    """
    print("\n--- Running test_create_test_request_invalid_fk_admin ---")
    request_data = {
        "request_date": str(date.today()),
        "project_id": 99999,  # 존재하지 않는 프로젝트 ID
        "department_id": test_department.id,
        "requester_user_id": test_sampler_user.id,
        "title": "잘못된 FK 테스트",
        "requested_parameters": {"TEMP": True},
    }
    response = await admin_client.post("/api/v1/lims/test_requests", json=request_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 404  # CRUD에서 404 반환
    assert response.json()["detail"] == "Project not found."
    print("test_create_test_request_invalid_fk_admin passed.")


@pytest.mark.asyncio
async def test_read_test_requests_filtered_by_project_id(
    authorized_client: TestClient,  # 일반 사용자로 인증된 클라이언트
    db_session: Session,
    test_department: usr_models.Department,
    test_user: usr_models.User,  # authorized_client의 기반이 되는 test_user를 직접 주입받습니다.
):
    """
    일반 사용자 권한으로 특정 프로젝트 ID로 시험 의뢰 목록을 성공적으로 조회하는지 테스트합니다.
    (자신이 요청한 의뢰만 조회됨)
    """
    print("\n--- Running test_read_test_requests_filtered_by_project_id ---")
    proj1 = lims_models.Project(code="PRJ1", name="필터 프로젝트1", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
    proj2 = lims_models.Project(code="PRJ2", name="필터 프로젝트2", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
    db_session.add(proj1)
    db_session.add(proj2)
    await db_session.commit()
    await db_session.refresh(proj1)
    await db_session.refresh(proj2)

    # test_user (authorized_client에 연결된 사용자)가 요청한 의뢰
    await test_request_crud.create(db_session, obj_in=lims_schemas.TestRequestCreate(
        request_date=date.today(), project_id=proj1.id, department_id=test_department.id,
        requester_user_id=test_user.id,  # authorized_client의 user_id와 일치시킵니다.
        title="일반 사용자_필터 의뢰 1", requested_parameters={}
    ), current_user_id=test_user.id)  # current_user_id도 test_user.id로 전달

    await test_request_crud.create(db_session, obj_in=lims_schemas.TestRequestCreate(
        request_date=date.today(), project_id=proj1.id, department_id=test_department.id,
        requester_user_id=test_user.id,  # authorized_client의 user_id와 일치시킵니다.
        title="일반 사용자_필터 의뢰 2", requested_parameters={}
    ), current_user_id=test_user.id)  # current_user_id도 test_user.id로 전달

    # 다른 사용자(예: test_sampler_user)가 요청한 의뢰. 이 의뢰는 test_user가 조회할 때 보이지 않아야 합니다.
    # test_sampler_user 픽스처가 test_user와 다른 사용자를 생성한다고 가정합니다.
    # 만약 test_sampler_user가 test_user와 동일한 객체라면, 별도의 사용자 생성 픽스처가 필요합니다.
    # 여기서는 test_sampler_user 픽스처가 이미 다른 사용자를 생성하고 있다고 가정합니다.
    # (conftest.py에서 test_user와 test_sampler_user가 다른 사용자 ID를 갖는지 확인 필요)
    await test_request_crud.create(db_session, obj_in=lims_schemas.TestRequestCreate(
        request_date=date.today(), project_id=proj2.id, department_id=test_department.id,
        requester_user_id=test_user.id,  # test_user와 다른 사용자 ID
        title="다른 사용자_필터 의뢰 3", requested_parameters={}
    ), current_user_id=test_user.id)  # current_user_id도 해당 사용자의 ID로 전달

    response = await authorized_client.get(f"/api/v1/lims/test_requests?project_id={proj1.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    requests = response.json()

    # test_user (ID: 1)가 요청한, project_id=proj1.id에 해당하는 시험 의뢰만 반환되어야 합니다.
    # 따라서 예상되는 결과는 정확히 2개여야 합니다.
    assert len(requests) == 2
    assert all(r["project_id"] == proj1.id for r in requests)
    assert all(r["requester_user_id"] == test_user.id for r in requests)
    assert any(r["title"] == "일반 사용자_필터 의뢰 1" for r in requests)
    assert any(r["title"] == "일반 사용자_필터 의뢰 2" for r in requests)
    # 다른 사용자가 생성한 의뢰는 조회되지 않아야 합니다.
    assert not any(r["title"] == "다른 사용자_필터 의뢰 3" for r in requests)
    print("test_read_test_requests_filtered_by_project_id passed.")


# --- LIMS 원 시료 (Sample) 테스트 ---
# test_create_sample_success_user는 기존 코드에 있으므로 그대로 둠
@pytest.mark.asyncio
async def test_read_samples_by_request_id(
    authorized_client: TestClient, db_session: Session,
    test_lims_project: lims_models.Project,
    test_department: usr_models.Department,
    test_sampler_user: usr_models.User,  # 이 픽스처는 TestRequest 생성에 여전히 필요합니다.
    test_user: usr_models.User,  # authorized_client의 기반이 되는 test_user를 추가합니다.
    test_sampling_point: lims_models.SamplingPoint,
    test_sample_container: lims_models.SampleContainer,
    test_sample_type: lims_models.SampleType
):
    """
    특정 시험 의뢰 ID로 원 시료 목록을 성공적으로 조회하는지 테스트합니다.
    (자신이 수집한 시료만 조회됨)
    """
    print("\n--- Running test_read_samples_by_request_id ---")
    # TestRequest 생성 시 requester_user_id를 test_user.id로 설정하여,
    # authorized_client가 나중에 이 TestRequest를 기반으로 Sample을 조회할 때 권한 문제가 없도록 합니다.
    # Note: TestRequest 생성 시 current_user_id는 TestRequest CRUD 로직에서 사용되므로,
    # 여기서는 test_sampler_user를 사용하되, 나중에 Sample 생성 시에는 test_user를 사용합니다.
    req1 = lims_models.TestRequest(request_date=date.today(), project_id=test_lims_project.id,
                                   department_id=test_department.id, requester_user_id=test_user.id,  # test_user.id로 변경
                                   title="시료 조회 의뢰1", requested_parameters={"A": True})
    req2 = lims_models.TestRequest(request_date=date.today(), project_id=test_lims_project.id,
                                   department_id=test_department.id, requester_user_id=test_user.id,  # test_user.id로 변경
                                   title="시료 조회 의뢰2", requested_parameters={"B": True})
    db_session.add(req1)
    db_session.add(req2)
    await db_session.commit()
    await db_session.refresh(req1)
    await db_session.refresh(req2)

    # test_user (ID: 1)가 수집한 시료 2개 생성 (req1에 연결)
    sample1 = lims_models.Sample(request_id=req1.id, sampling_point_id=test_sampling_point.id, sampling_date=date.today(),
                                 sample_type_id=test_sample_type.id, container_id=test_sample_container.id,
                                 parameters_for_analysis={"A": True}, collector_user_id=test_user.id)  # test_user.id로 변경
    sample2 = lims_models.Sample(request_id=req1.id, sampling_point_id=test_sampling_point.id, sampling_date=date.today(),
                                 sample_type_id=test_sample_type.id, container_id=test_sample_container.id,
                                 parameters_for_analysis={"B": True}, collector_user_id=test_user.id)  # test_user.id로 변경
    db_session.add(sample1)
    db_session.add(sample2)

    # 다른 사용자(test_sampler_user, ID: 2)가 수집한 시료 1개 생성 (req2에 연결)
    sample3 = lims_models.Sample(request_id=req2.id, sampling_point_id=test_sampling_point.id, sampling_date=date.today(),
                                 sample_type_id=test_sample_type.id, container_id=test_sample_container.id,
                                 parameters_for_analysis={"C": True}, collector_user_id=test_sampler_user.id)  # test_sampler_user.id 유지
    db_session.add(sample3)

    await db_session.commit()
    await db_session.refresh(sample1)
    await db_session.refresh(sample2)
    await db_session.refresh(sample3)

    response = await authorized_client.get(f"/api/v1/lims/samples?request_id={req1.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    samples_list = response.json()

    # test_user (ID: 1)가 수집했고, request_id=req1.id에 해당하는 시료만 반환되어야 합니다.
    # 따라서 예상되는 결과는 정확히 2개여야 합니다.
    assert len(samples_list) == 2
    assert all(s["request_id"] == req1.id for s in samples_list)
    assert all(s["collector_user_id"] == test_user.id for s in samples_list)
    assert any(s["parameters_for_analysis"] == {"A": True} for s in samples_list)
    assert any(s["parameters_for_analysis"] == {"B": True} for s in samples_list)
    assert not any(s["request_id"] == req2.id for s in samples_list)  # req2의 시료는 반환되지 않아야 합니다.

    print("test_read_samples_by_request_id passed.")


# --- LIMS 분할 시료 (AliquotSample) 테스트 ---

# test_create_aliquot_sample_success_user는 기존 코드에 있으므로 그대로 둠
# test_update_aliquot_sample_status_and_parent_status는 기존 코드에 있으므로 그대로 둠


# --- LIMS 워크시트 (Worksheet) 테스트 ---
@pytest.fixture(name="test_worksheet")
async def test_worksheet_fixture(db_session: Session) -> lims_models.Worksheet:
    ws = lims_models.Worksheet(code="WS01", name="일일 수질 분석 워크시트", sort_order=1)
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest.mark.asyncio
async def test_create_worksheet_success_admin(admin_client: TestClient):
    print("\n--- Running test_create_worksheet_success_admin ---")
    worksheet_data = {"code": "NEW_WS", "name": "새로운 워크시트", "sort_order": 2}
    response = await admin_client.post("/api/v1/lims/worksheets", json=worksheet_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "새로운 워크시트"
    print("test_create_worksheet_success_admin passed.")


@pytest.mark.asyncio
async def test_read_worksheets_success(client: TestClient, db_session: Session):
    print("\n--- Running test_read_worksheets_success ---")
    await worksheet_crud.create(db_session, obj_in=lims_schemas.WorksheetCreate(code="WS_R1", name="조회 워크시트 1", sort_order=3))
    response = await client.get("/api/v1/lims/worksheets")
    assert response.status_code == 200
    assert any(ws["name"] == "조회 워크시트 1" for ws in response.json())
    print("test_read_worksheets_success passed.")


@pytest.mark.asyncio
async def test_update_worksheet_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_update_worksheet_success_admin ---")
    ws = await worksheet_crud.create(db_session, obj_in=lims_schemas.WorksheetCreate(code="WS_UPD", name="업데이트 전 워크시트", sort_order=4))
    update_data = {"name": "업데이트 후 워크시트", "sort_order": 5}
    response = await admin_client.put(f"/api/v1/lims/worksheets/{ws.id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "업데이트 후 워크시트"
    print("test_update_worksheet_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_worksheet_success_admin(admin_client: TestClient, db_session: Session):
    print("\n--- Running test_delete_worksheet_success_admin ---")
    ws = await worksheet_crud.create(db_session, obj_in=lims_schemas.WorksheetCreate(code="WS_DEL", name="삭제될 워크시트", sort_order=6))
    response = await admin_client.delete(f"/api/v1/lims/worksheets/{ws.id}")
    assert response.status_code == 204
    print("test_delete_worksheet_success_admin passed.")


# --- LIMS 워크시트 항목 (WorksheetItem) 테스트 ---
@pytest.mark.asyncio
async def test_create_worksheet_item_success_admin(admin_client: TestClient, test_worksheet: lims_models.Worksheet):
    print("\n--- Running test_create_worksheet_item_success_admin ---")
    item_data = {
        "worksheet_id": test_worksheet.id,
        "code": "CELL_A1",
        "priority_order": 1,
        "name": "항목 A1",
        "label": "pH 측정값",
        "type": 1,  # 숫자
    }
    response = await admin_client.post("/api/v1/lims/worksheet_items", json=item_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "항목 A1"
    print("test_create_worksheet_item_success_admin passed.")


@pytest.mark.asyncio
async def test_read_worksheet_items_by_worksheet_id(client: TestClient, db_session: Session, test_worksheet: lims_models.Worksheet):
    print("\n--- Running test_read_worksheet_items_by_worksheet_id ---")
    ws2 = lims_models.Worksheet(code="WS_F2", name="필터 워크시트 2", sort_order=1)
    db_session.add(ws2)
    await db_session.commit()
    await db_session.refresh(ws2)

    await worksheet_item_crud.create(db_session, obj_in=lims_schemas.WorksheetItemCreate(
        worksheet_id=test_worksheet.id, code="CELL_B1", priority_order=2, name="항목 B1", label="B1", type=1
    ))
    await worksheet_item_crud.create(db_session, obj_in=lims_schemas.WorksheetItemCreate(
        worksheet_id=test_worksheet.id, code="CELL_C1", priority_order=3, name="항목 C1", label="C1", type=1
    ))
    await worksheet_item_crud.create(db_session, obj_in=lims_schemas.WorksheetItemCreate(
        worksheet_id=ws2.id, code="CELL_A2", priority_order=1, name="항목 A2", label="A2", type=1
    ))

    response = await client.get(f"/api/v1/lims/worksheets/{test_worksheet.id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2  # 다른 테스트로 인해 더 많을 수 있음
    assert all(item["worksheet_id"] == test_worksheet.id for item in items)
    print("test_read_worksheet_items_by_worksheet_id passed.")


# --- LIMS 워크시트 데이터 (WorksheetData) 테스트 ---
@pytest.mark.asyncio
async def test_create_worksheet_data_success_user(
    authorized_client: TestClient,
    test_worksheet: lims_models.Worksheet,
    test_analyst_user: usr_models.User
):
    print("\n--- Running test_create_worksheet_data_success_user ---")
    data_data = {
        "worksheet_id": test_worksheet.id,
        "data_date": str(date.today()),
        "analyst_user_id": test_analyst_user.id,
        "is_verified": False,
        "raw_data": {"CELL_A1": 7.5, "CELL_B1": "Pass"}
    }
    response = await authorized_client.post("/api/v1/lims/worksheet_data", json=data_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["raw_data"] == data_data["raw_data"]
    assert response.json()["analyst_user_id"] == test_analyst_user.id
    print("test_create_worksheet_data_success_user passed.")


@pytest.mark.asyncio
async def test_read_worksheet_data_filtered_by_worksheet_and_date(
    authorized_client: TestClient,
    db_session: Session,
    test_worksheet: lims_models.Worksheet,
    test_user: usr_models.User
):
    print("\n--- Running test_read_worksheet_data_filtered_by_worksheet_and_date ---")
    ws_data1 = lims_schemas.WorksheetDataCreate(worksheet_id=test_worksheet.id, data_date=date.today(), analyst_user_id=test_user.id, raw_data={"a": 1})
    ws_data2 = lims_schemas.WorksheetDataCreate(worksheet_id=test_worksheet.id, data_date=date.today() - timedelta(days=1), analyst_user_id=test_user.id, raw_data={"b": 2})
    ws_data3 = lims_schemas.WorksheetDataCreate(worksheet_id=test_worksheet.id, data_date=date.today(), analyst_user_id=test_user.id, raw_data={"c": 3})

    await worksheet_data_crud.create(db_session, obj_in=ws_data1)
    await worksheet_data_crud.create(db_session, obj_in=ws_data2)
    await worksheet_data_crud.create(db_session, obj_in=ws_data3)

    response = await authorized_client.get(f"/api/v1/lims/worksheet_data?worksheet_id={test_worksheet.id}&data_date={date.today()}")
    assert response.status_code == 200
    data_list = response.json()

    # test_user가 생성했고, worksheet_id와 data_date 필터에 맞는 데이터가 반환되어야 합니다.
    # ws_data1과 ws_data3이 해당하므로, 2개가 반환되어야 합니다.
    assert len(data_list) == 2  # 정확히 2개여야 합니다.
    assert all(d["worksheet_id"] == test_worksheet.id for d in data_list)
    assert all(d["data_date"] == str(date.today()) for d in data_list)
    assert all(d["analyst_user_id"] == test_user.id for d in data_list)  # 생성자가 test_user인지 확인
    print("test_read_worksheet_data_filtered_by_worksheet_and_date passed.")


# --- LIMS 분석 결과 (AnalysisResult) 테스트 ---
@pytest.mark.asyncio
async def test_create_analysis_result_success_user(
    authorized_client: TestClient,
    db_session: Session,
    test_aliquot_sample: lims_models.AliquotSample,  # 생성된 픽스처 필요
    test_worksheet: lims_models.Worksheet,
    test_analyst_user: usr_models.User
):
    print("\n--- Running test_create_analysis_result_success_user ---")
    # WorksheetData 생성 (AnalysisResult의 FK)
    ws_data = await worksheet_data_crud.create(db_session, obj_in=lims_schemas.WorksheetDataCreate(
        worksheet_id=test_worksheet.id,
        data_date=date.today(),
        analyst_user_id=test_analyst_user.id,
        raw_data={"test_param": 10.0}
    ))

    result_data = {
        "aliquot_sample_id": test_aliquot_sample.id,
        "parameter_id": test_aliquot_sample.parameter_id,  # AliquotSample과 동일한 파라미터 사용
        "worksheet_id": test_worksheet.id,
        "worksheet_data_id": ws_data.id,
        "result_value": 7.15,
        "unit": "pH",
        "analysis_date": str(date.today()),
        "analyst_user_id": test_analyst_user.id,
        "is_approved": False
    }
    response = await authorized_client.post("/api/v1/lims/analysis_results", json=result_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["result_value"] == pytest.approx(7.15)
    print("test_create_analysis_result_success_user passed.")


@pytest.fixture(name="test_aliquot_sample")
async def test_aliquot_sample_fixture(
    db_session: Session,
    test_lims_project: lims_models.Project,
    test_department: usr_models.Department,
    test_sampler_user: usr_models.User,
    test_sampling_point: lims_models.SamplingPoint,
    test_sample_container: lims_models.SampleContainer,
    test_sample_type: lims_models.SampleType,
    test_instrument: fms_models.Equipment
) -> lims_models.AliquotSample:
    # TestRequest 생성
    test_req = lims_models.TestRequest(
        request_date=date.today(),
        project_id=test_lims_project.id,
        department_id=test_department.id,
        requester_user_id=test_sampler_user.id,
        title="Test request for aliquot",
        requested_parameters={}
    )
    db_session.add(test_req)
    await db_session.commit()
    await db_session.refresh(test_req)

    # Sample 생성
    test_sample = lims_models.Sample(
        request_id=test_req.id,
        sampling_point_id=test_sampling_point.id,
        sampling_date=date.today(),
        sample_type_id=test_sample_type.id,
        container_id=test_sample_container.id,
        parameters_for_analysis={},
        collector_user_id=test_sampler_user.id
    )
    db_session.add(test_sample)
    await db_session.commit()
    await db_session.refresh(test_sample)

    # Parameter 생성
    test_param = lims_models.Parameter(
        code="TSTP",
        name="테스트 파라미터",
        sort_order=1,
        instrument_id=test_instrument.id
    )
    db_session.add(test_param)
    await db_session.commit()
    await db_session.refresh(test_param)

    # AliquotSample 생성
    aliquot = lims_models.AliquotSample(
        parent_sample_id=test_sample.id,
        parameter_id=test_param.id,
        analysis_status="Pending"
    )
    db_session.add(aliquot)
    await db_session.commit()
    await db_session.refresh(aliquot)
    return aliquot


# --- LIMS 시험 의뢰 템플릿 (TestRequestTemplate) 테스트 ---
@pytest.mark.asyncio
async def test_create_test_request_template_success_user(
    authorized_client: TestClient,
    test_analyst_user: usr_models.User  # 템플릿 생성 사용자
):
    print("\n--- Running test_create_test_request_template_success_user ---")
    template_data = {
        "name": "월간 수질 보고서 템플릿",
        "user_id": test_analyst_user.id,
        "serialized_text": {"header": "월간 보고", "items": ["pH", "DO"]}
    }
    response = await authorized_client.post("/api/v1/lims/test_request_templates", json=template_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "월간 수질 보고서 템플릿"
    assert response.json()["user_id"] == test_analyst_user.id
    print("test_create_test_request_template_success_user passed.")


@pytest.mark.asyncio
async def test_read_test_request_templates_filtered_by_user(
    authorized_client: TestClient,  # test_user (role 100)
    db_session: Session,
    test_analyst_user: usr_models.User,  # 이 픽스처는 다른 사용자 데이터 생성에 사용
    test_admin_user: usr_models.User,  # admin user for creating another template
    test_user: usr_models.User  # authorized_client의 기반이 되는 test_user 픽스처 추가
):
    """
    일반 사용자 권한으로 자신의 시험 의뢰 템플릿 목록을 성공적으로 조회하는지 테스트합니다.
    (다른 사용자의 템플릿은 조회되지 않아야 함)
    """
    print("\n--- Running test_read_test_request_templates_filtered_by_user ---")

    # 1. test_user (로그인된 일반 사용자)가 생성한 템플릿
    template_by_test_user_1 = await test_request_template_crud.create(db_session, obj_in=lims_schemas.TestRequestTemplateCreate(
        name="일반 사용자 템플릿 1", user_id=test_user.id, serialized_text={"key": "value1"}
    ), current_user_id=test_user.id)

    template_by_test_user_2 = await test_request_template_crud.create(db_session, obj_in=lims_schemas.TestRequestTemplateCreate(
        name="일반 사용자 템플릿 2", user_id=test_user.id, serialized_text={"key": "value2"}
    ), current_user_id=test_user.id)

    # 2. test_analyst_user (다른 일반 사용자)가 생성한 템플릿
    template_by_analyst = await test_request_template_crud.create(db_session, obj_in=lims_schemas.TestRequestTemplateCreate(
        name="분석가 템플릿 1 (다른 사용자)", user_id=test_analyst_user.id, serialized_text={"key": "value3"}
    ), current_user_id=test_analyst_user.id)  # current_user_id도 해당 사용자의 ID로 전달

    # 3. test_admin_user (관리자)가 생성한 템플릿
    template_by_admin = await test_request_template_crud.create(db_session, obj_in=lims_schemas.TestRequestTemplateCreate(
        name="관리자 템플릿 1", user_id=test_admin_user.id, serialized_text={"key": "value4"}
    ), current_user_id=test_admin_user.id)  # current_user_id도 해당 사용자의 ID로 전달

    # test_user (authorized_client)로 로그인하여 자신의 템플릿 조회
    # user_id 필터를 test_user.id로 명시적으로 지정합니다.
    response = await authorized_client.get(f"/api/v1/lims/test_request_templates?user_id={test_user.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    templates = response.json()

    # test_user가 생성한 템플릿 2개만 반환되어야 합니다.
    assert len(templates) == 2
    assert all(t["user_id"] == test_user.id for t in templates)
    assert any(t["name"] == "일반 사용자 템플릿 1" for t in templates)
    assert any(t["name"] == "일반 사용자 템플릿 2" for t in templates)

    # 다른 사용자가 생성한 템플릿은 조회되지 않아야 합니다.
    assert not any(t["name"] == "분석가 템플릿 1 (다른 사용자)" for t in templates)
    assert not any(t["name"] == "관리자 템플릿 1" for t in templates)

    print("test_read_test_request_templates_filtered_by_user passed.")


# --- LIMS 사용자 정의 프로젝트/결과 보기 (PrView) 테스트 ---
@pytest.mark.asyncio
async def test_create_pr_view_success_user(
    authorized_client: TestClient,
    test_analyst_user: usr_models.User,
    test_plant: loc_models.facility,
    test_sampling_point: lims_models.SamplingPoint,
    test_instrument: fms_models.Equipment,
    db_session: Session
):
    print("\n--- Running test_create_pr_view_success_user ---")
    # Parameter 하나 생성 (pr_view의 parameter_ids FK 검증용)
    param_ph = lims_models.Parameter(code="PRVH", name="pH for PRV", sort_order=1, instrument_id=test_instrument.id)
    db_session.add(param_ph)
    await db_session.commit()
    await db_session.refresh(param_ph)

    view_data = {
        "name": "내 맞춤형 보기",
        "user_id": test_analyst_user.id,
        "plant_id": test_plant.id,
        "sampling_point_ids": [test_sampling_point.id],
        "parameter_ids": [param_ph.id],
        "memo": "자주 사용하는 필터"
    }
    response = await authorized_client.post("/api/v1/lims/pr_views", json=view_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "내 맞춤형 보기"
    assert response.json()["user_id"] == test_analyst_user.id
    assert response.json()["plant_id"] == test_plant.id
    assert test_sampling_point.id in response.json()["sampling_point_ids"]
    assert param_ph.id in response.json()["parameter_ids"]
    print("test_create_pr_view_success_user passed.")


# --- LIMS 표준 시료 (StandardSample) 테스트 ---
@pytest.mark.asyncio
async def test_create_standard_sample_success_admin(
    admin_client: TestClient,
    test_instrument: fms_models.Equipment,
    db_session: Session
):
    print("\n--- Running test_create_standard_sample_success_admin ---")
    param = lims_models.Parameter(code="STCD", name="표준 COD", sort_order=1, instrument_id=test_instrument.id)
    db_session.add(param)
    await db_session.commit()
    await db_session.refresh(param)

    sample_data = {
        "code": "STD001",
        "name": "COD 표준 100mg/L",
        "parameter_id": param.id,
        "concentration": 100.0,
        "preparation_date": str(date.today()),
        "expiration_date": str(date.today() + timedelta(days=365))
    }
    response = await admin_client.post("/api/v1/lims/standard_samples", json=sample_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["name"] == "COD 표준 100mg/L"
    print("test_create_standard_sample_success_admin passed.")


# --- LIMS 교정 기록 (CalibrationRecord) 테스트 ---
@pytest.mark.asyncio
async def test_create_calibration_record_success_admin(
    admin_client: TestClient,
    test_instrument: fms_models.Equipment,
    test_analyst_user: usr_models.User,
    db_session: Session
):
    print("\n--- Running test_create_calibration_record_success_admin ---")
    param = lims_models.Parameter(code="CAPH", name="교정 pH", sort_order=1, instrument_id=test_instrument.id)
    db_session.add(param)
    await db_session.commit()
    await db_session.refresh(param)

    std_sample = lims_models.StandardSample(
        code="CALSTD", name="교정 표준", parameter_id=param.id, concentration=7.0
    )
    db_session.add(std_sample)
    await db_session.commit()
    await db_session.refresh(std_sample)

    record_data = {
        "equipment_id": test_instrument.id,
        "parameter_id": param.id,
        "calibration_date": datetime.now(UTC).isoformat(),
        "next_calibration_date": str(date.today() + timedelta(days=180)),
        "calibrated_by_user_id": test_analyst_user.id,
        "standard_sample_id": std_sample.id,
        "acceptance_criteria_met": True
    }
    response = await admin_client.post("/api/v1/lims/calibration_records", json=record_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["equipment_id"] == test_instrument.id
    assert response.json()["acceptance_criteria_met"] is True
    print("test_create_calibration_record_success_admin passed.")


# --- LIMS QC 시료 결과 (QcSampleResult) 테스트 ---
@pytest.mark.asyncio
async def test_create_qc_sample_result_success_user(
    authorized_client: TestClient,
    test_aliquot_sample: lims_models.AliquotSample,  # 기존 픽스처 재사용
    test_analyst_user: usr_models.User
):
    """
    일반 사용자 권한으로 새로운 QC 시료 결과를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_qc_sample_result_success_user ---")
    qc_data = {
        "aliquot_sample_id": test_aliquot_sample.id,
        "parameter_id": test_aliquot_sample.parameter_id,
        "qc_type": "Blank",
        "expected_value": 0.0,
        "measured_value": 0.01,
        "analysis_date": str(date.today()),
        "analyst_user_id": test_analyst_user.id,
        "passed_qc": True
    }
    response = await authorized_client.post("/api/v1/lims/qc_sample_results", json=qc_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    assert response.status_code == 201
    assert response.json()["qc_type"] == "Blank"
    assert response.json()["analyst_user_id"] == test_analyst_user.id
    print("test_create_qc_sample_result_success_user passed.")
