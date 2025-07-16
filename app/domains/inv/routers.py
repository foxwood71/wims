# app/domains/inv/routers.py (전체 최종 파일)

from typing import List  # , Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.core import dependencies as deps
from app.domains.inv import crud as inv_crud, schemas as inv_schemas
from app.domains.usr.models import User as UsrUser

router = APIRouter(
    tags=["Inventory Management (자재 관리)"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# 1. inv.material_categories 엔드포인트
# =============================================================================
@router.post(
    "/material_categories",
    response_model=inv_schemas.MaterialCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_material_category(
    category_create: inv_schemas.MaterialCategoryCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """새로운 자재 카테고리를 생성합니다.  관리자 권한이 필요합니다."""
    if await inv_crud.material_category.get_by_code(db, code=category_create.code):
        raise HTTPException(
            status_code=400, detail="Material category with this code already exists."
        )
    return await inv_crud.material_category.create(db=db, obj_in=category_create)


@router.get(
    "/material_categories", response_model=List[inv_schemas.MaterialCategoryResponse]
)
async def read_material_categories(
    skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db_session)
):
    """모든 자재 카테고리 목록을 조회합니다."""
    return await inv_crud.material_category.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/material_categories/{category_code}",
    response_model=inv_schemas.MaterialCategoryResponse,
)
async def read_material_category(
    category_code: str, db: Session = Depends(deps.get_db_session)
):
    """코드로 특정 자재 카테고리를 조회합니다."""
    db_category = await inv_crud.material_category.get_by_code(db, code=category_code)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Material category not found.")
    return db_category


@router.put(
    "/material_categories/{category_code}",
    response_model=inv_schemas.MaterialCategoryResponse,
)
async def update_material_category(
    category_code: str,
    category_update: inv_schemas.MaterialCategoryUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """코드로 특정 자재 카테고리를 업데이트합니다.  관리자 권한이 필요합니다."""
    db_category = await inv_crud.material_category.get_by_code(db, code=category_code)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Material category not found.")
    return await inv_crud.material_category.update(
        db=db, db_obj=db_category, obj_in=category_update
    )


@router.delete(
    "/material_categories/{category_code}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_material_category(
    category_code: str,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """코드로 특정 자재 카테고리를 삭제합니다.  관리자 권한이 필요합니다."""
    db_category = await inv_crud.material_category.get_by_code(db, code=category_code)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Material category not found.")
    await inv_crud.material_category.delete(db, id=db_category.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 2. inv.material_spec_definitions 엔드포인트
# =============================================================================
@router.post(
    "/material_spec_definitions",
    response_model=inv_schemas.MaterialSpecDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_material_spec_definition(
    spec_def_create: inv_schemas.MaterialSpecDefinitionCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """새로운 자재 스펙 정의를 생성합니다.  관리자 권한이 필요합니다."""
    return await inv_crud.material_spec_definition.create(db=db, obj_in=spec_def_create)


@router.put(
    "/material_spec_definitions/{spec_def_id}",
    response_model=inv_schemas.MaterialSpecDefinitionResponse,
)
async def update_material_spec_definition(
    spec_def_id: int,
    spec_def_update: inv_schemas.MaterialSpecDefinitionUpdate,
    request: Request,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """자재 스펙 정의를 업데이트합니다.  이름 변경 시 관련 스펙 키가 자동 업데이트됩니다."""
    db_spec_def = await inv_crud.material_spec_definition.get(db, id=spec_def_id)
    if not db_spec_def:
        raise HTTPException(status_code=404, detail="Spec definition not found.")

    arq_redis_pool = getattr(request.app.state, "redis", None)
    return await inv_crud.material_spec_definition.update(
        db=db,
        db_obj=db_spec_def,
        obj_in=spec_def_update,
        arq_redis_pool=arq_redis_pool,
    )


@router.delete(
    "/material_spec_definitions/{spec_def_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_material_spec_definition(
    spec_def_id: int,
    request: Request,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """자재 스펙 정의를 삭제합니다.  관리자 권한이 필요합니다."""
    db_spec_def = await inv_crud.material_spec_definition.get(db, id=spec_def_id)
    if not db_spec_def:
        raise HTTPException(status_code=404, detail="Spec definition not found.")

    arq_redis_pool = getattr(request.app.state, "redis", None)
    await inv_crud.material_spec_definition.remove(
        db=db, id=spec_def_id, arq_redis_pool=arq_redis_pool
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 3. inv.material_category_spec_definitions 엔드포인트
# =============================================================================
@router.post(
    "/material_category_spec_definitions",
    response_model=inv_schemas.MaterialCategorySpecDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_spec_definition_to_material_category(
    link_create: inv_schemas.MaterialCategorySpecDefinitionCreate,
    request: Request,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """카테고리에 스펙 정의를 연결하고, 관련 자재 스펙에 키를 자동 추가합니다."""
    arq_redis_pool = getattr(request.app.state, "redis", None)
    return await inv_crud.material_category_spec_definition.create(
        db=db, obj_in=link_create, arq_redis_pool=arq_redis_pool
    )


@router.delete(
    "/material_category_spec_definitions", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_spec_definition_from_material_category(
    material_category_id: int,
    spec_definition_id: int,
    request: Request,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """카테고리와 스펙 정의 연결을 해제하고, 관련 자재 스펙에서 키를 삭제합니다."""
    arq_redis_pool = getattr(request.app.state, "redis", None)
    db_link = await inv_crud.material_category_spec_definition.delete_link(
        db,
        material_category_id=material_category_id,
        spec_definition_id=spec_definition_id,
        arq_redis_pool=arq_redis_pool,
    )
    if db_link is None:
        raise HTTPException(status_code=404, detail="Link not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 4. inv.materials 엔드포인트
# =============================================================================
@router.post(
    "/materials",
    response_model=inv_schemas.MaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_material(
    material_create: inv_schemas.MaterialCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """새로운 자재 품목을 생성합니다.  관리자 권한이 필요합니다."""
    return await inv_crud.material.create(db=db, obj_in=material_create)


@router.get("/materials", response_model=List[inv_schemas.MaterialResponse])
async def read_materials(
    skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db_session)
):
    """모든 자재 품목 목록을 조회합니다."""
    return await inv_crud.material.get_multi(db=db, skip=skip, limit=limit)


@router.get("/materials/{material_code}", response_model=inv_schemas.MaterialResponse)
async def read_material(
    material_code: str, db: Session = Depends(deps.get_db_session)
):
    """코드로 특정 자재 품목을 조회합니다."""
    db_material = await inv_crud.material.get_by_code(db, code=material_code)
    if db_material is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return db_material


# --- 👇 누락되었던 PUT, DELETE 엔드포인트를 복구했습니다 ---
@router.put(
    "/materials/{material_code}", response_model=inv_schemas.MaterialResponse
)
async def update_material(
    material_code: str,
    material_in: inv_schemas.MaterialUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """코드로 특정 자재 품목을 업데이트합니다."""
    db_material = await inv_crud.material.get_by_code(db, code=material_code)
    if not db_material:
        raise HTTPException(status_code=404, detail="Material not found")
    return await inv_crud.material.update(
        db=db, db_obj=db_material, obj_in=material_in
    )


@router.delete("/materials/{material_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_code: str,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """코드로 특정 자재 품목을 삭제합니다."""
    db_material = await inv_crud.material.get_by_code(db, code=material_code)
    if not db_material:
        raise HTTPException(status_code=404, detail="Material not found")
    await inv_crud.material.delete(db=db, id=db_material.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# 5. inv.materials_specs 엔드포인트
# =============================================================================
@router.post(
    "/materials_specs",
    response_model=inv_schemas.MaterialSpecResponse,
)
async def create_or_update_material_spec(
    spec_in: inv_schemas.MaterialSpecCreate,
    response: Response,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """
    자재 스펙을 생성하거나 업데이트합니다. (Upsert)
    - 스펙이 없으면: 201 Created
    - 스펙이 있으면: 200 OK
    """
    existing_spec = await inv_crud.material_spec.get_specs_for_material(
        db, materials_id=spec_in.materials_id
    )
    if existing_spec:
        update_data = inv_schemas.MaterialSpecUpdate(specs=spec_in.specs)
        updated_spec = await inv_crud.material_spec.update(
            db, db_obj=existing_spec, obj_in=update_data
        )
        response.status_code = status.HTTP_200_OK
        return updated_spec
    else:
        new_spec = await inv_crud.material_spec.create(db, obj_in=spec_in)
        response.status_code = status.HTTP_201_CREATED
        return new_spec


@router.put(
    "/materials/{material_code}/specs", response_model=inv_schemas.MaterialSpecResponse
)
async def update_material_spec_by_material_code(
    material_code: str,
    spec_update: inv_schemas.MaterialSpecUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user),
):
    """자재 코드로 특정 자재의 스펙을 업데이트합니다."""
    db_material = await inv_crud.material.get_by_code(db, code=material_code)
    if not db_material:
        raise HTTPException(status_code=404, detail="Material not found.")

    db_spec = await inv_crud.material_spec.get_specs_for_material(
        db, materials_id=db_material.id
    )
    if not db_spec:
        raise HTTPException(
            status_code=404,
            detail="Spec for this material not found. Use POST to create one.",
        )
    return await inv_crud.material_spec.update(
        db=db, db_obj=db_spec, obj_in=spec_update
    )


# =============================================================================
# 6 & 7. MaterialBatch, MaterialTransaction 라우터
# =============================================================================
@router.post(
    "/material_transactions",
    response_model=List[inv_schemas.MaterialTransactionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_material_transaction(
    transaction_create: inv_schemas.MaterialTransactionCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user),
):
    """
    새로운 자재 거래를 생성합니다.
    - USAGE: FIFO 로직에 따라 재고를 차감하며, 여러 개의 거래 이력이 생성될 수 있습니다.
    - PURCHASE: 새로운 배치를 생성하고 재고를 추가합니다.
    """
    if transaction_create.performed_by_login_id is None:
        transaction_create.performed_by_login_id = current_user.id

    transactions = await inv_crud.material_transaction.create(
        db=db, obj_in=transaction_create
    )

    if not isinstance(transactions, list):
        return [transactions]
    return transactions
