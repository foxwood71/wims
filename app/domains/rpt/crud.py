# app/domains/rpt/crud.py

from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from . import models, schemas


def create_report_form(
    db: Session, *, form_in: schemas.ReportFormCreate
) -> models.ReportForm:
    """ 새로운 보고서 양식을 생성합니다. """
    db_obj = models.ReportForm.model_validate(form_in)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_report_form(db: Session, form_id: int) -> Optional[models.ReportForm]:
    """ ID로 특정 보고서 양식을 조회합니다. (템플릿 파일 정보 포함) """
    statement = (
        select(models.ReportForm)
        .where(models.ReportForm.id == form_id)
        .options(selectinload(models.ReportForm.template_file))
    )
    return db.exec(statement).first()


def get_multi_report_forms(db: Session, skip: int = 0, limit: int = 100) -> List[models.ReportForm]:
    """ 모든 보고서 양식 목록을 조회합니다. (템플릿 파일 정보 포함) """
    statement = (
        select(models.ReportForm)
        .offset(skip)
        .limit(limit)
        .options(selectinload(models.ReportForm.template_file))
    )
    return db.exec(statement).all()


def update_report_form(
    db: Session, *, db_obj: models.ReportForm, obj_in: schemas.ReportFormUpdate
) -> models.ReportForm:
    """ 보고서 양식 정보를 수정합니다. """
    update_data = obj_in.model_dump(exclude_unset=True)
    db_obj.sqlmodel_update(update_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_report_form(db: Session, *, db_obj: models.ReportForm) -> models.ReportForm:
    """ 보고서 양식을 삭제합니다. """
    db.delete(db_obj)
    db.commit()
    return db_obj
