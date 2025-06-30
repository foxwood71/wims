# tests/domains/test_shared_n.py

"""
'shared' 도메인 (애플리케이션 공용 데이터 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 SHARED 엔티티 (애플리케이션 버전, 이미지 유형, 이미지, 엔티티 이미지)의 CRUD 테스트.
- 파일 업로드 및 삭제, 대표 이미지 설정과 같은 비즈니스 로직 검증.
- 역할 기반 접근 제어(RBAC)를 포함한 다양한 사용자 역할에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""
import os
import tempfile
import pytest
import pytest_asyncio
# from datetime import date
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.domains.usr import models as usr_models
from app.domains.fms import models as fms_models
from app.domains.inv import models as inv_models
from app.domains.shared import models as shared_models
from app.domains.shared import schemas as shared_schemas
from app.domains.shared.crud import image_type as image_type_crud
from app.domains.shared.crud import image as image_crud
from app.domains.shared.crud import entity_image as entity_image_crud


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
    await entity_image_crud.create(db_session, obj_in=link_data)

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
    await entity_image_crud.create(db_session, obj_in=link_data)

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

    link1 = await entity_image_crud.create(db_session, obj_in=shared_schemas.EntityImageCreate(image_id=image1.id, entity_type="EQUIPMENT", entity_id=equipment.id))
    link2 = await entity_image_crud.create(db_session, obj_in=shared_schemas.EntityImageCreate(image_id=image2.id, entity_type="EQUIPMENT", entity_id=equipment.id))

    await admin_client.put(f"/api/v1/shared/entity_images/{link1.id}/set_main?entity_type=EQUIPMENT&entity_id={equipment.id}")
    await admin_client.put(f"/api/v1/shared/entity_images/{link2.id}/set_main?entity_type=EQUIPMENT&entity_id={equipment.id}")

    updated_link1_after = await entity_image_crud.get(db_session, id=link1.id)
    updated_link2_after = await entity_image_crud.get(db_session, id=link2.id)
    assert updated_link1_after.is_main_image is False
    assert updated_link2_after.is_main_image is True

    await admin_client.delete(f"/api/v1/shared/entity_images/{link1.id}")
    assert await entity_image_crud.get(db_session, id=link1.id) is None
    assert await image_crud.get(db_session, id=image1.id) is not None
