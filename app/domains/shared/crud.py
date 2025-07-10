# app/domains/shared/crud.py

"""
'shared' 도메인 (공용 데이터)과 관련된 CRUD 로직을 담당하는 모듈입니다.
"""
import uuid
# import shutil
from pathlib import Path
from fastapi import UploadFile

from typing import List, Optional
from sqlalchemy.orm import selectinload
from sqlmodel import select, Session
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException  # , status

# 공통 CRUDBase 및 Shared 도메인의 모델, 스키마 임포트
from app.core.config import settings
from app.core.crud_base import CRUDBase
from . import models as shared_models
from . import schemas as shared_schemas


# =============================================================================
# 1. 버전 (Version) CRUD
# =============================================================================
class CRUDVersion(
    CRUDBase[
        shared_models.Version,
        shared_schemas.VersionCreate,
        shared_schemas.VersionUpdate
    ]
):
    def __init__(self):
        super().__init__(model=shared_models.Version)

    async def get_by_version_string(self, db: AsyncSession, *, version: str) -> Optional[shared_models.Version]:
        """버전 문자열로 조회합니다."""
        statement = select(self.model).where(self.model.version == version)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_version_by_number(self, db: AsyncSession, *, version: str) -> Optional[shared_models.Version]:
        """버전 번호(문자열)로 버전을 조회합니다. (get_by_version_string과 동일)"""
        return await self.get_by_version_string(db, version=version)


version = CRUDVersion()


# =============================================================================
# 2. 이미지 유형 (ImageType) CRUD
# =============================================================================
class CRUDImageType(
    CRUDBase[
        shared_models.ImageType,
        shared_schemas.ImageTypeCreate,
        shared_schemas.ImageTypeUpdate
    ]
):
    def __init__(self):
        super().__init__(model=shared_models.ImageType)

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[shared_models.ImageType]:
        """유형 이름으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def delete(self, db: Session, *, id: int) -> Optional[shared_models.ImageType]:
        """ID로 이미지 유형을 삭제합니다. 관련된 이미지가 있으면 제한합니다."""
        from .models import Image
        check_query = select(Image).where(Image.image_type_id == id)
        result = await db.execute(select(check_query.exists()))
        if result.scalar():
            raise HTTPException(status_code=400, detail="Cannot delete image type as it is currently in use.")
        return await super().delete(db, id=id)


image_type = CRUDImageType()


# =============================================================================
# 3. 이미지 (Image) CRUD
# =============================================================================
class CRUDImage(
    CRUDBase[
        shared_models.Image,
        shared_schemas.ImageCreate,
        shared_schemas.ImageUpdate
    ]
):
    def __init__(self):
        super().__init__(model=shared_models.Image)

    # 참고: 이미지 파일 생성(create)은 파일 시스템에 파일을 저장하는 로직과
    # 함께 서비스 계층(services)에서 처리하는 것이 더 일반적입니다.
    # 여기서는 데이터베이스 레코드 생성만 다룹니다.
    async def create(self, db: AsyncSession, *, obj_in: shared_schemas.ImageCreate) -> shared_models.Image:
        """FK 유효성을 확인하고 생성합니다."""
        from app.domains.usr.crud import user

        if obj_in.image_type_id and not await image_type.get(db, id=obj_in.image_type_id):
            raise HTTPException(status_code=404, detail="Image type not found.")
        if obj_in.uploaded_by_user_id and not await user.get(db, id=obj_in.uploaded_by_user_id):
            raise HTTPException(status_code=404, detail="Uploader user not found.")

        return await super().create(db, obj_in=obj_in)


image = CRUDImage()


# =============================================================================
# 4. 엔티티-이미지 연결 (EntityImage) CRUD
# =============================================================================
class CRUDEntityImage(
    CRUDBase[
        shared_models.EntityImage,
        shared_schemas.EntityImageCreate,
        shared_schemas.EntityImageUpdate
    ]
):
    def __init__(self):
        super().__init__(model=shared_models.EntityImage)

    async def get_by_entity(
        self, db: AsyncSession, *, entity_type: str, entity_id: int
    ) -> List[shared_models.EntityImage]:
        """특정 엔티티에 연결된 모든 이미지 링크를 조회합니다."""
        # statement = select(self.model).where(
        #     self.model.entity_type == entity_type,
        #     self.model.entity_id == entity_id
        # )
        # result = await db.execute(statement)
        # return result.scalars().all()
        statement = (
            select(self.model)
            .where(
                self.model.entity_type == entity_type,
                self.model.entity_id == entity_id
            )
            .options(selectinload(shared_models.EntityImage.image))  # Image 관계를 Eager Loading
        )
        result = await db.execute(statement)
        return result.scalars().unique().all()  # 중복 방지

    async def get_by_image_id(self, db: Session, *, image_id: int) -> List[shared_models.EntityImage]:
        """특정 이미지 ID에 연결된 모든 엔티티 링크를 조회합니다."""
        statement = select(self.model).where(self.model.image_id == image_id)
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: shared_schemas.EntityImageCreate) -> shared_models.EntityImage:
        """이미지 ID 유효성을 확인하고 생성합니다."""
        if not await image.get(db, id=obj_in.image_id):
            raise HTTPException(status_code=404, detail="Image to link not found.")

        return await super().create(db, obj_in=obj_in)


entity_image = CRUDEntityImage()


# ==============================================================================
# 5. 파일(File) 관련 CRUD (이 부분을 추가)
# ==============================================================================
class CRUDFile:
    async def create_file(self, db: AsyncSession, *, file_info: UploadFile) -> shared_models.File:
        """
        파일을 저장하고 DB에 레코드를 생성합니다.
        """
        # # 1. 파일 내용 읽기 및 크기 계산
        # contents = await file.read()
        # file_size = len(contents)
        # await file.seek(0)  # 포인터를 다시 처음으로

        # # 2. 고유한 파일명 생성 (UUID 사용)
        # file_extension = Path(file.filename).suffix
        # unique_filename = f"{uuid.uuid4()}{file_extension}"

        # # 3. 파일 저장 경로 설정 및 저장
        # upload_dir = Path(settings.UPLOAD_DIR)
        # upload_dir.mkdir(parents=True, exist_ok=True)  # 디렉토리 생성
        # file_path = upload_dir / unique_filename

        # with open(file_path, "wb") as buffer:
        #     shutil.copyfileobj(file.file, buffer)

        # 4. DB 모델 객체 생성
        db_obj = file_info

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_file(self, db: AsyncSession, *, file_id: uuid.UUID) -> shared_models.File | None:
        """
        ID로 파일 레코드를 조회합니다.
        """
        statement = select(shared_models.File).where(shared_models.File.id == file_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    def get_full_file_path(self, db_file: shared_models.File) -> Path:
        """
        DB에 저장된 상대 경로로 전체 파일 시스템 경로를 반환합니다.
        """
        return Path(settings.UPLOAD_DIR) / db_file.path


file = CRUDFile()
