# app/domains/corp/crud.py
from typing import Any, Dict, Union, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from fastapi.encoders import jsonable_encoder

from app.core.crud_base import CRUDBase
from . import models, schemas


class CRUDCompanyInfo(CRUDBase[models.CompanyInfo, schemas.CompanyInfoCreate, schemas.CompanyInfoUpdate]):
    async def get(self, db: AsyncSession, id: Any) -> Optional[models.CompanyInfo]:
        """
        ID로 회사 정보를 조회하며, 로고 파일 관계를 즉시 로드합니다.
        """
        statement = (
            select(self.model)
            .where(self.model.id == id)
            .options(selectinload(self.model.logo))  # <-- 즉시 로딩 설정
        )
        result = await db.execute(statement)
        return result.scalars().first()

    async def get_or_create(self, db: AsyncSession) -> models.CompanyInfo:
        """
        회사 정보를 조회하고, 없으면 기본값으로 생성하여 반환합니다.
        로고 파일 관계를 함께 로드합니다.
        """
        statement = (
            select(self.model)
            .where(self.model.id == 1)
            .options(selectinload(self.model.logo))
        )
        result = await db.execute(statement)
        company_info = result.scalars().first()

        if not company_info:
            company_info = self.model(id=1, name="기본 회사명")  # type: ignore
            db.add(company_info)
            await db.commit()
            await db.refresh(company_info)
        return company_info

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: models.CompanyInfo,
        obj_in: Union[schemas.CompanyInfoUpdate, Dict[str, Any]]
    ) -> models.CompanyInfo:
        """
        Pydantic 모델 또는 dict를 사용하여 회사 정보를 업데이트합니다.
        """
        #  CRUDBase와 달리, obj_in이 dict인지 먼저 확인합니다.
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            #  Pydantic 모델이면 기존처럼 model_dump를 사용합니다.
            update_data = obj_in.model_dump(exclude_unset=True)

        #  기존 객체의 필드를 순회하며 받은 데이터로 값을 갱신합니다.
        obj_data = jsonable_encoder(db_obj)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


company_info = CRUDCompanyInfo(models.CompanyInfo)
