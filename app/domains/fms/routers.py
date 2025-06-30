# app/domains/fms/routers.py

"""
'fms' 도메인 (PostgreSQL 'fms' 스키마)의 API 엔드포인트를 정의하는 모듈입니다.

이 라우터는 설비 카테고리, 설비 스펙 정의, 설비, 설비 스펙 및 설비 이력 정보에 대한
CRUD 작업을 위한 HTTP 엔드포인트를 제공합니다.
FastAPI의 APIRouter를 사용하여 엔드포인트를 그룹화하고 관리하며,
의존성 주입을 통해 데이터베이스 세션 및 사용자 인증/권한을 처리합니다.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

#  핵심 의존성 (데이터베이스 세션, 사용자 인증 등)
from app.core.dependencies import get_db_session_dependency, get_current_active_user, get_current_admin_user
from app.domains.usr.models import User as UsrUser  # 사용자 모델 (권한 검증용)
from app.domains.usr import crud as usr_crud

#  'fms' 도메인의 CRUD, 모델, 스키마
from app.domains.fms import crud as fms_crud
from app.domains.fms import models as fms_models
from app.domains.fms import schemas as fms_schemas

#  다른 도메인의 CRUD (FK 유효성 검증용)
from app.domains.loc import crud as loc_crud
from app.domains.ven import crud as ven_crud


# 수정: router 선언에서 prefix 제거
router = APIRouter(
    tags=["Facility Management (설비 관리)"],
    responses={404: {"description": "Not found"}},
)


#  =============================================================================
#  1. fms.equipment_categories 엔드포인트 (설비 카테고리 관리)
#  =============================================================================
@router.post("/equipment_categories", response_model=fms_schemas.EquipmentCategoryResponse, status_code=status.HTTP_201_CREATED, summary="새 설비 카테고리 생성")
async def create_equipment_category(
    category_create: fms_schemas.EquipmentCategoryCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    새로운 설비 카테고리를 생성합니다. (관리자 권한 필요)
    - `name`: 카테고리 명칭 (고유, 필수)
    """
    return await fms_crud.equipment_category.create(db=db, obj_in=category_create)


@router.get("/equipment_categories", response_model=List[fms_schemas.EquipmentCategoryResponse], summary="모든 설비 카테고리 목록 조회")
async def read_equipment_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session_dependency)
):
    """
    모든 설비 카테고리 목록을 조회합니다.
    """
    return await fms_crud.equipment_category.get_multi(db, skip=skip, limit=limit)


@router.get("/equipment_categories/{category_id}", response_model=fms_schemas.EquipmentCategoryResponse, summary="특정 설비 카테고리 정보 조회")
async def read_equipment_category(
    category_id: int,
    db: Session = Depends(get_db_session_dependency)
):
    """
    특정 ID의 설비 카테고리 정보를 조회합니다.
    """
    db_category = await fms_crud.equipment_category.get(db, id=category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Equipment category not found")
    return db_category


@router.put("/equipment_categories/{category_id}", response_model=fms_schemas.EquipmentCategoryResponse, summary="설비 카테고리 정보 업데이트")
async def update_equipment_category(
    category_id: int,
    category_update: fms_schemas.EquipmentCategoryUpdate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 카테고리 정보를 업데이트합니다. (관리자 권한 필요)
    """
    db_category = await fms_crud.equipment_category.get(db, id=category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Equipment category not found")

    if category_update.name and category_update.name != db_category.name:
        existing_category_by_name = await fms_crud.equipment_category.get_by_name(db, name=category_update.name)
        if existing_category_by_name:
            raise HTTPException(status_code=400, detail="Another equipment category with this name already exists.")

    return await fms_crud.equipment_category.update(db=db, db_obj=db_category, obj_in=category_update)


@router.delete("/equipment_categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="설비 카테고리 삭제")
async def delete_equipment_category(
    category_id: int,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 카테고리를 삭제합니다. (관리자 권한 필요)
    """
    db_category = await fms_crud.equipment_category.delete(db, id=category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Equipment category not found")
    return {}


#  =============================================================================
#  2. fms.equipment_spec_definitions 엔드포인트 (설비 스펙 정의 관리)
#  =============================================================================
@router.post("/equipment_spec_definitions", response_model=fms_schemas.EquipmentSpecDefinitionResponse, status_code=status.HTTP_201_CREATED, summary="새 설비 스펙 정의 생성")
async def create_equipment_spec_definition(
    spec_def_create: fms_schemas.EquipmentSpecDefinitionCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    새로운 설비 스펙 정의 항목을 생성합니다. (관리자 권한 필요)
    """
    return await fms_crud.equipment_spec_definition.create(db=db, obj_in=spec_def_create)


@router.get("/equipment_spec_definitions", response_model=List[fms_schemas.EquipmentSpecDefinitionResponse], summary="모든 설비 스펙 정의 목록 조회")
async def read_equipment_spec_definitions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session_dependency)
):
    """
    모든 설비 스펙 정의 목록을 조회합니다.
    """
    return await fms_crud.equipment_spec_definition.get_multi(db, skip=skip, limit=limit)


@router.get("/equipment_spec_definitions/{spec_def_id}", response_model=fms_schemas.EquipmentSpecDefinitionResponse, summary="특정 설비 스펙 정의 정보 조회")
async def read_equipment_spec_definition(
    spec_def_id: int,
    db: Session = Depends(get_db_session_dependency)
):
    """
    특정 ID의 설비 스펙 정의 정보를 조회합니다.
    """
    db_spec_def = await fms_crud.equipment_spec_definition.get(db, id=spec_def_id)
    if db_spec_def is None:
        raise HTTPException(status_code=404, detail="Equipment spec definition not found")
    return db_spec_def


@router.put("/equipment_spec_definitions/{spec_def_id}", response_model=fms_schemas.EquipmentSpecDefinitionResponse, summary="설비 스펙 정의 정보 업데이트")
async def update_equipment_spec_definition(
    spec_def_id: int,
    spec_def_update: fms_schemas.EquipmentSpecDefinitionUpdate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 스펙 정의 정보를 업데이트합니다. (관리자 권한 필요)
    'name'(키)이 변경되면, 이 스펙을 사용하는 모든 설비의 스펙 정보가 자동으로 업데이트됩니다.
    """
    db_spec_def = await fms_crud.equipment_spec_definition.get(db, id=spec_def_id)
    if db_spec_def is None:
        raise HTTPException(status_code=404, detail="Equipment spec definition not found")

    if spec_def_update.name and spec_def_update.name != db_spec_def.name:
        existing_spec_def_by_name = await fms_crud.equipment_spec_definition.get_by_name(db, name=spec_def_update.name)
        if existing_spec_def_by_name:
            raise HTTPException(status_code=400, detail="Another equipment spec definition with this name already exists.")

    return await fms_crud.equipment_spec_definition.update(db=db, db_obj=db_spec_def, obj_in=spec_def_update)


@router.delete("/equipment_spec_definitions/{spec_def_id}", status_code=status.HTTP_204_NO_CONTENT, summary="설비 스펙 정의 삭제")
async def delete_equipment_spec_definition(
    spec_def_id: int,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 스펙 정의를 삭제합니다. (관리자 권한 필요)
    """
    db_spec_def = await fms_crud.equipment_spec_definition.delete(db, id=spec_def_id)
    if db_spec_def is None:
        raise HTTPException(status_code=404, detail="Equipment spec definition not found")
    return {}


#  =============================================================================
#  3. fms.equipment_category_spec_definitions 엔드포인트 (설비 카테고리 - 스펙 정의 연결 관리)
#  =============================================================================
@router.post("/equipment_category_spec_definitions", response_model=fms_schemas.EquipmentCategorySpecDefinitionResponse, status_code=status.HTTP_201_CREATED, summary="설비 카테고리에 스펙 정의 연결")
async def add_spec_definition_to_category(
    link_create: fms_schemas.EquipmentCategorySpecDefinitionCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 설비 카테고리에 스펙 정의를 연결합니다. (관리자 권한 필요)
    연결 시 해당 카테고리에 속한 모든 설비의 스펙 정보에 이 스펙이 `null` 값으로 추가됩니다.
    """
    if not await fms_crud.equipment_category.get(db, id=link_create.equipment_category_id):
        raise HTTPException(status_code=400, detail="Equipment category not found.")

    db_spec_def = await fms_crud.equipment_spec_definition.get(db, id=link_create.spec_definition_id)
    if not db_spec_def:
        raise HTTPException(status_code=400, detail="Equipment spec definition not found.")

    if await fms_crud.equipment_category_spec_definition.get_link(
        db, equipment_category_id=link_create.equipment_category_id, spec_definition_id=link_create.spec_definition_id
    ):
        raise HTTPException(status_code=400, detail="This spec definition is already linked to the equipment category.")

    return await fms_crud.equipment_category_spec_definition.add_spec_to_category_and_update_equipment(
        db=db, link_create=link_create, spec_name=db_spec_def.name
    )


@router.get("/equipment_categories/{category_id}/spec_definitions", response_model=List[fms_schemas.EquipmentSpecDefinitionResponse], summary="특정 설비 카테고리의 모든 스펙 정의 조회")
async def read_spec_definitions_for_category(
    category_id: int,
    db: Session = Depends(get_db_session_dependency)
):
    """
    특정 설비 카테고리에 연결된 모든 스펙 정의 목록을 조회합니다.
    """
    if not await fms_crud.equipment_category.get(db, id=category_id):
        raise HTTPException(status_code=404, detail="Equipment category not found")

    return await fms_crud.equipment_category_spec_definition.get_by_category_id(db, equipment_category_id=category_id)


@router.delete("/equipment_category_spec_definitions", status_code=status.HTTP_204_NO_CONTENT, summary="설비 카테고리와 스펙 정의 연결 해제")
async def remove_spec_definition_from_category(
    equipment_category_id: int,
    spec_definition_id: int,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 설비 카테고리와 스펙 정의 간의 연결을 해제합니다. (관리자 권한 필요)
    연결 해제 시 해당 카테고리에 속한 모든 설비의 스펙 정보에서 이 스펙이 제거됩니다.
    """
    db_spec_def = await fms_crud.equipment_spec_definition.get(db, id=spec_definition_id)
    if not db_spec_def:
        raise HTTPException(status_code=404, detail="Equipment spec definition not found.")

    db_link = await fms_crud.equipment_category_spec_definition.remove_spec_from_category_and_update_equipment(
        db,
        equipment_category_id=equipment_category_id,
        spec_definition_id=spec_definition_id,
        spec_name=db_spec_def.name
    )

    if db_link is None:
        raise HTTPException(status_code=404, detail="Equipment Category-Spec Definition link not found.")
    return {}


#  =============================================================================
#  4. fms.equipments 엔드포인트 (설비 관리)
#  =============================================================================
@router.post("/equipments", response_model=fms_schemas.EquipmentResponse, status_code=status.HTTP_201_CREATED, summary="새 설비 생성")
async def create_equipment(
    equipment_create: fms_schemas.EquipmentCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    새로운 설비를 생성합니다. (관리자 권한 필요)
    """
    if not await loc_crud.facility.get(db, id=equipment_create.facility_id):
        raise HTTPException(status_code=400, detail="Facility not found for the given ID.")

    if not await fms_crud.equipment_category.get(db, id=equipment_create.equipment_category_id):
        raise HTTPException(status_code=400, detail="Equipment category not found for the given ID.")

    if equipment_create.current_location_id:
        db_location = await loc_crud.location.get(db, id=equipment_create.current_location_id)
        if not db_location:
            raise HTTPException(status_code=400, detail="Location not found for the given ID.")
        if db_location.facility_id != equipment_create.facility_id:
            raise HTTPException(status_code=400, detail="Equipment's location must belong to its facility.")

    if equipment_create.serial_number:
        if await fms_crud.equipment.get_by_serial_number(db, serial_number=equipment_create.serial_number):
            raise HTTPException(status_code=400, detail="Equipment with this serial number already exists.")

    if equipment_create.asset_tag:
        if await fms_crud.equipment.get_by_asset_tag(db, asset_tag=equipment_create.asset_tag):
            raise HTTPException(status_code=400, detail="Equipment with this asset tag already exists.")

    return await fms_crud.equipment.create(db=db, obj_in=equipment_create)


@router.get("/equipments", response_model=List[fms_schemas.EquipmentResponse], summary="모든 설비 목록 조회")
async def read_equipments(
    facility_id: Optional[int] = None,
    location_id: Optional[int] = None,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session_dependency)
):
    """
    모든 설비 목록을 조회하거나, 필터링하여 조회합니다.
    """
    if facility_id:
        return await fms_crud.equipment.get_by_facility_id(db, facility_id=facility_id, skip=skip, limit=limit)
    if location_id:
        return await fms_crud.equipment.get_by_location_id(db, location_id=location_id, skip=skip, limit=limit)

    return await fms_crud.equipment.get_multi(db, skip=skip, limit=limit)


@router.get("/equipments/{equipment_id}", response_model=fms_schemas.EquipmentResponse, summary="특정 설비 정보 조회")
async def read_equipment(
    equipment_id: int,
    db: Session = Depends(get_db_session_dependency)
):
    """
    특정 ID의 설비 정보를 조회합니다.
    """
    db_equipment = await fms_crud.equipment.get(db, id=equipment_id)
    if db_equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return db_equipment


@router.put("/equipments/{equipment_id}", response_model=fms_schemas.EquipmentResponse, summary="설비 정보 업데이트")
async def update_equipment(
    equipment_id: int,
    equipment_update: fms_schemas.EquipmentUpdate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 정보를 업데이트합니다. (관리자 권한 필요)
    """
    db_equipment = await fms_crud.equipment.get(db, id=equipment_id)
    if db_equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")

    return await fms_crud.equipment.update(db=db, db_obj=db_equipment, obj_in=equipment_update)


@router.delete("/equipments/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="설비 삭제")
async def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비를 삭제합니다. (관리자 권한 필요)
    """
    db_equipment = await fms_crud.equipment.delete(db, id=equipment_id)
    if db_equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return {}


#  =============================================================================
#  5. fms.equipment_specs 엔드포인트 (설비 스펙 관리)
#  =============================================================================
@router.post("/equipment_specs", response_model=fms_schemas.EquipmentSpecResponse, status_code=status.HTTP_201_CREATED, summary="설비 스펙 생성/업데이트")
async def create_or_update_equipment_spec(
    spec_create_update: fms_schemas.EquipmentSpecCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 설비의 스펙 정보를 생성하거나 업데이트합니다.
    (설비당 하나의 스펙 레코드를 가집니다. 이미 존재하면 200 OK, 없으면 201 Created를 반환합니다)
    """
    if not await fms_crud.equipment.get(db, id=spec_create_update.equipment_id):
        raise HTTPException(status_code=400, detail="Equipment not found for the given ID.")

    db_spec = await fms_crud.equipment_spec.get_by_equipment_id(db, equipment_id=spec_create_update.equipment_id)

    if db_spec:
        updated_spec = await fms_crud.equipment_spec.update(db=db, db_obj=db_spec, obj_in=spec_create_update)
        return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(updated_spec))
    else:
        return await fms_crud.equipment_spec.create(db=db, obj_in=spec_create_update)


@router.get("/equipments/{equipment_id}/specs", response_model=fms_schemas.EquipmentSpecResponse, summary="특정 설비의 스펙 정보 조회")
async def read_equipment_specs(
    equipment_id: int,
    db: Session = Depends(get_db_session_dependency)
):
    """
    특정 설비의 스펙 정보를 조회합니다.
    """
    db_spec = await fms_crud.equipment_spec.get_by_equipment_id(db, equipment_id=equipment_id)
    if db_spec is None:
        raise HTTPException(status_code=404, detail="Equipment specs not found for this equipment.")
    return db_spec


@router.delete("/equipment_specs/{spec_id}", status_code=status.HTTP_204_NO_CONTENT, summary="설비 스펙 삭제")
async def delete_equipment_spec(
    spec_id: int,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 스펙을 삭제합니다. (관리자 권한 필요)
    """
    if not await fms_crud.equipment_spec.delete(db, id=spec_id):
        raise HTTPException(status_code=404, detail="Equipment spec not found")
    return {}


#  =============================================================================
#  6. fms.equipment_history 엔드포인트 (설비 이력 관리)
#  =============================================================================
@router.post("/equipment_history", response_model=fms_schemas.EquipmentHistoryResponse, status_code=status.HTTP_201_CREATED, summary="새 설비 이력 기록 생성")
async def create_equipment_history(
    history_create: fms_schemas.EquipmentHistoryCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_active_user)
):
    """
    새로운 설비 이력 기록을 생성합니다.
    """
    if not await fms_crud.equipment.get(db, id=history_create.equipment_id):
        raise HTTPException(status_code=400, detail="Equipment not found for the given ID.")

    if history_create.performed_by_user_id is None:
        history_create.performed_by_user_id = current_user.id
    elif not await usr_crud.user.get(db, id=history_create.performed_by_user_id):
        raise HTTPException(status_code=400, detail="Performed by user not found for the given ID.")

    if history_create.service_provider_vendor_id:
        if not await ven_crud.vendor.get(db, id=history_create.service_provider_vendor_id):
            raise HTTPException(status_code=400, detail="Service provider vendor not found for the given ID.")

    return await fms_crud.equipment_history.create(db=db, obj_in=history_create)


@router.get("/equipments/{equipment_id}/history", response_model=List[fms_schemas.EquipmentHistoryResponse], summary="특정 설비의 모든 이력 기록 조회")
async def read_equipment_history(
    equipment_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session_dependency)
):
    """
    특정 설비의 모든 이력 기록 목록을 조회합니다.
    """
    if not await fms_crud.equipment.get(db, id=equipment_id):
        raise HTTPException(status_code=404, detail="Equipment not found.")

    return await fms_crud.equipment_history.get_by_equipment_id_with_paging(db, equipment_id=equipment_id, skip=skip, limit=limit)


@router.get("/equipment_history/{history_id}", response_model=fms_schemas.EquipmentHistoryResponse, summary="특정 설비 이력 기록 조회")
async def read_single_equipment_history(
    history_id: int,
    db: Session = Depends(get_db_session_dependency)
):
    """
    특정 ID의 설비 이력 기록을 조회합니다.
    """
    db_history = await fms_crud.equipment_history.get(db, id=history_id)
    if db_history is None:
        raise HTTPException(status_code=404, detail="Equipment history record not found")
    return db_history


@router.put("/equipment_history/{history_id}", response_model=fms_schemas.EquipmentHistoryResponse, summary="설비 이력 기록 업데이트")
async def update_equipment_history(
    history_id: int,
    history_update: fms_schemas.EquipmentHistoryUpdate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 이력 기록을 업데이트합니다. (관리자 권한 필요)
    """
    db_history = await fms_crud.equipment_history.get(db, id=history_id)
    if db_history is None:
        raise HTTPException(status_code=404, detail="Equipment history record not found")

    return await fms_crud.equipment_history.update(db=db, db_obj=db_history, obj_in=history_update)


@router.delete("/equipment_history/{history_id}", status_code=status.HTTP_204_NO_CONTENT, summary="설비 이력 기록 삭제")
async def delete_equipment_history(
    history_id: int,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    특정 ID의 설비 이력 기록을 삭제합니다. (관리자 권한 필요)
    """
    if not await fms_crud.equipment_history.delete(db, id=history_id):
        raise HTTPException(status_code=404, detail="Equipment history record not found")
    return {}
