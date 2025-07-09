# tests/domains/test_inv_n.py

"""
'inv' 도메인 (자재 및 재고 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.
... (이하 주석 동일) ...
"""

import pytest
from httpx import AsyncClient
from decimal import Decimal
from datetime import date, datetime, timedelta, UTC

#  테스트 대상 및 의존성 임포트
from app.domains.inv import models as inv_models
from app.domains.inv import crud as inv_crud
from app.domains.loc import models as loc_models
from app.domains.usr import models as usr_models
from app.domains.ven import models as ven_models
from app.domains.fms import models as fms_models
from sqlmodel.ext.asyncio.session import AsyncSession


# =================================================================================
# 0. 테스트를 위한 Fixture 설정
# =================================================================================
@pytest.fixture(scope="function")
async def inv_test_category(db_session: AsyncSession) -> inv_models.MaterialCategory:
    """테스트용 자재 카테고리 생성 픽스처"""
    category = inv_models.MaterialCategory(code="CAT-TEST-01", name="테스트용 기본 카테고리")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture(scope="function")
async def inv_test_material(db_session: AsyncSession, inv_test_category: inv_models.MaterialCategory) -> inv_models.Material:
    """테스트용 자재 품목 생성 픽스처"""
    material = inv_models.Material(
        code="MAT-TEST-01",
        material_category_id=inv_test_category.id,
        name="테스트 기본 자재",
        unit_of_measure="EA"
    )
    db_session.add(material)
    await db_session.commit()
    await db_session.refresh(material)
    return material


@pytest.fixture
async def test_spec_def(db_session: AsyncSession) -> inv_models.MaterialSpecDefinition:
    """테스트용 자재 스펙 정의 생성 픽스처"""
    spec_def = inv_models.MaterialSpecDefinition(
        name="viscosity_cp", display_name="점도", data_type="numeric", unit="cP"
    )
    db_session.add(spec_def)
    await db_session.commit()
    await db_session.refresh(spec_def)
    return spec_def


@pytest.fixture
async def misc_spec_def(db_session: AsyncSession) -> inv_models.MaterialSpecDefinition:
    """'기타 속성'용 스펙 정의 픽스처"""
    spec_def = inv_models.MaterialSpecDefinition(
        name="misc_notes", display_name="기타 특이사항", data_type="text"
    )
    db_session.add(spec_def)
    await db_session.commit()
    await db_session.refresh(spec_def)
    return spec_def


@pytest.fixture(name="inv_test_plant")
async def inv_test_plant_fixture(db_session: AsyncSession) -> loc_models.Facility:
    plant = loc_models.Facility(code="INVPL", name="INV 테스트 처리장")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)
    return plant


@pytest.fixture(name="inv_test_vendor")
async def inv_test_vendor_fixture(db_session: AsyncSession) -> ven_models.Vendor:
    vendor = ven_models.Vendor(name="INV 테스트 공급업체", business_number="987-65-43210")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


# =================================================================================
# 1. 자재 카테고리 (MaterialCategory) 테스트
# =================================================================================
@pytest.mark.asyncio
async def test_create_material_category(admin_client: AsyncClient):
    """(성공) 관리자: 새 자재 카테고리 생성"""
    category_data = {"code": "CAT-NEW-01", "name": "새 카테고리"}
    response = await admin_client.post("/api/v1/inv/material_categories", json=category_data)
    assert response.status_code == 201
    assert response.json()["code"] == category_data["code"]


@pytest.mark.asyncio
async def test_create_category_fails_for_regular_user(authorized_client: AsyncClient):
    """(실패) 권한: 일반 사용자가 카테고리 생성 시 403 에러 발생"""
    category_data = {"code": "CAT-FAIL-01", "name": "실패용 카테고리"}
    response = await authorized_client.post("/api/v1/inv/material_categories", json=category_data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_read_material_categories_list(client: AsyncClient, inv_test_category: inv_models.MaterialCategory):
    """(성공) 모든 사용자: 자재 카테고리 목록 조회"""
    response = await client.get("/api/v1/inv/material_categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(c["code"] == inv_test_category.code for c in response.json())


@pytest.mark.asyncio
async def test_read_single_material_category_by_code(client: AsyncClient, inv_test_category: inv_models.MaterialCategory):
    """(성공) 모든 사용자: Code로 특정 자재 카테고리 조회"""
    response = await client.get(f"/api/v1/inv/material_categories/{inv_test_category.code}")
    assert response.status_code == 200
    assert response.json()["name"] == inv_test_category.name


@pytest.mark.asyncio
async def test_read_nonexistent_material_category(client: AsyncClient):
    """(실패) 예외: 존재하지 않는 카테고리 조회 시 404 에러 발생"""
    response = await client.get("/api/v1/inv/material_categories/NON-EXISTENT-CODE")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_material_category(admin_client: AsyncClient, inv_test_category: inv_models.MaterialCategory):
    """(성공) 관리자: 자재 카테고리 업데이트"""
    update_data = {"name": "업데이트된 카테고리 이름"}
    response = await admin_client.put(f"/api/v1/inv/material_categories/{inv_test_category.code}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == update_data["name"]


@pytest.mark.asyncio
async def test_delete_material_category(admin_client: AsyncClient, db_session: AsyncSession):
    """(성공) 관리자: 자재 카테고리 삭제"""
    category_to_delete = inv_models.MaterialCategory(code="CAT-TO-DELETE", name="삭제될 카테고리")
    db_session.add(category_to_delete)
    await db_session.commit()
    await db_session.refresh(category_to_delete)

    response = await admin_client.delete(f"/api/v1/inv/material_categories/{category_to_delete.code}")
    assert response.status_code == 204

    deleted_in_db = await inv_crud.material_category.get_by_code(db_session, code=category_to_delete.code)
    assert deleted_in_db is None


# =================================================================================
# 2. 자재 스펙 정의 및 유효성 검사 테스트
# =================================================================================
@pytest.mark.asyncio
async def test_update_placeholder_spec_with_valid_key(
    admin_client: AsyncClient, inv_test_category: inv_models.MaterialCategory, inv_test_material: inv_models.Material, test_spec_def: inv_models.MaterialSpecDefinition
):
    """(성공) 자동 생성된 스펙(placeholder)에 유효한 키로 값을 업데이트"""
    #  [Given] 카테고리에 스펙 정의를 연결하면, 자재에 {'viscosity_cp': None} 스펙이 자동 생성됨
    link_data = {"material_category_id": inv_test_category.id, "spec_definition_id": test_spec_def.id}
    await admin_client.post("/api/v1/inv/material_category_spec_definitions", json=link_data)

    #  [When] 해당 키('viscosity_cp')를 사용하여 스펙 값을 업데이트
    spec_data = {"materials_id": inv_test_material.id, "specs": {"viscosity_cp": 1.5}}
    response = await admin_client.post("/api/v1/inv/materials_specs", json=spec_data)

    #  [Then] 기존 레코드를 업데이트했으므로 200 OK를 반환
    assert response.status_code == 200
    assert response.json()["specs"]["viscosity_cp"] == 1.5


@pytest.mark.asyncio
async def test_create_spec_with_invalid_key(admin_client: AsyncClient, inv_test_material: inv_models.Material):
    """(실패) 유효성: 정의되지 않은 키로 스펙 생성 시 400 에러 테스트"""
    spec_data = {"materials_id": inv_test_material.id, "specs": {"undefined_key": "some_value"}}
    response = await admin_client.post("/api/v1/inv/materials_specs", json=spec_data)
    assert response.status_code == 400
    assert "Invalid spec key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_spec_with_misc_notes_key(
    admin_client: AsyncClient, inv_test_category: inv_models.MaterialCategory, inv_test_material: inv_models.Material, misc_spec_def: inv_models.MaterialSpecDefinition
):
    """(성공) 유연성: '기타 속성' 키를 사용하여 임시 스펙 추가 테스트"""
    link_data = {"material_category_id": inv_test_category.id, "spec_definition_id": misc_spec_def.id}
    await admin_client.post("/api/v1/inv/material_category_spec_definitions", json=link_data)

    spec_data = {"materials_id": inv_test_material.id, "specs": {"misc_notes": "이 로트는 특별 관리가 필요함."}}
    response = await admin_client.post("/api/v1/inv/materials_specs", json=spec_data)
    assert response.status_code == 200  # 자동 생성된 레코드 업데이트
    assert response.json()["specs"]["misc_notes"] == "이 로트는 특별 관리가 필요함."


@pytest.mark.asyncio
async def test_update_spec_with_null_to_delete_key(
    admin_client: AsyncClient, db_session: AsyncSession, inv_test_category: inv_models.MaterialCategory, inv_test_material: inv_models.Material, test_spec_def: inv_models.MaterialSpecDefinition
):
    """(성공) 기능: 스펙 업데이트 시 null 값을 보내 키-값 쌍을 삭제하는 기능 테스트"""
    link_data = {"material_category_id": inv_test_category.id, "spec_definition_id": test_spec_def.id}
    await admin_client.post("/api/v1/inv/material_category_spec_definitions", json=link_data)

    update_data_1 = {"materials_id": inv_test_material.id, "specs": {"viscosity_cp": 1.5}}
    await admin_client.post("/api/v1/inv/materials_specs", json=update_data_1)

    spec_before = await inv_crud.material_spec.get_specs_for_material(db_session, materials_id=inv_test_material.id)
    assert spec_before.specs.get("viscosity_cp") == 1.5

    update_data_2 = {"specs": {"viscosity_cp": None}}
    response = await admin_client.put(f"/api/v1/inv/materials/{inv_test_material.code}/specs", json=update_data_2)
    assert response.status_code == 200
    assert "viscosity_cp" not in response.json()["specs"]


# =================================================================================
# 3. 스펙 정의 변경 시 자동 동기화 테스트
# =================================================================================
@pytest.mark.asyncio
async def test_add_spec_def_propagates_to_material_spec(
    admin_client: AsyncClient, db_session: AsyncSession, inv_test_category: inv_models.MaterialCategory, inv_test_material: inv_models.Material, test_spec_def: inv_models.MaterialSpecDefinition
):
    """(성공) 동기화: 카테고리에 스펙 정의 추가 시, 기존 자재 스펙에 null 값으로 자동 반영"""
    spec_before = await inv_crud.material_spec.get_specs_for_material(db_session, materials_id=inv_test_material.id)
    assert spec_before is None

    link_data = {"material_category_id": inv_test_category.id, "spec_definition_id": test_spec_def.id}
    response = await admin_client.post("/api/v1/inv/material_category_spec_definitions", json=link_data)
    assert response.status_code == 201

    await db_session.refresh(inv_test_material, attribute_names=["specs"])
    assert inv_test_material.specs is not None
    assert inv_test_material.specs.specs == {test_spec_def.name: None}


@pytest.mark.asyncio
async def test_remove_spec_def_propagates_to_material_spec(
    admin_client: AsyncClient, db_session: AsyncSession, inv_test_category: inv_models.MaterialCategory, inv_test_material: inv_models.Material, test_spec_def: inv_models.MaterialSpecDefinition
):
    """(성공) 동기화: 카테고리에서 스펙 정의 제거 시, 기존 자재 스펙에서 자동 삭제"""
    link_data = {"material_category_id": inv_test_category.id, "spec_definition_id": test_spec_def.id}
    await admin_client.post("/api/v1/inv/material_category_spec_definitions", json=link_data)

    update_data = {"specs": {test_spec_def.name: "some_value"}}
    await admin_client.put(f"/api/v1/inv/materials/{inv_test_material.code}/specs", json=update_data)

    await db_session.refresh(inv_test_material, attribute_names=["specs"])
    assert test_spec_def.name in inv_test_material.specs.specs

    response = await admin_client.delete(f"/api/v1/inv/material_category_spec_definitions?material_category_id={inv_test_category.id}&spec_definition_id={test_spec_def.id}")
    assert response.status_code == 204

    await db_session.refresh(inv_test_material, attribute_names=["specs"])
    assert test_spec_def.name not in inv_test_material.specs.specs


@pytest.mark.asyncio
async def test_update_spec_def_name_propagates_to_material_spec(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    inv_test_category: inv_models.MaterialCategory,
    inv_test_material: inv_models.Material,
    test_spec_def: inv_models.MaterialSpecDefinition
):
    """(성공) 동기화: 스펙 정의 이름(name) 변경 시, 자재 스펙의 키가 자동 변경되는지 테스트"""
    #  [Given] 카테고리에 스펙을 연결하고, 자재에 해당 스펙 값을 입력
    link_data = {"material_category_id": inv_test_category.id, "spec_definition_id": test_spec_def.id}
    await admin_client.post("/api/v1/inv/material_category_spec_definitions", json=link_data)

    spec_data = {"materials_id": inv_test_material.id, "specs": {test_spec_def.name: 123.45}}
    await admin_client.post("/api/v1/inv/materials_specs", json=spec_data)

    await db_session.refresh(inv_test_material, attribute_names=["specs"])
    assert inv_test_material.specs.specs.get(test_spec_def.name) == 123.45

    #  [When] 스펙 정의의 이름을 변경
    old_name = test_spec_def.name
    new_name = "viscosity_cst"  # 'viscosity_cp' -> 'viscosity_cst'
    update_payload = {"name": new_name}
    response = await admin_client.put(f"/api/v1/inv/material_spec_definitions/{test_spec_def.id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["name"] == new_name

    #  [Then] 자재의 스펙 키도 새로운 이름으로 변경되었는지 확인
    await db_session.refresh(inv_test_material, attribute_names=["specs"])
    assert old_name not in inv_test_material.specs.specs
    assert new_name in inv_test_material.specs.specs
    assert inv_test_material.specs.specs.get(new_name) == 123.45


# =================================================================================
# 4. 자재 거래 (MaterialTransaction) 및 FIFO 로직 테스트
# =================================================================================
async def setup_fifo_test_data(db_session, material, plant, vendor):
    """FIFO 테스트를 위한 배치 데이터 생성 헬퍼 함수"""
    batch1 = inv_models.MaterialBatch(
        material_id=material.id,
        facility_id=plant.id,
        quantity=Decimal("20.0"),
        received_date=datetime(2025, 1, 1, tzinfo=UTC),
        vendor_id=vendor.id
    )
    batch2 = inv_models.MaterialBatch(
        material_id=material.id,
        facility_id=plant.id,
        quantity=Decimal("30.0"),
        received_date=datetime(2025, 2, 1, tzinfo=UTC),
        vendor_id=vendor.id
    )
    db_session.add_all([batch1, batch2])
    await db_session.commit()
    await db_session.refresh(batch1)
    await db_session.refresh(batch2)
    return batch1, batch2


@pytest.mark.asyncio
async def test_create_transaction_usage_fifo_partial_depletion(
    authorized_client: AsyncClient,
    db_session: AsyncSession,
    inv_test_material: inv_models.Material,
    inv_test_plant: loc_models.Facility,
    inv_test_vendor: ven_models.Vendor
):
    """(성공) FIFO: 첫 번째 배치를 부분적으로 소모하는 로직 테스트"""
    batch1, batch2 = await setup_fifo_test_data(
        db_session, inv_test_material, inv_test_plant, inv_test_vendor
    )

    usage_qty = -10.0
    transaction_data = {
        "material_id": inv_test_material.id,
        "facility_id": inv_test_plant.id,
        "transaction_type": "USAGE",
        "quantity_change": usage_qty
    }
    response = await authorized_client.post(
        "/api/v1/inv/material_transactions", json=transaction_data
    )
    assert response.status_code == 201

    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["source_batch_id"] == batch1.id

    await db_session.refresh(batch1)
    await db_session.refresh(batch2)

    assert batch1.quantity == Decimal('10.00')
    assert batch2.quantity == Decimal('30.00')
