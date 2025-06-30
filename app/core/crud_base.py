# app/core/crud_base.py

"""
공통 CRUD(Create, Read, Update, Delete) 작업을 위한 기본 클래스 모듈입니다.
모든 메서드는 비동기(async) 환경에 맞게 수정되었습니다.
"""

from typing import Generic, List, Optional, Type, TypeVar, Any

# [수정] 비동기 세션을 위한 임포트를 명확히 합니다.
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    모든 CRUD 작업에 대한 기본 클래스를 정의합니다.
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """
        ID를 기준으로 단일 레코드를 조회합니다.
        (참고: await db.get()은 AsyncSession에서 지원하는 편리한 기능입니다)
        """
        # [수정] 타입 힌트를 AsyncSession으로 변경
        return await db.get(self.model, id)

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> List[ModelType]:
        """
        여러 레코드를 조회합니다. 필터링을 위한 키워드 인자를 지원합니다.
        """
        # [수정] 타입 힌트를 AsyncSession으로 변경
        query = select(self.model).offset(skip).limit(limit)

        for field, value in kwargs.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)

        # [수정] .exec() 대신 .execute()와 .scalars().all()을 사용합니다.
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_attribute(
        self, db: AsyncSession, *, attribute: str, value: Any
    ) -> Optional[ModelType]:
        statement = select(self.model).where(getattr(self.model, attribute) == value)
        response = await db.execute(statement)
        return response.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        새로운 레코드를 생성합니다.
        """
        # [수정] 타입 힌트를 AsyncSession으로 변경
        db_obj = self.model.model_validate(obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        """
        기존 레코드를 업데이트합니다.
        """
        # [수정] 타입 힌트를 AsyncSession으로 변경
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """
        ID를 기준으로 레코드를 삭제합니다.
        """
        # [수정] 타입 힌트를 AsyncSession으로 변경
        db_obj = await db.get(self.model, id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj
