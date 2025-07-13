# app/domains/shared/services.py

import uuid
import aiofiles
import math
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.domains.usr import models as usr_models
from . import models, crud, schemas


async def _save_resource_to_disk(upload_file: UploadFile) -> tuple[Path, str, int]:
    """
    UploadFile 객체를 받아 디스크에 저장하고, 파일 경로와 정보를 반환합니다.
    """
    # UPLOAD_DIRECTORY를 전역 변수가 아닌, 함수 내에서 런타임에 정의합니다.
    # 이렇게 해야 monkeypatch로 변경된 settings 값을 올바르게 참조할 수 있습니다.
    upload_directory = Path(settings.UPLOAD_DIR)
    upload_directory.mkdir(parents=True, exist_ok=True)

    #  파일 내용 읽기
    file_content = await upload_file.read()
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="업로드된 파일이 비어있습니다."
        )

    #  고유한 파일명 생성 (보안강화, safe_filename 이것이 상대 경로가 됩니다)
    safe_resource_name = f"{uuid.uuid4()}-{upload_file.filename}"
    resource_path = upload_directory / safe_resource_name

    try:
        #  파일을 비동기적으로 저장
        async with aiofiles.open(resource_path, "wb") as f:
            await f.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 저장 중 오류 발생: {e}",
        )

    resource_size_kb = math.ceil(len(file_content) / 1024)
    return resource_path, safe_resource_name, resource_size_kb


async def upload_resource(
    db: AsyncSession, *, upload_file: UploadFile,
    uploader_id: int, department_id: int,
    resource_type: models.ResourceType, category_id: Optional[int], description: Optional[str],
) -> models.Resource:
    """
    모든 리소스를(이미지/파일) 저장하고, 해당 메타데이터를 DB에 기록하는 공용 서비스.
    """
    # 1. 이미지 파일 확장자 검사
    # 이미지일 경우에만 확장자 검사
    if resource_type == models.ResourceType.IMAGE:
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        file_extension = Path(upload_file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="지원하지 않는 이미지 파일 형식입니다.")

    # 2. 파일 저장 (공통 헬퍼 함수 사용)
    resource_path, safe_resource_name, resource_size_kb = await _save_resource_to_disk(upload_file)

    # 3. DB에 저장할 Image 모델 객체 생성
    resource_data = schemas.ResourceCreate(
        type=resource_type,
        category_id=category_id,
        name=upload_file.filename,
        path=safe_resource_name,
        size_kb=resource_size_kb,
        content_type=upload_file.content_type,
        description=description,
        uploader_id=uploader_id,
        department_id=department_id,
        uploaded_at=datetime.now(UTC),
    )
    return await crud.resource.create(db=db, obj_in=resource_data)


async def prepare_resource_for_download(
    db: AsyncSession, *, resource_id: int
) -> tuple[Path, str]:
    """
    다운로드할 파일의 유효성을 검사하고,
    파일의 전체 경로와 원본 파일명을 반환합니다.

    Returns:
        tuple[Path, str]: (파일의 전체 절대 경로, 원본 파일명)
    """
    #  1. DB에서 파일 메타데이터를 조회합니다.
    db_resource = await crud.resource.get_resource(db=db, resource_id=resource_id)
    if not db_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found."
        )

    #  2. DB의 상대 경로와 설정의 기본 경로를 조합하여 전체 경로를 만듭니다.
    full_path = crud.file.get_full_resource_path(db_resource)

    #  3. 파일이 디스크에 실제로 존재하는지 확인합니다.
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found on disk."
        )

    return full_path, db_resource.name


async def check_resource_modification_permission(
    db: AsyncSession, *, resource_id: int, user: usr_models
) -> models.Resource:
    """
    사용자가 특정 파일을 수정/삭제할 수 있는 권한이 있는지 확인합니다.
    권한이 없으면 HTTPException을 발생시키고, 있으면 파일 객체를 반환합니다.
    """
    db_resource = await crud.resource.get(db, id=resource_id)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # 1. 소유자 여부 확인
    is_owner = db_resource.uploader_id == user.id
    # 2. 관리자(Admin) 이상 여부 확인
    is_admin = user.role <= usr_models.UserRole.ADMIN
    # 3. 같은 부서 소속 여부 확인
    is_in_same_department = (
        db_resource.department_id is not None
        and db_resource.department_id == user.department_id
    )
    # 4. 역할 기반 권한 확인 (RBAC) - 이미지나 파일 관련을 일단 보류 '2025.07.12.
    has_role_permission = False  # RBAC 기능 사용시 False 설정
    if isinstance(db_resource, models.Resource):
        linked_entities = await crud.entity_resource.get_by_resource_id(db, resource_id=db_resource.id)
        if linked_entities:
            entity_type = linked_entities[0].entity_type
            if (entity_type == "EQUIPMENT" and user.role == usr_models.UserRole.FACILITY_MANAGER) or \
               (entity_type == "MATERIAL" and user.role == usr_models.UserRole.INVENTORY_MANAGER):
                has_role_permission = True  # 역할 권한으로 통과

    # 최종 권한 판단: 위 조건 중 하나라도 만족하지 않으면 에러 발생
    if not (is_owner or is_admin or is_in_same_department or has_role_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this file."
        )

    return db_resource

# def create_file_download_url(file_id: int) -> str:
#     """
#     파일 ID를 기반으로 다운로드 URL을 생성합니다.  #  URL 생성 로직 중앙화
#     """
#     return f"/api/v1/shared/files/download/{file_id}"
