# app/core/crud_base.py

"""
공통 CRUD(Create, Read, Update, Delete) 작업을 위한 기본 클래스 모듈입니다.
모든 메서드는 비동기(async) 환경에 맞게 수정되었습니다.
"""

from typing import Generic, List, Optional, Type, TypeVar, Any, Dict
from datetime import date, timedelta

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

    """
    조건을 만족하는 레코드가 여러개면 offset과 limit를 활용하여 반환하며,
    조건을 만족하는 레코드가 전혀 없으면 None을 반환
    """
    async def get_filtered(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None,  # 다중 속성 필터: {"attribute_name": "value"}
        date_range_field: Optional[str] = None,    # 기간 검색을 적용할 날짜 필드 이름 (예: "request_date")
        start_date: Optional[date] = None,         # 기간 검색 시작일
        end_date: Optional[date] = None,           # 기간 검색 종료일
        order_by_field: Optional[str] = None,      # 정렬할 필드 (예: "id")
        order_desc: bool = True,                   # 내림차순 정렬 여부
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        다중 속성 및 기간 검색 기능을 포함한 다중 조회.
        """
        query = select(self.model)
        conditions = []

        # 1. 다중 속성 필터링
        if filters:
            for attribute, value in filters.items():
                if hasattr(self.model, attribute):
                    conditions.append(getattr(self.model, attribute) == value)
                else:
                    # 유효하지 않은 속성이 전달될 경우 경고 또는 에러 처리
                    print(f"Warning: Model {self.model.__name__} has no attribute '{attribute}'")

        # 2. 기간 검색 필터링
        if date_range_field and hasattr(self.model, date_range_field):
            date_field = getattr(self.model, date_range_field)
            if start_date is not None:
                conditions.append(date_field >= start_date)
            if end_date is not None:
                # end_date 당일까지 포함하기 위함
                conditions.append(date_field < end_date + timedelta(days=1))
        elif date_range_field:
            print(f"Warning: Model {self.model.__name__} has no attribute '{date_range_field}' for date range filtering.")

        # 모든 조건을 하나의 where 절로 합칩니다.
        if conditions:
            query = query.where(*conditions)

        # 3. 정렬 (선택 사항)
        if order_by_field and hasattr(self.model, order_by_field):
            if order_desc:
                query = query.order_by(getattr(self.model, order_by_field).desc())
            else:
                query = query.order_by(getattr(self.model, order_by_field))
        elif order_by_field:
            print(f"Warning: Model {self.model.__name__} has no attribute '{order_by_field}' for ordering.")
        else:
            # 기본 정렬 (예: id 내림차순)
            if hasattr(self.model, 'id'):
                query = query.order_by(self.model.id.desc())

        # 4. 페이징
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    """
    조건을 만족하는 레코드가 여러 개 있더라도, 이 함수는 그 중 첫 번째 것을 반환하며,
    조건을 만족하는 레코드가 전혀 없으면 None을 반환
    """
    async def get_one_filtered(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None,
        date_range_field: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[ModelType]:
        """
        다중 속성 및 기간 검색 기능을 포함하여 단일 항목 조회.
        """
        query = select(self.model)
        conditions = []

        # 다중 속성 필터링
        if filters:
            for attribute, value in filters.items():
                if hasattr(self.model, attribute):
                    conditions.append(getattr(self.model, attribute) == value)

        # 기간 검색 필터링
        if date_range_field and hasattr(self.model, date_range_field):
            date_field = getattr(self.model, date_range_field)
            if start_date is not None:
                conditions.append(date_field >= start_date)
            if end_date is not None:
                conditions.append(date_field < end_date + timedelta(days=1))

        if conditions:
            query = query.where(*conditions)

        response = await db.execute(query)
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
