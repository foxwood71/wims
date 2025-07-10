# app/domains/corp/router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import dependencies as deps
from app.domains.usr import models as usr_models
from app.domains.shared import services as shared_services
from . import schemas, crud


router = APIRouter(
    tags=["Corporation Information Management (회사 정보 관리)"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=schemas.CompanyInfoReadWithLogo, summary="회사 정보 조회")
async def get_company_info(
    session: AsyncSession = Depends(deps.get_db_session)
):
    """
    시스템에 저장된 단일 회사 정보를 조회합니다. 로고 파일 정보를 포함합니다.
    - 데이터가 없는 경우, '기본 회사명'으로 자동 생성 후 반환합니다.
    """
    return await crud.company_info.get_or_create(session)


@router.patch("/", response_model=schemas.CompanyInfoRead, summary="회사 정보 수정")
async def update_company_info(
    *,
    session: AsyncSession = Depends(deps.get_db_session),
    info_in: schemas.CompanyInfoUpdate,
):
    """
    시스템의 회사 정보를 수정합니다 (부분 업데이트 지원).
    로고 파일 수정은 별도 엔드포인트(/logo)를 사용해야 합니다.
    """
    db_info = await crud.company_info.get_or_create(session)

    update_data = info_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="수정할 데이터가 없습니다.")

    return await crud.company_info.update(db=session, db_obj=db_info, obj_in=info_in)


@router.post("/logo", response_model=schemas.CompanyInfoReadWithLogo, summary="회사 로고 업로드")
async def upload_company_logo(
    *,
    session: AsyncSession = Depends(deps.get_db_session),
    upload_file: UploadFile,
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    """
    회사 로고 파일을 업로드하고 정보를 갱신합니다.
    """
    db_info = await crud.company_info.get_or_create(session)

    #  shared 서비스를 사용하여 파일 업로드
    file_record = await shared_services.upload_file(
        db=session,
        upload_file=upload_file,
        uploader_id=current_user.id
    )

    #  회사 정보에 로고 파일 ID 연결
    update_data = schemas.CompanyInfoUpdate(logo_file_id=file_record.id)
    updated_info = await crud.company_info.update(
        db=session, db_obj=db_info, obj_in=update_data
    )
    #  업데이트된 전체 정보를 다시 로드하여 반환
    return await crud.company_info.get(db=session, id=updated_info.id)
