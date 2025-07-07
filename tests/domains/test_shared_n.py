# tests/domains/test_shared_n.py

"""
'shared' 도메인 (애플리케이션 공용 데이터 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 SHARED 엔티티 (애플리케이션 버전, 이미지 유형, 이미지, 엔티티 이미지)의 CRUD 테스트.
- 파일 업로드 및 삭제, 대표 이미지 설정과 같은 비즈니스 로직 검증.
- 역할 기반 접근 제어(RBAC)를 포함한 다양한 사용자 역할에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""
import os
import io
import tempfile  # tempfile.TemporaryDirectory() 픽스처 사용 시 필요
from pathlib import Path
from datetime import datetime, UTC

import pytest
import pytest_asyncio  # @pytest.mark.asyncio 데코레이터 및 비동기 픽스처 사용 시 필요
from sqlmodel import Session, select
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domains.usr import models as usr_models
from app.domains.fms import models as fms_models
from app.domains.inv import models as inv_models

from app.domains.shared import models as shared_models
from app.domains.shared import schemas as shared_schemas
from app.domains.shared import crud as shared_crud


@pytest.fixture(scope="module", autouse=True)
def set_test_upload_dir():
    """테스트를 위해 임시 파일 업로드 디렉토리를 설정하고, 테스트 완료 후 정리합니다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = tmpdir
        yield
        settings.UPLOAD_DIR = original_upload_dir


# --- 애플리케이션 버전 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_version_success_admin(admin_client: TestClient):
    """관리자 권한으로 새로운 애플리케이션 버전을 성공적으로 생성하는지 테스트합니다."""
    version_data = {"version": "1.0.0", "publish_date": "2025-05-01", "notes": "초기 릴리즈"}
    response = await admin_client.post("/api/v1/shared/versions", json=version_data)
    assert response.status_code == 201
    created_version = response.json()
    assert created_version["version"] == version_data["version"]


@pytest.mark.asyncio
async def test_create_version_unauthorized(authorized_client: TestClient, client: TestClient):
    """일반/비인증 사용자가 버전 생성을 시도할 때 권한 오류가 발생하는지 테스트합니다."""
    version_data = {"version": "1.0.1-unauth", "publish_date": "2025-05-02"}
    response_user = await authorized_client.post("/api/v1/shared/versions", json=version_data)
    assert response_user.status_code == 403
    response_no_auth = await client.post("/api/v1/shared/versions", json=version_data)
    assert response_no_auth.status_code == 401


# --- 이미지 유형 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_delete_image_type_restrict_by_image(admin_client: TestClient, db_session: Session, test_user: usr_models.User):
    """사용 중인 이미지 유형 삭제 시도 시 400 Bad Request를 반환하는지 테스트합니다."""
    img_type = shared_models.ImageType(name="사용중인 이미지 유형")
    db_session.add(img_type)
    await db_session.commit()
    await db_session.refresh(img_type)

    img = shared_models.Image(image_type_id=img_type.id, file_name="test.jpg", file_path="/fake/test.jpg", uploaded_by_user_id=test_user.id)
    db_session.add(img)
    await db_session.commit()

    response = await admin_client.delete(f"/api/v1/shared/image_types/{img_type.id}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete image type as it is currently in use."


# --- 이미지 파일 및 권한 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_upload_image_success(authorized_client: TestClient):
    """사용자가 이미지를 성공적으로 업로드하는지 테스트합니다."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_file.write(b"fake image data")
        temp_file_path = temp_file.name

    with open(temp_file_path, "rb") as f:
        files = {"file": (os.path.basename(temp_file_path), f, "image/png")}
        response = await authorized_client.post("/api/v1/shared/images", files=files)

    os.unlink(temp_file_path)

    assert response.status_code == 201
    uploaded_image = response.json()
    assert Path(uploaded_image["file_path"]).exists()


@pytest.mark.asyncio
async def test_image_permissions_as_admin(admin_client: TestClient, db_session: Session, get_password_hash_fixture):
    """[RBAC] 관리자는 소유권과 관계없이 모든 이미지를 수정/삭제할 수 있습니다."""
    other_user = usr_models.User(
        username="otheruser_for_admin_test",
        password_hash=get_password_hash_fixture("password"),
        role=usr_models.UserRole.GENERAL_USER
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    with tempfile.NamedTemporaryFile(dir=settings.UPLOAD_DIR, delete=False) as tmp:
        image = shared_models.Image(file_name="other.jpg", file_path=tmp.name, uploaded_by_user_id=other_user.id)
        db_session.add(image)
        await db_session.commit()
        await db_session.refresh(image)

    response_update = await admin_client.put(f"/api/v1/shared/images/{image.id}", json={"description": "Updated by admin"})
    assert response_update.status_code == 200

    response_delete = await admin_client.delete(f"/api/v1/shared/images/{image.id}")
    assert response_delete.status_code == 204


@pytest.mark.asyncio
async def test_image_permissions_as_owner(authorized_client: TestClient, test_user: usr_models.User, db_session: Session):
    """[RBAC] 일반 사용자는 자신이 올린 이미지를 수정/삭제할 수 있습니다."""
    with tempfile.NamedTemporaryFile(dir=settings.UPLOAD_DIR, delete=False) as tmp:
        image = shared_models.Image(file_name="my.jpg", file_path=tmp.name, uploaded_by_user_id=test_user.id)
        db_session.add(image)
        await db_session.commit()
        await db_session.refresh(image)

    response_update = await authorized_client.put(f"/api/v1/shared/images/{image.id}", json={"description": "Updated by owner"})
    assert response_update.status_code == 200

    response_delete = await authorized_client.delete(f"/api/v1/shared/images/{image.id}")
    assert response_delete.status_code == 204


@pytest.mark.asyncio
async def test_image_permissions_as_facility_manager(facility_manager_client: TestClient, db_session: Session, test_user: usr_models.User, test_facility, test_equipment_category):
    """[RBAC] 설비 관리자는 다른 사람이 올린 '설비' 이미지를 수정/삭제할 수 있습니다."""
    with tempfile.NamedTemporaryFile(dir=settings.UPLOAD_DIR, delete=False) as tmp:
        image = shared_models.Image(file_name="equipment_img.jpg", file_path=tmp.name, uploaded_by_user_id=test_user.id)
        db_session.add(image)
        await db_session.commit()
        await db_session.refresh(image)

    equipment = fms_models.Equipment(facility_id=test_facility.id, equipment_category_id=test_equipment_category.id, name="RBAC 테스트 설비", code="EQP-RBAC")
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    link_data = shared_schemas.EntityImageCreate(image_id=image.id, entity_type="EQUIPMENT", entity_id=equipment.id)
    await shared_crud.entity_image.create(db_session, obj_in=link_data)

    response_update = await facility_manager_client.put(f"/api/v1/shared/images/{image.id}", json={"description": "Updated by facility manager"})
    assert response_update.status_code == 200

    response_delete = await facility_manager_client.delete(f"/api/v1/shared/images/{image.id}")
    assert response_delete.status_code == 204


@pytest.mark.asyncio
async def test_image_permissions_as_unauthorized_role(
    authorized_client: TestClient,
    facility_manager_client: TestClient,  # [추가] 설비 관리자 클라이언트 주입
    db_session: Session,
    get_password_hash_fixture,
    test_user: usr_models.User,
    # [추가] 자재 이미지 생성을 위한 픽스처
    test_material_category
):
    """[RBAC] 관련 없는 역할을 가진 사용자는 다른 엔티티의 이미지를 수정/삭제할 수 없습니다."""
    # 시나리오 1: 일반 사용자가 다른 일반 사용자의 이미지 수정/삭제 시도
    other_user = usr_models.User(
        username="another_user",
        password_hash=get_password_hash_fixture("password"),
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    image_by_other = shared_models.Image(file_name="secret.jpg", file_path="/fake/secret.jpg", uploaded_by_user_id=other_user.id)
    db_session.add(image_by_other)
    await db_session.commit()
    await db_session.refresh(image_by_other)

    response_update = await authorized_client.put(f"/api/v1/shared/images/{image_by_other.id}", json={"description": "Attempt to update"})
    assert response_update.status_code == 403

    # --- [추가된 시나리오] ---
    # 시나리오 2: 설비 관리자가 자재 이미지 수정 시도
    material = inv_models.Material(  # 자재(Material) 모델 임포트 필요: from app.domains.inv import models as inv_models
        code="TEST-MAT-001",
        material_category_id=test_material_category.id,
        name="테스트 약품",
        unit_of_measure="kg"
    )
    material_image = shared_models.Image(file_name="material.jpg", file_path="/fake/material.jpg", uploaded_by_user_id=test_user.id)
    db_session.add_all([material, material_image])
    await db_session.commit()
    await db_session.refresh(material)
    await db_session.refresh(material_image)

    # 자재와 이미지를 연결
    link_data = shared_schemas.EntityImageCreate(image_id=material_image.id, entity_type="MATERIAL", entity_id=material.id)
    await shared_crud.entity_image.create(db_session, obj_in=link_data)

    # 설비 관리자가 자재 이미지 수정 시도 -> 실패
    response_fm_update = await facility_manager_client.put(f"/api/v1/shared/images/{material_image.id}", json={"description": "FM trying to update material image"})
    assert response_fm_update.status_code == 403


# --- 엔티티-이미지 연결 관리 엔드포인트 테스트 ---

@pytest_asyncio.fixture
async def setup_for_entity_image_test(db_session: Session, test_user: usr_models.User, test_facility, test_equipment_category):
    """엔티티-이미지 테스트를 위한 기본 객체들을 생성하는 픽스처"""
    image1 = shared_models.Image(file_name="image1.jpg", file_path="/fake/image1.jpg", uploaded_by_user_id=test_user.id)
    image2 = shared_models.Image(file_name="image2.jpg", file_path="/fake/image2.jpg", uploaded_by_user_id=test_user.id)
    db_session.add_all([image1, image2])

    equipment = fms_models.Equipment(facility_id=test_facility.id, equipment_category_id=test_equipment_category.id, name="이미지연결테스트설비", code="EQP-IMG-TEST")
    db_session.add(equipment)

    await db_session.commit()
    await db_session.refresh(image1)
    await db_session.refresh(image2)
    await db_session.refresh(equipment)

    return image1, image2, equipment


@pytest.mark.asyncio
async def test_entity_image_link_and_read(authorized_client: TestClient, setup_for_entity_image_test):
    """엔티티에 이미지를 연결하고, 해당 엔티티로 이미지를 조회하는 것을 테스트합니다."""
    image1, image2, equipment = setup_for_entity_image_test

    await authorized_client.post("/api/v1/shared/entity_images", json={"image_id": image1.id, "entity_type": "EQUIPMENT", "entity_id": equipment.id})
    await authorized_client.post("/api/v1/shared/entity_images", json={"image_id": image2.id, "entity_type": "EQUIPMENT", "entity_id": equipment.id})

    response_read = await authorized_client.get(f"/api/v1/shared/entity_images/by_entity/EQUIPMENT/{equipment.id}")
    assert response_read.status_code == 200
    linked_images = response_read.json()
    assert len(linked_images) == 2
    assert {li['image_id'] for li in linked_images} == {image1.id, image2.id}


@pytest.mark.asyncio
async def test_create_entity_image_with_nonexistent_image(authorized_client: TestClient, setup_for_entity_image_test):
    """존재하지 않는 이미지 ID로 엔티티-이미지 연결 시 404를 반환하는지 테스트합니다."""
    _, _, equipment = setup_for_entity_image_test
    link_data = {"image_id": 99999, "entity_type": "EQUIPMENT", "entity_id": equipment.id}
    response = await authorized_client.post("/api/v1/shared/entity_images", json=link_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_set_main_image_and_delete_link(admin_client: TestClient, db_session: Session, setup_for_entity_image_test):
    """대표 이미지를 설정하고, 연결을 해제하는 것을 테스트합니다."""
    image1, image2, equipment = setup_for_entity_image_test

    link1 = await shared_crud.entity_image.create(db_session, obj_in=shared_schemas.EntityImageCreate(image_id=image1.id, entity_type="EQUIPMENT", entity_id=equipment.id))
    link2 = await shared_crud.entity_image.create(db_session, obj_in=shared_schemas.EntityImageCreate(image_id=image2.id, entity_type="EQUIPMENT", entity_id=equipment.id))

    await admin_client.put(f"/api/v1/shared/entity_images/{link1.id}/set_main?entity_type=EQUIPMENT&entity_id={equipment.id}")
    await admin_client.put(f"/api/v1/shared/entity_images/{link2.id}/set_main?entity_type=EQUIPMENT&entity_id={equipment.id}")

    updated_link1_after = await shared_crud.entity_image.get(db_session, id=link1.id)
    updated_link2_after = await shared_crud.entity_image.get(db_session, id=link2.id)
    assert updated_link1_after.is_main_image is False
    assert updated_link2_after.is_main_image is True

    await admin_client.delete(f"/api/v1/shared/entity_images/{link1.id}")
    assert await shared_crud.entity_image.get(db_session, id=link1.id) is None
    assert await shared_crud.image.get(db_session, id=image1.id) is not None


# ==============================================================================
# 이미지(Image) 및 엔티티-이미지(EntityImage) 관련 API 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_read_entity_images_for_entity_with_image_details(
    admin_client: TestClient,          # 1. '관리자' 클라이언트 (테스트 환경 설정용)
    authorized_client: TestClient,     # 2. '일반 사용자' 클라이언트 (주요 기능 테스트용)
    db_session: Session,
    test_user: usr_models.User,        # 3. '일반 사용자' 객체
):
    """
    특정 엔티티에 연결된 이미지 조회 시, 이미지 상세 정보가 함께 반환되는지 테스트합니다.
    """
    # 단계 1: (관리자 권한으로) 테스트에 필요한 '이미지 유형' 미리 생성
    image_type_create = {
        "name": "설비사진",
        "description": "설비의 외형 사진"
    }
    response = await admin_client.post(
        "/api/v1/shared/image_types",
        json=image_type_create
    )
    assert response.status_code == 201
    image_type_id = response.json()["id"]

    # 단계 2: (일반 사용자 권한으로) 이미지 레코드 생성 (DB 직접 추가)
    dummy_file_name = "test_equipment_photo.jpg"
    dummy_file_path = str(Path(settings.UPLOAD_DIR) / dummy_file_name)

    with open(dummy_file_path, "wb") as f:
        f.write(b"dummy image content")

    image_create_data = shared_schemas.ImageCreate(
        image_type_id=image_type_id,
        file_name=dummy_file_name,
        file_path=dummy_file_path,
        file_size_kb=10,
        mime_type="image/jpeg",
        description="테스트 설비 사진",
        uploaded_by_user_id=test_user.id,  # 일반 사용자의 ID를 사용
        uploaded_at=datetime.now(UTC),
        department_id=test_user.department_id
    )
    # SQLModel v2 호환성을 위해 from_orm 대신 model_validate 사용
    db_image = shared_models.Image.model_validate(image_create_data)
    db_session.add(db_image)
    await db_session.commit()
    await db_session.refresh(db_image)
    image_id = db_image.id

    # 단계 3: (일반 사용자 권한으로) 엔티티-이미지 연결 생성
    entity_type = "EQUIPMENT"
    entity_id = 999  # 가상의 설비 ID
    entity_image_create = {
        "image_id": str(image_id),  # JSON으로 보내기 위해 str로 변환
        "entity_type": entity_type,
        "entity_id": entity_id,
        "is_main_image": True
    }
    response = await authorized_client.post(  # 일반 사용자 클라이언트로 호출
        "/api/v1/shared/entity_images",
        json=entity_image_create
    )
    assert response.status_code == 201

    # 단계 4: (권한 없이 또는 일반 사용자 권한으로) 설비에 연결된 이미지 정보 조회
    response = await authorized_client.get(
        f"/api/v1/shared/entity_images/by_entity/{entity_type}/{entity_id}"
    )
    assert response.status_code == 200
    linked_images = response.json()

    # --- 이하 검증 로직은 동일 ---
    assert len(linked_images) == 1
    linked_image_data = linked_images[0]

    assert linked_image_data["image_id"] == image_id
    assert "image" in linked_image_data
    assert linked_image_data["image"] is not None

    assert linked_image_data["image"]["id"] == image_id
    assert linked_image_data["image"]["file_name"] == dummy_file_name
    assert linked_image_data["image"]["file_path"] == dummy_file_path
    assert linked_image_data["image"]["mime_type"] == "image/jpeg"
    assert linked_image_data["image"]["file_size_kb"] == 10
    assert linked_image_data["image"]["description"] == "테스트 설비 사진"
    assert linked_image_data["image"]["uploaded_by_user_id"] == test_user.id


# ==============================================================================
# 파일(File) 관련 API 테스트 (여기에 추가)
# ==============================================================================
@pytest.mark.asyncio
async def test_upload_file_success(
    authorized_client: TestClient,
    db_session: Session,
    test_user: usr_models.User
):
    """
    일반 사용자가 파일을 성공적으로 업로드하는지 테스트합니다.
    """
    # 단계 1: 테스트용 더미 파일 준비
    dummy_file_name = "test_upload.txt"
    dummy_content = b"This is a test file for WIMS."
    file_data = {"upload_file": (dummy_file_name, io.BytesIO(dummy_content), "text/plain")}

    # 단계 2: 파일 업로드 API 호출
    response = await authorized_client.post("/api/v1/shared/files/upload", files=file_data)

    # 단계 3: 응답 검증
    assert response.status_code == 201, f"응답 실패: {response.text}"
    response_data = response.json()

    assert "id" in response_data
    assert "url" in response_data
    assert response_data["message"] == "File uploaded successfully."

    # 단계 4: 데이터베이스에 파일 레코드가 생성되었는지 확인
    file_id = response_data["id"]
    statement = select(shared_models.File).where(shared_models.File.id == file_id)
    result = await db_session.execute(statement)
    db_file = result.scalar_one_or_none()

    assert db_file is not None
    assert db_file.name == dummy_file_name
    assert db_file.content_type == "text/plain"
    assert db_file.size == len(dummy_content)
    assert db_file.uploaded_by_user_id == test_user.id

    # 단계 5: 실제 파일 시스템에 파일이 생성되었는지 확인
    expected_path = Path(settings.UPLOAD_DIR) / db_file.path
    assert expected_path.exists()
    assert expected_path.read_bytes() == dummy_content

    print(f"\n테스트 성공: 파일 '{dummy_file_name}'이 성공적으로 업로드 되었습니다.")


@pytest.mark.asyncio
async def test_download_file_success(authorized_client: TestClient):
    """
    업로드된 파일을 성공적으로 다운로드하는지 테스트합니다.
    """
    # 단계 1: 테스트용 파일 업로드
    dummy_file_name = "download_test.log"
    dummy_content = b"Log file content for download test."
    file_data = {"upload_file": (dummy_file_name, io.BytesIO(dummy_content), "text/x-log")}

    upload_response = await authorized_client.post("/api/v1/shared/files/upload", files=file_data)
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    # 단계 2: 파일 다운로드 API 호출
    download_response = await authorized_client.get(f"/api/v1/shared/files/download/{file_id}")

    # 단계 3: 응답 검증
    assert download_response.status_code == 200
    assert download_response.content == dummy_content
    assert "attachment" in download_response.headers["content-disposition"]
    assert f'filename="{dummy_file_name}"' in download_response.headers["content-disposition"]

    print(f"\n테스트 성공: 파일 '{dummy_file_name}'을 성공적으로 다운로드했습니다.")


@pytest.mark.asyncio
async def test_download_non_existent_file(authorized_client: TestClient):
    """
    존재하지 않는 파일을 다운로드 시 404 에러를 반환하는지 테스트합니다.
    """
    non_existent_id = 999999999
    response = await authorized_client.get(f"/api/v1/shared/files/download/{non_existent_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found."

    print("\n테스트 성공: 존재하지 않는 파일 다운로드 시 404 에러를 올바르게 반환합니다.")


@pytest.mark.asyncio
async def test_read_file_metadata_success(authorized_client: TestClient):
    """
    업로드된 파일의 메타데이터를 성공적으로 조회하는지 테스트합니다.
    """
    # 단계 1: 테스트용 파일 업로드
    dummy_file_name = "metadata_test.json"
    dummy_content = b'{"key": "value"}'
    file_data = {"upload_file": (dummy_file_name, io.BytesIO(dummy_content), "application/json")}

    upload_response = await authorized_client.post("/api/v1/shared/files/upload", files=file_data)
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]

    # 단계 2: 파일 메타데이터 조회 API 호출
    metadata_response = await authorized_client.get(f"/api/v1/shared/files/{file_id}")

    # 단계 3: 응답 검증
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()

    assert metadata["id"] == file_id
    assert metadata["name"] == dummy_file_name
    assert metadata["content_type"] == "application/json"
    assert metadata["size"] == len(dummy_content)
    assert "url" in metadata
    assert "created_at" in metadata

    print(f"\n테스트 성공: 파일 '{dummy_file_name}'의 메타데이터를 성공적으로 조회했습니다.")
