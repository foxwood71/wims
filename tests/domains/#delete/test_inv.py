# tests/domains/test_inv.py

"""
'inv' 도메인 (자재 및 재고 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 INV 엔티티 (자재 카테고리, 자재 품목, 자재 배치, 자재 거래 등)의 CRUD 테스트.
- SKU/이름/코드 고유성 제약 검증.
- FIFO 재고 차감 로직 검증.
- 다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

# 다른 도메인의 모델 임포트 추가
from app.domains.loc import models as loc_models  # loc_models 임포트 추가
from app.domains.usr import models as usr_models  # usr_models 임포트 추가 (test_user 등 사용)
from app.domains.ven import models as ven_models  # ven_models 임포트 추가 (inv_test_vendor 사용)
from app.domains.fms import models as fms_models  # fms_models 임포트 추가 (inv_test_equipment 사용)


# INV 도메인의 CRUD, 모델, 스키마
from app.domains.inv import models as inv_models
from app.domains.inv import schemas as inv_schemas
from app.domains.inv.crud import material_category as material_category_crud  # CRUD 직접 사용 (테스트 셋업용)
from app.domains.inv.crud import material as material_crud
from app.domains.inv.crud import material_batch as material_batch_crud
from app.domains.inv.crud import material_transaction as material_transaction_crud


# conftest.py에서 정의된 픽스처들을 Pytest가 자동으로 감지하여 사용할 수 있습니다.
# client, db_session, admin_client, authorized_client, test_user, test_admin_user


# --- INV 보조 데이터 생성 픽스처 (다른 테스트에서 재사용) ---
@pytest.fixture(name="inv_test_plant")
async def inv_test_plant_fixture(db_session: Session) -> loc_models.facility:
    plant = loc_models.facility(code="INVPL", name="INV 테스트 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)
    return plant


@pytest.fixture(name="inv_test_location_type")
async def inv_test_location_type_fixture(db_session: Session) -> loc_models.LocationType:
    loc_type = loc_models.LocationType(name="INV 보관 장소 유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)
    return loc_type


@pytest.fixture(name="inv_test_storage_location")
async def inv_test_storage_location_fixture(db_session: Session, inv_test_plant: loc_models.facility, inv_test_location_type: loc_models.LocationType) -> loc_models.Location:
    location = loc_models.Location(
        plant_id=inv_test_plant.id,
        location_type_id=inv_test_location_type.id,
        name="INV 보관 장소"
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest.fixture(name="inv_test_vendor")
async def inv_test_vendor_fixture(db_session: Session) -> ven_models.Vendor:
    vendor = ven_models.Vendor(name="INV 테스트 공급업체", business_number="987-65-43210")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


@pytest.fixture(name="inv_test_equipment")
async def inv_test_equipment_fixture(db_session: Session, inv_test_plant: loc_models.facility) -> fms_models.Equipment:
    eq_cat = fms_models.EquipmentCategory(name="INV 테스트 설비 카테고리")
    db_session.add(eq_cat)
    await db_session.commit()
    await db_session.refresh(eq_cat)

    equipment = fms_models.Equipment(
        plant_id=inv_test_plant.id,
        equipment_category_id=eq_cat.id,
        name="INV 테스트 설비",
        serial_number="EQP-INV-001"
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)
    return equipment


# --- 자재 카테고리 관리 엔드포인트 테스트 ---
@pytest.mark.asyncio
async def test_create_material_category_success_admin(
    admin_client: TestClient,  # 관리자로 인증된 클라이언트
):
    """
    관리자 권한으로 새로운 자재 카테고리를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_material_category_success_admin ---")
    category_data = {
        "name": "테스트 시약",
        "description": "실험실 시약 카테고리"
    }
    response = await admin_client.post("/api/v1/inv/material_categories", json=category_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_category = response.json()
    assert created_category["name"] == category_data["name"]
    assert "id" in created_category
    print("test_create_material_category_success_admin passed.")


@pytest.mark.asyncio
async def test_create_material_category_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 존재하는 이름의 자재 카테고리를 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_material_category_duplicate_name_admin ---")
    existing_category = inv_models.MaterialCategory(name="기존 자재 카테고리")
    db_session.add(existing_category)
    await db_session.commit()
    await db_session.refresh(existing_category)

    category_data = {
        "name": "기존 자재 카테고리",  # 중복 이름
    }
    response = await admin_client.post("/api/v1/inv/material_categories", json=category_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Material category with this name already exists."
    print("test_create_material_category_duplicate_name_admin passed.")


@pytest.mark.asyncio
async def test_read_material_categories_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 자재 카테고리 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_material_categories_success ---")
    cat1 = inv_models.MaterialCategory(name="필터")
    cat2 = inv_models.MaterialCategory(name="배관 자재")
    db_session.add(cat1)
    db_session.add(cat2)
    await db_session.commit()
    await db_session.refresh(cat1)
    await db_session.refresh(cat2)

    response = await client.get("/api/v1/inv/material_categories")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    categories_list = response.json()
    assert len(categories_list) >= 2
    assert any(c["name"] == "필터" for c in categories_list)
    assert any(c["name"] == "배관 자재" for c in categories_list)
    print("test_read_material_categories_success passed.")


# --- 자재 품목 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_material_success_admin(
    admin_client: TestClient,
    db_session: Session,
    inv_test_equipment: fms_models.Equipment  # FK
):
    """
    관리자 권한으로 새로운 자재 품목을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_material_success_admin ---")
    # 자재 카테고리 생성 (FK)
    mat_cat = inv_models.MaterialCategory(name="기본 자재 카테고리")
    db_session.add(mat_cat)
    await db_session.commit()
    await db_session.refresh(mat_cat)

    material_data = {
        "material_category_id": mat_cat.id,
        "name": "염산 35%",
        "unit_of_measure": "L",
        "sku": "HCL-001",
        "min_stock_level": 10.0,
        "related_equipment_id": inv_test_equipment.id
    }
    response = await admin_client.post("/api/v1/inv/materials", json=material_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_material = response.json()
    assert created_material["name"] == material_data["name"]
    assert created_material["sku"] == material_data["sku"]
    assert created_material["material_category_id"] == mat_cat.id
    assert "id" in created_material
    print("test_create_material_success_admin passed.")


@pytest.mark.asyncio
async def test_create_material_duplicate_sku_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 존재하는 SKU의 자재 품목을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_material_duplicate_sku_admin ---")
    # 자재 카테고리 생성
    mat_cat = inv_models.MaterialCategory(name="중복 SKU 카테고리")
    db_session.add(mat_cat)
    await db_session.commit()
    await db_session.refresh(mat_cat)

    existing_material = inv_models.Material(
        material_category_id=mat_cat.id, name="기존 자재", unit_of_measure="EA", sku="DUP-SKU"
    )
    db_session.add(existing_material)
    await db_session.commit()
    await db_session.refresh(existing_material)

    material_data = {
        "material_category_id": mat_cat.id,
        "name": "새로운 자재",
        "unit_of_measure": "EA",
        "sku": "DUP-SKU",  # 중복 SKU
    }
    response = await admin_client.post("/api/v1/inv/materials", json=material_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Material with this SKU already exists."
    print("test_create_material_duplicate_sku_admin passed.")


@pytest.mark.asyncio
async def test_read_materials_success(client: TestClient, db_session: Session, inv_test_equipment: fms_models.Equipment):
    """
    모든 사용자가 자재 품목 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_materials_success ---")
    mat_cat = inv_models.MaterialCategory(name="조회 자재 카테고리")
    db_session.add(mat_cat)
    await db_session.commit()
    await db_session.refresh(mat_cat)

    mat1 = inv_models.Material(material_category_id=mat_cat.id, name="볼트", unit_of_measure="EA", sku="BOLT1", related_equipment_id=inv_test_equipment.id)
    mat2 = inv_models.Material(material_category_id=mat_cat.id, name="너트", unit_of_measure="EA", sku="NUT1")
    db_session.add(mat1)
    db_session.add(mat2)
    await db_session.commit()
    await db_session.refresh(mat1)
    await db_session.refresh(mat2)

    response = await client.get("/api/v1/inv/materials")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    materials_list = response.json()
    assert len(materials_list) >= 2
    assert any(m["name"] == "볼트" for m in materials_list)
    assert any(m["name"] == "너트" for m in materials_list)
    print("test_read_materials_success passed.")


# --- 자재 배치 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_material_batch_success_admin(
    admin_client: TestClient,
    db_session: Session,
    inv_test_plant: loc_models.facility,  # FK
    inv_test_storage_location: loc_models.Location,  # FK
    inv_test_vendor: ven_models.Vendor  # FK
):
    """
    관리자 권한으로 새로운 자재 재고 배치를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_material_batch_success_admin ---")
    # 자재 품목 생성 (FK)
    mat_cat = inv_models.MaterialCategory(name="배치용 카테고리")
    db_session.add(mat_cat)
    await db_session.commit()
    await db_session.refresh(mat_cat)

    material = inv_models.Material(
        material_category_id=mat_cat.id, name="테스트 배치 자재", unit_of_measure="EA", sku="BATCH-001"
    )
    db_session.add(material)
    await db_session.commit()
    await db_session.refresh(material)

    batch_data = {
        "material_id": material.id,
        "plant_id": inv_test_plant.id,
        "storage_location_id": inv_test_storage_location.id,
        "lot_number": "LOT20250529",
        "quantity": 100.0,
        "unit_cost": 5.50,
        "received_date": str(datetime.now()),
        "expiration_date": str(date(2026, 12, 31)),
        "vendor_id": inv_test_vendor.id
    }
    response = await admin_client.post("/api/v1/inv/material_batches", json=batch_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_batch = response.json()
    assert created_batch["material_id"] == material.id
    assert created_batch["plant_id"] == inv_test_plant.id
    assert created_batch["quantity"] == 100.0
    assert "id" in created_batch
    print("test_create_material_batch_success_admin passed.")


@pytest.mark.asyncio
async def test_read_material_batches_by_material_and_plant(
    client: TestClient,
    db_session: Session,
    inv_test_plant: loc_models.facility  # FK
):
    """
    특정 자재 품목 및 처리장 ID로 자재 배치 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_material_batches_by_material_and_plant ---")
    # 자재 카테고리 및 자재 품목 생성
    mat_cat = inv_models.MaterialCategory(name="조회 배치 카테고리")
    db_session.add(mat_cat)
    await db_session.commit()
    await db_session.refresh(mat_cat)

    material_a = inv_models.Material(material_category_id=mat_cat.id, name="자재 A", unit_of_measure="L", sku="MAT-A")
    material_b = inv_models.Material(material_category_id=mat_cat.id, name="자재 B", unit_of_measure="KG", sku="MAT-B")
    db_session.add(material_a)
    db_session.add(material_b)
    await db_session.commit()
    await db_session.refresh(material_a)
    await db_session.refresh(material_b)

    # 배치 생성
    batch1_ma_p1 = inv_models.MaterialBatch(material_id=material_a.id, plant_id=inv_test_plant.id, quantity=50, received_date=datetime(2025, 1, 1))
    batch2_ma_p1 = inv_models.MaterialBatch(material_id=material_a.id, plant_id=inv_test_plant.id, quantity=30, received_date=datetime(2025, 2, 1))
    batch3_mb_p1 = inv_models.MaterialBatch(material_id=material_b.id, plant_id=inv_test_plant.id, quantity=20, received_date=datetime(2025, 3, 1))
    db_session.add(batch1_ma_p1)
    db_session.add(batch2_ma_p1)
    db_session.add(batch3_mb_p1)
    await db_session.commit()
    await db_session.refresh(batch1_ma_p1)
    await db_session.refresh(batch2_ma_p1)
    await db_session.refresh(batch3_mb_p1)

    # 쿼리 파라미터 앞에 슬래시가 없는 형태로 요청
    # (FastAPI의 redirect_slashes 동작이 쿼리 파라미터와 결합될 때 예상과 다를 수 있으므로 시도)
    # response = await client.get(f"/api/v1/inv/material_batches/?material_id={material_a.id}&plant_id={inv_test_plant.id}")
    response = await client.get(f"/api/v1/inv/material_batches?material_id={material_a.id}&plant_id={inv_test_plant.id}")  #
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    batches_list = response.json()
    assert len(batches_list) == 2
    assert all(b["material_id"] == material_a.id for b in batches_list)
    assert all(b["plant_id"] == inv_test_plant.id for b in batches_list)
    assert any(b["quantity"] == 50 for b in batches_list)
    assert any(b["quantity"] == 30 for b in batches_list)
    print("test_read_material_batches_by_material_and_plant passed.")


# --- 자재 거래 이력 관리 엔드포인트 및 FIFO 로직 테스트 ---
@pytest.mark.asyncio
async def test_create_material_transaction_usage_fifo_success(
    authorized_client: TestClient,  # 일반 사용자 권한
    db_session: Session,
    inv_test_plant: loc_models.facility,
    inv_test_vendor: ven_models.Vendor,
    test_user: usr_models.User  # performed_by_user_id
):
    """
    'USAGE' 타입의 자재 거래 생성 시 FIFO 방식으로 재고가 성공적으로 차감되는지 테스트합니다.
    """
    print("\n--- Running test_create_material_transaction_usage_fifo_success ---")
    # 1. 자재 품목 생성
    mat_cat = inv_models.MaterialCategory(name="FIFO 테스트 카테고리")
    db_session.add(mat_cat)
    await db_session.commit()
    await db_session.refresh(mat_cat)

    material = inv_models.Material(
        material_category_id=mat_cat.id, name="FIFO 테스트 자재", unit_of_measure="EA", sku="FIFO-001"
    )
    db_session.add(material)
    await db_session.commit()
    await db_session.refresh(material)

    # 2. 여러 배치 입고 (FIFO 순서)
    batch1 = inv_models.MaterialBatch(material_id=material.id, plant_id=inv_test_plant.id, quantity=30.0, received_date=datetime(2025, 1, 1), vendor_id=inv_test_vendor.id)
    batch2 = inv_models.MaterialBatch(material_id=material.id, plant_id=inv_test_plant.id, quantity=40.0, received_date=datetime(2025, 2, 1), vendor_id=inv_test_vendor.id)
    batch3 = inv_models.MaterialBatch(material_id=material.id, plant_id=inv_test_plant.id, quantity=50.0, received_date=datetime(2025, 3, 1), vendor_id=inv_test_vendor.id)
    db_session.add(batch1)
    db_session.add(batch2)
    db_session.add(batch3)
    await db_session.commit()
    await db_session.refresh(batch1)
    await db_session.refresh(batch2)
    await db_session.refresh(batch3)

    # 초기 재고 확인
    initial_batches = await material_batch_crud.get_batches_by_material_and_plant(
        db_session,
        material_id=material.id,  # 키워드 인자로 변경
        plant_id=inv_test_plant.id  # 키워드 인자로 변경
    )
    initial_total_qty = sum(b.quantity for b in initial_batches)
    print(f"Initial total quantity: {initial_total_qty}")
    assert initial_total_qty == 120.0

    # 3. 자재 사용 거래 기록 (FIFO 차감)
    usage_qty = Decimal("70.0")  # 30 (batch1) + 40 (batch2) = 70
    transaction_data = {
        "material_id": material.id,
        "plant_id": inv_test_plant.id,
        "transaction_type": "USAGE",
        "quantity_change": float(-usage_qty),  # 사용은 음수로
        "performed_by_user_id": test_user.id
    }
    response = await authorized_client.post("/api/v1/inv/material_transactions", json=transaction_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_transaction = response.json()
    assert created_transaction["quantity_change"] == float(-usage_qty)
    assert created_transaction["transaction_type"] == "USAGE"
    assert "source_batch_id" in created_transaction  # 차감된 배치 ID 기록 확인

    # 4. 배치 수량 업데이트 확인
    await db_session.refresh(batch1)
    await db_session.refresh(batch2)
    await db_session.refresh(batch3)

    assert batch1.quantity == 0.0  # Batch 1은 모두 사용
    assert batch2.quantity == 0.0  # Batch 2도 모두 사용
    assert batch3.quantity == 50.0  # Batch 3은 사용되지 않음

    # 총 재고 확인
    final_batches = await material_batch_crud.get_batches_by_material_and_plant(
        db_session,
        material_id=material.id,  # 키워드 인자로 변경
        plant_id=inv_test_plant.id   # 키워드 인자로 변경
    )
    final_total_qty = sum(b.quantity for b in final_batches)
    print(f"Final total quantity: {final_total_qty}")
    assert final_total_qty == (initial_total_qty - usage_qty)
    assert created_transaction["source_batch_id"] == batch2.id  # 마지막으로 사용된 배치 ID가 기록됨 (설계에 따라 다름)
    print("test_create_material_transaction_usage_fifo_success passed.")


@pytest.mark.asyncio
async def test_create_material_transaction_usage_insufficient_stock(
    authorized_client: TestClient,
    db_session: Session,
    inv_test_plant: loc_models.facility,
    test_user: usr_models.User
):
    """
    'USAGE' 타입의 자재 거래 생성 시 재고가 부족할 경우 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_material_transaction_usage_insufficient_stock ---")
    # 1. 자재 품목 생성
    mat_cat = inv_models.MaterialCategory(name="재고 부족 테스트 카테고리")
    db_session.add(mat_cat)
    await db_session.commit()
    await db_session.refresh(mat_cat)

    material = inv_models.Material(
        material_category_id=mat_cat.id, name="재고 부족 자재", unit_of_measure="EA", sku="LOW-STOCK-001"
    )
    db_session.add(material)
    await db_session.commit()
    await db_session.refresh(material)

    # 2. 소량의 배치 입고
    batch1 = inv_models.MaterialBatch(material_id=material.id, plant_id=inv_test_plant.id, quantity=10.0, received_date=datetime(2025, 4, 1))
    db_session.add(batch1)
    await db_session.commit()
    await db_session.refresh(batch1)

    # 3. 사용량 > 재고인 거래 시도
    usage_qty = 20.0  # 재고는 10인데 20을 사용 시도
    transaction_data = {
        "material_id": material.id,
        "plant_id": inv_test_plant.id,
        "transaction_type": "USAGE",
        "quantity_change": -usage_qty,
        "performed_by_user_id": test_user.id
    }
    response = await authorized_client.post("/api/v1/inv/material_transactions", json=transaction_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert "Not enough stock for material ID" in response.json()["detail"]

    # 재고가 롤백되었는지 확인 (DB 변경 없음)
    await db_session.refresh(batch1)
    assert batch1.quantity == 10.0  # 여전히 10.0이어야 함
    print("test_create_material_transaction_usage_insufficient_stock passed.")
