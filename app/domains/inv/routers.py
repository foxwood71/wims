# app/domains/inv/routers.py

"""
'inv' 도메인 (PostgreSQL 'inv' 스키마)의 API 엔드포인트를 정의하는 모듈입니다.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

#  의존성 및 다른 도메인 모듈 임포트
from app.core.dependencies import get_db_session_dependency, get_current_active_user, get_current_admin_user
from app.domains.usr.models import User as UsrUser
from app.domains.inv import crud as inv_crud, models as inv_models, schemas as inv_schemas

router = APIRouter(
    tags=["Inventory Management (자재 관리)"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# 1. inv.material_categories 엔드포인트
# =============================================================================
@router.post("/material_categories", response_model=inv_schemas.MaterialCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_material_category(
    category_create: inv_schemas.MaterialCategoryCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    if await inv_crud.material_category.get_by_code(db, code=category_create.code):
        raise HTTPException(status_code=400, detail="Material category with this code already exists.")
    return await inv_crud.material_category.create(db=db, obj_in=category_create)


@router.get("/material_categories", response_model=List[inv_schemas.MaterialCategoryResponse])
async def read_material_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session_dependency)):
    return await inv_crud.material_category.get_multi(db, skip=skip, limit=limit)


@router.get("/material_categories/{category_code}", response_model=inv_schemas.MaterialCategoryResponse)
async def read_material_category(category_code: str, db: Session = Depends(get_db_session_dependency)):
    db_category = await inv_crud.material_category.get_by_code(db, code=category_code)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Material category not found.")
    return db_category


@router.put("/material_categories/{category_code}", response_model=inv_schemas.MaterialCategoryResponse)
async def update_material_category(
    category_code: str,
    category_update: inv_schemas.MaterialCategoryUpdate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    db_category = await inv_crud.material_category.get_by_code(db, code=category_code)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Material category not found.")
    return await inv_crud.material_category.update(db=db, db_obj=db_category, obj_in=category_update)


@router.delete("/material_categories/{category_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_category(category_code: str, db: Session = Depends(get_db_session_dependency), current_user: UsrUser = Depends(get_current_admin_user)):
    db_category = await inv_crud.material_category.get_by_code(db, code=category_code)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Material category not found.")

    # [수정] remove -> delete
    await inv_crud.material_category.delete(db, id=db_category.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 2. inv.material_spec_definitions 엔드포인트
# =============================================================================
# @router.post("/material_spec_definitions", response_model=inv_schemas.MaterialSpecDefinitionResponse, status_code=status.HTTP_201_CREATED)
# async def create_material_spec_definition(
#     spec_def_create: inv_schemas.MaterialSpecDefinitionCreate,
#     db: Session = Depends(get_db_session_dependency),
#     current_user: UsrUser = Depends(get_current_admin_user)
# ):
#     return await inv_crud.material_spec_definition.create(db=db, obj_in=spec_def_create)

@router.post("/material_spec_definitions", response_model=inv_schemas.MaterialSpecDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_material_spec_definition(
    spec_def_create: inv_schemas.MaterialSpecDefinitionCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """새로운 자재 스펙 정의를 생성합니다. 관리자 권한이 필요합니다."""
    return await inv_crud.material_spec_definition.create(db=db, obj_in=spec_def_create)


# @router.put("/material_spec_definitions/{spec_def_id}", response_model=inv_schemas.MaterialSpecDefinitionResponse)
# async def update_material_spec_definition(
#     spec_def_id: int,
#     spec_def_update: inv_schemas.MaterialSpecDefinitionUpdate,
#     db: Session = Depends(get_db_session_dependency),
#     current_user: UsrUser = Depends(get_current_admin_user)
# ):
#     """
#     [신규] 자재 스펙 정의를 업데이트합니다.
#     이름(name)이 변경되면 관련된 모든 자재의 스펙 키가 자동으로 업데이트됩니다.
#     """
#     db_spec_def = await inv_crud.material_spec_definition.get(db, id=spec_def_id)
#     if not db_spec_def:
#         raise HTTPException(status_code=404, detail="Material spec definition not found.")

#     # 이름 중복 확인 (새로운 이름으로 변경 시)
#     if spec_def_update.name and spec_def_update.name != db_spec_def.name:
#         existing_spec_def = await inv_crud.material_spec_definition.get_by_name(db, name=spec_def_update.name)
#         if existing_spec_def:
#             raise HTTPException(status_code=400, detail="A spec definition with this name already exists.")

#     return await inv_crud.material_spec_definition.update(db=db, db_obj=db_spec_def, obj_in=spec_def_update)

@router.put("/material_spec_definitions/{spec_def_id}", response_model=inv_schemas.MaterialSpecDefinitionResponse)
async def update_material_spec_definition(
    spec_def_id: int,
    spec_def_update: inv_schemas.MaterialSpecDefinitionUpdate,
    request: Request,  # Request 객체 주입
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """
    자재 스펙 정의를 업데이트합니다.
    이름(name)이 변경되면 관련된 모든 자재의 스펙 키가 자동으로 업데이트됩니다.
    관리자 권한이 필요합니다.
    """
    db_spec_def = await inv_crud.material_spec_definition.get(db, id=spec_def_id)
    if not db_spec_def:
        raise HTTPException(status_code=404, detail="Material spec definition not found.")

    # 이름 중복 확인 (새로운 이름으로 변경 시)
    if spec_def_update.name and spec_def_update.name != db_spec_def.name:
        existing_spec_def = await inv_crud.material_spec_definition.get_by_name(db, name=spec_def_update.name)
        if existing_spec_def and existing_spec_def.id != db_spec_def.id:  # 자기 자신 제외
            raise HTTPException(status_code=400, detail="A spec definition with this name already exists.")

    #  ARQ Redis 클라이언트를 CRUD 메서드로 전달
    return await inv_crud.material_spec_definition.update(
        db=db, db_obj=db_spec_def, obj_in=spec_def_update, arq_redis_pool=request.app.state.redis
    )


@router.delete("/material_spec_definitions/{spec_def_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_spec_definition(
    spec_def_id: int,
    request: Request,  # Request 객체 주입
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """자재 스펙 정의를 삭제합니다. 관리자 권한이 필요합니다."""
    db_spec_def = await inv_crud.material_spec_definition.get(db, id=spec_def_id)
    if not db_spec_def:
        raise HTTPException(status_code=404, detail="Material spec definition not found.")

    #  ARQ Redis 클라이언트를 CRUD 메서드로 전달
    await inv_crud.material_spec_definition.remove(
        db=db, id=spec_def_id, arq_redis_pool=request.app.state.redis
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 3. inv.material_category_spec_definitions 엔드포인트
# =============================================================================
# @router.post("/material_category_spec_definitions", response_model=inv_schemas.MaterialCategorySpecDefinitionResponse, status_code=status.HTTP_201_CREATED)
# async def add_spec_definition_to_material_category(
#     link_create: inv_schemas.MaterialCategorySpecDefinitionCreate,
#     db: Session = Depends(get_db_session_dependency),
#     current_user: UsrUser = Depends(get_current_admin_user)
# ):
#     """카테고리에 스펙 정의를 연결하고, 관련된 모든 자재의 스펙에 해당 키를 null 값으로 자동 추가합니다."""
#     db_category = await inv_crud.material_category.get(db, id=link_create.material_category_id)
#     if not db_category:
#         raise HTTPException(status_code=404, detail="Material category not found.")

#     db_spec_def = await inv_crud.material_spec_definition.get(db, id=link_create.spec_definition_id)
#     if not db_spec_def:
#         raise HTTPException(status_code=404, detail="Material spec definition not found.")

#     created_link = await inv_crud.material_category_spec_definition.create(db=db, obj_in=link_create)

#     stmt = (
#         select(inv_models.Material)
#         .where(inv_models.Material.material_category_id == link_create.material_category_id)
#         .options(selectinload(inv_models.Material.specs))
#     )
#     materials = (await db.execute(stmt)).scalars().all()

#     for material in materials:
#         if material.specs:
#             if db_spec_def.name not in material.specs.specs:
#                 material.specs.specs[db_spec_def.name] = None
#                 flag_modified(material.specs, "specs")
#         else:
#             new_spec = inv_models.MaterialSpec(materials_id=material.id, specs={db_spec_def.name: None})
#             db.add(new_spec)
#     await db.commit()

#     return created_link

@router.post("/material_category_spec_definitions", response_model=inv_schemas.MaterialCategorySpecDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def add_spec_definition_to_material_category(
    link_create: inv_schemas.MaterialCategorySpecDefinitionCreate,
    request: Request,  # Request 객체 주입
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """카테고리에 스펙 정의를 연결하고, 관련된 모든 자재의 스펙에 해당 키를 null 값으로 자동 추가합니다. 관리자 권한이 필요합니다."""
    db_category = await inv_crud.material_category.get(db, id=link_create.material_category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Material category not found.")

    db_spec_def = await inv_crud.material_spec_definition.get(db, id=link_create.spec_definition_id)
    if not db_spec_def:
        raise HTTPException(status_code=404, detail="Material spec definition not found.")

    #  ARQ Redis 클라이언트를 CRUD 메서드로 전달
    created_link = await inv_crud.material_category_spec_definition.create(
        db=db, obj_in=link_create, arq_redis_pool=request.app.state.redis
    )

    return created_link


# @router.delete("/material_category_spec_definitions", status_code=status.HTTP_204_NO_CONTENT)
# async def remove_spec_definition_from_material_category(
#     material_category_id: int,
#     spec_definition_id: int,
#     db: Session = Depends(get_db_session_dependency),
#     current_user: UsrUser = Depends(get_current_admin_user)
# ):
#     """카테고리와 스펙 정의 연결을 해제하고, 관련된 모든 자재의 스펙에서 해당 키를 삭제합니다."""
#     spec_def_to_delete = await inv_crud.material_spec_definition.get(db, id=spec_definition_id)
#     if not spec_def_to_delete:
#         raise HTTPException(status_code=404, detail="Spec definition to remove not found.")
#     key_to_remove = spec_def_to_delete.name

#     stmt = (
#         select(inv_models.Material)
#         .where(inv_models.Material.material_category_id == material_category_id)
#         .options(selectinload(inv_models.Material.specs))
#     )
#     materials = (await db.execute(stmt)).scalars().all()

#     for material in materials:
#         if material.specs and key_to_remove in material.specs.specs:
#             del material.specs.specs[key_to_remove]
#             flag_modified(material.specs, "specs")
#     await db.commit()

#     db_link = await inv_crud.material_category_spec_definition.delete_link(
#         db, material_category_id=material_category_id, spec_definition_id=spec_definition_id
#     )
#     if db_link is None:
#         raise HTTPException(status_code=404, detail="Link not found.")

#     return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/material_category_spec_definitions", status_code=status.HTTP_204_NO_CONTENT)
async def remove_spec_definition_from_material_category(
    material_category_id: int,
    spec_definition_id: int,
    request: Request,  # Request 객체 주입
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    """카테고리와 스펙 정의 연결을 해제하고, 관련된 모든 자재의 스펙에서 해당 키를 삭제합니다. 관리자 권한이 필요합니다."""
    # ARQ Redis 클라이언트를 CRUD 메서드로 전달
    db_link = await inv_crud.material_category_spec_definition.delete_link(
        db, material_category_id=material_category_id, spec_definition_id=spec_definition_id, arq_redis_pool=request.app.state.redis
    )
    if db_link is None:
        raise HTTPException(status_code=404, detail="Link not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 4. inv.materials 엔드포인트
# =============================================================================
@router.post("/materials", response_model=inv_schemas.MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    material_create: inv_schemas.MaterialCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    return await inv_crud.material.create(db=db, obj_in=material_create)


@router.get("/materials/{material_code}", response_model=inv_schemas.MaterialResponse)
async def read_material(material_code: str, db: Session = Depends(get_db_session_dependency)):
    db_material = await inv_crud.material.get_by_code(db, code=material_code)
    if db_material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return db_material


# =============================================================================
# 5. inv.materials_specs 엔드포인트
# =============================================================================
@router.post("/materials_specs", response_model=inv_schemas.MaterialSpecResponse)
async def create_or_update_material_spec(
    spec_create_update: inv_schemas.MaterialSpecCreate,
    response: Response,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    if not await inv_crud.material.get(db, id=spec_create_update.materials_id):
        raise HTTPException(status_code=404, detail="Material not found.")

    db_spec = await inv_crud.material_spec.get_specs_for_material(db, materials_id=spec_create_update.materials_id)

    if db_spec:
        return await inv_crud.material_spec.update(db=db, db_obj=db_spec, obj_in=spec_create_update)
    else:
        response.status_code = status.HTTP_201_CREATED
        return await inv_crud.material_spec.create(db=db, obj_in=spec_create_update)


@router.put("/materials/{material_code}/specs", response_model=inv_schemas.MaterialSpecResponse)
async def update_material_spec_by_material_code(
    material_code: str,
    spec_update: inv_schemas.MaterialSpecUpdate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_admin_user)
):
    db_material = await inv_crud.material.get_by_code(db, code=material_code)
    if not db_material:
        raise HTTPException(status_code=404, detail="Material not found.")

    db_spec = await inv_crud.material_spec.get_specs_for_material(db, materials_id=db_material.id)
    if not db_spec:
        raise HTTPException(status_code=404, detail="Material spec not found to update.")

    return await inv_crud.material_spec.update(db=db, db_obj=db_spec, obj_in=spec_update)


@router.get("/materials/{material_code}/specs", response_model=inv_schemas.MaterialSpecResponse)
async def read_material_specs(material_code: str, db: Session = Depends(get_db_session_dependency)):
    db_material = await inv_crud.material.get_by_code(db, code=material_code)
    if not db_material:
        raise HTTPException(status_code=404, detail="Material not found.")

    db_spec = await inv_crud.material_spec.get_specs_for_material(db, materials_id=db_material.id)
    if db_spec is None:
        raise HTTPException(status_code=404, detail="Material specs not found.")
    return db_spec


# =============================================================================
# 6 & 7. MaterialBatch, MaterialTransaction 라우터
# =============================================================================
# ... (이하 라우터들은 기존 구조를 유지하며, 필요 시 code 기반으로 수정 가능) ...
@router.post("/material_transactions", response_model=inv_schemas.MaterialTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_material_transaction(
    transaction_create: inv_schemas.MaterialTransactionCreate,
    db: Session = Depends(get_db_session_dependency),
    current_user: UsrUser = Depends(get_current_active_user)
):
    if transaction_create.performed_by_user_id is None:
        transaction_create.performed_by_user_id = current_user.id

    return await inv_crud.material_transaction.create(db=db, obj_in=transaction_create)
