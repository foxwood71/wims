# app/domains/lims/routers.py

"""
'lims' 도메인 (실험실 정보 관리 시스템 및 QA/QC) 관련 API 엔드포인트를 정의하는 모듈입니다.
"""
from typing import List, Optional
from datetime import date
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query

# 중앙 의존성 관리 모듈 임포트
from app.core import dependencies as deps
from app.domains.usr import models as usr_models
# from app.tasks import lims_tasks as lims_WsItem_task

# 도메인 관련 모듈 임포트
from . import crud as lims_crud
from . import schemas as lims_schemas

router = APIRouter(
    tags=["Laboratory Information Management (실험실 정보 관리)"],  # Swagger UI에 표시될 태그
    responses={404: {"description": "Not found"}},  # 이 라우터의 공통 응답 정의
)


# =============================================================================
# 1. 분석 항목 (Parameter) 라우터
# =============================================================================
@router.post("/parameters", response_model=lims_schemas.ParameterResponse, status_code=status.HTTP_201_CREATED, summary="새 분석 항목 생성")
async def create_parameter(
    parameter_in: lims_schemas.ParameterCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    """새로운 분석 항목을 생성합니다. 관리자 권한이 필요합니다."""
    return await lims_crud.parameter.create(db=db, obj_in=parameter_in)


@router.get("/parameters", response_model=List[lims_schemas.ParameterResponse], summary="모든 활성 분석 항목 조회")
async def read_parameters(
    skip: int = 0,
    limit: int = 100,
    analysis_group: Optional[str] = None,  # [추가]
    db: AsyncSession = Depends(deps.get_db_session)
):
    """
    모든 활성 분석 항목 목록을 조회합니다.
    `analysis_group` 쿼리 파라미터를 사용하여 특정 그룹의 항목만 필터링할 수 있습니다.
    """
    filter_kwargs = {"is_active": True}  # [수정] 항상 활성 항목만 조회
    if analysis_group:
        filter_kwargs["analysis_group"] = analysis_group

    return await lims_crud.parameter.get_multi(db, skip=skip, limit=limit, **filter_kwargs)


@router.get("/parameters/{parameter_id}", response_model=lims_schemas.ParameterResponse, summary="특정 분석 항목 조회")
async def read_parameter(
    parameter_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    """ID를 기준으로 특정 분석 항목을 조회합니다."""
    db_obj = await lims_crud.parameter.get(db=db, id=parameter_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found")
    return db_obj


@router.put("/parameters/{parameter_id}", response_model=lims_schemas.ParameterResponse, summary="분석 항목 업데이트")
async def update_parameter(
    parameter_id: int,
    parameter_in: lims_schemas.ParameterUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    """ID를 기준으로 분석 항목 정보를 업데이트합니다. 관리자 권한이 필요합니다."""
    db_obj = await lims_crud.parameter.get(db=db, id=parameter_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found")
    return await lims_crud.parameter.update(db=db, db_obj=db_obj, obj_in=parameter_in)


@router.delete(
    "/parameters/{parameter_id}",
    status_code=status.HTTP_200_OK,
    summary="분석 항목 비활성화 (Soft Delete)"
)
async def delete_parameter(
    parameter_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    """ID를 기준으로 분석 항목을 비활성화(Soft Delete)합니다."""
    db_obj = await lims_crud.parameter.get(db=db, id=parameter_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found")

    # is_active 상태를 업데이트하기 위한 스키마 객체 생성
    update_data = lims_schemas.ParameterUpdate(is_active=False)

    # 물리적 삭제 대신 is_active 플래그를 업데이트합니다.
    return await lims_crud.parameter.update(db=db, db_obj=db_obj, obj_in=update_data)


# =============================================================================
# 2. 프로젝트 (Project) 라우터
# =============================================================================
@router.post("/projects", response_model=lims_schemas.ProjectResponse, status_code=status.HTTP_201_CREATED, summary="새 프로젝트 생성")
async def create_project(
    project_in: lims_schemas.ProjectCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await lims_crud.project.create(db=db, obj_in=project_in)


@router.get("/projects", response_model=List[lims_schemas.ProjectResponse], summary="모든 프로젝트 조회")
async def read_projects(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.project.get_multi(db, skip=skip, limit=limit)


@router.get("/projects/{project_id}", response_model=lims_schemas.ProjectResponse, summary="특정 프로젝트 조회")
async def read_project(
    project_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.project.get(db, id=project_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return db_obj


@router.put("/projects/{project_id}", response_model=lims_schemas.ProjectResponse, summary="프로젝트 업데이트")
async def update_project(
    project_id: int,
    project_in: lims_schemas.ProjectUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.project.get(db, id=project_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await lims_crud.project.update(db, db_obj=db_obj, obj_in=project_in)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="프로젝트 삭제")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.project.get(db, id=project_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await lims_crud.project.delete(db, id=project_id)
    return


# =============================================================================
# 3. 시료 용기 (SampleContainer) 라우터
# =============================================================================
@router.post("/sample_containers", response_model=lims_schemas.SampleContainerResponse, status_code=status.HTTP_201_CREATED, summary="새 시료 용기 생성")
async def create_sample_container(
    container_in: lims_schemas.SampleContainerCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await lims_crud.sample_container.create(db, obj_in=container_in)


@router.get("/sample_containers", response_model=List[lims_schemas.SampleContainerResponse], summary="모든 시료 용기 조회")
async def read_sample_containers(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.sample_container.get_multi(db, skip=skip, limit=limit)


@router.get("/sample_containers/{container_id}", response_model=lims_schemas.SampleContainerResponse, summary="특정 시료 용기 조회")
async def read_sample_container(
    container_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.sample_container.get(db, id=container_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SampleContainer not found")
    return db_obj


@router.put("/sample_containers/{container_id}", response_model=lims_schemas.SampleContainerResponse, summary="시료 용기 업데이트")
async def update_sample_container(
    container_id: int,
    container_in: lims_schemas.SampleContainerUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sample_container.get(db, id=container_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SampleContainer not found")
    return await lims_crud.sample_container.update(db, db_obj=db_obj, obj_in=container_in)


@router.delete("/sample_containers/{container_id}", status_code=status.HTTP_204_NO_CONTENT, summary="시료 용기 삭제")
async def delete_sample_container(
    container_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sample_container.get(db, id=container_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SampleContainer not found")
    await lims_crud.sample_container.delete(db, id=container_id)
    return


# =============================================================================
# 4. 시료 유형 (SampleType) 라우터
# =============================================================================
@router.post("/sample_types", response_model=lims_schemas.SampleTypeResponse, status_code=status.HTTP_201_CREATED, summary="새 시료 유형 생성")
async def create_sample_type(
    type_in: lims_schemas.SampleTypeCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await lims_crud.sample_type.create(db, obj_in=type_in)


@router.get("/sample_types", response_model=List[lims_schemas.SampleTypeResponse], summary="모든 시료 유형 조회")
async def read_sample_types(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.sample_type.get_multi(db, skip=skip, limit=limit)


@router.get("/sample_types/{sample_type_id}", response_model=lims_schemas.SampleTypeResponse, summary="특정 시료 유형 조회")
async def read_sample_type(
    sample_type_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.sample_type.get(db, id=sample_type_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SampleType not found")
    return db_obj


@router.put("/sample_types/{sample_type_id}", response_model=lims_schemas.SampleTypeResponse, summary="시료 유형 업데이트")
async def update_sample_type(
    sample_type_id: int,
    type_in: lims_schemas.SampleTypeUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sample_type.get(db, id=sample_type_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SampleType not found")
    return await lims_crud.sample_type.update(db, db_obj=db_obj, obj_in=type_in)


@router.delete("/sample_types/{sample_type_id}", status_code=status.HTTP_204_NO_CONTENT, summary="시료 유형 삭제")
async def delete_sample_type(
    sample_type_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sample_type.get(db, id=sample_type_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SampleType not found")
    await lims_crud.sample_type.delete(db, id=sample_type_id)
    return


# =============================================================================
# 5. 채수 지점 (SamplingPoint) 라우터
# =============================================================================
@router.post("/sampling_points", response_model=lims_schemas.SamplingPointResponse, status_code=status.HTTP_201_CREATED, summary="새 채수 지점 생성")
async def create_sampling_point(
    point_in: lims_schemas.SamplingPointCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await lims_crud.sampling_point.create(db, obj_in=point_in)


@router.get("/sampling_points", response_model=List[lims_schemas.SamplingPointResponse], summary="모든 채수 지점 조회")
async def read_sampling_points(
    facility_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    filter_kwargs = {}
    if facility_id:
        filter_kwargs["facility_id"] = facility_id
    return await lims_crud.sampling_point.get_multi(db, skip=skip, limit=limit, **filter_kwargs)


@router.get("/sampling_points/{sampling_point_id}", response_model=lims_schemas.SamplingPointResponse, summary="특정 채수 지점 조회")
async def read_sampling_point(
    sampling_point_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.sampling_point.get(db, id=sampling_point_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SamplingPoint not found")
    return db_obj


@router.put("/sampling_points/{sampling_point_id}", response_model=lims_schemas.SamplingPointResponse, summary="채수 지점 업데이트")
async def update_sampling_point(
    sampling_point_id: int,
    point_in: lims_schemas.SamplingPointUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sampling_point.get(db, id=sampling_point_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SamplingPoint not found")
    return await lims_crud.sampling_point.update(db, db_obj=db_obj, obj_in=point_in)


@router.delete("/sampling_points/{sampling_point_id}", status_code=status.HTTP_204_NO_CONTENT, summary="채수 지점 삭제")
async def delete_sampling_point(
    sampling_point_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sampling_point.get(db, id=sampling_point_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SamplingPoint not found")
    await lims_crud.sampling_point.delete(db, id=sampling_point_id)
    return


# =============================================================================
# 6. 날씨 조건 (WeatherCondition) 라우터
# =============================================================================
@router.post("/weather_conditions", response_model=lims_schemas.WeatherConditionResponse, status_code=status.HTTP_201_CREATED, summary="새 날씨 조건 생성")
async def create_weather_condition(
    weather_in: lims_schemas.WeatherConditionCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await lims_crud.weather_condition.create(db, obj_in=weather_in)


@router.get("/weather_conditions", response_model=List[lims_schemas.WeatherConditionResponse], summary="모든 날씨 조건 조회")
async def read_weather_conditions(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.weather_condition.get_multi(db, skip=skip, limit=limit)


@router.get("/weather_conditions/{condition_id}", response_model=lims_schemas.WeatherConditionResponse, summary="특정 날씨 조건 조회")
async def read_weather_condition(
    condition_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.weather_condition.get(db, id=condition_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WeatherCondition not found")
    return db_obj


@router.put("/weather_conditions/{condition_id}", response_model=lims_schemas.WeatherConditionResponse, summary="날씨 조건 업데이트")
async def update_weather_condition(
    condition_id: int,
    weather_in: lims_schemas.WeatherConditionUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.weather_condition.get(db, id=condition_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WeatherCondition not found")
    return await lims_crud.weather_condition.update(db, db_obj=db_obj, obj_in=weather_in)


@router.delete("/weather_conditions/{condition_id}", status_code=status.HTTP_204_NO_CONTENT, summary="날씨 조건 삭제")
async def delete_weather_condition(
    condition_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.weather_condition.get(db, id=condition_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WeatherCondition not found")
    await lims_crud.weather_condition.delete(db, id=condition_id)
    return


# =============================================================================
# 7. 시험 의뢰 (TestRequest) 라우터
# =============================================================================
@router.post("/test_requests", response_model=lims_schemas.TestRequestResponse, status_code=status.HTTP_201_CREATED, summary="새 시험 의뢰 생성")
async def create_test_request(
    request_in: lims_schemas.TestRequestCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    return await lims_crud.test_request.create(db, obj_in=request_in, current_login_id=current_user.id)


@router.get(
    "/test_requests",
    response_model=List[lims_schemas.TestRequestResponse],
    summary="모든 시험 의뢰 조회"
)
async def read_test_requests(
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = Query(default=None, description="부서 ID (관리자/분석가용)"),
    start_date: date | None = Query(default=None, description="검색 시작일 (YYYY-MM-DD)"),
    end_date: date | None = Query(default=None, description="검색 종료일 (YYYY-MM-DD)")
):
    """
    시험 의뢰 목록을 조회합니다.

    - **department_id**: 특정 부서 ID로 필터링 (관리자/분석가 권한 필요)
    - **start_date**: 검색 시작일
    - **end_date**: 검색 종료일
    """
    # CRUD 함수에 전달할 파라미터를 딕셔너리로 구성
    crud_params = {
        "skip": skip,
        "limit": limit,
        "department_id": None,
        "start_date": start_date,
        "end_date": end_date,
    }

    # 권한에 따라 department_id 처리
    if current_user.role <= usr_models.UserRole.LAB_ANALYST:  # 수질분석자 이상 (관리자급)
        # 관리자급 사용자는 쿼리로 받은 department_id를 필터 조건으로 사용
        # 만약 department_id가 제공되지 않으면(None), 전체 부서 조회
        if department_id is not None:
            crud_params["department_id"] = department_id
    else:
        # 일반 사용자는 자신의 부서 데이터만 볼 수 있도록 강제
        # 쿼리로 department_id를 보내더라도 무시하고 자신의 부서 ID를 사용
        crud_params["department_id"] = current_user.department_id

    # 구성된 파라미터를 CRUD 함수에 한 번에 전달
    return await lims_crud.test_request.get_multi(db, **crud_params)


@router.get("/test_requests/{request_id}", response_model=lims_schemas.TestRequestResponse, summary="특정 시험 의뢰 조회")
async def read_test_request(
    request_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.test_request.get(db, id=request_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TestRequest not found")
    if current_user.role > 10 and db_obj.requester_login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return db_obj


@router.put("/test_requests/{request_id}", response_model=lims_schemas.TestRequestResponse, summary="시험 의뢰 업데이트")
async def update_test_request(
    request_id: int,
    request_in: lims_schemas.TestRequestUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.test_request.get(db, id=request_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TestRequest not found")
    if current_user.role > 10 and db_obj.requester_login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return await lims_crud.test_request.update(db, db_obj=db_obj, obj_in=request_in)


@router.delete("/test_requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT, summary="시험 의뢰 삭제")
async def delete_test_request(
    request_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.test_request.get(db, id=request_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TestRequest not found")
    await lims_crud.test_request.delete(db, id=request_id)
    return


# =============================================================================
# 8. 원 시료 (Sample) 라우터
# =============================================================================
@router.post("/samples", response_model=lims_schemas.SampleResponse, status_code=status.HTTP_201_CREATED, summary="새 원 시료 생성")
async def create_sample(
    sample_in: lims_schemas.SampleCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    return await lims_crud.sample.create(db=db, obj_in=sample_in)


@router.get("/samples", response_model=List[lims_schemas.SampleResponse], summary="모든 원 시료 조회")
async def read_samples(
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
    skip: int = 0, limit: int = 100,
):
    if current_user.role <= 10:
        return await lims_crud.sample.get_multi(db, skip=skip, limit=limit)
    return await lims_crud.sample.get_multi(db, collector_login_id=current_user.id, skip=skip, limit=limit)


@router.get("/samples/{sample_id}", response_model=lims_schemas.SampleResponse, summary="특정 원 시료 조회")
async def read_sample(
    sample_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.sample.get(db, id=sample_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    if current_user.role > 10 and db_obj.collector_login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return db_obj


@router.put("/samples/{sample_id}", response_model=lims_schemas.SampleResponse, summary="원 시료 업데이트")
async def update_sample(
    sample_id: int,
    sample_in: lims_schemas.SampleUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sample.get(db, id=sample_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    return await lims_crud.sample.update(db, db_obj=db_obj, obj_in=sample_in)


@router.delete("/samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT, summary="원 시료 삭제")
async def delete_sample(
    sample_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.sample.get(db, id=sample_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    await lims_crud.sample.delete(db, id=sample_id)
    return


# =============================================================================
# 9. 분할 시료 (AliquotSample) 라우터
# =============================================================================
@router.post("/aliquot_samples", response_model=lims_schemas.AliquotSampleResponse, status_code=status.HTTP_201_CREATED, summary="새 분할 시료 생성")
async def create_aliquot_sample(
    aliquot_in: lims_schemas.AliquotSampleCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    if not aliquot_in.analyst_login_id:
        aliquot_in.analyst_login_id = current_user.id
    return await lims_crud.aliquot_sample.create(db, obj_in=aliquot_in)


@router.get("/aliquot_samples", response_model=List[lims_schemas.AliquotSampleResponse], summary="모든 분할 시료 조회")
async def read_aliquot_samples(
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
    skip: int = 0, limit: int = 100,
):
    if current_user.role <= 10:
        return await lims_crud.aliquot_sample.get_multi(db, skip=skip, limit=limit)
    return await lims_crud.aliquot_sample.get_multi(db, analyst_login_id=current_user.id, skip=skip, limit=limit)


@router.get("/aliquot_samples/{aliquot_sample_id}", response_model=lims_schemas.AliquotSampleResponse, summary="특정 분할 시료 조회")
async def read_aliquot_sample(
    aliquot_sample_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.aliquot_sample.get(db, id=aliquot_sample_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AliquotSample not found")
    if current_user.role > 10 and db_obj.analyst_login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return db_obj


@router.put("/aliquot_samples/{aliquot_sample_id}", response_model=lims_schemas.AliquotSampleResponse, summary="분할 시료 업데이트")
async def update_aliquot_sample(
    aliquot_sample_id: int,
    aliquot_in: lims_schemas.AliquotSampleUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.aliquot_sample.get(db, id=aliquot_sample_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AliquotSample not found")
    return await lims_crud.aliquot_sample.update(db, db_obj=db_obj, obj_in=aliquot_in)


@router.delete("/aliquot_samples/{aliquot_sample_id}", status_code=status.HTTP_204_NO_CONTENT, summary="분할 시료 삭제")
async def delete_aliquot_sample(
    aliquot_sample_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.aliquot_sample.get(db, id=aliquot_sample_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AliquotSample not found")
    await lims_crud.aliquot_sample.delete(db, id=aliquot_sample_id)
    return


# =============================================================================
# 10. 워크시트 (Worksheet) 라우터
# =============================================================================
@router.post("/worksheets", response_model=lims_schemas.WorksheetResponse, status_code=status.HTTP_201_CREATED, summary="새 워크시트 생성")
async def create_worksheet(
    worksheet_in: lims_schemas.WorksheetCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await lims_crud.worksheet.create(db=db, obj_in=worksheet_in)


@router.get("/worksheets", response_model=List[lims_schemas.WorksheetResponse], summary="모든 워크시트 조회")
async def read_worksheets(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.worksheet.get_multi(db, skip=skip, limit=limit)


@router.get("/worksheets/{worksheet_id}", response_model=lims_schemas.WorksheetResponse, summary="특정 워크시트 조회")
async def read_worksheet(
    worksheet_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.worksheet.get(db, id=worksheet_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found")
    return db_obj


@router.put("/worksheets/{worksheet_id}", response_model=lims_schemas.WorksheetResponse, summary="워크시트 업데이트")
async def update_worksheet(
    worksheet_id: int,
    worksheet_in: lims_schemas.WorksheetUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.worksheet.get(db, id=worksheet_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found")
    return await lims_crud.worksheet.update(db, db_obj=db_obj, obj_in=worksheet_in)


@router.delete("/worksheets/{worksheet_id}", status_code=status.HTTP_204_NO_CONTENT, summary="워크시트 삭제")
async def delete_worksheet(
    worksheet_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.worksheet.get(db, id=worksheet_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found")
    await lims_crud.worksheet.delete(db, id=worksheet_id)
    return


# =============================================================================
# 11. 워크시트 항목 (WorksheetItem) 라우터
# =============================================================================
@router.post("/worksheet_items", response_model=lims_schemas.WorksheetItemResponse, status_code=status.HTTP_201_CREATED, summary="새 워크시트 항목 생성")
async def create_worksheet_item(
    request: Request,
    worksheet_item_in: lims_schemas.WorksheetItemCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    created_item = await lims_crud.worksheet_item.create(db=db, obj_in=worksheet_item_in)

    # <<< 보충 코드 시작 >>>
    # 관련된 과거 데이터가 있는지 확인
    existing_data = await lims_crud.worksheet_data.get_multi(
        db, limit=1, worksheet_id=created_item.worksheet_id
    )
    if existing_data:
        # 데이터가 있으면, 백그라운드 작업 예약
        task_queue_client = request.app.state.redis
        await task_queue_client.enqueue_job(
            "add_new_item_to_worksheet_data",
            created_item.worksheet_id,
            created_item.code,
        )
    # 데이터가 없으면, 동기화할 필요가 없으므로 아무 작업도 하지 않음
    # <<< 보충 코드 끝 >>>

    return created_item


@router.get("/worksheets/{worksheet_id}/items", response_model=List[lims_schemas.WorksheetItemResponse], summary="특정 워크시트의 모든 항목 조회")
async def read_worksheet_items_for_worksheet(
    worksheet_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
):
    """
    특정 워크시트 ID에 해당하는 모든 항목을 데이터베이스에서 직접 필터링하여 조회합니다.
    """
    #  애플리케이션 레벨 필터링 대신 DB에 직접 쿼리
    return await lims_crud.worksheet_item.get_multi(
        db, limit=None, worksheet_id=worksheet_id
    )


@router.get("/worksheet_items/{item_id}", response_model=lims_schemas.WorksheetItemResponse, summary="특정 워크시트 항목 조회")
async def read_worksheet_item(
    item_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.worksheet_item.get(db, id=item_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet item not found")
    return db_obj


@router.put("/worksheet_items/{item_id}", response_model=lims_schemas.WorksheetItemResponse, summary="워크시트 항목 정보 업데이트")
async def update_worksheet_item(
    request: Request,
    item_id: int,
    worksheet_item_update: lims_schemas.WorksheetItemUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_item = await lims_crud.worksheet_item.get(db, id=item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet item not found")

    original_code = db_item.code
    new_code = worksheet_item_update.code

    updated_item = await lims_crud.worksheet_item.update(
        db, db_obj=db_item, obj_in=worksheet_item_update
    )

    if new_code and original_code != new_code:
        # 관련된 과거 데이터가 있는지 확인
        existing_data = await lims_crud.worksheet_data.get_multi(
            db, limit=1, worksheet_id=updated_item.worksheet_id
        )
        if existing_data:
            # 데이터가 있으면, 백그라운드 작업 예약
            task_queue_client = request.app.state.redis
            await task_queue_client.enqueue_job(
                "sync_worksheet_item_code_change",
                updated_item.worksheet_id,
                original_code,
                new_code,
            )

    return updated_item


@router.delete("/worksheet_items/{item_id}", response_model=lims_schemas.WorksheetItemResponse, summary="워크시트 항목 비활성화 (Soft Delete)")
async def delete_worksheet_item(
    item_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    """
    항목을 DB에서 삭제하지 않고 is_active 플래그를 false로 업데이트합니다.
    과거 데이터 동기화 작업은 수행하지 않습니다.
    """
    db_item = await lims_crud.worksheet_item.get(db, id=item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet item not found")
    #  백그라운드 작업 호출 없이, 단순히 is_active 상태만 변경합니다.
    return await lims_crud.worksheet_item.update(
        db, db_obj=db_item, obj_in={"is_active": False}
    )


# =============================================================================
# 12. 워크시트 데이터 (WorksheetData) 라우터
# =============================================================================
@router.post("/worksheet_data", response_model=lims_schemas.WorksheetDataResponse, status_code=status.HTTP_201_CREATED, summary="새 워크시트 데이터 생성")
async def create_worksheet_data(
    data_in: lims_schemas.WorksheetDataCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    if not data_in.analyst_login_id:
        data_in.analyst_login_id = current_user.id
    return await lims_crud.worksheet_data.create(db, obj_in=data_in)


@router.get("/worksheet_data", response_model=List[lims_schemas.WorksheetDataResponse], summary="모든 워크시트 데이터 조회")
async def read_worksheet_data(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.worksheet_data.get_multi(db, skip=skip, limit=limit)


@router.get("/worksheet_data/{data_id}", response_model=lims_schemas.WorksheetDataResponse, summary="특정 워크시트 데이터 조회")
async def read_worksheet_data_by_id(
    data_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.worksheet_data.get(db, id=data_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorksheetData not found")
    return db_obj


@router.put("/worksheet_data/{data_id}", response_model=lims_schemas.WorksheetDataResponse, summary="워크시트 데이터 업데이트")
async def update_worksheet_data(
    data_id: int,
    data_in: lims_schemas.WorksheetDataUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.worksheet_data.get(db, id=data_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorksheetData not found")
    return await lims_crud.worksheet_data.update(db, db_obj=db_obj, obj_in=data_in)


@router.delete("/worksheet_data/{data_id}", status_code=status.HTTP_204_NO_CONTENT, summary="워크시트 데이터 삭제")
async def delete_worksheet_data(
    data_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.worksheet_data.get(db, id=data_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WorksheetData not found")
    await lims_crud.worksheet_data.delete(db, id=data_id)
    return


# =============================================================================
# 13. 분석 결과 (AnalysisResult) 라우터
# =============================================================================
@router.post("/analysis_results", response_model=lims_schemas.AnalysisResultResponse, status_code=status.HTTP_201_CREATED, summary="새 분석 결과 생성")
async def create_analysis_result(
    result_in: lims_schemas.AnalysisResultCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    if not result_in.analyst_login_id:
        result_in.analyst_login_id = current_user.id
    return await lims_crud.analysis_result.create(db, obj_in=result_in)


@router.get("/analysis_results", response_model=List[lims_schemas.AnalysisResultResponse], summary="모든 분석 결과 조회")
async def read_analysis_results(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.analysis_result.get_multi(db, skip=skip, limit=limit)


@router.get("/analysis_results/{result_id}", response_model=lims_schemas.AnalysisResultResponse, summary="특정 분석 결과 조회")
async def read_analysis_result(
    result_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.analysis_result.get(db, id=result_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AnalysisResult not found")
    return db_obj


@router.put("/analysis_results/{result_id}", response_model=lims_schemas.AnalysisResultResponse, summary="분석 결과 업데이트")
async def update_analysis_result(
    result_id: int,
    result_in: lims_schemas.AnalysisResultUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.analysis_result.get(db, id=result_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AnalysisResult not found")
    return await lims_crud.analysis_result.update(db, db_obj=db_obj, obj_in=result_in)


@router.delete("/analysis_results/{result_id}", status_code=status.HTTP_204_NO_CONTENT, summary="분석 결과 삭제")
async def delete_analysis_result(
    result_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.analysis_result.get(db, id=result_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AnalysisResult not found")
    await lims_crud.analysis_result.delete(db, id=result_id)
    return


# =============================================================================
# 14. 시험 의뢰 템플릿 (TestRequestTemplate) 라우터
# =============================================================================
@router.post("/test_request_templates", response_model=lims_schemas.TestRequestTemplateResponse, status_code=status.HTTP_201_CREATED, summary="새 시험 의뢰 템플릿 생성")
async def create_test_request_template(
    template_in: lims_schemas.TestRequestTemplateCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    return await lims_crud.test_request_template.create(db, obj_in=template_in, current_login_id=current_user.id)


@router.get("/test_request_templates", response_model=List[lims_schemas.TestRequestTemplateResponse], summary="사용자의 모든 시험 의뢰 템플릿 조회")
async def read_test_request_templates(
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
    skip: int = 0, limit: int = 100,
):
    if current_user.role <= 10:
        return await lims_crud.test_request_template.get_multi(db, skip=skip, limit=limit)
    return await lims_crud.test_request_template.get_multi(db, login_id=current_user.id, skip=skip, limit=limit)


@router.get("/test_request_templates/{template_id}", response_model=lims_schemas.TestRequestTemplateResponse, summary="특정 시험 의뢰 템플릿 조회")
async def read_test_request_template(
    template_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.test_request_template.get(db, id=template_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TestRequestTemplate not found")
    if current_user.role > 10 and db_obj.login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return db_obj


@router.put("/test_request_templates/{template_id}", response_model=lims_schemas.TestRequestTemplateResponse, summary="시험 의뢰 템플릿 업데이트")
async def update_test_request_template(
    template_id: int,
    template_in: lims_schemas.TestRequestTemplateUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.test_request_template.get(db, id=template_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TestRequestTemplate not found")
    if current_user.role > 10 and db_obj.login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return await lims_crud.test_request_template.update(db, db_obj=db_obj, obj_in=template_in)


@router.delete("/test_request_templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="시험 의뢰 템플릿 삭제")
async def delete_test_request_template(
    template_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.test_request_template.get(db, id=template_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TestRequestTemplate not found")
    if current_user.role > 10 and db_obj.login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    await lims_crud.test_request_template.delete(db, id=template_id)
    return


# =============================================================================
# 15. 표준 시료 (StandardSample) 라우터
# =============================================================================
@router.post("/standard_samples", response_model=lims_schemas.StandardSampleResponse, status_code=status.HTTP_201_CREATED, summary="새 표준 시료 생성")
async def create_standard_sample(
    sample_in: lims_schemas.StandardSampleCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await lims_crud.standard_sample.create(db, obj_in=sample_in)


@router.get("/standard_samples", response_model=List[lims_schemas.StandardSampleResponse], summary="모든 표준 시료 조회")
async def read_standard_samples(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.standard_sample.get_multi(db, skip=skip, limit=limit)


@router.get("/standard_samples/{sample_id}", response_model=lims_schemas.StandardSampleResponse, summary="특정 표준 시료 조회")
async def read_standard_sample(
    sample_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.standard_sample.get(db, id=sample_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="StandardSample not found")
    return db_obj


@router.put("/standard_samples/{sample_id}", response_model=lims_schemas.StandardSampleResponse, summary="표준 시료 업데이트")
async def update_standard_sample(
    sample_id: int,
    sample_in: lims_schemas.StandardSampleUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.standard_sample.get(db, id=sample_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="StandardSample not found")
    return await lims_crud.standard_sample.update(db, db_obj=db_obj, obj_in=sample_in)


@router.delete("/standard_samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT, summary="표준 시료 삭제")
async def delete_standard_sample(
    sample_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.standard_sample.get(db, id=sample_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="StandardSample not found")
    await lims_crud.standard_sample.delete(db, id=sample_id)
    return


# =============================================================================
# 16. 교정 기록 (CalibrationRecord) 라우터
# =============================================================================
@router.post("/calibration_records", response_model=lims_schemas.CalibrationRecordResponse, status_code=status.HTTP_201_CREATED, summary="새 교정 기록 생성")
async def create_calibration_record(
    record_in: lims_schemas.CalibrationRecordCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    if not record_in.calibrated_by_login_id:
        record_in.calibrated_by_login_id = current_user.id
    return await lims_crud.calibration_record.create(db, obj_in=record_in)


@router.get("/calibration_records", response_model=List[lims_schemas.CalibrationRecordResponse], summary="모든 교정 기록 조회")
async def read_calibration_records(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.calibration_record.get_multi(db, skip=skip, limit=limit)


@router.get("/calibration_records/{record_id}", response_model=lims_schemas.CalibrationRecordResponse, summary="특정 교정 기록 조회")
async def read_calibration_record(
    record_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.calibration_record.get(db, id=record_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="CalibrationRecord not found")
    return db_obj


@router.put("/calibration_records/{record_id}", response_model=lims_schemas.CalibrationRecordResponse, summary="교정 기록 업데이트")
async def update_calibration_record(
    record_id: int,
    record_in: lims_schemas.CalibrationRecordUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.calibration_record.get(db, id=record_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="CalibrationRecord not found")
    return await lims_crud.calibration_record.update(db, db_obj=db_obj, obj_in=record_in)


@router.delete("/calibration_records/{record_id}", status_code=status.HTTP_204_NO_CONTENT, summary="교정 기록 삭제")
async def delete_calibration_record(
    record_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.calibration_record.get(db, id=record_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="CalibrationRecord not found")
    await lims_crud.calibration_record.delete(db, id=record_id)
    return


# =============================================================================
# 17. QC 시료 결과 (QcSampleResult) 라우터
# =============================================================================
@router.post("/qc_sample_results", response_model=lims_schemas.QcSampleResultResponse, status_code=status.HTTP_201_CREATED, summary="새 QC 시료 결과 생성")
async def create_qc_sample_result(
    result_in: lims_schemas.QcSampleResultCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    if not result_in.analyst_login_id:
        result_in.analyst_login_id = current_user.id
    return await lims_crud.qc_sample_result.create(db, obj_in=result_in)


@router.get("/qc_sample_results", response_model=List[lims_schemas.QcSampleResultResponse], summary="모든 QC 시료 결과 조회")
async def read_qc_sample_results(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db_session)
):
    return await lims_crud.qc_sample_result.get_multi(db, skip=skip, limit=limit)


@router.get("/qc_sample_results/{result_id}", response_model=lims_schemas.QcSampleResultResponse, summary="특정 QC 시료 결과 조회")
async def read_qc_sample_result(
    result_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    db_obj = await lims_crud.qc_sample_result.get(db, id=result_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="QcSampleResult not found")
    return db_obj


@router.put("/qc_sample_results/{result_id}", response_model=lims_schemas.QcSampleResultResponse, summary="QC 시료 결과 업데이트")
async def update_qc_sample_result(
    result_id: int,
    result_in: lims_schemas.QcSampleResultUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.qc_sample_result.get(db, id=result_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="QcSampleResult not found")
    return await lims_crud.qc_sample_result.update(db, db_obj=db_obj, obj_in=result_in)


@router.delete("/qc_sample_results/{result_id}", status_code=status.HTTP_204_NO_CONTENT, summary="QC 시료 결과 삭제")
async def delete_qc_sample_result(
    result_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    db_obj = await lims_crud.qc_sample_result.get(db, id=result_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="QcSampleResult not found")
    await lims_crud.qc_sample_result.delete(db, id=result_id)
    return


# =============================================================================
# 18. 사용자 정의 프로젝트/결과 보기 (PrView) 라우터
# =============================================================================
@router.post("/pr_views", response_model=lims_schemas.PrViewResponse, status_code=status.HTTP_201_CREATED, summary="새 사용자 정의 보기 생성")
async def create_pr_view(
    view_in: lims_schemas.PrViewCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    return await lims_crud.pr_view.create(db, obj_in=view_in, current_login_id=current_user.id)


@router.get("/pr_views", response_model=List[lims_schemas.PrViewResponse], summary="사용자의 모든 정의 보기 조회")
async def read_pr_views(
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
    skip: int = 0, limit: int = 100,
):
    if current_user.role <= 10:
        return await lims_crud.pr_view.get_multi(db, skip=skip, limit=limit)
    return await lims_crud.pr_view.get_multi(db, login_id=current_user.id, skip=skip, limit=limit)


@router.get("/pr_views/{pr_view_id}", response_model=lims_schemas.PrViewResponse, summary="특정 사용자 정의 보기 조회")
async def read_pr_view(
    pr_view_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.pr_view.get(db, id=pr_view_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PrView not found")
    if current_user.role > 10 and db_obj.login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return db_obj


@router.put("/pr_views/{pr_view_id}", response_model=lims_schemas.PrViewResponse, summary="사용자 정의 보기 업데이트")
async def update_pr_view(
    pr_view_id: int,
    view_in: lims_schemas.PrViewUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.pr_view.get(db, id=pr_view_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PrView not found")
    if current_user.role > 10 and db_obj.login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return await lims_crud.pr_view.update(db, db_obj=db_obj, obj_in=view_in)


@router.delete("/pr_views/{pr_view_id}", status_code=status.HTTP_204_NO_CONTENT, summary="사용자 정의 보기 삭제")
async def delete_pr_view(
    pr_view_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    db_obj = await lims_crud.pr_view.get(db, id=pr_view_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PrView not found")
    if current_user.role > 10 and db_obj.login_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    await lims_crud.pr_view.delete(db, id=pr_view_id)
    return
