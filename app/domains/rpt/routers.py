# app/domains/rpt/routers.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import dependencies as deps
from . import crud, schemas

router = APIRouter(
    tags=["Report Management (보고서 관리)"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=schemas.ReportFormRead, status_code=201)
async def create_report_form(
    *,
    session: AsyncSession = Depends(deps.get_db_session),
    form_in: schemas.ReportFormCreate,
):
    """
    새로운 보고서 양식을 생성합니다.
    """
    return await crud.create_report_form(db=session, form_in=form_in)


@router.get("/", response_model=List[schemas.ReportFormReadWithTemplate])
async def read_report_forms(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(deps.get_db_session),
):
    """
    등록된 모든 보고서 양식 목록을 조회합니다.
    """
    return await crud.get_multi_report_forms(db=session, skip=skip, limit=limit)


@router.get("/{form_id}", response_model=schemas.ReportFormReadWithTemplate)
async def read_report_form(form_id: int, session: AsyncSession = Depends(deps.get_db_session)):
    """
    특정 ID의 보고서 양식 정보를 조회합니다.
    """
    db_form = await crud.get_report_form(db=session, form_id=form_id)
    if not db_form:
        raise HTTPException(status_code=404, detail="Report form not found")
    return db_form


@router.patch("/{form_id}", response_model=schemas.ReportFormRead)
async def update_report_form(
    form_id: int,
    *,
    session: AsyncSession = Depends(deps.get_db_session),
    form_in: schemas.ReportFormUpdate,
):
    """
    보고서 양식 정보를 수정합니다.
    """
    db_form = await crud.get_report_form(db=session, form_id=form_id)
    if not db_form:
        raise HTTPException(status_code=404, detail="Report form not found")
    return await crud.update_report_form(db=session, db_obj=db_form, obj_in=form_in)


@router.delete("/{form_id}", response_model=schemas.ReportFormRead)
async def delete_report_form(
    form_id: int, session: AsyncSession = Depends(deps.get_db_session)
):
    """
    보고서 양식을 삭제합니다.
    (참조하는 엑셀 파일 자체는 삭제되지 않습니다.)
    """
    db_form = await crud.get_report_form(db=session, form_id=form_id)
    if not db_form:
        raise HTTPException(status_code=404, detail="Report form not found")
    return await crud.delete_report_form(db=session, db_obj=db_form)
