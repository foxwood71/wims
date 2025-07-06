# app/domains/corp/router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from . import models, schemas

router = APIRouter(
    tags=["Corporation Information Management (회사 정보 관리)"],
    responses={404: {"description": "Not found"}},
)


def get_or_create_company_info(session: Session) -> models.CompanyInfo:
    """
    회사 정보를 조회하고, 없으면 기본값으로 생성하여 반환합니다.
    """
    company_info = session.get(models.CompanyInfo, 1)
    if not company_info:
        company_info = models.CompanyInfo(name="기본 회사명")
        session.add(company_info)
        session.commit()
        session.refresh(company_info)
    return company_info


@router.get(
    "/",
    response_model=schemas.CompanyInfoRead,
    summary="회사 정보 조회"
)
def get_company_info(
    session: Session = Depends(get_session)
):
    """
    시스템에 저장된 단일 회사 정보를 조회합니다.

    - 데이터가 없는 경우, '기본 회사명'으로 자동 생성 후 반환합니다.
    """
    return get_or_create_company_info(session)


@router.patch(
    "/",
    response_model=schemas.CompanyInfoRead,
    summary="회사 정보 수정"
)
def update_company_info(
    *,
    session: Session = Depends(get_session),
    info_in: schemas.CompanyInfoUpdate
):
    """
    시스템의 회사 정보를 수정합니다 (부분 업데이트 지원).
    """
    db_info = get_or_create_company_info(session)

    info_data = info_in.model_dump(exclude_unset=True)
    if not info_data:
        raise HTTPException(
            status_code=400, detail="수정할 데이터가 없습니다."
        )

    for key, value in info_data.items():
        setattr(db_info, key, value)

    session.add(db_info)
    session.commit()
    session.refresh(db_info)
    return db_info
