# app/domains/shared/services.py

import uuid
from pathlib import Path
import aiofiles
from fastapi import UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from . import models, crud

#  파일이 저장될 기본 디렉터리
UPLOAD_DIRECTORY = Path("uploads")


def create_file_download_url(file_id: int) -> str:
    """
    파일 ID를 기반으로 다운로드 URL을 생성합니다.  #  URL 생성 로직 중앙화
    """
    return f"/api/v1/shared/files/download/{file_id}"


async def upload_file(
    db: AsyncSession, *, upload_file: UploadFile, uploader_id: int
) -> models.File:
    """
    파일을 서버에 저장하고, 해당 파일의 메타데이터를 DB에 기록하는 공용 서비스.
    모든 도메인에서 이 서비스를 호출하여 파일을 업로드해야 합니다.
    """
    #  업로드 디렉터리가 없으면 생성
    UPLOAD_DIRECTORY.mkdir(exist_ok=True)

    #  파일 내용 읽기
    file_content = await upload_file.read()
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="업로드된 파일이 비어있습니다."
        )

    #  고유한 파일명 생성 (보안 강화)
    safe_filename = f"{uuid.uuid4()}-{upload_file.filename}"
    file_path = UPLOAD_DIRECTORY / safe_filename

    try:
        #  파일을 비동기적으로 저장
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 저장 중 오류 발생: {e}",
        )

    # db_obj = shared_models.File(
    #     name=file.filename,
    #     content_type=file.content_type,
    #     path=unique_filename,  # 전체 경로가 아닌 상대 경로(고유 파일명) 저장
    #     size=file_size,
    #     uploaded_by_user_id=user_id,
    # )

    #  DB에 저장할 파일 정보 생성
    upload_file_info = models.File(
        name=upload_file.filename,
        path=str(file_path),
        size=len(file_content),
        uploader_id=uploader_id,
        content_type=upload_file.content_type,
    )

    return await crud.file.create_file(
        db=db, file_info=upload_file_info
    )
