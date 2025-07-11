# app/domains/rpt/crud.py

from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from . import models, schemas


async def create_report_form(
    db: AsyncSession, *, form_in: schemas.ReportFormCreate
) -> models.ReportForm:
    """새로운 보고서 양식을 생성합니다."""
    db_obj = models.ReportForm.model_validate(form_in)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_report_form(db: AsyncSession, form_id: int) -> Optional[models.ReportForm]:
    """ID로 특정 보고서 양식을 조회합니다. (템플릿 파일 정보 포함)"""
    statement = (
        select(models.ReportForm)
        .where(models.ReportForm.id == form_id)
        .options(selectinload(models.ReportForm.template_file))
    )
    result = await db.execute(statement)
    return result.scalars().first()


async def get_multi_report_forms(
    db: AsyncSession, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
) -> List[models.ReportForm]:
    """모든 보고서 양식 목록을 조회합니다. (템플릿 파일 정보 포함)"""
    statement = (
        select(models.ReportForm)
        .offset(skip)
        .limit(limit)
        .options(selectinload(models.ReportForm.template_file))
        .order_by(models.ReportForm.id)
    )

    #  [추가] is_active 값이 주어졌을 때만 WHERE 조건을 추가합니다.
    if is_active is not None:
        statement = statement.where(models.ReportForm.is_active == is_active)

    result = await db.execute(statement)
    return result.scalars().all()


async def update_report_form(
    db: AsyncSession, *, db_obj: models.ReportForm, obj_in: schemas.ReportFormUpdate
) -> models.ReportForm:
    """보고서 양식 정보를 수정합니다."""
    update_data = obj_in.model_dump(exclude_unset=True)
    db_obj.sqlmodel_update(update_data)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_report_form(db: AsyncSession, *, db_obj: models.ReportForm) -> models.ReportForm:
    """보고서 양식을 삭제합니다."""
    await db.delete(db_obj)
    await db.commit()
    return db_obj
