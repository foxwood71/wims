# app/domains/shared/routers.py

"""
'shared' 도메인 (애플리케이션 공용 데이터 관리)의 API 엔드포인트를 정의하는 모듈입니다.

이 라우터는 애플리케이션의 공용 데이터(버전, 이미지 유형, 이미지, 엔티티 이미지)에 대한
CRUD 작업을 위한 HTTP 엔드포인트를 제공합니다.
FastAPI의 APIRouter를 사용하여 엔드포인트를 그룹화하고 관리하며,
역할 기반 접근 제어(RBAC)를 포함한 세분화된 권한 모델을 적용합니다.
"""
import math
from pathlib import Path
from datetime import datetime, UTC
from typing import List, Optional

from sqlmodel import Session, update
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, Form, File
from fastapi.responses import FileResponse

# 핵심 의존성 (데이터베이스 세션, 사용자 인증 등)
from app.core import dependencies as deps
from app.domains.usr.models import User as UsrUser, UserRole

# 'shared' 도메인의 CRUD, 모델, 스키마
from . import crud as shared_crud
from . import models as shared_models
from . import schemas as shared_schemas

# 애플리케이션 설정 (파일 저장 경로 등)
from app.core.config import settings


router = APIRouter(
    tags=["Shared (시스템 공용정보 관리)"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# 1. app.versions 엔드포인트
# =============================================================================
@router.post("/versions", response_model=shared_schemas.VersionRead, status_code=status.HTTP_201_CREATED)
async def create_version(
    version_create: shared_schemas.VersionCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)
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
    current_user: UsrUser = Depends(deps.get_current_admin_user)
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
    current_user: UsrUser = Depends(deps.get_current_admin_user)
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
# 2. app.image_types 엔드포인트
# =============================================================================
@router.post("/image_types", response_model=shared_schemas.ImageTypeRead, status_code=status.HTTP_201_CREATED)
async def create_image_type(
    image_type_create: shared_schemas.ImageTypeCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)
):
    """
    새로운 이미지 유형을 생성합니다. (관리자 권한 필요)
    """
    db_image_type = await shared_crud.image_type.get_by_name(db, name=image_type_create.name)
    if db_image_type:
        raise HTTPException(status_code=400, detail="Image type with this name already exists")

    return await shared_crud.image_type.create(db=db, obj_in=image_type_create)


@router.get("/image_types", response_model=List[shared_schemas.ImageTypeRead])
async def read_image_types(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 이미지 유형 목록을 조회합니다.
    """
    image_types = await shared_crud.image_type.get_multi(db, skip=skip, limit=limit)
    return image_types


@router.get("/image_types/{image_type_id}", response_model=shared_schemas.ImageTypeRead)
async def read_image_type(
    image_type_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 이미지 유형을 조회합니다.
    """
    db_image_type = await shared_crud.image_type.get(db, id=image_type_id)
    if db_image_type is None:
        raise HTTPException(status_code=404, detail="Image type not found")
    return db_image_type


@router.put("/image_types/{image_type_id}", response_model=shared_schemas.ImageTypeRead)
async def update_image_type(
    image_type_id: int,
    image_type_update: shared_schemas.ImageTypeUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)
):
    """
    특정 ID의 이미지 유형을 업데이트합니다. (관리자 권한 필요)
    """
    db_image_type = await shared_crud.image_type.get(db, id=image_type_id)
    if db_image_type is None:
        raise HTTPException(status_code=404, detail="Image type not found")

    return await shared_crud.image_type.update(db=db, db_obj=db_image_type, obj_in=image_type_update)


@router.delete("/image_types/{image_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_type(
    image_type_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)
):
    """
    특정 ID의 이미지 유형을 삭제합니다. (관리자 권한 필요)
    참고: 이 이미지 유형을 참조하는 이미지가 있다면 삭제가 실패할 수 있습니다 (DB 제약).
    """
    db_image_type = await shared_crud.image_type.get(db, id=image_type_id)
    if db_image_type is None:
        raise HTTPException(status_code=404, detail="Image type not found")

    await shared_crud.image_type.delete(db, id=image_type_id)
    return {}


# =============================================================================
# 3. app.images 엔드포인트 (파일 업로드 포함)
# =============================================================================
@router.post("/images", response_model=shared_schemas.ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    image_type_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user)
):
    """
    새로운 이미지를 업로드하고 데이터베이스에 정보를 저장합니다.
    """
    current_upload_dir = Path(settings.UPLOAD_DIR)
    if not current_upload_dir.exists():
        current_upload_dir.mkdir(parents=True, exist_ok=True)

    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")

    unique_filename = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}_{current_user.id}_{file.filename}"
    file_path_on_disk = current_upload_dir / unique_filename

    try:
        with open(file_path_on_disk, "wb") as buffer:
            while contents := await file.read(1024):
                buffer.write(contents)

        image_create_data = shared_schemas.ImageCreate(
            image_type_id=image_type_id,
            file_name=unique_filename,
            file_path=str(file_path_on_disk),
            file_size_kb=math.ceil(file_path_on_disk.stat().st_size / 1024),
            mime_type=file.content_type,
            description=description,
            uploaded_by_user_id=current_user.id,
            uploaded_at=datetime.now(UTC),
            department_id=current_user.department_id  # 업로더의 부서 ID를 이미지에 할당
        )
        return await shared_crud.image.create(db=db, obj_in=image_create_data)

    except Exception as e:
        if file_path_on_disk.exists():
            file_path_on_disk.unlink()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Image upload failed: {e}")


@router.get("/images", response_model=List[shared_schemas.ImageRead])
async def read_images(
    skip: int = 0,
    limit: int = 100,
    uploaded_by_user_id: Optional[int] = None,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 이미지 또는 특정 사용자가 업로드한 이미지 목록을 조회합니다.
    """
    if uploaded_by_user_id:
        return await shared_crud.image.get_multi(db, skip=skip, limit=limit, uploaded_by_user_id=uploaded_by_user_id)
    else:
        return await shared_crud.image.get_multi(db, skip=skip, limit=limit)


@router.get("/images/{image_id}", response_model=shared_schemas.ImageRead)
async def read_image(
    image_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 이미지 정보를 조회합니다.
    """
    db_image = await shared_crud.image.get(db, id=image_id)
    if db_image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return db_image


@router.put("/images/{image_id}", response_model=shared_schemas.ImageRead)
async def update_image(
    image_id: int,
    image_update: shared_schemas.ImageUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user)
):
    """
    이미지 정보를 업데이트합니다. 소유자, 관리자, 부서원 또는 역할 권한이 필요합니다.
    """
    db_image = await shared_crud.image.get(db, id=image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")

    # 1. 소유자 여부 확인
    is_owner = db_image.uploaded_by_user_id == current_user.id
    # 2. 관리자(Admin) 이상 여부 확인
    is_admin = current_user.role <= UserRole.ADMIN
    # 3. 같은 부서 소속 여부 확인 (퇴사자 문제 해결)
    is_in_same_department = db_image.department_id and (db_image.department_id == current_user.department_id)

    # 4. 역할 기반 권한 확인 (RBAC)
    has_role_permission = False
    linked_entities = await shared_crud.entity_image.get_by_image_id(db, image_id=db_image.id)
    if linked_entities:
        # 이미지가 여러 곳에 연결될 수 있으므로, 첫 번째 연결을 기준으로 검사
        entity_type = linked_entities[0].entity_type
        if entity_type == "EQUIPMENT" and current_user.role == UserRole.FACILITY_MANAGER:
            has_role_permission = True
        elif entity_type == "MATERIAL" and current_user.role == UserRole.INVENTORY_MANAGER:
            has_role_permission = True
        # ... 다른 엔티티/역할에 대한 규칙 추가 가능

    # 최종 권한 판단: 위 조건 중 하나라도 만족하면 통과
    if not (is_owner or is_admin or is_in_same_department or has_role_permission):
        raise HTTPException(status_code=403, detail="Not enough permissions to update this image.")

    return await shared_crud.image.update(db=db, db_obj=db_image, obj_in=image_update)


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user)
):
    """
    이미지 정보 및 파일을 삭제합니다. 소유자, 관리자, 부서원 또는 역할 권한이 필요합니다.
    """
    db_image = await shared_crud.image.get(db, id=image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")

    # update_image와 동일한 권한 확인 로직 적용
    is_owner = db_image.uploaded_by_user_id == current_user.id
    is_admin = current_user.role <= UserRole.ADMIN
    is_in_same_department = db_image.department_id and (db_image.department_id == current_user.department_id)

    has_role_permission = False
    linked_entities = await shared_crud.entity_image.get_by_image_id(db, image_id=db_image.id)
    if linked_entities:
        entity_type = linked_entities[0].entity_type
        if entity_type == "EQUIPMENT" and current_user.role == UserRole.FACILITY_MANAGER:
            has_role_permission = True
        elif entity_type == "MATERIAL" and current_user.role == UserRole.INVENTORY_MANAGER:
            has_role_permission = True

    if not (is_owner or is_admin or is_in_same_department or has_role_permission):
        raise HTTPException(status_code=403, detail="Not enough permissions to delete this image.")

    file_path_on_disk = Path(db_image.file_path)
    if file_path_on_disk.exists():
        try:
            file_path_on_disk.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete image file: {e}")

    await shared_crud.image.delete(db, id=image_id)
    return {}


# =============================================================================
# 4. app.entity_images 엔드포인트
# =============================================================================
@router.post("/entity_images", response_model=shared_schemas.EntityImageRead, status_code=status.HTTP_201_CREATED)
async def create_entity_image(
    entity_image_create: shared_schemas.EntityImageCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user)
):
    """
    특정 엔티티(설비, 자재 등)에 이미지를 연결합니다.
    """
    db_image = await shared_crud.image.get(db, id=entity_image_create.image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Image to link not found.")

    return await shared_crud.entity_image.create(db=db, obj_in=entity_image_create)


@router.get(
    "/entity_images/by_entity/{entity_type}/{entity_id}",
    response_model=List[shared_schemas.EntityImageRead],
    summary="특정 엔티티의 모든 이미지 정보 조회 (상세 이미지 정보 포함)"
)
async def read_entity_images_for_entity(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 엔티티(유형과 ID)에 연결된 모든 이미지 정보를 조회합니다.
    """
    return await shared_crud.entity_image.get_by_entity(db, entity_type=entity_type, entity_id=entity_id)


@router.put("/entity_images/{entity_image_id}/set_main", response_model=shared_schemas.EntityImageRead)
async def set_main_entity_image(
    entity_image_id: int,
    entity_type: str,
    entity_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user)
):
    """
    특정 엔티티에 대해 연결된 이미지 중 하나를 '대표 이미지'로 설정합니다.
    기존의 대표 이미지는 해제됩니다. (관리자 권한 필요)
    """
    async with db.begin_nested():
        stmt_unsettle = (
            update(shared_models.EntityImage)
            .where(
                shared_models.EntityImage.entity_type == entity_type,
                shared_models.EntityImage.entity_id == entity_id,
                shared_models.EntityImage.is_main_image
            )
            .values(is_main_image=False)
        )
        await db.execute(stmt_unsettle)

        target_link = await shared_crud.entity_image.get(db, id=entity_image_id)
        if not target_link or target_link.entity_type != entity_type or target_link.entity_id != entity_id:
            raise HTTPException(status_code=404, detail="Entity-image link not found or does not match entity.")

        target_link.is_main_image = True
        db.add(target_link)

    await db.refresh(target_link)
    return target_link


@router.delete("/entity_images/{entity_image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity_image(
    entity_image_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user)
):
    """
    특정 엔티티와 이미지 간의 연결 정보를 삭제합니다. (실제 이미지는 삭제되지 않음) (관리자 권한 필요)
    """
    db_entity_image = await shared_crud.entity_image.get(db, id=entity_image_id)
    if db_entity_image is None:
        raise HTTPException(status_code=404, detail="Entity image link not found")

    await shared_crud.entity_image.delete(db, id=entity_image_id)
    return {}


# ====================================================================
# 5. File Upload End Pointer
# ====================================================================
# ==============================================================================
# 파일(File) 관련 라우트 (이 부분을 추가)
# ==============================================================================

@router.post("/files/upload", response_model=shared_schemas.FileUploadResponse, status_code=201)
async def upload_file(
    *,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_active_user),
    upload_file: UploadFile = File(...)
):
    """
    파일을 서버에 업로드하고 데이터베이스에 메타데이터를 저장합니다.
    """
    try:
        db_file = await shared_crud.file.create_file(
            db=db, file=upload_file, user_id=current_user.id
        )
        # 파일 접근 URL 생성 (필요에 따라 수정)
        file_url = f"/api/v1/shared/files/download/{db_file.id}"

        # --- 반환하는 딕셔너리의 키를 수정합니다 ---
        return {
            "id": db_file.id,  # 'file_id' -> 'id'로 수정
            "url": file_url,    # 'file_url' -> 'url'로 수정
            "message": "File uploaded successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File could not be uploaded: {e}")


@router.get("/files/download/{file_id}")
async def download_file(
    *,
    db: Session = Depends(deps.get_db_session),
    file_id: int,
    # current_user: UsrUser = Depends(get_current_active_user), # 필요시 권한 체크
):
    """
    ID를 사용하여 파일을 다운로드합니다.
    """
    db_file = await shared_crud.file.get_file(db=db, file_id=file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found.")

    # 실제 파일 시스템 경로 결합
    file_path = shared_crud.file.get_full_file_path(db_file)
    if not file_path.exists():
        # DB에 레코드는 있으나 실제 파일이 없는 경우
        raise HTTPException(status_code=500, detail="File not found on server.")

    return FileResponse(
        path=str(file_path),
        filename=db_file.name,
        media_type=db_file.content_type,
        headers={"Content-Disposition": f"attachment; filename=\"{db_file.name}\""}
    )


@router.get("/files/{file_id}", response_model=shared_schemas.FileRead)
async def read_file_metadata(
    *,
    db: Session = Depends(deps.get_db_session),
    file_id: int,
    current_user: UsrUser = Depends(deps.get_current_active_user),
):
    """
    파일의 메타데이터를 조회합니다.
    """
    db_file = await shared_crud.file.get_file(db=db, file_id=file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found.")
    return db_file
