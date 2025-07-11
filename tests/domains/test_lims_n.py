# tests/domains/test_lims_n.py

"""
'lims' 도메인 (실험실 정보 관리 시스템 및 QA/QC) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 LIMS 엔티티 (분석 항목, 프로젝트, 시료, 시험 의뢰, 분할 시료 등)의 CRUD 테스트.
- 자동 코드 생성, 상태 업데이트 연동과 같은 비즈니스 로직 검증.
- 다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

# 다른 도메인의 모델 임포트
from app.domains.loc import models as loc_models
from app.domains.usr import models as usr_models
from app.domains.fms import models as fms_models

# LIMS 도메인의 CRUD, 모델, 스키마
from app.domains.lims import crud as lims_crud
from app.domains.lims import models as lims_models
from app.domains.lims import schemas as lims_schemas

from datetime import date, datetime, timedelta, UTC

# -----------------------------------------------------------------------------
# 참고:
# 모든 테스트 픽스처(client, db_session, admin_client, authorized_client, test_user,
# test_lims_project, test_instrument 등)는 conftest.py 파일에 중앙 관리되고 있으며,
# pytest가 자동으로 주입합니다. 이 테스트 파일 내에서는 픽스처를 재정의하지 않습니다.
# -----------------------------------------------------------------------------


# =============================================================================
# 1. 분석 항목 (Parameter) 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_parameter_success_admin(
    admin_client: AsyncClient,
    test_instrument: fms_models.Equipment
):
    """
    [성공] 관리자 권한으로 새로운 분석 항목을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_parameter_success_admin ---")
    param_data = {
        "code": "BOD5",
        "name": "생물학적 산소 요구량 5일",
        "units": "mg/L",
        "method": "SM 5210 B",
        "instrument_id": test_instrument.id,
        "sort_order": 1,
        "is_active": True
    }
    response = await admin_client.post("/api/v1/lims/parameters", json=param_data)
    created_param = response.json()

    assert response.status_code == 201
    assert created_param["code"] == param_data["code"]
    assert created_param["name"] == param_data["name"]
    assert "id" in created_param


@pytest.mark.asyncio
async def test_create_parameter_unauthorized_user(
    authorized_client: AsyncClient,
    test_instrument: fms_models.Equipment
):
    """
    [실패/권한] 일반 사용자가 분석 항목 생성을 시도할 때 403 Forbidden을 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_parameter_unauthorized_user ---")
    param_data = {
        "code": "NOAU",
        "name": "권한 없는 사용자 생성 시도",
        "instrument_id": test_instrument.id,
        "sort_order": 99
    }
    response = await authorized_client.post("/api/v1/lims/parameters", json=param_data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_parameter_validation_error(
    admin_client: AsyncClient
):
    """
    [실패/유효성] 필수 필드(name) 누락 시 422 Unprocessable Entity를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_parameter_validation_error ---")
    invalid_data = {
        "code": "INV",
        # "name": "필수 필드 누락",  # name 필드 누락
        "sort_order": 1
    }
    response = await admin_client.post("/api/v1/lims/parameters", json=invalid_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_parameter_duplicate_code_admin(
    admin_client: AsyncClient,
    test_instrument: fms_models.Equipment
):
    """
    [실패/무결성] 관리자 권한으로 이미 존재하는 코드의 분석 항목 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_parameter_duplicate_code_admin ---")
    param_data_existing = {
        "code": "DUPC",
        "name": "중복 코드 파라미터",
        "sort_order": 1,
        "instrument_id": test_instrument.id
    }
    await admin_client.post("/api/v1/lims/parameters", json=param_data_existing)

    param_data_duplicate = {
        "code": "DUPC",
        "name": "새로운 파라미터",
        "sort_order": 2,
        "instrument_id": test_instrument.id
    }
    response = await admin_client.post("/api/v1/lims/parameters", json=param_data_duplicate)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_parameters_success(client: AsyncClient, db_session: AsyncSession, test_instrument: fms_models.Equipment):
    """
    [성공] 모든 사용자가 분석 항목 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_parameters_success ---")
    await lims_crud.parameter.create(db_session, obj_in=lims_schemas.ParameterCreate(code="COD", name="화학적 산소 요구량", units="mg/L", sort_order=1, instrument_id=test_instrument.id))
    await lims_crud.parameter.create(db_session, obj_in=lims_schemas.ParameterCreate(code="SS", name="부유물질", units="mg/L", sort_order=2, instrument_id=test_instrument.id))

    response = await client.get("/api/v1/lims/parameters")
    assert response.status_code == 200
    params_list = response.json()
    assert len(params_list) >= 2
    assert any(p["name"] == "화학적 산소 요구량" for p in params_list)


@pytest.mark.asyncio
async def test_read_parameters_by_analysis_group(
    admin_client: AsyncClient, db_session: AsyncSession
):
    """
    [성공/신규] analysis_group으로 파라미터를 필터링하여 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_parameters_by_analysis_group ---")

    # 테스트 데이터 생성
    param1_data = {"code": "BOD", "name": "생물학적 산소 요구량", "sort_order": 1, "analysis_group": "BOD_GROUP"}
    param2_data = {"code": "BOD5_2", "name": "5일 생물학적 산소 요구량", "sort_order": 2, "analysis_group": "BOD_GROUP"}  # 중복 코드 방지
    param3_data = {"code": "COD_2", "name": "화학적 산소 요구량", "sort_order": 3, "analysis_group": "COD_GROUP"}  # 중복 코드 방지

    await admin_client.post("/api/v1/lims/parameters", json=param1_data)
    await admin_client.post("/api/v1/lims/parameters", json=param2_data)
    await admin_client.post("/api/v1/lims/parameters", json=param3_data)

    # analysis_group으로 필터링하여 API 호출
    response = await admin_client.get("/api/v1/lims/parameters?analysis_group=BOD_GROUP")
    assert response.status_code == 200

    result_data = response.json()
    assert len(result_data) >= 2  # 다른 테스트와 격리되지 않으므로, 최소 2개 이상

    result_codes = {item['code'] for item in result_data}
    assert "BOD" in result_codes
    assert "BOD5_2" in result_codes
    assert "COD_2" not in result_codes  # 다른 그룹의 항목은 포함되지 않아야 함


@pytest.mark.asyncio
async def test_update_parameter_unauthorized_user(
    authorized_client: AsyncClient,
    test_parameter: lims_models.Parameter
):
    """
    [실패/권한] 일반 사용자가 분석 항목 수정을 시도할 때 403 Forbidden을 반환하는지 테스트합니다.
    """
    print("\n--- Running test_update_parameter_unauthorized_user ---")
    update_data = {"name": "권한 없는 사용자 수정 시도"}
    response = await authorized_client.put(f"/api/v1/lims/parameters/{test_parameter.id}", json=update_data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_parameter_success_admin(
    admin_client: AsyncClient,
    test_parameter: lims_models.Parameter
):
    """
    [성공] 관리자 권한으로 분석 항목을 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_parameter_success_admin ---")
    update_data = {
        "name": "업데이트 후",
        "units": "mg/L (수정됨)",
        "sort_order": 10
    }
    response = await admin_client.put(f"/api/v1/lims/parameters/{test_parameter.id}", json=update_data)
    assert response.status_code == 200
    updated_param = response.json()
    assert updated_param["id"] == test_parameter.id
    assert updated_param["name"] == update_data["name"]


#  [수정] 기존 물리적 삭제 테스트를 논리적 삭제(Soft Delete) 테스트로 변경
@pytest.mark.asyncio
async def test_soft_delete_parameter_success_admin(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    test_parameter: lims_models.Parameter
):
    """
    [성공/수정] 관리자가 파라미터를 논리적으로 삭제(비활성화)하는지 테스트합니다.
    """
    print("\n--- Running test_soft_delete_parameter_success_admin ---")
    param_id_to_delete = test_parameter.id

    # 삭제(비활성화) 요청
    delete_response = await admin_client.delete(f"/api/v1/lims/parameters/{param_id_to_delete}")
    assert delete_response.status_code == 200  # 업데이트이므로 200 OK
    assert delete_response.json()["is_active"] is False

    # 비활성화된 객체를 ID로 직접 조회 시 여전히 조회되어야 함
    get_response = await admin_client.get(f"/api/v1/lims/parameters/{param_id_to_delete}")
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False

    # 전체 목록 조회 시에는 비활성화된 항목이 포함되지 않아야 함
    list_response = await admin_client.get("/api/v1/lims/parameters")
    assert list_response.status_code == 200
    assert not any(p["id"] == param_id_to_delete for p in list_response.json())


# =============================================================================
# 2. 프로젝트 (Project) 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_project_success_admin(admin_client: AsyncClient):
    """
    [성공] 관리자 권한으로 새로운 프로젝트를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_project_success_admin ---")
    project_data = {
        "code": "PRJ2",
        "name": "새로운 LIMS 프로젝트",
        "start_date": "2025-06-01",
        "end_date": "2025-12-31"
    }
    response = await admin_client.post("/api/v1/lims/projects", json=project_data)
    assert response.status_code == 201
    created_project = response.json()
    assert created_project["name"] == project_data["name"]


@pytest.mark.asyncio
async def test_delete_project_and_cascade_to_test_request(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    test_lims_project: lims_models.Project,
    test_department: usr_models.Department,
    test_user: usr_models.User
):
    """
    [성공/무결성] 프로젝트 삭제 시 관련된 TestRequest도 연쇄적으로 삭제되는지(cascade) 테스트합니다.
    """
    print("\n--- Running test_delete_project_and_cascade_to_test_request ---")
    req_to_delete = await lims_crud.test_request.create(db_session, obj_in=lims_schemas.TestRequestCreate(
        request_date=date.today(),
        project_id=test_lims_project.id,
        department_id=test_department.id,
        requester_user_id=test_user.id,
        title="삭제될 프로젝트의 의뢰",
        requested_parameters={}
    ), current_user_id=test_user.id)
    req_id = req_to_delete.id

    delete_response = await admin_client.delete(f"/api/v1/lims/projects/{test_lims_project.id}")
    assert delete_response.status_code == 204

    deleted_req = await lims_crud.test_request.get(db_session, id=req_id)
    assert deleted_req is None


# =============================================================================
# 3. 채수 지점 (SamplingPoint) 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_sampling_point_success_admin(
    admin_client: AsyncClient,
    test_facility: loc_models.Facility
):
    """
    [성공] 관리자 권한으로 새로운 채수 지점을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_sampling_point_success_admin ---")
    data = {"code": "IN-01", "name": "1계열 유입", "facility_id": test_facility.id}
    response = await admin_client.post("/api/v1/lims/sampling_points", json=data)
    assert response.status_code == 201
    created_obj = response.json()
    assert created_obj["name"] == data["name"]
    assert created_obj["facility_id"] == data["facility_id"]


@pytest.mark.asyncio
async def test_create_sampling_point_unauthorized_user(
    authorized_client: AsyncClient,
    test_facility: loc_models.Facility
):
    """
    [실패/권한] 일반 사용자가 채수 지점 생성을 시도할 때 403 Forbidden을 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_sampling_point_unauthorized_user ---")
    data = {"code": "IN-02", "name": "권한없는 사용자 생성시도", "facility_id": test_facility.id}
    response = await authorized_client.post("/api/v1/lims/sampling_points", json=data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_sampling_point_nonexistent_facility(admin_client: AsyncClient):
    """
    [실패/FK] 존재하지 않는 시설(facility) ID로 채수 지점 생성 시 404 Not Found를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_sampling_point_nonexistent_facility ---")
    non_existent_facility_id = 9999
    data = {"code": "IN-03", "name": "유령 채수지점", "facility_id": non_existent_facility_id}
    response = await admin_client.post("/api/v1/lims/sampling_points", json=data)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_sampling_points_with_filter(
    client: AsyncClient,
    db_session: AsyncSession,
    test_facility: loc_models.Facility
):
    """
    [성공] facility_id로 채수 지점 목록을 필터링하여 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_sampling_points_with_filter ---")
    # 테스트 데이터 생성
    await lims_crud.sampling_point.create(db_session, obj_in=lims_schemas.SamplingPointCreate(
        code="FILTER-01", name="필터 테스트 지점 1", facility_id=test_facility.id
    ))

    # 다른 시설 생성 (필터링 대상이 아닌 데이터)
    other_facility = loc_models.Facility(code="OTHER", name="다른 처리장")
    db_session.add(other_facility)
    await db_session.commit()
    await lims_crud.sampling_point.create(db_session, obj_in=lims_schemas.SamplingPointCreate(
        code="FILTER-02", name="필터 테스트 지점 2", facility_id=other_facility.id
    ))

    response = await client.get(f"/api/v1/lims/sampling_points?facility_id={test_facility.id}")
    assert response.status_code == 200
    points = response.json()
    assert len(points) >= 1
    assert any(p["name"] == "필터 테스트 지점 1" and p["facility_id"] == test_facility.id for p in points)
    assert not any(p["name"] == "필터 테스트 지점 2" for p in points)


# =============================================================================
# 4. 시험 의뢰 (TestRequest) 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_test_request_with_auto_user_id(
    authorized_client: AsyncClient,
    test_lims_project: lims_models.Project,
    test_department: usr_models.Department,
    test_user: usr_models.User
):
    """
    [성공/로직] requester_user_id 없이 시험 의뢰 생성 시, 현재 로그인된 사용자로 자동 할당되는지 테스트합니다.
    """
    print("\n--- Running test_create_test_request_with_auto_user_id ---")
    request_data = {
        "request_date": str(date.today()),
        "project_id": test_lims_project.id,
        "department_id": test_department.id,
        "title": "사용자 ID 자동 할당 테스트",
        "requested_parameters": {"BOD5": True}
    }
    response = await authorized_client.post("/api/v1/lims/test_requests", json=request_data)
    assert response.status_code == 201
    created_request = response.json()
    assert created_request["requester_user_id"] == test_user.id


#  [신규] TestRequest 생성 시 유효성 검사 실패 테스트 추가
@pytest.mark.asyncio
async def test_create_test_request_with_invalid_parameter_code(
    authorized_client: AsyncClient,
    test_lims_project: lims_models.Project,
    test_department: usr_models.Department
):
    """
    [실패/유효성/신규] 등록되지 않은 파라미터 코드로 시험 의뢰 생성 시 400 에러를 받는지 테스트합니다.
    """
    print("\n--- Running test_create_test_request_with_invalid_parameter_code ---")
    request_data = {
        "request_date": str(date.today()),
        "project_id": test_lims_project.id,
        "department_id": test_department.id,
        "title": "잘못된 파라미터 코드 테스트",
        "requested_parameters": {"INVALID_CODE": True}
    }
    response = await authorized_client.post("/api/v1/lims/test_requests", json=request_data)
    assert response.status_code == 400
    assert "등록되지 않은 분석 항목 코드가 포함되어 있습니다" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_own_test_requests_as_user(
    authorized_client: AsyncClient,
    db_session: AsyncSession,
    test_user: usr_models.User,
    test_admin_user: usr_models.User,
    test_lims_project: lims_models.Project,
    test_department: usr_models.Department,
):
    """
    [성공/권한] 일반 사용자가 자신의 시험 의뢰 목록만 조회할 수 있는지 테스트합니다.
    """
    print("\n--- Running test_read_own_test_requests_as_user ---")

    await lims_crud.test_request.create(db_session, obj_in=lims_schemas.TestRequestCreate(
        request_date=date.today(),
        project_id=test_lims_project.id,
        department_id=test_department.id,
        title="내 의뢰",
        requested_parameters={}
    ), current_user_id=test_user.id)

    await lims_crud.test_request.create(db_session, obj_in=lims_schemas.TestRequestCreate(
        request_date=date.today(),
        project_id=test_lims_project.id,
        department_id=test_department.id,
        title="다른 사람 의뢰",
        requested_parameters={}
    ), current_user_id=test_admin_user.id)

    response = await authorized_client.get("/api/v1/lims/test_requests")
    assert response.status_code == 200
    requests = response.json()

    assert len(requests) == 1
    assert requests[0]["title"] == "내 의뢰"


@pytest.mark.asyncio
async def test_read_other_user_test_request_forbidden(
    authorized_client: AsyncClient,
    db_session: AsyncSession,
    test_admin_user: usr_models.User,
    test_lims_project: lims_models.Project,
    test_department: usr_models.Department
):
    """
    [실패/권한] 일반 사용자가 다른 사용자의 시험 의뢰를 ID로 직접 조회 시 403 Forbidden을 받는지 테스트합니다.
    """
    print("\n--- Running test_read_other_user_test_request_forbidden ---")

    #  다른 사용자(admin)의 시험 의뢰 데이터를 생성합니다.
    other_user_request = await lims_crud.test_request.create(db_session, obj_in=lims_schemas.TestRequestCreate(
        request_date=date.today(),
        project_id=test_lims_project.id,
        department_id=test_department.id,
        title="다른 사람 의뢰",
        requested_parameters={}
    ), current_user_id=test_admin_user.id)

    #  일반 사용자(authorized_client)로 다른 사용자의 의뢰를 ID로 조회합니다.
    response = await authorized_client.get(f"/api/v1/lims/test_requests/{other_user_request.id}")

    #  접근이 거부되어야 합니다 (403 Forbidden).
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_test_request_and_cascade_to_samples(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    test_test_request: lims_models.TestRequest,
    test_sampling_point: lims_models.SamplingPoint,
    test_sample_type: lims_models.SampleType,
    test_sample_container: lims_models.SampleContainer,
    test_user: usr_models.User,
):
    """
    [성공/무결성/신규] 시험 의뢰 삭제 시 관련된 Sample도 연쇄적으로 삭제되는지 테스트합니다.
    """
    print("\n--- Running test_delete_test_request_and_cascade_to_samples ---")
    #  삭제될 시험 의뢰에 대한 시료를 생성합니다.
    sample_to_delete = await lims_crud.sample.create(db_session, obj_in=lims_schemas.SampleCreate(
        request_id=test_test_request.id,
        sampling_point_id=test_sampling_point.id,
        sampling_date=date.today(),
        sample_type_id=test_sample_type.id,
        container_id=test_sample_container.id,
        parameters_for_analysis={"Test": True},
        collector_user_id=test_user.id,
    ))
    sample_id = sample_to_delete.id

    #  시험 의뢰를 삭제합니다.
    delete_response = await admin_client.delete(f"/api/v1/lims/test_requests/{test_test_request.id}")
    assert delete_response.status_code == 204

    #  연쇄 삭제된 시료가 조회되지 않는지 확인합니다.
    deleted_sample = await lims_crud.sample.get(db_session, id=sample_id)
    assert deleted_sample is None


# =============================================================================
# 5. 원 시료 (Sample) 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_sample_success(
    authorized_client: AsyncClient,
    test_test_request: lims_models.TestRequest,
    test_sampling_point: lims_models.SamplingPoint,
    test_sample_type: lims_models.SampleType,
    test_sample_container: lims_models.SampleContainer,
    test_user: usr_models.User
):
    """
    [성공] 인증된 사용자가 새로운 원 시료를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_sample_success ---")
    sample_data = {
        "request_id": test_test_request.id,
        "sampling_point_id": test_sampling_point.id,
        "sampling_date": str(date.today()),
        "sample_type_id": test_sample_type.id,
        "container_id": test_sample_container.id,
        "parameters_for_analysis": {"TN": True, "TP": True},
        "collector_user_id": test_user.id,
    }
    response = await authorized_client.post("/api/v1/lims/samples", json=sample_data)
    assert response.status_code == 201
    created_sample = response.json()
    assert created_sample["request_id"] == sample_data["request_id"]
    assert "sample_code" in created_sample and created_sample["sample_code"] is not None


@pytest.mark.asyncio
async def test_create_sample_nonexistent_request_id(
    authorized_client: AsyncClient,
    test_sampling_point: lims_models.SamplingPoint,
    test_sample_type: lims_models.SampleType,
    test_sample_container: lims_models.SampleContainer,
    test_user: usr_models.User
):
    """
    [실패/FK/신규] 존재하지 않는 시험의뢰(request_id)로 원 시료 생성 시 404를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_sample_nonexistent_request_id ---")
    non_existent_request_id = 9999
    sample_data = {
        "request_id": non_existent_request_id,
        "sampling_point_id": test_sampling_point.id,
        "sampling_date": str(date.today()),
        "sample_type_id": test_sample_type.id,
        "container_id": test_sample_container.id,
        "parameters_for_analysis": {"TN": True, "TP": True},
        "collector_user_id": test_user.id,
    }
    response = await authorized_client.post("/api/v1/lims/samples", json=sample_data)
    assert response.status_code == 404
    assert "Test request not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_sample_unauthorized_user(
    authorized_client: AsyncClient,
    test_sample: lims_models.Sample
):
    """
    [실패/권한] 일반 사용자가 원 시료 수정을 시도할 때 403 Forbidden을 반환하는지 테스트합니다.
    """
    print("\n--- Running test_update_sample_unauthorized_user ---")
    update_data = {"memo": "일반 사용자가 메모 수정 시도"}
    response = await authorized_client.put(f"/api/v1/lims/samples/{test_sample.id}", json=update_data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_sample_success_admin(
    admin_client: AsyncClient,
    test_sample: lims_models.Sample
):
    """
    [성공] 관리자 권한으로 원 시료를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_sample_success_admin ---")
    update_data = {"memo": "관리자가 메모 수정", "analysis_status": "Completed"}
    response = await admin_client.put(f"/api/v1/lims/samples/{test_sample.id}", json=update_data)
    assert response.status_code == 200
    updated_sample = response.json()
    assert updated_sample["memo"] == update_data["memo"]
    assert updated_sample["analysis_status"] == update_data["analysis_status"]


@pytest.mark.asyncio
async def test_delete_sample_and_cascade_to_aliquot(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    test_sample: lims_models.Sample,
    test_parameter: lims_models.Parameter,
    test_user: usr_models.User,
):
    """
    [성공/무결성/신규] 원 시료 삭제 시 관련된 AliquotSample도 연쇄적으로 삭제되는지 테스트합니다.
    """
    print("\n--- Running test_delete_sample_and_cascade_to_aliquot ---")
    aliquot_to_delete = await lims_crud.aliquot_sample.create(db_session, obj_in=lims_schemas.AliquotSampleCreate(
        parent_sample_id=test_sample.id,
        parameter_id=test_parameter.id,
        analyst_user_id=test_user.id
    ))
    aliquot_id = aliquot_to_delete.id

    #  원 시료를 삭제합니다.
    delete_response = await admin_client.delete(f"/api/v1/lims/samples/{test_sample.id}")
    assert delete_response.status_code == 204

    #  연쇄 삭제된 분할 시료가 조회되지 않는지 확인합니다.
    deleted_aliquot = await lims_crud.aliquot_sample.get(db_session, id=aliquot_id)
    assert deleted_aliquot is None


# =============================================================================
# 6. 분할 시료 (AliquotSample) 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_aliquot_sample_success(
    authorized_client: AsyncClient,
    test_sample: lims_models.Sample,
    test_parameter: lims_models.Parameter,
    test_user: usr_models.User,
):
    """
    [성공] 인증된 사용자가 새로운 분할 시료를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_aliquot_sample_success ---")
    aliquot_data = {
        "parent_sample_id": test_sample.id,
        "parameter_id": test_parameter.id,
        "analyst_user_id": test_user.id
    }
    response = await authorized_client.post("/api/v1/lims/aliquot_samples", json=aliquot_data)
    assert response.status_code == 201
    created_aliquot = response.json()
    assert created_aliquot["parent_sample_id"] == test_sample.id
    assert created_aliquot["parameter_id"] == test_parameter.id
    assert "aliquot_code" in created_aliquot and created_aliquot["aliquot_code"] is not None


@pytest.mark.asyncio
async def test_read_aliquot_samples_with_filter(
    authorized_client: AsyncClient,
    test_aliquot_sample: lims_models.AliquotSample,
):
    """
    [성공] parent_sample_id로 분할 시료 목록을 필터링하여 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_aliquot_samples_with_filter ---")
    parent_id = test_aliquot_sample.parent_sample_id
    response = await authorized_client.get(f"/api/v1/lims/aliquot_samples?parent_sample_id={parent_id}")
    assert response.status_code == 200
    aliquots = response.json()
    assert len(aliquots) >= 1
    assert all(a["parent_sample_id"] == parent_id for a in aliquots)


@pytest.mark.asyncio
async def test_update_aliquot_sample_status_triggers_parent_update(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    test_sample: lims_models.Sample,
    test_user: usr_models.User
):
    """
    [성공/로직] 모든 분할 시료 상태가 'Completed'일 때, 부모 시료의 상태가 'Completed'로 변경되는지 테스트합니다.
    """
    print("\n--- Running test_update_aliquot_sample_status_triggers_parent_update ---")
    #  두 개의 파라미터 생성
    param1 = await lims_crud.parameter.create(db_session, obj_in=lims_schemas.ParameterCreate(code="P1", name="p1", sort_order=1))
    param2 = await lims_crud.parameter.create(db_session, obj_in=lims_schemas.ParameterCreate(code="P2", name="p2", sort_order=2))

    #  두 개의 분할 시료 생성
    aliquot1 = await lims_crud.aliquot_sample.create(db_session, obj_in=lims_schemas.AliquotSampleCreate(
        parent_sample_id=test_sample.id, parameter_id=param1.id, analyst_user_id=test_user.id
    ))
    aliquot2 = await lims_crud.aliquot_sample.create(db_session, obj_in=lims_schemas.AliquotSampleCreate(
        parent_sample_id=test_sample.id, parameter_id=param2.id, analyst_user_id=test_user.id
    ))
    await db_session.refresh(test_sample)
    assert test_sample.analysis_status == 'Pending'  # 초기 상태

    #  첫 번째 분할 시료만 완료 -> 부모는 'In Progress'
    await admin_client.put(f"/api/v1/lims/aliquot_samples/{aliquot1.id}", json={"analysis_status": "Completed"})
    await db_session.refresh(test_sample)
    assert test_sample.analysis_status == 'In Progress'

    #  두 번째 분할 시료도 완료 -> 부모는 'Completed'
    await admin_client.put(f"/api/v1/lims/aliquot_samples/{aliquot2.id}", json={"analysis_status": "Completed"})
    await db_session.refresh(test_sample)
    assert test_sample.analysis_status == 'Completed'


# =============================================================================
# 7. 분석 결과 (AnalysisResult) 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_analysis_result_success_user(
    authorized_client: AsyncClient,
    test_analysis_result: lims_models.AnalysisResult  # conftest에서 생성됨
):
    """
    [성공] 분석 결과가 성공적으로 생성되는지 확인합니다. (픽스처 생성으로 검증)
    """
    print("\n--- Running test_create_analysis_result_success_user ---")
    assert test_analysis_result is not None
    assert test_analysis_result.id is not None
    assert test_analysis_result.result_value == 7.2  # conftest에 정의된 값


@pytest.mark.asyncio
async def test_create_analysis_result_duplicate_error(
    authorized_client: AsyncClient,
    test_analysis_result: lims_models.AnalysisResult
):
    """
    [실패/무결성] 동일한 (분할 시료, 파라미터, 워크시트 데이터) 조합으로 분석 결과 생성 시도 시 400 에러를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_analysis_result_duplicate_error ---")
    duplicate_data = {
        "aliquot_sample_id": test_analysis_result.aliquot_sample_id,
        "parameter_id": test_analysis_result.parameter_id,
        "worksheet_id": test_analysis_result.worksheet_id,
        "worksheet_data_id": test_analysis_result.worksheet_data_id,
        "result_value": 9.99,
        "unit": "mg/L",
        "analysis_date": str(date.today()),
        "analyst_user_id": test_analysis_result.analyst_user_id,
    }
    response = await authorized_client.post("/api/v1/lims/analysis_results", json=duplicate_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


# =============================================================================
# 8. 기타 엔티티 CRUD 기본 테스트
# =============================================================================

@pytest.mark.asyncio
async def test_crud_sample_container(admin_client: AsyncClient, authorized_client: AsyncClient):
    """
    [성공/실패] 시료 용기(SampleContainer)의 기본적인 CRUD 및 권한을 테스트합니다.
    """
    print("\n--- Running test_crud_sample_container ---")
    #  1. Admin으로 생성 (성공)
    container_data = {"code": 101, "name": "1L PE Bottle"}
    response = await admin_client.post("/api/v1/lims/sample_containers", json=container_data)
    assert response.status_code == 201
    created_container = response.json()
    container_id = created_container["id"]

    #  2. 일반 유저로 생성 (실패)
    response = await authorized_client.post("/api/v1/lims/sample_containers", json={"code": 102, "name": "실패 용기"})
    assert response.status_code == 403

    #  3. 모든 사용자가 조회 (성공)
    response = await authorized_client.get(f"/api/v1/lims/sample_containers/{container_id}")
    assert response.status_code == 200
    assert response.json()["name"] == container_data["name"]

    #  4. Admin으로 삭제 (성공)
    response = await admin_client.delete(f"/api/v1/lims/sample_containers/{container_id}")
    assert response.status_code == 204

    #  5. 삭제 확인 (실패 - 404)
    response = await admin_client.get(f"/api/v1/lims/sample_containers/{container_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_crud_weather_condition(admin_client: AsyncClient, authorized_client: AsyncClient):
    """
    [성공/실패/신규] 날씨(WeatherCondition)의 기본적인 CRUD 및 권한을 테스트합니다.
    """
    print("\n--- Running test_crud_weather_condition ---")
    #  1. Admin으로 생성 (성공)
    data = {"code": 10, "status": "폭설"}
    response = await admin_client.post("/api/v1/lims/weather_conditions", json=data)
    assert response.status_code == 201
    created_obj = response.json()
    obj_id = created_obj["id"]

    #  2. 일반 유저로 생성 (실패)
    response = await authorized_client.post("/api/v1/lims/weather_conditions", json={"code": 11, "status": "태풍"})
    assert response.status_code == 403

    #  3. 모든 사용자가 조회 (성공)
    response = await authorized_client.get(f"/api/v1/lims/weather_conditions/{obj_id}")
    assert response.status_code == 200
    assert response.json()["status"] == data["status"]

    #  4. Admin으로 삭제 (성공)
    response = await admin_client.delete(f"/api/v1/lims/weather_conditions/{obj_id}")
    assert response.status_code == 204

    #  5. 삭제 확인 (실패 - 404)
    response = await admin_client.get(f"/api/v1/lims/weather_conditions/{obj_id}")
    assert response.status_code == 404


# =============================================================================
# [신규] 9. 워크시트 (Worksheet) 및 워크시트 항목(WorksheetItem) 테스트
# =============================================================================
@pytest.mark.asyncio
class TestWorksheetAndItems:
    """워크시트 및 워크시트 항목 관련 테스트 그룹"""

    @pytest.fixture(scope="class")
    async def test_worksheet(self, db_session: AsyncSession) -> lims_models.Worksheet:
        """이 테스트 클래스에서 사용할 워크시트 픽스처"""
        ws = await lims_crud.worksheet.create(
            db_session,
            obj_in=lims_schemas.WorksheetCreate(code="WS-TEST", name="테스트용 워크시트")
        )
        return ws

    async def test_create_worksheet_item_success(
        self, admin_client: AsyncClient, test_worksheet: lims_models.Worksheet
    ):
        """[성공/신규] 워크시트 항목을 성공적으로 생성하는지 테스트합니다."""
        item_data = {
            "worksheet_id": test_worksheet.id,
            "code": "INITIAL_DO",
            "name": "초기 DO",
            "label": "초기 DO (mg/L)",
            "priority_order": 1,
            "type": 1,  # Numeric
        }
        response = await admin_client.post("/api/v1/lims/worksheet_items", json=item_data)
        assert response.status_code == 201
        assert response.json()["code"] == "INITIAL_DO"

    async def test_soft_delete_worksheet_item(
        self, admin_client: AsyncClient, db_session: AsyncSession, test_worksheet: lims_models.Worksheet
    ):
        """[성공/신규] 워크시트 항목이 논리적으로 삭제(비활성화)되는지 테스트합니다."""
        item = await lims_crud.worksheet_item.create(db_session, obj_in=lims_schemas.WorksheetItemCreate(
            worksheet_id=test_worksheet.id,
            code="ITEM_TO_DELETE",
            name="삭제될 아이템",
            label="삭제될 라벨",
            priority_order=10,
            type=1,
        ))
        assert item.is_active is True

        #  비활성화 요청
        response = await admin_client.delete(f"/api/v1/lims/worksheet_items/{item.id}")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        #  DB에서 직접 확인
        await db_session.refresh(item)


# =============================================================================
# [신규] 10. 사용자 정의 보기 (PrView) 테스트
# =============================================================================
@pytest.mark.asyncio
class TestPrView:
    """사용자 정의 보기 (PrView) 관련 테스트 그룹"""

    async def test_create_pr_view_success(
        self, authorized_client: AsyncClient, test_user: usr_models.User, test_facility: loc_models.Facility, test_sampling_point: lims_models.SamplingPoint, test_parameter: lims_models.Parameter
    ):
        """[성공/신규] 사용자가 자신의 보기 설정을 성공적으로 생성하는지 테스트합니다."""
        view_data = {
            "name": "나의 첫번째 보기",
            "facility_id": test_facility.id,
            "facility_ids": [test_facility.id],
            "sampling_point_ids": [test_sampling_point.id],
            "parameter_ids": [test_parameter.id],
            "memo": "자주 보는 항목 모음"
        }
        response = await authorized_client.post("/api/v1/lims/pr_views", json=view_data)
        assert response.status_code == 201
        created_view = response.json()
        assert created_view["name"] == "나의 첫번째 보기"
        assert created_view["user_id"] == test_user.id
        assert created_view["parameter_ids"] == [test_parameter.id]

    async def test_create_pr_view_with_invalid_fk(
        self, authorized_client: AsyncClient, test_facility: loc_models.Facility
    ):
        """[실패/FK/신규] 존재하지 않는 ID로 보기 설정 생성 시 404 에러를 받는지 테스트합니다."""
        invalid_param_id = 99999
        view_data = {
            "name": "잘못된 보기",
            "facility_id": test_facility.id,
            "parameter_ids": [invalid_param_id]
        }
        response = await authorized_client.post("/api/v1/lims/pr_views", json=view_data)
        assert response.status_code == 404
        assert f"Parameter with IDs [{invalid_param_id}] not found" in response.json()["detail"]

    async def test_user_can_only_manage_own_pr_view(
        self, authorized_client: AsyncClient, db_session: AsyncSession, test_admin_user: usr_models.User, test_facility: loc_models.Facility
    ):
        """[실패/권한/신규] 사용자가 다른 사람의 보기 설정을 조회/수정/삭제할 수 없는지 테스트합니다."""
        #  다른 사용자(admin)의 보기 설정 생성
        other_user_view = await lims_crud.pr_view.create(db_session, obj_in=lims_schemas.PrViewCreate(
            name="관리자용 보기",
            user_id=test_admin_user.id,
            facility_id=test_facility.id
        ), current_user_id=test_admin_user.id)

        #  1. 다른 사람의 보기 ID로 직접 조회 시도 -> 실패 (403)
        response_get = await authorized_client.get(f"/api/v1/lims/pr_views/{other_user_view.id}")
        assert response_get.status_code == 403

        #  2. 다른 사람의 보기 수정 시도 -> 실패 (403)
        response_put = await authorized_client.put(f"/api/v1/lims/pr_views/{other_user_view.id}", json={"memo": "수정 시도"})
        assert response_put.status_code == 403

        #  3. 다른 사람의 보기 삭제 시도 -> 실패 (403)
        response_delete = await authorized_client.delete(f"/api/v1/lims/pr_views/{other_user_view.id}")
        assert response_delete.status_code == 403
