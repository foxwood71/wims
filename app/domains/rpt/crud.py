# app/domains/rpt/crud.py

from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.shared import crud as shared_crud
from . import models, schemas


async def create_report_form(
    db: AsyncSession, *, form_in: schemas.ReportFormCreate
) -> models.ReportForm:
    """새로운 보고서 양식을 생성합니다."""
    # [수정] template_file_id 유효성 검사 추가
    # shared.resources 테이블에서 template_file_id에 해당하는 리소스가 존재하는지 확인합니다.
    existing_file = await shared_crud.resource.get(db, id=form_in.template_file_id)
    if not existing_file:
        # 파일이 존재하지 않으면, 404 Not Found 예외를 발생시킵니다.
        # 이 예외는 라우터에서 포착되어 HTTP 404 응답으로 변환됩니다.
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template file with ID {form_in.template_file_id} not found."
        )

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
