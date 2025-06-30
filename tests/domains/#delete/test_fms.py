# tests/domains/test_fms.py

"""
'fms' 도메인 (설비 관리 시스템) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 FMS 엔티티 (설비 카테고리, 설비 스펙 정의, 설비, 설비 이력 등)의 CRUD 테스트.
- 고유성 제약 (이름, 코드, 일련번호, 자산태그) 검증.
- 다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

# 다른 도메인의 모델과 CRUD 임포트 추가
from app.domains.loc import models as loc_models  # loc_models 임포트 추가
from app.domains.usr import models as usr_models  # usr_models 임포트 추가 (test_user 등 사용)
from app.domains.ven import models as ven_models  # ven_models 임포트 추가 (fms_test_vendor 사용)

# FMS 도메인의 CRUD, 모델, 스키마
from app.domains.fms import models as fms_models
from app.domains.fms import schemas as fms_schemas
from app.domains.fms.crud import equipment_category as equipment_category_crud  # CRUD 직접 사용 (테스트 셋업용)
from app.domains.fms.crud import equipment_spec_definition as equipment_spec_definition_crud
from app.domains.fms.crud import equipment_category_spec_definition as equipment_category_spec_definition_crud
from app.domains.fms.crud import equipment as equipment_crud
from app.domains.fms.crud import equipment_spec as equipment_spec_crud
from app.domains.fms.crud import equipment_history as equipment_history_crud

from datetime import date, datetime

# conftest.py에서 정의된 픽스처들을 Pytest가 자동으로 감지하여 사용할 수 있습니다.
# client, db_session, admin_client, authorized_client, test_user, test_admin_user


# --- FMS 보조 데이터 생성 픽스처 (다른 테스트에서 재사용) ---

@pytest.fixture(name="fms_test_plant")
async def fms_test_plant_fixture(db_session: Session) -> loc_models.facility:
    plant = loc_models.facility(code="FMSPL", name="FMS 테스트 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)
    return plant


@pytest.fixture(name="fms_test_location_type")
async def fms_test_location_type_fixture(db_session: Session) -> loc_models.LocationType:
    loc_type = loc_models.LocationType(name="FMS 테스트 장소 유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)
    return loc_type


@pytest.fixture(name="fms_test_location")
async def fms_test_location_fixture(db_session: Session, fms_test_plant: loc_models.facility, fms_test_location_type: loc_models.LocationType) -> loc_models.Location:
    location = loc_models.Location(
        plant_id=fms_test_plant.id,
        location_type_id=fms_test_location_type.id,
        name="FMS 테스트 장소"
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest.fixture(name="fms_test_vendor")
async def fms_test_vendor_fixture(db_session: Session) -> ven_models.Vendor:
    vendor = ven_models.Vendor(name="FMS 테스트 공급업체", business_number="111-22-33333")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


# --- 설비 카테고리 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_equipment_category_success_admin(
    admin_client: TestClient,  # 관리자로 인증된 클라이언트
):
    """
    관리자 권한으로 새로운 설비 카테고리를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_equipment_category_success_admin ---")
    department_data = {
        "name": "펌프",
        "description": "다양한 펌프 설비",
        "korean_useful_life_years": 10
    }
    response = await admin_client.post("/api/v1/fms/equipment_categories", json=department_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_category = response.json()
    assert created_category["name"] == department_data["name"]
    assert "id" in created_category
    print("test_create_equipment_category_success_admin passed.")


@pytest.mark.asyncio
async def test_create_equipment_category_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session  # 데이터베이스에 카테고리 미리 생성하기 위해
):
    """
    관리자 권한으로 이미 존재하는 이름의 설비 카테고리를 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_equipment_category_duplicate_name_admin ---")
    existing_category = fms_models.EquipmentCategory(name="기존 설비 카테고리")
    db_session.add(existing_category)
    await db_session.commit()
    await db_session.refresh(existing_category)

    category_data = {
        "name": "기존 설비 카테고리",  # 중복 이름
    }
    response = await admin_client.post("/api/v1/fms/equipment_categories", json=category_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Equipment category with this name already exists"
    print("test_create_equipment_category_duplicate_name_admin passed.")


@pytest.mark.asyncio
async def test_read_equipment_categories_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 설비 카테고리 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_equipment_categories_success ---")
    cat1 = fms_models.EquipmentCategory(name="모터")
    cat2 = fms_models.EquipmentCategory(name="밸브")
    db_session.add(cat1)
    db_session.add(cat2)
    await db_session.commit()
    await db_session.refresh(cat1)
    await db_session.refresh(cat2)

    response = await client.get("/api/v1/fms/equipment_categories")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    categories_list = response.json()
    assert len(categories_list) >= 2
    assert any(c["name"] == "모터" for c in categories_list)
    assert any(c["name"] == "밸브" for c in categories_list)
    print("test_read_equipment_categories_success passed.")


# --- 설비 스펙 정의 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_equipment_spec_definition_success_admin(
    admin_client: TestClient,
):
    """
    관리자 권한으로 새로운 설비 스펙 정의를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_equipment_spec_definition_success_admin ---")
    spec_data = {
        "name": "power_kw",
        "display_name": "정격 출력 (kW)",
        "unit": "kW",
        "data_type": "numeric",
        "is_required": True,
        "sort_order": 1
    }
    response = await admin_client.post("/api/v1/fms/equipment_spec_definitions", json=spec_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_spec_def = response.json()
    assert created_spec_def["name"] == spec_data["name"]
    assert created_spec_def["display_name"] == spec_data["display_name"]
    assert "id" in created_spec_def
    print("test_create_equipment_spec_definition_success_admin passed.")


@pytest.mark.asyncio
async def test_create_equipment_spec_definition_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 존재하는 이름의 설비 스펙 정의 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_equipment_spec_definition_duplicate_name_admin ---")
    existing_spec_def = fms_models.EquipmentSpecDefinition(name="DUP_SPEC", display_name="중복 스펙 정의", data_type="text")
    db_session.add(existing_spec_def)
    await db_session.commit()
    await db_session.refresh(existing_spec_def)

    spec_data = {
        "name": "DUP_SPEC",  # 중복 이름
        "display_name": "새로운 스펙 정의",
        "data_type": "numeric"
    }
    response = await admin_client.post("/api/v1/fms/equipment_spec_definitions", json=spec_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Equipment spec definition with this name already exists."
    print("test_create_equipment_spec_definition_duplicate_name_admin passed.")


# --- 설비 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_equipment_success_admin(
    admin_client: TestClient,
    db_session: Session,
    fms_test_plant: loc_models.facility,  # FK
    fms_test_location: loc_models.Location  # FK
):
    """
    관리자 권한으로 새로운 설비를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_equipment_success_admin ---")
    # 설비 카테고리 생성 (FK)
    eq_cat = fms_models.EquipmentCategory(name="테스트 펌프")
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    equipment_data = {
        "plant_id": fms_test_plant.id,
        "equipment_category_id": eq_cat.id,
        "current_location_id": fms_test_location.id,
        "name": "유입 펌프  #1",
        "model_number": "PUMP-XYZ-100",
        "serial_number": "SN-PUMP-001",
        "manufacturer": "펌프제조사",
        "installation_date": str(date(2023, 1, 1)),
        "status": "OPERATIONAL",
        "asset_tag": "ASSET-001"
    }
    response = await admin_client.post("/api/v1/fms/equipments", json=equipment_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_equipment = response.json()
    assert created_equipment["name"] == equipment_data["name"]
    assert created_equipment["serial_number"] == equipment_data["serial_number"]
    assert "id" in created_equipment
    print("test_create_equipment_success_admin passed.")


@pytest.mark.asyncio
async def test_create_equipment_duplicate_serial_number_admin(
    admin_client: TestClient,
    db_session: Session,
    fms_test_plant: loc_models.facility  # FK
):
    """
    관리자 권한으로 이미 존재하는 일련번호의 설비 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_equipment_duplicate_serial_number_admin ---")
    eq_cat = fms_models.EquipmentCategory(name="중복 일련번호 카테고리")
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    existing_eq = fms_models.Equipment(
        plant_id=fms_test_plant.id, equipment_category_id=eq_cat.id, name="기존 설비", serial_number="DUP-SN"
    )
    db_session.add(existing_eq)
    await db_session.commit()
    await db_session.refresh(existing_eq)

    equipment_data = {
        "plant_id": fms_test_plant.id,
        "equipment_category_id": eq_cat.id,
        "name": "새로운 설비",
        "serial_number": "DUP-SN",  # 중복 일련번호
    }
    response = await admin_client.post("/api/v1/fms/equipments", json=equipment_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Equipment with this serial number already exists."
    print("test_create_equipment_duplicate_serial_number_admin passed.")


@pytest.mark.asyncio
async def test_read_equipments_by_plant_id_success(
    client: TestClient, db_session: Session,
    fms_test_plant: loc_models.facility,
    fms_test_location: loc_models.Location
):
    """
    특정 처리장 ID로 설비 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_equipments_by_plant_id_success ---")
    plant1 = loc_models.facility(code="EQP1", name="조회 설비 플랜트1")
    plant2 = loc_models.facility(code="EQP2", name="조회 설비 플랜트2")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    eq_cat = fms_models.EquipmentCategory(name="조회 설비 카테고리")
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    eq1_p1 = fms_models.Equipment(plant_id=plant1.id, equipment_category_id=eq_cat.id, name="설비1_플1", serial_number="S1P1")
    eq2_p1 = fms_models.Equipment(plant_id=plant1.id, equipment_category_id=eq_cat.id, name="설비2_플1", serial_number="S2P1")
    eq1_p2 = fms_models.Equipment(plant_id=plant2.id, equipment_category_id=eq_cat.id, name="설비1_플2", serial_number="S1P2")
    db_session.add(eq1_p1)
    db_session.add(eq2_p1)
    db_session.add(eq1_p2)
    await db_session.commit()
    await db_session.refresh(eq1_p1)
    await db_session.refresh(eq2_p1)
    await db_session.refresh(eq1_p2)

    response = await client.get(f"/api/v1/fms/equipments?plant_id={plant1.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    equipments_list = response.json()
    assert len(equipments_list) == 2
    assert all(eq["plant_id"] == plant1.id for eq in equipments_list)
    assert any(eq["name"] == "설비1_플1" for eq in equipments_list)
    assert any(eq["name"] == "설비2_플1" for eq in equipments_list)
    print("test_read_equipments_by_plant_id_success passed.")


# --- 설비 스펙 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_or_update_equipment_spec_success_admin(
    admin_client: TestClient,
    db_session: Session,
    fms_test_plant: loc_models.facility
):
    """
    관리자 권한으로 설비 스펙을 생성하거나 업데이트하는지 테스트합니다 (upsert 로직).
    """
    print("\n--- Running test_create_or_update_equipment_spec_success_admin ---")
    eq_cat = fms_models.EquipmentCategory(name="스펙 테스트 카테고리")
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    equipment = fms_models.Equipment(plant_id=fms_test_plant.id, equipment_category_id=eq_cat.id, name="스펙 테스트 설비", serial_number="SPEC-TEST")
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    # 1. 스펙 생성 시도
    spec_data = {
        "equipment_id": equipment.id,
        "specs": {"voltage": 220, "power": 1.5, "unit": "KW"}
    }
    response_create = await admin_client.post("/api/v1/fms/equipment_specs", json=spec_data)
    print(f"Response (create) status code: {response_create.status_code}")
    print(f"Response (create) JSON: {response_create.json()}")
    assert response_create.status_code == 201
    created_spec = response_create.json()
    assert created_spec["equipment_id"] == equipment.id
    assert created_spec["specs"] == spec_data["specs"]

    # 2. 동일 설비에 대해 스펙 업데이트 시도
    updated_specs = {"voltage": 380, "power": 2.2, "frequency": 60}
    update_data = {
        "equipment_id": equipment.id,
        "specs": updated_specs
    }
    response_update = await admin_client.post("/api/v1/fms/equipment_specs", json=update_data)  # POST는 upsert 로직을 가정
    print(f"Response (update) status code: {response_update.status_code}")
    print(f"Response (update) JSON: {response_update.json()}")
    assert response_update.status_code == 201  # 또는 200 (PUT으로 처리하는 경우)
    updated_spec_result = response_update.json()
    assert updated_spec_result["id"] == created_spec["id"]  # 기존 ID와 동일해야 함
    assert updated_spec_result["specs"] == updated_specs
    print("test_create_or_update_equipment_spec_success_admin passed.")


# --- 설비 이력 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_equipment_history_success_user(
    authorized_client: TestClient,  # 일반 사용자 권한 (performed_by_user_id는 자동 설정)
    db_session: Session,
    fms_test_plant: loc_models.facility,  # FK
    fms_test_vendor: ven_models.Vendor,  # FK
    test_user: usr_models.User  # performed_by_user_id
):
    """
    일반 사용자 권한으로 새로운 설비 이력 기록을 성공적으로 생성하는지 테스트합니다.
    `performed_by_user_id`가 자동으로 현재 사용자로 설정되는지 검증합니다.
    """
    print("\n--- Running test_create_equipment_history_success_user ---")
    eq_cat = fms_models.EquipmentCategory(name="이력 테스트 카테고리")
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    equipment = fms_models.Equipment(plant_id=fms_test_plant.id, equipment_category_id=eq_cat.id, name="이력 테스트 설비", serial_number="HIST-TEST")
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    history_data = {
        "equipment_id": equipment.id,
        "change_type": "MAINTENANCE",
        "description": "월간 정기 점검",
        "service_provider_vendor_id": fms_test_vendor.id,
        # performed_by_user_id를 명시적으로 설정하지 않아도 현재 사용자로 채워지는지 확인
        # "performed_by_user_id": test_user.id
        "next_service_date": str(date(2025, 7, 1))
    }
    response = await authorized_client.post("/api/v1/fms/equipment_history", json=history_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_history = response.json()
    assert created_history["equipment_id"] == equipment.id
    assert created_history["change_type"] == history_data["change_type"]
    assert created_history["performed_by_user_id"] == test_user.id  # 자동 설정 확인
    assert "id" in created_history
    print("test_create_equipment_history_success_user passed.")


@pytest.mark.asyncio
async def test_read_equipment_history_by_equipment_id(
    client: TestClient,
    db_session: Session,
    fms_test_plant: loc_models.facility
):
    """
    특정 설비 ID로 이력 기록 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_equipment_history_by_equipment_id ---")
    eq_cat = fms_models.EquipmentCategory(name="조회 이력 카테고리")
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    equipment = fms_models.Equipment(plant_id=fms_test_plant.id, equipment_category_id=eq_cat.id, name="조회 이력 설비", serial_number="GET-HIST")
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    hist1 = fms_models.EquipmentHistory(equipment_id=equipment.id, change_type="INSTALL", description="설치", change_date=datetime(2024, 1, 1))
    hist2 = fms_models.EquipmentHistory(equipment_id=equipment.id, change_type="REPAIR", description="수리", change_date=datetime(2024, 6, 1))
    db_session.add(hist1)
    db_session.add(hist2)
    await db_session.commit()
    await db_session.refresh(hist1)
    await db_session.refresh(hist2)

    response = await client.get(f"/api/v1/fms/equipments/{equipment.id}/history")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    history_list = response.json()
    assert len(history_list) == 2
    assert all(h["equipment_id"] == equipment.id for h in history_list)
    assert history_list[0]["change_type"] == "REPAIR"  # 최신순 정렬 가정 (crud에서 desc)
    assert history_list[1]["change_type"] == "INSTALL"
    print("test_read_equipment_history_by_equipment_id passed.")
