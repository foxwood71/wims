# app/domains/shared/routers.py

"""
'shared' 도메인 (애플리케이션 공용 데이터 관리)의 API 엔드포인트를 정의하는 모듈입니다.

이 라우터는 애플리케이션의 공용 데이터(버전, 리소스 유형, 리소스, 엔티티 리소스)에 대한
CRUD 작업을 위한 HTTP 엔드포인트를 제공합니다.
FastAPI의 APIRouter를 사용하여 엔드포인트를 그룹화하고 관리하며,
역할 기반 접근 제어(RBAC)를 포함한 세분화된 권한 모델을 적용합니다.
"""
from pathlib import Path
from typing import List, Optional

from sqlmodel import Session, update
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, Form, File


# 핵심 의존성 (데이터베이스 세션, 사용자 인증 등)
from app.core import dependencies as deps
from app.domains.usr import models as usr_models

# 'shared' 도메인의 CRUD, 모델, 스키마
from . import crud as shared_crud
from . import models as shared_models
from . import schemas as shared_schemas
from . import services as shared_services


router = APIRouter(
    tags=["Shared (시스템 공용정보 관리)"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# 1. shared.versions 엔드포인트
# =============================================================================
@router.post("/versions", response_model=shared_schemas.VersionRead, status_code=status.HTTP_201_CREATED)
async def create_version(
    version_create: shared_schemas.VersionCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_admin_user)
):
    """
    새로운 애플리케이션 버전을 생성합니다. (관리자 권한 필요)
    """
    db_version = await shared_crud.version.get_version_by_number(db, version=version_create.version)
    if db_version:
        raise HTTPException(status_code=400, detail="Version already exists")

    return await shared_crud.version.create(db=db, obj_in=version_create)


@router.get("/versions", response_model=List[shared_schemas.VersionRead])
async def read_versions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 애플리케이션 버전 목록을 조회합니다.
    """
    versions = await shared_crud.version.get_multi(db, skip=skip, limit=limit)
    return versions


@router.get("/versions/{version_id}", response_model=shared_schemas.VersionRead)
async def read_version(
    version_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 애플리케이션 버전을 조회합니다.
    """
    db_version = await shared_crud.version.get(db, id=version_id)
    if db_version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return db_version


@router.put("/versions/{version_id}", response_model=shared_schemas.VersionRead)
async def update_version(
    version_id: int,
    version_update: shared_schemas.VersionUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_admin_user)
):
    """
    특정 ID의 애플리케이션 버전을 업데이트합니다. (관리자 권한 필요)
    """
    db_version = await shared_crud.version.get(db, id=version_id)
    if db_version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    return await shared_crud.version.update(db=db, db_obj=db_version, obj_in=version_update)


@router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    version_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_admin_user)
):
    """
    특정 ID의 애플리케이션 버전을 삭제합니다. (관리자 권한 필요)
    """
    db_version = await shared_crud.version.get(db, id=version_id)
    if db_version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    await shared_crud.version.delete(db, id=version_id)
    return {}


# =============================================================================
# 2. shared.resource_category_types 엔드포인트
# =============================================================================
@router.post("/resources/category-types", response_model=shared_schemas.ResourceCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_resource_category_types(
    resource_category_create: shared_schemas.ResourceCategoryCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_admin_user)
):
    """
    새로운 리소스 유형을 생성합니다. (관리자 권한 필요)
    """
    db_resource_type = await shared_crud.resource_category.get_by_name(db, name=resource_category_create.name)
    if db_resource_type:
        raise HTTPException(status_code=400, detail="Resource Category with this name already exists")

    return await shared_crud.resource_category.create(db=db, obj_in=resource_category_create)


@router.get("/resources/category-types", response_model=List[shared_schemas.ResourceCategoryRead])
async def read_resource_category_types(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 리소스 유형 목록을 조회합니다.
    """
    resource_types = await shared_crud.resource_category.get_multi(db, skip=skip, limit=limit)
    return resource_types


@router.get("/resources/category-types/{resource_category_id}", response_model=shared_schemas.ResourceCategoryRead)
async def read_resource_category_type(
    resource_category_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 리소스 유형을 조회합니다.
    """
    db_resource_type = await shared_crud.resource_category.get(db, id=resource_category_id)
    if db_resource_type is None:
        raise HTTPException(status_code=404, detail="Resource type not found")
    return db_resource_type


@router.put("/resources/category-types/{resource_category_id}", response_model=shared_schemas.ResourceCategoryRead)
async def update_resource_category_type(
    resource_category_id: int,
    resource_category_update: shared_schemas.ResourceCategoryUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_admin_user)
):
    """
    특정 ID의 리소스 유형을 업데이트합니다. (관리자 권한 필요)
    """
    db_resource_type = await shared_crud.image_type.get(db, id=resource_category_id)
    if db_resource_type is None:
        raise HTTPException(status_code=404, detail="Resource type not found")

    return await shared_crud.resource_category.update(db=db, db_obj=db_resource_type, obj_in=resource_category_update)


@router.delete("/resources/category-types/{resource_category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource_category_type(
    resource_category_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_admin_user)
):
    """
    특정 ID의 리소스 유형을 삭제합니다. (관리자 권한 필요)
    참고: 이 리소스 유형을 참조하는 리소스가 있다면 삭제가 실패할 수 있습니다 (DB 제약).
    """
    db_resource_type = await shared_crud.resource_category.get(db, id=resource_category_id)
    if db_resource_type is None:
        raise HTTPException(status_code=404, detail="Resource type not found")

    await shared_crud.resource_category.delete(db, id=resource_category_id)
    return {}


# =============================================================================
# 3. shared.resource 엔드포인트 (파일 업로드 포함)
# =============================================================================
@router.post("/resources", response_model=shared_schemas.ResourceRead, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    file: UploadFile = File(...),
    category_id: Optional[int] = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user)
):
    """
    새로운 리소스를 업로드하고 데이터베이스에 정보를 저장합니다.
    """
    try:
        # [추가] 파일의 MIME 타입을 기반으로 리소스 유형을 결정합니다.
        resource_type = (
            shared_models.ResourceType.IMAGE
            if "image" in file.content_type
            else shared_models.ResourceType.FILE
        )

        #  이제 라우터는 서비스 함수를 호출하는 역할만 합니다.
        return await shared_services.upload_resource(
            db=db,
            upload_file=file,
            uploader_id=current_user.id,  # 서비스에서 이 객체로부터 id, department_id를 추출
            department_id=current_user.department_id,
            resource_type=resource_type,
            category_id=category_id,
            description=description
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        # 디버깅을 위해 실제 에러를 서버 로그에 출력합니다.
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리소스 업로드에 실패했습니다: {e}"
        )


@router.get("/resources", response_model=List[shared_schemas.ResourceRead])
async def read_resources(
    skip: int = 0,
    limit: int = 100,
    uploader_id: Optional[int] = None,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 리소스 또는 특정 사용자가 업로드한 리소스 목록을 조회합니다.
    """
    if uploader_id:
        return await shared_crud.resource.get_multi(db, skip=skip, limit=limit, uploader_id=uploader_id)
    else:
        return await shared_crud.resource.get_multi(db, skip=skip, limit=limit)


@router.get("/resources/{resource_id}", response_model=shared_schemas.ResourceRead)
async def read_resource(
    resource_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 리소스 정보를 조회합니다.
    """
    db_resource = await shared_crud.resource.get(db, id=resource_id)
    if db_resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return db_resource


@router.put(
    "/resources/{resource_id}",
    response_model=shared_schemas.ResourceRead
)
async def update_resource(
    resource_id: int,
    resource_update: shared_schemas.ResourceUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user)
):
    """
    리소스 정보를 업데이트합니다. 소유자, 관리자, 부서원 또는 역할 권한이 필요합니다.
    """
    #  1. 서비스 함수를 호출하여 권한 확인 및 리소스 객체 가져오기
    db_resource = await shared_services.check_resource_modification_permission(db=db, resource_id=resource_id, user=current_user)

    #  2. 권한 확인이 통과되면, 업데이트 로직 실행
    return await shared_crud.resource.update(db=db, db_obj=db_resource, obj_in=resource_update)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user)
):
    """
    리소스 정보 및 파일을 삭제합니다.
    소유자, 같은 부서원, 또는 관리자만 삭제할 수 있습니다.
    """
    #  1. 서비스 함수를 호출하여 권한 확인 및 리소스 객체 가져오기
    db_resource = await shared_services.check_resource_modification_permission(db=db, resource_id=resource_id, user=current_user)

    # 2. 권한 확인이 통과되면, 파일 및 DB 레코드 삭제 로직 실행
    resource_path_on_disk = Path(db_resource.path)
    if resource_path_on_disk.exists():
        try:
            resource_path_on_disk.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete resource: {e}")

    await shared_crud.resource.delete(db, id=resource_id)
    return {}


# =============================================================================
# 4. shared.resources.entity 엔드포인트 entities 복수
# =============================================================================
@router.post("/resources/entity", response_model=shared_schemas.EntityResourceRead, status_code=status.HTTP_201_CREATED)
async def create_entity_resource(
    entity_resource_create: shared_schemas.EntityResourceCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user)
):
    """
    특정 엔티티(설비, 자재 등)에 리소스를 연결합니다.
    """
    db_resource = await shared_crud.resource.get(db, id=entity_resource_create.resource_id)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource to link not found.")

    return await shared_crud.entity_resource.create(db=db, obj_in=entity_resource_create)


@router.get(
    "/resources/entity/{entity_type}/{entity_id}",
    response_model=List[shared_schemas.EntityResourceRead],
    summary="특정 엔티티의 모든 리소스 정보 조회 (상세 리소스 정보 포함)"
)
async def read_entity_resources_for_entity(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 엔티티(유형과 ID)에 연결된 모든 리소스 정보를 조회합니다.
    """
    return await shared_crud.entity_resource.get_by_entity(db, entity_type=entity_type, entity_id=entity_id)


@router.put("/resources/entity/{entity_resource_id}/set_main", response_model=shared_schemas.EntityResourceRead)
async def set_main_entity_resource(
    entity_resource_id: int,
    entity_type: str,
    entity_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user)
):
    """
    특정 엔티티에 대해 연결된 리소스 중 하나를 '대표 리소스'로 설정합니다.
    기존의 대표 리소스는 해제됩니다. (관리자 권한 필요)
    """
    async with db.begin_nested():
        stmt_unsettle = (
            update(shared_models.EntityResource)
            .where(
                shared_models.EntityResource.entity_type == entity_type,
                shared_models.EntityResource.entity_id == entity_id,
                shared_models.EntityResource.is_main
            )
            .values(is_main=False)
        )
        await db.execute(stmt_unsettle)

        target_link = await shared_crud.entity_resource.get(db, id=entity_resource_id)
        if not target_link or target_link.entity_type != entity_type or target_link.entity_id != entity_id:
            raise HTTPException(status_code=404, detail="Entity-resource link not found or does not match entity.")

        target_link.is_main = True
        db.add(target_link)

    await db.refresh(target_link)
    return target_link


@router.delete("/resources/entity/{entity_resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity_resource(
    entity_resource_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user)
):
    """
    특정 엔티티와 리소스 간의 연결 정보를 삭제합니다. (실제 리소스는 삭제되지 않음) (관리자 권한 필요)
    """
    db_entity_resource = await shared_crud.entity_resource.get(db, id=entity_resource_id)
    if db_entity_resource is None:
        raise HTTPException(status_code=404, detail="Entity resource link not found")

    await shared_crud.entity_resource.delete(db, id=entity_resource_id)
    return {}
