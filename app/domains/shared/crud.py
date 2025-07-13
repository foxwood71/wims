# app/domains/shared/crud.py

"""
'shared' 도메인 (공용 데이터)과 관련된 CRUD 로직을 담당하는 모듈입니다.
"""
from pathlib import Path

from typing import List, Optional
from sqlalchemy.orm import selectinload

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException  # , status

# 공통 CRUDBase 및 Shared 도메인의 모델, 스키마 임포트
from app.core.config import settings
from app.core.crud_base import CRUDBase
from app.domains.usr import crud as usr_crud
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
# 2. 리소스 유형 (ResourceType) CRUD
# =============================================================================
class CRUDResourceCategory(
    CRUDBase[
        shared_models.ResourceCategory,
        shared_schemas.ResourceCategoryCreate,
        shared_schemas.ResourceCategoryUpdate,
    ]
):
    def __init__(self):
        super().__init__(model=shared_models.ResourceCategory)

    # wrapping functions
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[shared_models.ResourceCategory]:
        """이름으로 리소스 유형을 조회합니다."""
        return await super().get_by_attribute(db, attribute="name", value=name)

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[shared_models.ResourceCategory]:
        """ID로 이미지 유형을 삭제합니다. 관련된 이미지가 있으면 제한합니다."""
        check_query = select(shared_models.Resource).where(shared_models.Resource.category_id == id)
        result = await db.execute(select(check_query.exists()))
        if result.scalar():
            raise HTTPException(status_code=400, detail="Cannot delete this category as it is currently in use by one or more resources.")
        return await super().delete(db, id=id)


resource_category = CRUDResourceCategory()


# =============================================================================
# 3. 리소스 (Resource) CRUD
# =============================================================================
class CRUDResource(
    CRUDBase[
        shared_models.Resource,
        shared_schemas.ResourceCreate,
        shared_schemas.ResourceUpdate
    ]
):
    def __init__(self):
        super().__init__(model=shared_models.Resource)

    # 참고: 이미지 파일 생성(create)은 파일 시스템에 파일을 저장하는 로직과
    # 함께 서비스 계층(services)에서 처리하는 것이 더 일반적입니다.
    # 여기서는 데이터베이스 레코드 생성만 다룹니다.
    async def create(self, db: AsyncSession, *, obj_in: shared_schemas.ResourceCreate) -> shared_models.Resource:
        """FK 유효성을 확인하고 생성합니다."""

        if obj_in.category_id and not await resource_category.get(db, id=obj_in.category_id):
            raise HTTPException(status_code=404, detail="Resource type not found.")
        if obj_in.uploader_id and not await usr_crud.user.get(db, id=obj_in.uploader_id):
            raise HTTPException(status_code=404, detail="Uploader not found.")

        return await super().create(db, obj_in=obj_in)

    def get_full_file_path(self, db_resource: shared_models.Resource) -> Path:
        """DB에 저장된 상대 경로로 전체 파일 시스템 경로를 반환합니다."""
        return Path(settings.UPLOAD_DIR) / db_resource.path


resource = CRUDResource()


# =============================================================================
# 4. 엔티티-리소스 연결 (EntityResource) CRUD
# =============================================================================
class CRUDEntityResource(
    CRUDBase[
        shared_models.EntityResource,
        shared_schemas.EntityResourceCreate,
        shared_schemas.EntityResourceUpdate
    ]
):
    def __init__(self):
        super().__init__(model=shared_models.EntityResource)

    async def get_by_entity(
        self, db: AsyncSession, *, entity_type: str, entity_id: int
    ) -> List[shared_models.EntityResource]:
        """
        특정 엔티티에 연결된 모든 이미지 링크를 조회합니다.
        """
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
            .options(selectinload(shared_models.EntityResource.resource))  # Resource 관계를 Eager Loading
        )
        result = await db.execute(statement)
        return result.scalars().unique().all()

    async def get_by_resource_id(self, db: AsyncSession, *, resource_id: int) -> List[shared_models.EntityResource]:
        """
        특정 이미지 ID에 연결된 모든 엔티티 링크를 조회합니다.
        (비동기 환경에 맞게 db 세션 타입을 AsyncSession으로 수정)
        """
        statement = select(self.model).where(self.model.resource_id == resource_id)
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: shared_schemas.EntityResourceCreate) -> shared_models.EntityResource:
        """
        이미지 ID 유효성을 확인하고 생성합니다.
        """
        if not await resource.get(db, id=obj_in.resource_id):
            raise HTTPException(status_code=404, detail="Resource to link not found.")

        return await super().create(db, obj_in=obj_in)


entity_resource = CRUDEntityResource()
