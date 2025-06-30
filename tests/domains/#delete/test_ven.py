# tests/domains/test_ven.py

"""
'ven' 도메인 (공급업체 관리) 관련 API 엔드포인트에 대한 통합 테스트를 정의하는 모듈입니다.

- 공급업체 카테고리 관리 엔드포인트 테스트:
    - `POST /ven/vendor_categories/` (생성)
    - `GET /ven/vendor_categories/` (목록 조회)
    - `GET /ven/vendor_categories/{id}` (단일 조회)
    - `PUT /ven/vendor_categories/{id}` (업데이트)
    - `DELETE /ven/vendor_categories/{id}` (삭제)
- 공급업체 관리 엔드포인트 테스트:
    - `POST /ven/vendors/` (생성)
    - `GET /ven/vendors/` (목록 조회)
    - `GET /ven/vendors/{id}` (단일 조회)
    - `PUT /ven/vendors/{id}` (업데이트)
    - `DELETE /ven/vendors/{id}` (삭제)
- 공급업체-카테고리 연결 관리 엔드포인트 테스트:
    - `POST /ven/vendor_vendor_categories/` (생성)
    - `GET /ven/vendors/{vendor_id}/categories/` (특정 공급업체의 카테고리 목록 조회)
    - `DELETE /ven/vendor_vendor_categories/` (삭제)
- 공급업체 담당자 관리 엔드포인트 테스트:
    - `POST /ven/vendor_contacts/` (생성)
    - `GET /ven/vendors/{vendor_id}/contacts/` (특정 공급업체의 담당자 목록 조회)
    - `GET /ven/vendor_contacts/{id}` (단일 조회)
    - `PUT /ven/vendor_contacts/{id}` (업데이트)
    - `DELETE /ven/vendor_contacts/{id}` (삭제)

다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
인증 및 권한 부여 로직을 검증합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.domains.ven import models as vendor_models
from app.domains.ven import schemas as vendor_schemas
from app.domains.ven.crud import vendor_category as vendor_category_crud  # CRUD 직접 사용 (테스트 셋업용)
from app.domains.ven.crud import vendor as vendor_crud
from app.domains.ven.crud import vendor_vendor_category as vendor_vendor_category_crud
from app.domains.ven.crud import vendor_contact as vendor_contact_crud


# --- 공급업체 카테고리 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_vendor_category_success_admin(
    admin_client: TestClient,  # 관리자로 인증된 클라이언트
):
    """
    관리자 권한으로 새로운 공급업체 카테고리를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_vendor_category_success_admin ---")
    category_data = {
        "name": "시약",
        "description": "실험실 시약 공급업체"
    }
    response = await admin_client.post("/api/v1/ven/vendor_categories", json=category_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_category = response.json()
    assert created_category["name"] == category_data["name"]
    assert "id" in created_category
    print("test_create_vendor_category_success_admin passed.")


@pytest.mark.asyncio
async def test_create_vendor_category_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session  # 데이터베이스에 카테고리 미리 생성하기 위해
):
    """
    관리자 권한으로 이미 존재하는 이름의 공급업체 카테고리를 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_vendor_category_duplicate_name_admin ---")
    existing_category = vendor_models.VendorCategory(name="기존 카테고리")
    db_session.add(existing_category)
    await db_session.commit()
    await db_session.refresh(existing_category)

    category_data = {
        "name": "기존 카테고리",  # 중복 이름
    }
    response = await admin_client.post("/api/v1/ven/vendor_categories", json=category_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Vendor category with this name already exists"
    print("test_create_vendor_category_duplicate_name_admin passed.")


@pytest.mark.asyncio
async def test_create_vendor_category_unauthorized(
    authorized_client: TestClient,  # 일반 사용자로 인증된 클라이언트
    client: TestClient  # 비인증 클라이언트
):
    """
    일반 사용자 및 비인증 사용자가 공급업체 카테고리 생성 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_vendor_category_unauthorized ---")
    category_data = {
        "name": "권한없음 카테고리",
    }

    # 일반 사용자 시도
    response_user = await authorized_client.post("/api/v1/ven/vendor_categories", json=category_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.post("/api/v1/ven/vendor_categories", json=category_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_create_vendor_category_unauthorized passed.")


@pytest.mark.asyncio
async def test_read_vendor_categories_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 공급업체 카테고리 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_vendor_categories_success ---")
    cat1 = vendor_models.VendorCategory(name="케미컬")
    cat2 = vendor_models.VendorCategory(name="장비")
    db_session.add(cat1)
    db_session.add(cat2)
    await db_session.commit()
    await db_session.refresh(cat1)
    await db_session.refresh(cat2)

    response = await client.get("/api/v1/ven/vendor_categories")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    assert len(response.json()) >= 2
    assert any(c["name"] == "케미컬" for c in response.json())
    assert any(c["name"] == "장비" for c in response.json())
    print("test_read_vendor_categories_success passed.")


@pytest.mark.asyncio
async def test_update_vendor_category_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체 카테고리 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_vendor_category_success_admin ---")
    category = vendor_models.VendorCategory(name="업데이트 대상 카테고리")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)

    '''
    # 추가: 데이터가 실제로 db_session에서 조회되는지 확인
    retrieved_category = await vendor_crud.vendor_category.get(db_session, id=category.id)
    print(f"DEBUG: Retrieved category in test: {retrieved_category}")
    if retrieved_category is None:
        print("ERROR: Category not retrieved from db_session after commit/refresh!")
        # 이 경우, 데이터베이스 세션 문제로 판단할 수 있습니다.

    '''
    print(f"DEBUG: Created category ID: {category.id}, Name: {category.name}")

    update_data = {"name": "업데이트된 카테고리명", "description": "수정된 설명"}
    response = await admin_client.put(f"/api/v1/ven/vendor_categories/{category.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_category = response.json()
    assert updated_category["id"] == category.id
    assert updated_category["name"] == update_data["name"]
    assert updated_category["description"] == update_data["description"]
    print("test_update_vendor_category_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_vendor_category_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체 카테고리를 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_vendor_category_success_admin ---")
    vendor = vendor_models.Vendor(name="해제 공급업체", business_number="1234567894")
    category = vendor_models.VendorCategory(name="삭제 대상 카테고리")
    db_session.add(vendor)
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(vendor)
    await db_session.refresh(category)

    link = vendor_models.VendorVendorCategory(vendor_id=vendor.id, vendor_category_id=category.id)
    db_session.add(link)
    await db_session.flush()  # 여기에 flush 추가  #
    await db_session.commit()
    # await db_session.refresh(link) # refresh는 여기서 필수는 아님, primary key가 명시적 ID이므로

    response = await admin_client.delete("/api/v1/ven/vendor_vendor_categories", params={
        "vendor_id": vendor.id,
        "vendor_category_id": category.id
    })
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 연결이 해제되었는지 확인
    deleted_link = await vendor_vendor_category_crud.get_link(db_session, vendor.id, category.id)
    assert deleted_link is None
    print("test_remove_vendor_category_from_vendor_success_admin passed.")


# --- 공급업체 관리 엔드포인트 테스트 ---
@pytest.mark.asyncio
async def test_create_vendor_success_admin(
    admin_client: TestClient,
):
    """
    관리자 권한으로 새로운 공급업체를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_vendor_success_admin ---")
    vendor_data = {
        "name": "테스트공급업체1",
        "business_number": "123-45-67890",
        "email": "test@vendor.com"
    }
    response = await admin_client.post("/api/v1/ven/vendors", json=vendor_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_vendor = response.json()
    assert created_vendor["name"] == vendor_data["name"]
    assert created_vendor["business_number"] == vendor_data["business_number"]
    assert "id" in created_vendor
    print("test_create_vendor_success_admin passed.")


@pytest.mark.asyncio
async def test_create_vendor_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 존재하는 이름의 공급업체를 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_vendor_duplicate_name_admin ---")
    existing_vendor = vendor_models.Vendor(name="기존공급업체", business_number="111-11-11111")
    db_session.add(existing_vendor)
    await db_session.commit()
    await db_session.refresh(existing_vendor)

    vendor_data = {
        "name": "기존공급업체",  # 중복 이름
        "business_number": "222-22-22222",
    }
    response = await admin_client.post("/api/v1/ven/vendors", json=vendor_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Vendor with this name already exists"
    print("test_create_vendor_duplicate_name_admin passed.")


@pytest.mark.asyncio
async def test_read_vendors_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 공급업체 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_vendors_success ---")
    vendor1 = vendor_models.Vendor(name="공급업체A", business_number="123")
    vendor2 = vendor_models.Vendor(name="공급업체B", business_number="456")
    db_session.add(vendor1)
    db_session.add(vendor2)
    await db_session.commit()
    await db_session.refresh(vendor1)
    await db_session.refresh(vendor2)

    response = await client.get("/api/v1/ven/vendors")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    assert len(response.json()) >= 2
    assert any(v["name"] == "공급업체A" for v in response.json())
    assert any(v["name"] == "공급업체B" for v in response.json())
    print("test_read_vendors_success passed.")


@pytest.mark.asyncio
async def test_update_vendor_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_vendor_success_admin ---")
    vendor = vendor_models.Vendor(name="업데이트 대상 공급업체", business_number="999-99-99999")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)

    update_data = {"name": "업데이트된 공급업체명", "phone": "010-1234-5678"}
    response = await admin_client.put(f"/api/v1/ven/vendors/{vendor.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_vendor = response.json()
    assert updated_vendor["id"] == vendor.id
    assert updated_vendor["name"] == update_data["name"]
    assert updated_vendor["phone"] == update_data["phone"]
    print("test_update_vendor_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_vendor_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체를 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_vendor_success_admin ---")
    vendor = vendor_models.Vendor(name="삭제 대상 공급업체", business_number="000-00-00000")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)

    response = await admin_client.delete(f"/api/v1/ven/vendors/{vendor.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_vendor = await vendor_crud.get(db_session, id=vendor.id)
    assert deleted_vendor is None
    print("test_delete_vendor_success_admin passed.")


# --- 공급업체-카테고리 연결 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_add_vendor_category_to_vendor_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체에 카테고리를 성공적으로 연결하는지 테스트합니다.
    """
    print("\n--- Running test_add_vendor_category_to_vendor_success_admin ---")
    vendor = vendor_models.Vendor(name="연결 공급업체", business_number="1234567891")
    category = vendor_models.VendorCategory(name="연결 카테고리")
    db_session.add(vendor)
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(vendor)
    await db_session.refresh(category)

    link_data = {
        "vendor_id": vendor.id,
        "vendor_category_id": category.id
    }
    response = await admin_client.post("/api/v1/ven/vendor_vendor_categories", json=link_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_link = response.json()
    assert created_link["vendor_id"] == vendor.id
    assert created_link["vendor_category_id"] == category.id
    print("test_add_vendor_category_to_vendor_success_admin passed.")


@pytest.mark.asyncio
async def test_add_vendor_category_to_vendor_duplicate_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 연결된 공급업체-카테고리를 다시 연결 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_add_vendor_category_to_vendor_duplicate_admin ---")
    vendor = vendor_models.Vendor(name="중복 연결 공급업체", business_number="1234567892")
    category = vendor_models.VendorCategory(name="중복 연결 카테고리")
    db_session.add(vendor)
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(vendor)
    await db_session.refresh(category)

    # 먼저 연결
    link = vendor_models.VendorVendorCategory(vendor_id=vendor.id, vendor_category_id=category.id)
    db_session.add(link)
    await db_session.commit()

    # 다시 연결 시도
    link_data = {
        "vendor_id": vendor.id,
        "vendor_category_id": category.id
    }
    response = await admin_client.post("/api/v1/ven/vendor_vendor_categories", json=link_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Vendor is already linked to this category."
    print("test_add_vendor_category_to_vendor_duplicate_admin passed.")


@pytest.mark.asyncio
async def test_read_vendor_categories_for_vendor_success(
    client: TestClient,
    db_session: Session
):
    """
    특정 공급업체에 연결된 카테고리 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_vendor_categories_for_vendor_success ---")
    vendor = vendor_models.Vendor(name="조회 공급업체", business_number="1234567893")
    cat1 = vendor_models.VendorCategory(name="조회 카테고리1")
    cat2 = vendor_models.VendorCategory(name="조회 카테고리2")
    db_session.add(vendor)
    db_session.add(cat1)
    db_session.add(cat2)
    await db_session.commit()
    await db_session.refresh(vendor)
    await db_session.refresh(cat1)
    await db_session.refresh(cat2)

    link1 = vendor_models.VendorVendorCategory(vendor_id=vendor.id, vendor_category_id=cat1.id)
    link2 = vendor_models.VendorVendorCategory(vendor_id=vendor.id, vendor_category_id=cat2.id)
    db_session.add(link1)
    db_session.add(link2)
    await db_session.commit()

    response = await client.get(f"/api/v1/ven/vendors/{vendor.id}/categories")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    categories_list = response.json()
    assert len(categories_list) == 2
    assert any(c["name"] == "조회 카테고리1" for c in categories_list)
    assert any(c["name"] == "조회 카테고리2" for c in categories_list)
    print("test_read_vendor_categories_for_vendor_success passed.")


@pytest.mark.asyncio
async def test_remove_vendor_category_from_vendor_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체와 카테고리 간의 연결을 성공적으로 해제하는지 테스트합니다.
    """
    print("\n--- Running test_remove_vendor_category_from_vendor_success_admin ---")
    vendor = vendor_models.Vendor(name="해제 공급업체", business_number="1234567894")
    category = vendor_models.VendorCategory(name="해제 카테고리")
    db_session.add(vendor)
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(vendor)
    await db_session.refresh(category)

    link = vendor_models.VendorVendorCategory(vendor_id=vendor.id, vendor_category_id=category.id)
    db_session.add(link)
    await db_session.commit()
    await db_session.refresh(link)

    response = await admin_client.delete("/api/v1/ven/vendor_vendor_categories", params={
        "vendor_id": vendor.id,
        "vendor_category_id": category.id
    })
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 연결이 해제되었는지 확인
    deleted_link = await vendor_vendor_category_crud.get_link(db_session, vendor.id, category.id)
    assert deleted_link is None
    print("test_remove_vendor_category_from_vendor_success_admin passed.")


# --- 공급업체 담당자 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_vendor_contact_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 새로운 공급업체 담당자를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_vendor_contact_success_admin ---")
    vendor = vendor_models.Vendor(name="담당자테스트 공급업체", business_number="1234567895")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)

    contact_data = {
        "vendor_id": vendor.id,
        "name": "홍길동",
        "email": "gildong.hong@example.com"
    }
    response = await admin_client.post("/api/v1/ven/vendor_contacts", json=contact_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_contact = response.json()
    assert created_contact["name"] == contact_data["name"]
    assert created_contact["vendor_id"] == vendor.id
    assert "id" in created_contact
    print("test_create_vendor_contact_success_admin passed.")


@pytest.mark.asyncio
async def test_read_vendor_contacts_for_vendor_success(
    client: TestClient,
    db_session: Session
):
    """
    특정 공급업체에 속한 담당자 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_vendor_contacts_for_vendor_success ---")
    vendor = vendor_models.Vendor(name="담당자조회 공급업체", business_number="1234567896")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)

    contact1 = vendor_models.VendorContact(vendor_id=vendor.id, name="김철수")
    contact2 = vendor_models.VendorContact(vendor_id=vendor.id, name="이영희")
    db_session.add(contact1)
    db_session.add(contact2)
    await db_session.commit()
    await db_session.refresh(contact1)
    await db_session.refresh(contact2)

    response = await client.get(f"/api/v1/ven/vendors/{vendor.id}/contacts")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    contacts_list = response.json()
    assert len(contacts_list) == 2
    assert all(c["vendor_id"] == vendor.id for c in contacts_list)
    assert any(c["name"] == "김철수" for c in contacts_list)
    assert any(c["name"] == "이영희" for c in contacts_list)
    print("test_read_vendor_contacts_for_vendor_success passed.")


@pytest.mark.asyncio
async def test_update_vendor_contact_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체 담당자 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_vendor_contact_success_admin ---")
    vendor = vendor_models.Vendor(name="담당자업데이트 공급업체", business_number="1234567897")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)

    contact_to_update = vendor_models.VendorContact(vendor_id=vendor.id, name="업데이트 대상 담당자")
    db_session.add(contact_to_update)
    await db_session.commit()
    await db_session.refresh(contact_to_update)

    update_data = {"title": "영업부장", "phone": "02-1234-5678"}
    response = await admin_client.put(f"/api/v1/ven/vendor_contacts/{contact_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_contact = response.json()
    assert updated_contact["id"] == contact_to_update.id
    assert updated_contact["title"] == update_data["title"]
    assert updated_contact["phone"] == update_data["phone"]
    print("test_update_vendor_contact_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_vendor_contact_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 공급업체 담당자를 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_vendor_contact_success_admin ---")
    vendor = vendor_models.Vendor(name="담당자삭제 공급업체", business_number="1234567898")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)

    contact_to_delete = vendor_models.VendorContact(vendor_id=vendor.id, name="삭제 대상 담당자")
    db_session.add(contact_to_delete)
    await db_session.commit()
    await db_session.refresh(contact_to_delete)

    response = await admin_client.delete(f"/api/v1/ven/vendor_contacts/{contact_to_delete.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_contact = await vendor_contact_crud.get(db_session, id=contact_to_delete.id)
    assert deleted_contact is None
    print("test_delete_vendor_contact_success_admin passed.")
