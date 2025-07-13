# tests/domains/test_shared_n.py

"""
'shared' 도메인 (애플리케이션 공용 데이터 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 SHARED 엔티티 (애플리케이션 버전, 리소스 유형, 리소스, 엔티티 리소스)의 CRUD 테스트.
- 파일 업로드 및 삭제, 대표 리소스 설정과 같은 비즈니스 로직 검증.
- 역할 기반 접근 제어(RBAC)를 포함한 다양한 사용자 역할에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""
import tempfile  # tempfile.TemporaryDirectory() 픽스처 사용 시 필요
from pathlib import Path
from datetime import datetime, UTC

import pytest
import pytest_asyncio  # @pytest.mark.asyncio 데코레이터 및 비동기 픽스처 사용 시 필요
from sqlmodel.ext.asyncio.session import AsyncSession
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


@pytest_asyncio.fixture
async def test_resource_category(db_session: AsyncSession) -> shared_models.ResourceCategory:
    """테스트용 리소스 카테고리를 생성하는 픽스처"""
    category = shared_models.ResourceCategory(name="테스트 카테고리", description="테스트용입니다.")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category

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


# --- 리소스 유형 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_delete_resource_category_restrict_by_resource(
    admin_client: TestClient, db_session: AsyncSession, test_user: usr_models.User
):
    """사용 중인 리소스 유형 삭제 시도 시 400 Bad Request를 반환하는지 테스트합니다."""
    test_resource_category = shared_models.ResourceCategory(name="사용중인 리소스 유형")
    db_session.add(test_resource_category)
    await db_session.commit()
    await db_session.refresh(test_resource_category)

    resource = shared_models.Resource(
        type=shared_models.ResourceType.FILE,
        category_id=test_resource_category.id,  # 사용중인 카테고리 ID
        name="test.txt",
        path="/fake/test.txt",
        size_kb=1,
        content_type="text/plain",
        uploader_id=test_user.id
    )
    db_session.add(resource)
    await db_session.commit()

    # 사용 중인 카테고리 삭제 시도
    response = await admin_client.delete(f"/api/v1/shared/resources/category-types/{test_resource_category.id}")

    assert response.status_code == 400
    assert "Cannot delete this category" in response.json()["detail"]


# --- 리소스 파일 및 권한 관리 엔드포인트 테스트 ---
@pytest.mark.asyncio
async def test_upload_resource_success(authorized_client: TestClient, test_resource_category: shared_models.ResourceCategory):
    """
    사용자가 리소스(이미지)를 성공적으로 업로드하는지 테스트합니다.
    """
    dummy_file_name = "test_image.png"
    # form-data로 전송할 데이터를 구성합니다.
    files = {"file": (dummy_file_name, b"fake image data", "image/png")}
    data = {"category_id": test_resource_category.id, "description": "테스트 업로드"}

    # 새로운 통합 엔드포인트로 리소스를 업로드합니다.
    response = await authorized_client.post("/api/v1/shared/resources", files=files, data=data)

    # 검증: 201 Created와 반환된 ResourceRead 스키마를 확인합니다.
    assert response.status_code == 201
    uploaded_resource = response.json()

    assert uploaded_resource["name"] == dummy_file_name
    assert uploaded_resource["description"] == "테스트 업로드"
    assert uploaded_resource["category_id"] == test_resource_category.id
    assert uploaded_resource["type"] == "IMAGE"  # 서비스 로직에서 content_type 기반으로 추론해야 함
    assert "id" in uploaded_resource
    assert "url" in uploaded_resource
    assert Path(settings.UPLOAD_DIR, Path(uploaded_resource["path"]).name).exists()


@pytest.mark.asyncio
async def test_resource_permissions_as_admin(
    admin_client: TestClient,
    db_session: AsyncSession,
    get_password_hash_fixture,
    test_resource_category: shared_models.ResourceCategory
):
    """[수정] RBAC: 관리자는 소유권과 관계없이 모든 리소스를 수정/삭제할 수 있습니다."""
    # 다른 사용자를 생성합니다.
    other_user = usr_models.User(
        user_id="otheruser_for_admin_test",
        password_hash=get_password_hash_fixture("password"),
        role=usr_models.UserRole.GENERAL_USER
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # 다른 사용자가 업로드한 리소스를 생성합니다.
    with tempfile.NamedTemporaryFile(dir=settings.UPLOAD_DIR, delete=False) as tmp:
        resource = shared_models.Resource(
            type=shared_models.ResourceType.FILE,
            name="other.jpg",
            path=tmp.name,
            size_kb=1,
            content_type="image/jpeg",
            uploader_id=other_user.id,
            category_id=test_resource_category.id
        )
        db_session.add(resource)
        await db_session.commit()
        await db_session.refresh(resource)

    # 관리자가 해당 리소스를 수정하고 삭제합니다.
    response_update = await admin_client.put(f"/api/v1/shared/resources/{resource.id}", json={"description": "Updated by admin"})
    assert response_update.status_code == 200

    response_delete = await admin_client.delete(f"/api/v1/shared/resources/{resource.id}")
    assert response_delete.status_code == 204


@pytest.mark.asyncio
async def test_resource_permissions_as_owner(
    authorized_client: TestClient,
    test_user: usr_models.User,
    db_session: AsyncSession,
    test_resource_category: shared_models.ResourceCategory
):
    """[수정] RBAC: 일반 사용자는 자신이 올린 리소스를 수정/삭제할 수 있습니다."""
    with tempfile.NamedTemporaryFile(dir=settings.UPLOAD_DIR, delete=False) as tmp:
        resource = shared_models.Resource(
            type=shared_models.ResourceType.FILE,
            name="my.jpg", path=tmp.name, size_kb=1,
            content_type="image/jpeg",
            uploader_id=test_user.id,
            category_id=test_resource_category.id
        )
        db_session.add(resource)
        await db_session.commit()
        await db_session.refresh(resource)

    response_update = await authorized_client.put(f"/api/v1/shared/resources/{resource.id}", json={"description": "Updated by owner"})
    assert response_update.status_code == 200

    response_delete = await authorized_client.delete(f"/api/v1/shared/resources/{resource.id}")
    assert response_delete.status_code == 204


@pytest.mark.asyncio
async def test_resource_permissions_as_facility_manager(
    facility_manager_client: TestClient,
    db_session: AsyncSession,
    test_user: usr_models.User,
    test_resource_category: shared_models.ResourceCategory,
    test_facility,
    test_equipment_category
):
    """[수정] RBAC: 설비 관리자는 다른 사람이 올린 '설비' 리소스를 수정/삭제할 수 있습니다."""
    # 다른 일반 유저가 올린 리소스를 생성합니다.
    with tempfile.NamedTemporaryFile(dir=settings.UPLOAD_DIR, delete=False) as tmp:
        resource = shared_models.Resource(
            type=shared_models.ResourceType.IMAGE,
            name="equipment_res.jpg",
            path=tmp.name,
            size_kb=1,
            content_type="image/jpeg",
            uploader_id=test_user.id,
            category_id=test_resource_category.id
        )
        db_session.add(resource)
        await db_session.commit()
        await db_session.refresh(resource)

    # 설비(Equipment)를 생성하고 위 리소스와 연결합니다.
    equipment = fms_models.Equipment(facility_id=test_facility.id, equipment_category_id=test_equipment_category.id, name="RBAC 테스트 설비", code="EQP-RBAC")
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    link_data = shared_schemas.EntityResourceCreate(resource_id=resource.id, entity_type="EQUIPMENT", entity_id=equipment.id)
    await shared_crud.entity_resource.create(db_session, obj_in=link_data)

    # 설비 관리자가 해당 설비의 리소스를 수정/삭제합니다.
    response_update = await facility_manager_client.put(f"/api/v1/shared/resources/{resource.id}", json={"description": "Updated by facility manager"})
    assert response_update.status_code == 200

    response_delete = await facility_manager_client.delete(f"/api/v1/shared/resources/{resource.id}")
    assert response_delete.status_code == 204


@pytest.mark.asyncio
async def test_image_permissions_as_unauthorized_role(
    authorized_client: TestClient,
    facility_manager_client: TestClient,  # [추가] 설비 관리자 클라이언트 주입
    db_session: AsyncSession,
    get_password_hash_fixture,
    test_user: usr_models.User,
    test_material_category,
    test_resource_category: shared_models.ResourceCategory
):
    """[RBAC] 관련 없는 역할을 가진 사용자는 다른 엔티티의 이미지를 수정/삭제할 수 없습니다."""
    # 시나리오 1: 일반 사용자가 다른 일반 사용자의 리소스 수정/삭제 시도
    other_user = usr_models.User(
        user_id="another_user",
        password_hash=get_password_hash_fixture("password"),
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    resource_by_other = shared_models.Resource(
        type=shared_models.ResourceType.FILE,
        name="secret.jpg",
        path="/fake/secret.jpg",
        size_kb=1,
        content_type="image/jpeg",
        uploader_id=other_user.id,
        category_id=test_resource_category.id
    )
    db_session.add(resource_by_other)
    await db_session.commit()
    await db_session.refresh(resource_by_other)

    response_update = await authorized_client.put(
        f"/api/v1/shared/resources/{resource_by_other.id}",
        json={"description": "Attempt to update"}
    )
    assert response_update.status_code == 403

    # --- [추가된 시나리오] ---
    # 시나리오 2: 설비 관리자가 자재 리소스 수정 시도
    material = inv_models.Material(  # 자재(Material) 모델 임포트 필요: from app.domains.inv import models as inv_models
        code="TEST-MAT-001",
        material_category_id=test_material_category.id,
        name="테스트 약품",
        unit_of_measure="kg"
    )

    material_resource = shared_models.Resource(
        type=shared_models.ResourceType.IMAGE,
        name="material.jpg",
        path="/fake/material.jpg",
        size_kb=1,
        content_type="image/jpeg",
        uploader_id=test_user.id,
        category_id=test_resource_category.id
    )

    db_session.add_all([material, material_resource])
    await db_session.commit()
    await db_session.refresh(material)
    await db_session.refresh(material_resource)

    # 자재와 이미지를 연결
    link_data = shared_schemas.EntityResourceCreate(
        resource_id=material_resource.id,  # image_id -> resource_id
        entity_type="MATERIAL",
        entity_id=material.id
    )
    await shared_crud.entity_resource.create(db_session, obj_in=link_data)

    # 설비 관리자가 자재 리소스 수정 시도 -> 실패
    response_fm_update = await facility_manager_client.put(
        f"/api/v1/shared/resources/{material_resource.id}",  # 엔드포인트 수정
        json={"description": "FM trying to update material image"}
    )
    assert response_fm_update.status_code == 403


# --- 엔티티-리소스 연결 관리 엔드포인트 테스트 ---
@pytest_asyncio.fixture
async def setup_for_entity_resource_test(
    db_session: AsyncSession,
    test_user: usr_models.User,
    test_facility,
    test_equipment_category,
    test_resource_category: shared_models.ResourceCategory
):
    """[수정] 엔티티-리소스 테스트를 위한 기본 객체들을 생성하는 픽스처"""
    resource1 = shared_models.Resource(
        type=shared_models.ResourceType.IMAGE,
        name="res1.jpg",
        path="/fake/res1.jpg",
        size_kb=1,
        content_type="image/jpeg",
        uploader_id=test_user.id,
        category_id=test_resource_category.id
    )
    resource2 = shared_models.Resource(
        type=shared_models.ResourceType.IMAGE,
        name="res2.jpg",
        path="/fake/res2.jpg",
        size_kb=1,
        content_type="image/jpeg",
        uploader_id=test_user.id,
        category_id=test_resource_category.id
    )
    db_session.add_all([resource1, resource2])

    equipment = fms_models.Equipment(
        facility_id=test_facility.id, equipment_category_id=test_equipment_category.id, name="리소스연결테스트설비", code="EQP-RES-TEST"
    )
    db_session.add(equipment)

    await db_session.commit()
    await db_session.refresh(resource1)
    await db_session.refresh(resource2)
    await db_session.refresh(equipment)

    return resource1, resource2, equipment


@pytest.mark.asyncio
async def test_entity_resource_link_and_read(authorized_client: TestClient, setup_for_entity_resource_test):
    """[수정] 엔티티에 리소스를 연결하고, 해당 엔티티로 리소스를 조회하는 것을 테스트합니다."""
    resource1, resource2, equipment = setup_for_entity_resource_test

    # 새로운 엔드포인트와 페이로드로 리소스를 연결합니다.
    await authorized_client.post("/api/v1/shared/resources/entity", json={"resource_id": resource1.id, "entity_type": "EQUIPMENT", "entity_id": equipment.id})
    await authorized_client.post("/api/v1/shared/resources/entity", json={"resource_id": resource2.id, "entity_type": "EQUIPMENT", "entity_id": equipment.id})

    # 새로운 엔드포인트로 연결된 리소스 목록을 조회합니다.
    response_read = await authorized_client.get(f"/api/v1/shared/resources/entity/EQUIPMENT/{equipment.id}")
    assert response_read.status_code == 200
    linked_resources = response_read.json()

    # 검증: 반환된 데이터의 구조와 값을 확인합니다.
    assert len(linked_resources) == 2
    assert {li['resource_id'] for li in linked_resources} == {resource1.id, resource2.id}
    # 응답에 리소스 상세 정보가 포함되어 있는지 확인
    assert "resource" in linked_resources[0]
    assert linked_resources[0]["resource"]["name"] == resource1.name


@pytest.mark.asyncio
async def test_create_entity_resource_with_nonexistent_resource(authorized_client: TestClient, setup_for_entity_resource_test):
    """[수정] 존재하지 않는 리소스 ID로 엔티티-리소스 연결 시 404를 반환하는지 테스트합니다."""
    _, _, equipment = setup_for_entity_resource_test
    link_data = {"resource_id": 99999, "entity_type": "EQUIPMENT", "entity_id": equipment.id}
    response = await authorized_client.post("/api/v1/shared/resources/entity", json=link_data)
    assert response.status_code == 404
    assert "Resource to link not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_set_main_resource_and_delete_link(admin_client: TestClient, db_session: AsyncSession, setup_for_entity_resource_test):
    """[수정] 대표 리소스를 설정하고, 연결을 해제하는 것을 테스트합니다."""
    resource1, resource2, equipment = setup_for_entity_resource_test

    # 테스트를 위해 DB에 직접 링크를 생성합니다.
    link1_create = shared_schemas.EntityResourceCreate(resource_id=resource1.id, entity_type="EQUIPMENT", entity_id=equipment.id)
    link2_create = shared_schemas.EntityResourceCreate(resource_id=resource2.id, entity_type="EQUIPMENT", entity_id=equipment.id, is_main=True)
    link1 = await shared_crud.entity_resource.create(db_session, obj_in=link1_create)
    link2 = await shared_crud.entity_resource.create(db_session, obj_in=link2_create)
    assert link2.is_main is True

    # link1을 새로운 대표 리소스로 설정합니다.
    response_set_main = await admin_client.put(f"/api/v1/shared/resources/entity/{link1.id}/set_main?entity_type=EQUIPMENT&entity_id={equipment.id}")
    assert response_set_main.status_code == 200

    # DB에서 직접 상태를 확인합니다.
    await db_session.refresh(link1)
    await db_session.refresh(link2)
    assert link1.is_main is True   # link1이 대표로 설정됨
    assert link2.is_main is False  # 기존 대표였던 link2는 해제됨

    # link 연결을 삭제합니다.
    response_delete_link = await admin_client.delete(f"/api/v1/shared/resources/entity/{link1.id}")
    assert response_delete_link.status_code == 204

    # 연결은 삭제되었지만, 원본 리소스는 남아있는지 확인합니다.
    assert await shared_crud.entity_resource.get(db_session, id=link1.id) is None
    assert await shared_crud.resource.get(db_session, id=resource1.id) is not None


# ==============================================================================
# 리소스 및 엔티티-리소스 관련 API 테스트
# =============================================================================
async def test_read_entity_resources_for_entity_with_resource_details(
    admin_client: TestClient,
    authorized_client: TestClient,
    db_session: AsyncSession,
    test_user: usr_models.User,
    test_resource_category: shared_models.ResourceCategory,  # [수정] 픽스처 사용
):
    """
    [수정] 특정 엔티티에 연결된 리소스 조회 시, 리소스 상세 정보가 함께 반환되는지 테스트합니다.
    """
    # [삭제] 단계 1은 test_resource_category 픽스처로 대체

    # 단계 2: (일반 사용자 권한으로) 리소스 레코드 생성 (DB 직접 추가)
    dummy_resource_name = "test_equipment_photo.jpg"
    # [수정] settings.UPLOAD_DIR은 테스트 환경에 맞게 동적으로 설정됨
    dummy_resource_path_name = f"fake_path/{dummy_resource_name}"

    db_resource = shared_models.Resource(
        type=shared_models.ResourceType.IMAGE,
        category_id=test_resource_category.id,
        name=dummy_resource_name,
        path=dummy_resource_path_name,
        size_kb=10,
        content_type="image/jpeg",
        description="테스트 설비 사진",
        uploader_id=test_user.id,
        department_id=test_user.department_id,
        uploaded_at=datetime.now(UTC)
    )
    db_session.add(db_resource)
    await db_session.commit()
    await db_session.refresh(db_resource)
    resource_id = db_resource.id

    # 단계 3: (일반 사용자 권한으로) 엔티티-리소스 연결 생성
    entity_type = "EQUIPMENT"
    entity_id = 999  # 가상의 설비 ID
    # [수정] EntityImageCreate -> EntityResourceCreate, 필드명 변경
    entity_resource_create = {
        "resource_id": resource_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "is_main": True
    }
    # [수정] API 엔드포인트 변경
    response = await authorized_client.post(
        "/api/v1/shared/resources/entity",
        json=entity_resource_create
    )
    assert response.status_code == 201

    # 단계 4: 설비에 연결된 리소스 정보 조회
    # [수정] API 엔드포인트 변경
    response = await authorized_client.get(
        f"/api/v1/shared/resources/entity/{entity_type}/{entity_id}"
    )
    assert response.status_code == 200
    linked_resources = response.json()

    # --- 검증 로직 수정 ---
    assert len(linked_resources) == 1
    linked_resource_data = linked_resources[0]

    assert linked_resource_data["resource_id"] == resource_id
    # [수정] 응답 본문의 중첩된 'resource' 객체를 확인
    assert "resource" in linked_resource_data
    assert linked_resource_data["resource"] is not None

    # [수정] 중첩된 resource 객체의 필드들을 검증 (새로운 필드명 기준)
    resource_details = linked_resource_data["resource"]
    assert resource_details["id"] == resource_id
    assert resource_details["name"] == dummy_resource_name
    assert resource_details["path"] == dummy_resource_path_name
    assert resource_details["content_type"] == "image/jpeg"
    assert resource_details["size_kb"] == 10
    assert resource_details["description"] == "테스트 설비 사진"
    assert resource_details["uploader_id"] == test_user.id
