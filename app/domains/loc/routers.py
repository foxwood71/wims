# app/domains/loc/routers.py

"""
'loc' 도메인 (PostgreSQL 'loc' 스키마)의 API 엔드포인트를 정의하는 모듈입니다.

이 라우터는 시설(Facility), 장소 유형, 그리고 시설 내의 특정 장소 정보에 대한
CRUD 작업을 위한 HTTP 엔드포인트를 제공합니다.
FastAPI의 APIRouter를 사용하여 엔드포인트를 그룹화하고 관리하며,
의존성 주입을 통해 데이터베이스 세션 및 사용자 인증/권한을 처리합니다.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

# 핵심 의존성 (데이터베이스 세션, 사용자 인증 등)
from app.core import dependencies as deps
from app.domains.usr.models import User as UsrUser  # 사용자 모델 (권한 검증용)

# 'loc' 도메인의 CRUD, 모델, 스키마
from app.domains.loc import crud as loc_crud
# from app.domains.loc import models as loc_models
from app.domains.loc import schemas as loc_schemas

# 라우터 인스턴스 생성
router = APIRouter(
    tags=["Location Management (위치 관리)"],  # Swagger UI에 표시될 태그
    responses={404: {"description": "Not found"}},  # 이 라우터의 공통 응답 정의
)


# =============================================================================
# 1. loc.facilities 엔드포인트 (시설 관리)
# =============================================================================
@router.post("/facilities/", response_model=loc_schemas.FacilityRead, status_code=status.HTTP_201_CREATED, summary="새 시설 생성")
async def create_facility(
    facility_create: loc_schemas.FacilityCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 생성 가능
):
    """
    새로운 시설 정보를 생성합니다. (관리자 권한 필요)
    - `name`: 시설 현장 호칭 명칭 (필수)
    - `code`: 시설 코드 (고유)
    """
    db_facility = await loc_crud.facility.get_by_name(db, name=facility_create.name)
    if db_facility:
        raise HTTPException(status_code=400, detail="Facility with this name already exists")

    if facility_create.code:  # 코드가 제공된 경우 중복 확인
        db_facility = await loc_crud.facility.get_by_code(db, code=facility_create.code)
        if db_facility:
            raise HTTPException(status_code=400, detail="Facility with this code already exists")

    return await loc_crud.facility.create(db=db, obj_in=facility_create)


@router.get("/facilities/", response_model=List[loc_schemas.FacilityRead], summary="모든 시설 목록 조회")
async def read_facilities(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 시설 목록을 조회합니다.
    - `skip`: 건너뛸 레코드 수
    - `limit`: 가져올 최대 레코드 수
    """
    facilities = await loc_crud.facility.get_multi(db, skip=skip, limit=limit)
    return facilities


@router.get("/facilities/{facility_id}", response_model=loc_schemas.FacilityRead, summary="특정 시설 정보 조회")
async def read_facility(
    facility_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 시설 정보를 조회합니다.
    - `facility_id`: 조회할 시설의 고유 ID
    """
    db_facility = await loc_crud.facility.get(db, id=facility_id)
    if db_facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    return db_facility


@router.put("/facilities/{facility_id}", response_model=loc_schemas.FacilityRead, summary="시설 정보 업데이트")
async def update_facility(
    facility_id: int,
    facility_update: loc_schemas.FacilityUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 업데이트 가능
):
    """
    특정 ID의 시설 정보를 업데이트합니다. (관리자 권한 필요)
    - `facility_id`: 업데이트할 시설의 고유 ID
    - `facility_update`: 업데이트할 시설 정보 (부분 업데이트 가능)
    """
    db_facility = await loc_crud.facility.get(db, id=facility_id)
    if db_facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")

    # 이름 또는 코드 변경 시 중복 확인
    if facility_update.name and facility_update.name != db_facility.name:
        existing_facility = await loc_crud.facility.get_by_name(db, name=facility_update.name)
        if existing_facility:
            raise HTTPException(status_code=400, detail="Another facility with this name already exists.")

    if facility_update.code and facility_update.code != db_facility.code:
        existing_facility = await loc_crud.facility.get_by_code(db, code=facility_update.code)
        if existing_facility:
            raise HTTPException(status_code=400, detail="Another facility with this code already exists.")

    return await loc_crud.facility.update(db=db, db_obj=db_facility, obj_in=facility_update)


@router.delete("/facilities/{facility_id}", status_code=status.HTTP_204_NO_CONTENT, summary="시설 삭제")
async def delete_facility(
    facility_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 삭제 가능
):
    """
    특정 ID의 시설을 삭제합니다. (관리자 권한 필요)
    참고: 이 시설을 참조하는 하위 장소, 설비, 자재 배치, 채수 지점 등의 데이터가 있다면
    `ON DELETE RESTRICT` 또는 `ON DELETE CASCADE` 정책에 따라 삭제가 실패하거나 연쇄 삭제될 수 있습니다.
    - `facility_id`: 삭제할 시설의 고유 ID
    """
    db_facility = await loc_crud.facility.remove(db, id=facility_id)
    if db_facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    return {}


# =============================================================================
# 2. loc.location_types 엔드포인트 (장소 유형 관리)
# =============================================================================
@router.post("/location_types/", response_model=loc_schemas.LocationTypeRead, status_code=status.HTTP_201_CREATED, summary="새 장소 유형 생성")
async def create_location_type(
    location_type_create: loc_schemas.LocationTypeCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 생성 가능
):
    """
    새로운 장소 유형을 생성합니다. (관리자 권한 필요)
    - `name`: 장소 유형 명칭 (고유, 필수)
    """
    db_location_type = await loc_crud.location_type.get_by_name(db, name=location_type_create.name)
    if db_location_type:
        raise HTTPException(status_code=400, detail="Location type with this name already exists")

    return await loc_crud.location_type.create(db=db, obj_in=location_type_create)


@router.get("/location_types/", response_model=List[loc_schemas.LocationTypeRead], summary="모든 장소 유형 목록 조회")
async def read_location_types(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 장소 유형의 목록을 조회합니다.
    - `skip`: 건너뛸 레코드 수
    - `limit`: 가져올 최대 레코드 수
    """
    location_types = await loc_crud.location_type.get_multi(db, skip=skip, limit=limit)
    return location_types


@router.get("/location_types/{location_type_id}", response_model=loc_schemas.LocationTypeRead, summary="특정 장소 유형 정보 조회")
async def read_location_type(
    location_type_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 장소 유형 정보를 조회합니다.
    - `location_type_id`: 조회할 장소 유형의 고유 ID
    """
    db_location_type = await loc_crud.location_type.get(db, id=location_type_id)
    if db_location_type is None:
        raise HTTPException(status_code=404, detail="Location type not found")
    return db_location_type


@router.put("/location_types/{location_type_id}", response_model=loc_schemas.LocationTypeRead, summary="장소 유형 정보 업데이트")
async def update_location_type(
    location_type_id: int,
    location_type_update: loc_schemas.LocationTypeUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 업데이트 가능
):
    """
    특정 ID의 장소 유형 정보를 업데이트합니다. (관리자 권한 필요)
    - `location_type_id`: 업데이트할 장소 유형의 고유 ID
    - `location_type_update`: 업데이트할 장소 유형 정보 (부분 업데이트 가능)
    """
    db_location_type = await loc_crud.location_type.get(db, id=location_type_id)
    if db_location_type is None:
        raise HTTPException(status_code=404, detail="Location type not found")

    # 이름 변경 시 중복 확인
    if location_type_update.name and location_type_update.name != db_location_type.name:
        existing_type_by_name = await loc_crud.location_type.get_by_name(db, name=location_type_update.name)
        if existing_type_by_name:
            raise HTTPException(status_code=400, detail="Another location type with this name already exists.")

    return await loc_crud.location_type.update(db=db, db_obj=db_location_type, obj_in=location_type_update)


@router.delete("/location_types/{location_type_id}", status_code=status.HTTP_204_NO_CONTENT, summary="장소 유형 삭제")
async def delete_location_type(
    location_type_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 삭제 가능
):
    """
    특정 ID의 장소 유형을 삭제합니다. (관리자 권한 필요)
    참고: 이 유형을 참조하는 장소 데이터가 있다면 `ON DELETE RESTRICT` 정책에 따라 삭제가 실패합니다.
    - `location_type_id`: 삭제할 장소 유형의 고유 ID
    """
    db_location_type = await loc_crud.location_type.remove(db, id=location_type_id)
    if db_location_type is None:
        raise HTTPException(status_code=404, detail="Location type not found")
    return {}


# =============================================================================
# 3. loc.locations 엔드포인트 (시설 내 장소 관리)
# =============================================================================
@router.post("/locations/", response_model=loc_schemas.LocationRead, status_code=status.HTTP_201_CREATED, summary="새 장소 생성")
async def create_location(
    location_create: loc_schemas.LocationCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 생성 가능
):
    """
    새로운 장소 정보를 생성합니다. (관리자 권한 필요)
    - `facility_id`: 소속 시설 ID (필수)
    - `name`: 장소 현장 호칭 명칭 (필수)
    - `parent_location_id`: 상위 장소 ID (선택 사항, 계층 구조)
    """
    # 관련 시설 존재 여부 확인
    db_facility = await loc_crud.facility.get(db, id=location_create.facility_id)
    if not db_facility:
        raise HTTPException(status_code=400, detail="Facility not found for the given ID")

    # 관련 장소 유형 존재 여부 확인
    if location_create.location_type_id:
        db_location_type = await loc_crud.location_type.get(db, id=location_create.location_type_id)
        if not db_location_type:
            raise HTTPException(status_code=400, detail="Location type not found for the given ID")

    # 상위 장소 존재 여부 확인 및 동일 시설 내 상위 장소인지 확인
    if location_create.parent_location_id:
        db_parent_location = await loc_crud.location.get(db, id=location_create.parent_location_id)
        if not db_parent_location:
            raise HTTPException(status_code=400, detail="Parent location not found for the given ID")
        if db_parent_location.facility_id != location_create.facility_id:
            raise HTTPException(status_code=400, detail="Parent location must belong to the same facility.")

    # facility_id, name, parent_location_id 조합의 UNIQUE 제약 조건 확인
    db_location = await loc_crud.location.get_by_name_and_facility(
        db,
        facility_id=location_create.facility_id,
        name=location_create.name,
        parent_location_id=location_create.parent_location_id
    )
    if db_location:
        raise HTTPException(status_code=400, detail="Location with this name and parent already exists in this facility.")
    return await loc_crud.location.create(db=db, obj_in=location_create)


@router.get("/locations/", response_model=List[loc_schemas.LocationRead], summary="모든 장소 목록 조회")
async def read_locations(
    facility_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 장소 또는 특정 시설에 속한 장소 목록을 조회합니다.
    - `facility_id`: 특정 시설의 장소만 필터링 (선택 사항)
    - `skip`: 건너뛸 레코드 수
    - `limit`: 가져올 최대 레코드 수
    """
    if facility_id:
        # 특정 시설 존재 여부 확인
        db_facility = await loc_crud.facility.get(db, id=facility_id)
        if not db_facility:
            raise HTTPException(status_code=404, detail="Facility not found for the given facility_id.")
        locations = await loc_crud.location.get_by_facility(db, facility_id=facility_id, skip=skip, limit=limit)
    else:
        locations = await loc_crud.location.get_multi(db, skip=skip, limit=limit)
    return locations


@router.get("/locations/{location_id}", response_model=loc_schemas.LocationRead, summary="특정 장소 정보 조회")
async def read_location(
    location_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 장소 정보를 조회합니다.
    - `location_id`: 조회할 장소의 고유 ID
    """
    db_location = await loc_crud.location.get(db, id=location_id)
    if db_location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return db_location


@router.put("/locations/{location_id}", response_model=loc_schemas.LocationRead, summary="장소 정보 업데이트")
async def update_location(
    location_id: int,
    location_update: loc_schemas.LocationUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 업데이트 가능
):
    """
    특정 ID의 장소 정보를 업데이트합니다. (관리자 권한 필요)
    - `location_id`: 업데이트할 장소의 고유 ID
    - `location_update`: 업데이트할 장소 정보 (부분 업데이트 가능)
    """
    db_location = await loc_crud.location.get(db, id=location_id)
    if db_location is None:
        raise HTTPException(status_code=404, detail="Location not found")

    # facility_id 변경 시 해당 시설 존재 여부 확인
    if location_update.facility_id and location_update.facility_id != db_location.facility_id:
        db_facility = await loc_crud.facility.get(db, id=location_update.facility_id)
        if not db_facility:
            raise HTTPException(status_code=400, detail="New facility not found for the given ID")

    # location_type_id 변경 시 해당 유형 존재 여부 확인
    if location_update.location_type_id and location_update.location_type_id != db_location.location_type_id:
        db_location_type = await loc_crud.location_type.get(db, id=location_update.location_type_id)
        if not db_location_type:
            raise HTTPException(status_code=400, detail="New location type not found for the given ID")

    # parent_location_id 변경 시 해당 상위 장소 존재 여부 확인 및 동일 시설 내인지 확인
    if location_update.parent_location_id is not None:
        if location_update.parent_location_id != db_location.parent_location_id:
            if location_update.parent_location_id:
                db_parent_location = await loc_crud.location.get(db, id=location_update.parent_location_id)
                if not db_parent_location:
                    raise HTTPException(status_code=400, detail="New parent location not found for the given ID")

                target_facility_id = location_update.facility_id if location_update.facility_id else db_location.facility_id
                if db_parent_location.facility_id != target_facility_id:
                    raise HTTPException(status_code=400, detail="Parent location must belong to the same facility.")

    # name, facility_id, parent_location_id 조합의 UNIQUE 제약 조건 확인
    target_facility_id = location_update.facility_id if location_update.facility_id else db_location.facility_id
    target_name = location_update.name if location_update.name else db_location.name
    target_parent_id = location_update.parent_location_id if location_update.parent_location_id is not None else db_location.parent_location_id

    if (target_facility_id != db_location.facility_id
            or target_name != db_location.name
            or target_parent_id != db_location.parent_location_id):

        existing_location_with_new_params = await loc_crud.location.get_by_name_and_facility(
            db,
            facility_id=target_facility_id,
            name=target_name,
            parent_location_id=target_parent_id
        )
        if existing_location_with_new_params and existing_location_with_new_params.id != location_id:
            raise HTTPException(status_code=400, detail="Another location with this name and parent already exists in the target facility.")

    return await loc_crud.location.update(db=db, db_obj=db_location, obj_in=location_update)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT, summary="장소 삭제")
async def delete_location(
    location_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 삭제 가능
):
    """
    특정 ID의 장소를 삭제합니다. (관리자 권한 필요)
    참고: 이 장소를 참조하는 하위 장소, 설비, 자재 배치, 시료 등의 데이터가 있다면
    `ON DELETE CASCADE` 또는 `ON DELETE RESTRICT` 정책에 따라 삭제가 연쇄되거나 실패할 수 있습니다.
    - `location_id`: 삭제할 장소의 고유 ID
    """
    db_location = await loc_crud.location.remove(db, id=location_id)
    if db_location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return {}
