# app/utils/files.py

import os
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile

# 프로젝트의 최상위 디렉토리를 기준으로 static 디렉토리 경로를 설정합니다.
# 이 파일(files.py)의 위치는 app/utils/files.py 입니다.
# Path(__file__) -> app/utils/files.py
# .parent -> app/utils/
# .parent -> app/
# .parent -> 프로젝트 루트
STATIC_DIR = Path(__file__).parent.parent.parent / "static"


def save_upload_file_to_static(sub_dir: str, upload_file: UploadFile) -> str:
    """
    업로드된 파일을 static 디렉토리 하위의 지정된 경로에 저장합니다.

    - 파일명은 중복을 피하기 위해 UUID를 사용하여 새로 생성합니다.
    - 저장 후, 웹에서 접근 가능한 상대 경로를 반환합니다.

    Args:
        sub_dir (str): static/uploads/ 아래에 생성할 하위 디렉토리 이름 (예: "images", "files")
        upload_file (UploadFile): FastAPI를 통해 업로드된 파일 객체

    Returns:
        str: 저장된 파일의 웹 접근 경로 (예: "/static/uploads/files/some-uuid.xlsx")
    """
    #  1. 저장할 전체 디렉토리 경로를 생성합니다. (e.g., /path/to/project/static/uploads/files)
    upload_dir = STATIC_DIR / "uploads" / sub_dir
    os.makedirs(upload_dir, exist_ok=True)  # 디렉토리가 없으면 생성

    #  2. 파일명 중복을 피하기 위해 UUID와 원본 확장자를 조합하여 새 파일명을 만듭니다.
    file_extension = Path(upload_file.filename).suffix
    new_filename = f"{uuid.uuid4()}{file_extension}"
    save_path = upload_dir / new_filename

    #  3. 파일을 지정된 경로에 저장합니다.
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()

    #  4. 웹에서 접근 가능한 상대 경로를 반환합니다. (e.g., /static/uploads/files/new_filename.ext)
    #    os.path.join을 사용하여 OS에 맞는 경로 구분자로 생성합니다.
    web_path = os.path.join("/static", "uploads", sub_dir, new_filename).replace("\\", "/")

    return web_path
