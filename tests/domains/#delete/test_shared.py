# tests/domains/test_shared.py

"""
'shared' 도메인 (애플리케이션 공용 데이터 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 SHARED 엔티티 (애플리케이션 버전, 이미지 유형, 이미지, 엔티티 이미지)의 CRUD 테스트.
- 파일 업로드 및 삭제, 대표 이미지 설정과 같은 비즈니스 로직 검증.
- 다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""
import os
import tempfile  # 임시 파일 생성을 위해
import pytest
from datetime import date, datetime
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import Session

# 다른 도메인의 모델 임포트 추가
from app.core.config import settings

# loc_models와 usr_models는 test_shared.py의 픽스처에서 사용됩니다.
from app.domains.loc import models as loc_models
from app.domains.usr import models as usr_models  # usr_models 임포트 추가

# SHARED 도메인의 CRUD, 모델, 스키마
from app.domains.shared import models as shared_models
from app.domains.shared import schemas as shared_schemas
from app.domains.shared.crud import version as version_crud  # CRUD 직접 사용 (테스트 셋업용)
from app.domains.shared.crud import image_type as image_type_crud
from app.domains.shared.crud import image as image_crud
from app.domains.shared.crud import entity_image as entity_image_crud


# --- 테스트 환경 설정 (파일 업로드 디렉토리 Mocking) ---
# 실제 파일 시스템에 파일을 생성하는 대신, 테스트용 임시 디렉토리를 사용하도록 설정합니다.
# `app.core.config.settings.UPLOAD_DIR`을 직접 변경하는 대신,
# 테스트 런타임에 이 값을 설정하는 것이 더 견고합니다.
# 하지만 FastAPI 앱 초기화 시 settings가 이미 로드되므로,
# `conftest.py`에서 `client` 픽스처가 생성될 때 settings를 오버라이드하거나
# 테스트용 `UPLOAD_DIRECTORY` 변수를 사용하도록 라우터에서 설정해야 합니다.
# 현재 라우터는 `settings.UPLOAD_DIR`을 사용하므로, 여기에 동적으로 설정하는 것을 가정합니다.
# 실제 프로덕션 코드에 영향을 주지 않으려면 `main_app.dependency_overrides`를 활용해야 합니다.
# 간편화를 위해 테스트 시점에 `settings.UPLOAD_DIR`을 변경하는 방식을 사용합니다.
@pytest.fixture(scope="module", autouse=True)  # 모든 테스트 파일에서 자동 사용
def set_test_upload_dir():
    """
    테스트를 위해 임시 파일 업로드 디렉토리를 설정하고, 테스트 완료 후 정리합니다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # settings.UPLOAD_DIR이 설정되어 있지 않다면 생성
        original_upload_dir = None
        if hasattr(settings, 'UPLOAD_DIR'):
            original_upload_dir = settings.UPLOAD_DIR

        settings.UPLOAD_DIR = tmpdir  # 임시 디렉토리로 설정
        # 라우터 파일에서 UPLOAD_DIRECTORY가 `settings.UPLOAD_DIR`에 종속되므로
        # 라우터를 다시 로드하거나, 테스트 시작 전에 `main.py`를 다시 로드해야 함.
        # (실제 애플리케이션에서는 앱 시작 전에 설정이 고정되므로,
        # `TestClient` 내부에서 `app.main`을 다시 로드하는 방식으로 해결할 수 있습니다.)

        # 또한, `app/domains/shared/routers.py`에서 `UPLOAD_DIRECTORY` Path 객체를
        # 함수 스코프 픽스처처럼 테스트마다 새로 생성하도록 변경하는 것이 더 견고합니다.
        # 예: UPLOAD_DIRECTORY = Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        # 이 부분은 `app/domains/shared/routers.py`의 `UPLOAD_DIRECTORY`가
        # `Path(settings.UPLOAD_DIR)`을 사용하도록 구현되어 있음을 전제로 합니다.

        yield
        # 테스트 완료 후에는 자동으로 임시 디렉토리가 삭제됩니다.
        if original_upload_dir:
            settings.UPLOAD_DIR = original_upload_dir  # 원래 값으로 되돌림


# --- 애플리케이션 버전 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_version_success_admin(
    admin_client: TestClient,  # 관리자로 인증된 클라이언트
):
    """
    관리자 권한으로 새로운 애플리케이션 버전을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_version_success_admin ---")
    version_data = {
        "version": "1.0.0",
        "publish_date": "2025-05-01",
        "notes": "초기 릴리즈"
    }
    response = await admin_client.post("/api/v1/shared/versions", json=version_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_version = response.json()
    assert created_version["version"] == version_data["version"]
    assert created_version["publish_date"] == version_data["publish_date"]
    assert "id" in created_version
    print("test_create_version_success_admin passed.")


@pytest.mark.asyncio
async def test_create_version_duplicate_version_admin(
    admin_client: TestClient,
    db_session: Session  # 데이터베이스에 버전 미리 생성하기 위해
):
    """
    관리자 권한으로 이미 존재하는 버전 번호의 버전을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_version_duplicate_version_admin ---")
    existing_version = shared_models.Version(version="0.9.0", publish_date=date(2025, 4, 1))
    db_session.add(existing_version)
    await db_session.commit()
    await db_session.refresh(existing_version)

    version_data = {
        "version": "0.9.0",  # 중복 버전
        "publish_date": "2025-04-15",
    }
    response = await admin_client.post("/api/v1/shared/versions", json=version_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Version already exists"
    print("test_create_version_duplicate_version_admin passed.")


@pytest.mark.asyncio
async def test_read_versions_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 버전 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_versions_success ---")
    v1 = shared_models.Version(version="2.0.0", publish_date=date(2025, 1, 1))
    v2 = shared_models.Version(version="2.1.0", publish_date=date(2025, 2, 1))
    db_session.add(v1)
    db_session.add(v2)
    await db_session.commit()
    await db_session.refresh(v1)
    await db_session.refresh(v2)

    response = await client.get("/api/v1/shared/versions")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    versions_list = response.json()
    assert len(versions_list) >= 2
    assert any(v["version"] == "2.0.0" for v in versions_list)
    assert any(v["version"] == "2.1.0" for v in versions_list)
    print("test_read_versions_success passed.")


# --- 이미지 유형 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_image_type_success_admin(
    admin_client: TestClient,
):
    """
    관리자 권한으로 새로운 이미지 유형을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_image_type_success_admin ---")
    image_type_data = {
        "name": "설비 사진",
        "description": "다양한 설비 사진"
    }
    response = await admin_client.post("/api/v1/shared/image_types", json=image_type_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_type = response.json()
    assert created_type["name"] == image_type_data["name"]
    assert "id" in created_type
    print("test_create_image_type_success_admin passed.")


@pytest.mark.asyncio
async def test_create_image_type_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 존재하는 이름의 이미지 유형 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_image_type_duplicate_name_admin ---")
    existing_type = shared_models.ImageType(name="기존 이미지 유형")
    db_session.add(existing_type)
    await db_session.commit()
    await db_session.refresh(existing_type)

    image_type_data = {
        "name": "기존 이미지 유형",  # 중복 이름
    }
    response = await admin_client.post("/api/v1/shared/image_types", json=image_type_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Image type with this name already exists"
    print("test_create_image_type_duplicate_name_admin passed.")


# --- 이미지 파일 정보 관리 엔드포인트 테스트 (파일 업로드 포함) ---

@pytest.mark.asyncio
async def test_upload_image_success_user(
    authorized_client: TestClient,  # 일반 사용자로 인증된 클라이언트
    test_user: usr_models.User,  # 업로드 사용자 확인용
    db_session: Session  # image_type 생성을 위해
):
    """
    활성 사용자 권한으로 이미지를 성공적으로 업로드하고 DB 기록을 생성하는지 테스트합니다.
    """
    print("\n--- Running test_upload_image_success_user ---")
    # 이미지 유형 생성 (FK)
    img_type = shared_models.ImageType(name="업로드 테스트 이미지 유형")
    db_session.add(img_type)
    await db_session.commit()
    await db_session.refresh(img_type)

    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_file.write(b"fake image data")
        temp_file_path = temp_file.name

    # ensure_dir_exists() is called in router for safety, but not directly tested here.
    # The actual Path creation logic is in the router.

    # 이미지 업로드
    files = {"file": (os.path.basename(temp_file_path), open(temp_file_path, "rb"), "image/png")}
    form_data = {
        "image_type_id": str(img_type.id),  # FastAPI UploadFile과 JSON 필드 혼합 시 str 필요
        "description": "테스트 이미지 입니다."
    }
    response = await authorized_client.post("/api/v1/shared/images", files=files, data=form_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    # 임시 파일 닫기
    if not temp_file.closed:
        temp_file.close()
    os.unlink(temp_file_path)  # 사용 후 임시 파일 삭제

    assert response.status_code == 201
    uploaded_image = response.json()
    assert uploaded_image["file_name"].startswith(datetime.now().strftime('%Y%m%d%H%M%S'))  # 자동 생성 파일명
    assert uploaded_image["file_path"].endswith(uploaded_image["file_name"])  # 경로에 파일명 포함
    assert uploaded_image["file_size_kb"] == 1  # 15바이트 / 1024 = 0 (정수 나눗셈)
    assert uploaded_image["mime_type"] == "image/png"
    assert uploaded_image["uploaded_by_user_id"] == test_user.id
    assert uploaded_image["image_type_id"] == img_type.id
    assert "id" in uploaded_image

    # 실제 파일이 저장되었는지 확인
    stored_file_path = Path(uploaded_image["file_path"])
    assert stored_file_path.exists()
    assert stored_file_path.read_bytes() == b"fake image data"

    # 테스트 완료 후 파일도 정리 (conftest의 set_test_upload_dir이 처리)
    print("test_upload_image_success_user passed.")


@pytest.mark.asyncio
async def test_delete_image_success_admin(
    admin_client: TestClient,
    db_session: Session,
    test_user: usr_models.User  # 업로드 사용자
):
    """
    관리자 권한으로 이미지 정보 및 실제 파일을 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_image_success_admin ---")
    # 1. 이미지 유형 생성
    img_type = shared_models.ImageType(name="삭제 테스트 이미지 유형")
    db_session.add(img_type)
    await db_session.commit()
    await db_session.refresh(img_type)

    # 2. 임시 파일 생성 및 DB 레코드 준비
    test_content = b"data to be deleted"
    with tempfile.NamedTemporaryFile(dir=settings.UPLOAD_DIR, suffix=".txt", delete=False) as temp_file:
        temp_file.write(test_content)
        temp_file_path = temp_file.name

    # DB 레코드 생성
    image_data = shared_models.Image(
        image_type_id=img_type.id,
        name=os.path.basename(temp_file_path),
        path=str(temp_file_path),
        size=len(test_content) // 1024,
        content_type="text/plain",
        description="삭제될 이미지",
        uploaded_by_user_id=test_user.id,
        uploaded_at=datetime.now()
    )
    db_session.add(image_data)
    await db_session.commit()
    await db_session.refresh(image_data)

    # 실제 파일이 존재하는지 확인
    assert Path(temp_file_path).exists()

    # 3. 이미지 삭제 요청
    response = await admin_client.delete(f"/api/v1/shared/images/{image_data.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 4. DB 레코드가 삭제되었는지 확인
    deleted_image_db = await image_crud.get(db_session, id=image_data.id)
    assert deleted_image_db is None

    # 5. 실제 파일이 삭제되었는지 확인
    assert not Path(temp_file_path).exists()
    print("test_delete_image_success_admin passed.")
