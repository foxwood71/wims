# tests/domains/test_fms_n.py

"""
'fms' 도메인 (설비 관리 시스템) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.

- 주요 FMS 엔티티 (설비 카테고리, 설비 스펙 정의, 설비, 설비 이력 등)의 CRUD 테스트.
- 고유성 제약 (이름, 코드, 일련번호, 자산태그) 검증.
- 스펙 정의 변경 시 설비 스펙 자동 동기화 기능 검증.
- 다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
  인증 및 권한 부여 로직을 검증합니다.
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

#  다른 도메인의 모델 임포트
from app.domains.loc import models as loc_models
from app.domains.usr import models as usr_models
from app.domains.ven import models as ven_models

#  FMS 도메인의 모델 임포트
from app.domains.fms import models as fms_models

from datetime import date


#  --- FMS 보조 데이터 생성 픽스처 ---

@pytest.fixture(name="fms_test_plant")
async def fms_test_plant_fixture(db_session: AsyncSession) -> loc_models.Facility:
    """테스트용 처리장을 생성하는 픽스처"""
    plant = loc_models.Facility(code="FMSPL", name="FMS 테스트 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)
    return plant


@pytest.fixture(name="fms_test_location")
async def fms_test_location_fixture(db_session: AsyncSession, fms_test_plant: loc_models.Facility) -> loc_models.Location:
    """테스트용 장소를 생성하는 픽스처"""
    location = loc_models.Location(
        facility_id=fms_test_plant.id,
        name="FMS 테스트 장소"
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


@pytest.fixture(name="fms_test_vendor")
async def fms_test_vendor_fixture(db_session: AsyncSession) -> ven_models.Vendor:
    """테스트용 공급업체를 생성하는 픽스처"""
    vendor = ven_models.Vendor(name="FMS 테스트 공급업체", business_number="111-22-33333")
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


@pytest.fixture(name="fms_test_category")
async def fms_test_category_fixture(db_session: AsyncSession) -> fms_models.EquipmentCategory:
    """테스트용 설비 카테고리를 생성하는 픽스처"""
    category = fms_models.EquipmentCategory(name="테스트 카테고리")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture(name="fms_test_spec_def")
async def fms_test_spec_def_fixture(db_session: AsyncSession) -> fms_models.EquipmentSpecDefinition:
    """테스트용 설비 스펙 정의를 생성하는 픽스처"""
    spec_def = fms_models.EquipmentSpecDefinition(
        name="test_spec", display_name="테스트 스펙", data_type="text"
    )
    db_session.add(spec_def)
    await db_session.commit()
    await db_session.refresh(spec_def)
    return spec_def


# [신규] 기존 데이터를 표현하기 위한 별도의 스펙 정의 픽스처 추가
@pytest.fixture(name="fms_existing_spec_def")
async def fms_existing_spec_def_fixture(db_session: AsyncSession) -> fms_models.EquipmentSpecDefinition:
    """초기 데이터 세팅을 위한 기존 스펙 정의 픽스처"""
    spec_def = fms_models.EquipmentSpecDefinition(
        name="existing_spec", display_name="기존 스펙", data_type="text"
    )
    db_session.add(spec_def)
    await db_session.commit()
    await db_session.refresh(spec_def)
    return spec_def


@pytest.fixture(name="fms_test_equipment")
async def fms_test_equipment_fixture(
    db_session: AsyncSession,
    fms_test_plant: loc_models.Facility,
    fms_test_category: fms_models.EquipmentCategory
) -> fms_models.Equipment:
    """테스트용 설비를 생성하는 픽스처"""
    equipment = fms_models.Equipment(
        facility_id=fms_test_plant.id,
        equipment_category_id=fms_test_category.id,
        name="테스트 설비",
        serial_number="SN-TEST-FMS-001"
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)
    return equipment


#  =============================================================================
#  1. 설비 카테고리 (equipment_categories) 엔드포인트 테스트
#  =============================================================================

@pytest.mark.asyncio
class TestEquipmentCategory:
    """설비 카테고리 API 테스트 그룹"""

    async def test_create_equipment_category_by_admin(self, admin_client: AsyncClient):
        """(성공) 관리자가 새 설비 카테고리 생성"""
        response = await admin_client.post("/api/v1/fms/equipment_categories", json={"name": "펌프"})
        assert response.status_code == 201
        assert response.json()["name"] == "펌프"

    async def test_create_equipment_category_by_user_fails(self, authorized_client: AsyncClient):
        """(실패) 일반 유저가 설비 카테고리 생성 시 403 Forbidden"""
        response = await authorized_client.post("/api/v1/fms/equipment_categories", json={"name": "펌프-실패"})
        assert response.status_code == 403

    async def test_create_duplicate_equipment_category_fails(self, admin_client: AsyncClient, fms_test_category: fms_models.EquipmentCategory):
        """(실패) 중복된 이름으로 카테고리 생성 시 400 Bad Request"""
        response = await admin_client.post("/api/v1/fms/equipment_categories", json={"name": fms_test_category.name})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_read_equipment_categories(self, client: AsyncClient, fms_test_category: fms_models.EquipmentCategory):
        """(성공) 모든 설비 카테고리 목록 조회"""
        response = await client.get("/api/v1/fms/equipment_categories")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert any(cat["id"] == fms_test_category.id for cat in response.json())

    async def test_read_equipment_category_by_id(self, client: AsyncClient, fms_test_category: fms_models.EquipmentCategory):
        """(성공) ID로 특정 설비 카테고리 조회"""
        response = await client.get(f"/api/v1/fms/equipment_categories/{fms_test_category.id}")
        assert response.status_code == 200
        assert response.json()["name"] == fms_test_category.name

    async def test_read_equipment_category_not_found(self, client: AsyncClient):
        """(실패) 존재하지 않는 ID로 카테고리 조회 시 404 Not Found"""
        response = await client.get("/api/v1/fms/equipment_categories/99999")
        assert response.status_code == 404

    async def test_update_equipment_category_by_admin(self, admin_client: AsyncClient, fms_test_category: fms_models.EquipmentCategory):
        """(성공) 관리자가 설비 카테고리 업데이트"""
        update_data = {"name": "업데이트된 카테고리", "description": "설명 추가"}
        response = await admin_client.put(f"/api/v1/fms/equipment_categories/{fms_test_category.id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == update_data["name"]
        assert response.json()["description"] == update_data["description"]

    async def test_delete_equipment_category_by_admin(self, admin_client: AsyncClient, db_session: AsyncSession):
        """(성공) 관리자가 설비 카테고리 삭제"""
        category_to_delete = fms_models.EquipmentCategory(name="삭제될 카테고리")
        db_session.add(category_to_delete)
        await db_session.commit()
        await db_session.refresh(category_to_delete)

        response = await admin_client.delete(f"/api/v1/fms/equipment_categories/{category_to_delete.id}")
        assert response.status_code == 204

        get_response = await admin_client.get(f"/api/v1/fms/equipment_categories/{category_to_delete.id}")
        assert get_response.status_code == 404


#  =============================================================================
#  2. 설비 스펙 정의 (equipment_spec_definitions) 엔드포인트 테스트
#  =============================================================================

@pytest.mark.asyncio
class TestEquipmentSpecDefinition:
    """설비 스펙 정의 API 테스트 그룹"""

    async def test_create_spec_definition_by_admin(self, admin_client: AsyncClient):
        """(성공) 관리자가 새 스펙 정의 생성"""
        spec_data = {"name": "power_kw", "display_name": "정격 출력", "data_type": "numeric"}
        response = await admin_client.post("/api/v1/fms/equipment_spec_definitions", json=spec_data)
        assert response.status_code == 201
        assert response.json()["name"] == "power_kw"

    async def test_read_spec_definitions(self, client: AsyncClient, fms_test_spec_def: fms_models.EquipmentSpecDefinition):
        """(성공) 모든 스펙 정의 목록 조회"""
        response = await client.get("/api/v1/fms/equipment_spec_definitions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert any(spec["id"] == fms_test_spec_def.id for spec in response.json())

    async def test_update_spec_definition_name_syncs_equipment_specs(
        self,
        admin_client: AsyncClient,
        fms_test_equipment: fms_models.Equipment,
        fms_test_spec_def: fms_models.EquipmentSpecDefinition,
        fms_test_category: fms_models.EquipmentCategory
    ):
        """(성공/수정) 스펙 정의 이름 변경 시 모든 설비의 스펙 키가 동기화되는지 검증"""
        # 전제조건: 스펙 키가 유효하도록 카테고리에 스펙 정의를 먼저 연결
        link_data = {
            "equipment_category_id": fms_test_category.id,
            "spec_definition_id": fms_test_spec_def.id
        }
        link_response = await admin_client.post("/api/v1/fms/equipment_category_spec_definitions", json=link_data)
        assert link_response.status_code == 201

        # 초기 스펙 설정
        initial_spec_key = fms_test_spec_def.name
        spec_data = {"equipment_id": fms_test_equipment.id, "specs": {initial_spec_key: 100}}
        create_response = await admin_client.post("/api/v1/fms/equipment_specs", json=spec_data)
        assert create_response.status_code == 201, f"초기 스펙 생성 실패: {create_response.json()}"

        # 스펙 정의 이름 변경
        new_spec_key = "updated_spec_key"
        update_data = {"name": new_spec_key}
        update_response = await admin_client.put(
            f"/api/v1/fms/equipment_spec_definitions/{fms_test_spec_def.id}", json=update_data
        )
        assert update_response.status_code == 200

        # 설비의 스펙이 변경되었는지 확인
        response = await admin_client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}/specs")
        assert response.status_code == 200
        updated_specs = response.json()["specs"]

        assert new_spec_key in updated_specs
        assert updated_specs[new_spec_key] == 100
        assert initial_spec_key not in updated_specs


#  =============================================================================
#  3. 카테고리-스펙 연결 (equipment_category_spec_definitions) 테스트
#  =============================================================================

@pytest.mark.asyncio
class TestCategorySpecLink:
    """설비 카테고리-스펙 정의 연결 API 및 동기화 테스트 그룹"""

    async def test_add_spec_to_category_and_sync_equipment(
        self,
        admin_client: AsyncClient,
        fms_test_category: fms_models.EquipmentCategory,
        fms_test_spec_def: fms_models.EquipmentSpecDefinition,
        fms_existing_spec_def: fms_models.EquipmentSpecDefinition,  # [수정] 신규 픽스처 주입
        fms_test_equipment: fms_models.Equipment
    ):
        """(성공/수정) 카테고리에 스펙 연결 시 설비에 스펙 필드가 null로 추가되는지 검증"""
        # [수정-1] 전제조건: "기존" 스펙을 먼저 카테고리에 연결
        link_existing_spec_data = {
            "equipment_category_id": fms_test_category.id,
            "spec_definition_id": fms_existing_spec_def.id
        }
        link_res = await admin_client.post("/api/v1/fms/equipment_category_spec_definitions", json=link_existing_spec_data)
        assert link_res.status_code == 201

        # [수정-2] 유효한 "기존" 스펙 키를 사용하여 초기 스펙 설정
        initial_spec_data = {
            "equipment_id": fms_test_equipment.id,
            "specs": {fms_existing_spec_def.name: "initial_value"}
        }
        create_res = await admin_client.post("/api/v1/fms/equipment_specs", json=initial_spec_data)
        assert create_res.status_code == 201, f"초기 스펙 생성 실패: {create_res.json()}"

        # [수정-3] 테스트하려는 "신규" 스펙을 카테고리에 연결 (핵심 테스트 동작)
        link_new_spec_data = {
            "equipment_category_id": fms_test_category.id,
            "spec_definition_id": fms_test_spec_def.id
        }
        response = await admin_client.post("/api/v1/fms/equipment_category_spec_definitions", json=link_new_spec_data)
        assert response.status_code == 201

        # 설비 스펙을 다시 조회하여 확인
        spec_response = await admin_client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}/specs")
        assert spec_response.status_code == 200
        updated_specs = spec_response.json()["specs"]

        # [수정-4] 기존 데이터 보존 및 신규 데이터 추가(null) 동시 확인
        assert fms_existing_spec_def.name in updated_specs
        assert updated_specs[fms_existing_spec_def.name] == "initial_value"
        assert fms_test_spec_def.name in updated_specs
        assert updated_specs[fms_test_spec_def.name] is None

    async def test_remove_spec_from_category_and_sync_equipment(
        self,
        admin_client: AsyncClient,
        fms_test_category: fms_models.EquipmentCategory,
        fms_test_spec_def: fms_models.EquipmentSpecDefinition,
        fms_existing_spec_def: fms_models.EquipmentSpecDefinition,  # [수정] 픽스처 주입
        fms_test_equipment: fms_models.Equipment
    ):
        """(성공/수정) 카테고리에서 스펙 연결 해제 시 설비의 스펙 필드가 제거되는지 검증"""
        # [수정-1] 테스트할 스펙과 유지될 스펙을 모두 카테고리에 연결
        await admin_client.post(
            "/api/v1/fms/equipment_category_spec_definitions",
            json={"equipment_category_id": fms_test_category.id, "spec_definition_id": fms_test_spec_def.id}
        )
        await admin_client.post(
            "/api/v1/fms/equipment_category_spec_definitions",
            json={"equipment_category_id": fms_test_category.id, "spec_definition_id": fms_existing_spec_def.id}
        )

        # [수정-2] 유효한 키들로 초기 스펙 데이터 생성
        spec_key_to_remove = fms_test_spec_def.name
        spec_key_to_keep = fms_existing_spec_def.name
        initial_spec_data = {
            "equipment_id": fms_test_equipment.id,
            "specs": {spec_key_to_remove: "some_value", spec_key_to_keep: "keep_this"}
        }
        create_res = await admin_client.post("/api/v1/fms/equipment_specs", json=initial_spec_data)
        assert create_res.status_code == 201

        # [수정-3] 제거할 스펙의 연결만 해제
        params = {"equipment_category_id": fms_test_category.id, "spec_definition_id": fms_test_spec_def.id}
        response = await admin_client.delete("/api/v1/fms/equipment_category_spec_definitions", params=params)
        assert response.status_code == 204

        # 설비 스펙을 다시 조회하여 확인
        spec_response = await admin_client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}/specs")
        assert spec_response.status_code == 200
        updated_specs = spec_response.json()["specs"]

        # [수정-4] 해당 키는 제거되고, 유지될 키는 남아있는지 확인
        assert spec_key_to_remove not in updated_specs
        assert spec_key_to_keep in updated_specs
        assert updated_specs[spec_key_to_keep] == "keep_this"


#  =============================================================================
#  4. 설비 (equipments) 엔드포인트 테스트
#  =============================================================================
@pytest.mark.asyncio
class TestEquipment:
    """설비 API 테스트 그룹"""

    async def test_create_equipment_success_admin(
        self, admin_client: AsyncClient, fms_test_plant: loc_models.Facility, fms_test_category: fms_models.EquipmentCategory, fms_test_location: loc_models.Location
    ):
        """(성공) 관리자가 새 설비 생성"""
        equipment_data = {
            "facility_id": fms_test_plant.id,
            "equipment_category_id": fms_test_category.id,
            "current_location_id": fms_test_location.id,
            "name": "유입 펌프 #1",
            "serial_number": "SN-PUMP-001",
            "asset_tag": "ASSET-001"
        }
        response = await admin_client.post("/api/v1/fms/equipments", json=equipment_data)
        assert response.status_code == 201
        assert response.json()["name"] == equipment_data["name"]

    async def test_read_equipments_with_filters(self, client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(성공) 다양한 필터로 설비 목록 조회"""
        # 필터 없이 전체 조회
        response = await client.get("/api/v1/fms/equipments")
        assert response.status_code == 200
        assert len(response.json()) >= 1

        # facility_id로 필터링
        response = await client.get(f"/api/v1/fms/equipments?facility_id={fms_test_equipment.facility_id}")
        assert response.status_code == 200
        assert len(response.json()) >= 1
        assert all(eq["facility_id"] == fms_test_equipment.facility_id for eq in response.json())

    async def test_read_equipment_by_id(self, client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(성공) ID로 특정 설비 조회"""
        response = await client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}")
        assert response.status_code == 200
        assert response.json()["id"] == fms_test_equipment.id

    async def test_update_equipment_by_admin(self, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(성공) 관리자가 설비 정보 업데이트"""
        update_data = {"name": "업데이트된 설비명", "status": "UNDER_MAINTENANCE"}
        response = await admin_client.put(f"/api/v1/fms/equipments/{fms_test_equipment.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["status"] == update_data["status"]

    async def test_delete_equipment_by_admin(self, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(성공) 관리자가 설비 삭제"""
        response = await admin_client.delete(f"/api/v1/fms/equipments/{fms_test_equipment.id}")
        assert response.status_code == 204
        get_response = await admin_client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}")
        assert get_response.status_code == 404


#  =============================================================================
#  5. 설비 스펙 (equipment_specs) 엔드포인트 테스트
#  =============================================================================
@pytest.mark.asyncio
class TestEquipmentSpec:
    """설비 스펙 API 테스트 그룹"""

    async def test_create_or_update_equipment_spec(self, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment, fms_test_category: fms_models.EquipmentCategory, fms_test_spec_def: fms_models.EquipmentSpecDefinition):
        """(성공) 설비 스펙 생성(201) 및 업데이트(200) - 유효한 키 사용"""
        # [전제조건] 카테고리에 유효한 스펙 키를 미리 연결
        link_data = {"equipment_category_id": fms_test_category.id, "spec_definition_id": fms_test_spec_def.id}
        await admin_client.post("/api/v1/fms/equipment_category_spec_definitions", json=link_data)

        # 유효한 키('test_spec')를 사용하여 생성
        spec_data = {"equipment_id": fms_test_equipment.id, "specs": {fms_test_spec_def.name: "value1"}}

        response_create = await admin_client.post("/api/v1/fms/equipment_specs", json=spec_data)
        assert response_create.status_code == 201
        created_spec = response_create.json()
        assert created_spec["specs"][fms_test_spec_def.name] == "value1"

        # 유효한 키('test_spec')를 사용하여 업데이트
        update_data = {"equipment_id": fms_test_equipment.id, "specs": {fms_test_spec_def.name: "value2"}}
        response_update = await admin_client.post("/api/v1/fms/equipment_specs", json=update_data)
        assert response_update.status_code == 200
        updated_spec = response_update.json()
        assert updated_spec["id"] == created_spec["id"]
        assert updated_spec["specs"][fms_test_spec_def.name] == "value2"

    async def test_create_spec_with_invalid_key_fails(
        self, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment
    ):
        """(실패/신규) 카테고리에 정의되지 않은 키로 스펙 생성 시 400 에러 발생"""
        # [Given] 설비가 존재하지만, 카테고리에는 어떤 스펙도 연결되지 않은 상태

        # [When] 정의되지 않은 'invalid_key'로 스펙 생성을 시도
        spec_data = {"equipment_id": fms_test_equipment.id, "specs": {"invalid_key": "some_value"}}
        response = await admin_client.post("/api/v1/fms/equipment_specs", json=spec_data)

        # [Then] 400 Bad Request 에러가 발생해야 함
        assert response.status_code == 400
        assert "Invalid spec key" in response.json()["detail"]
        assert "'invalid_key'" in response.json()["detail"]

    async def test_read_equipment_specs(self, client: AsyncClient, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment, fms_test_category: fms_models.EquipmentCategory, fms_test_spec_def: fms_models.EquipmentSpecDefinition):
        """(성공) 특정 설비의 스펙 조회"""
        # [수정] 스펙을 조회하려면 먼저 유효한 스펙을 생성해야 함
        await admin_client.post(
            "/api/v1/fms/equipment_category_spec_definitions",
            json={"equipment_category_id": fms_test_category.id, "spec_definition_id": fms_test_spec_def.id}
        )
        spec_data = {"equipment_id": fms_test_equipment.id, "specs": {fms_test_spec_def.name: "value"}}
        await admin_client.post("/api/v1/fms/equipment_specs", json=spec_data)

        response = await client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}/specs")
        assert response.status_code == 200
        assert response.json()["specs"] == {fms_test_spec_def.name: "value"}

    async def test_read_equipment_specs_not_found(self, client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(실패) 스펙이 없는 설비 조회 시 404 Not Found"""
        response = await client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}/specs")
        assert response.status_code == 404

    async def test_delete_equipment_spec(self, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment, fms_test_category: fms_models.EquipmentCategory, fms_test_spec_def: fms_models.EquipmentSpecDefinition):
        """(성공) 관리자가 설비 스펙 삭제"""
        # [수정] 삭제할 스펙을 유효한 방식으로 생성
        await admin_client.post(
            "/api/v1/fms/equipment_category_spec_definitions",
            json={"equipment_category_id": fms_test_category.id, "spec_definition_id": fms_test_spec_def.id}
        )
        spec_data = {"equipment_id": fms_test_equipment.id, "specs": {fms_test_spec_def.name: "data_to_delete"}}
        create_res = await admin_client.post("/api/v1/fms/equipment_specs", json=spec_data)
        spec_id = create_res.json()["id"]

        delete_res = await admin_client.delete(f"/api/v1/fms/equipment_specs/{spec_id}")
        assert delete_res.status_code == 204


#  =============================================================================
#  6. 설비 이력 (equipment_history) 엔드포인트 테스트
#  =============================================================================
@pytest.mark.asyncio
class TestEquipmentHistory:
    """설비 이력 API 테스트 그룹"""

    async def test_create_equipment_history_by_user(
        self, authorized_client: AsyncClient, fms_test_equipment: fms_models.Equipment, test_user: usr_models.User
    ):
        """(성공) 일반 유저가 새 설비 이력 생성 (수행자는 자동으로 현재 유저)"""
        history_data = {"equipment_id": fms_test_equipment.id, "change_type": "MAINTENANCE", "description": "월간 정기 점검"}
        response = await authorized_client.post("/api/v1/fms/equipment_history", json=history_data)
        assert response.status_code == 201
        created_history = response.json()
        assert created_history["equipment_id"] == fms_test_equipment.id
        assert created_history["performed_by_user_id"] == test_user.id

    async def test_create_equipment_history_with_invalid_fk_fails(self, admin_client: AsyncClient):
        """(실패) 존재하지 않는 설비 ID로 이력 생성 시 400 Bad Request"""
        history_data = {"equipment_id": 99999, "change_type": "FAILURE", "description": "잘못된 이력"}
        response = await admin_client.post("/api/v1/fms/equipment_history", json=history_data)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    async def test_read_equipment_history_for_equipment(
        self, client: AsyncClient, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment
    ):
        """(성공) 특정 설비의 모든 이력 기록 조회"""
        await admin_client.post("/api/v1/fms/equipment_history", json={"equipment_id": fms_test_equipment.id, "change_type": "INSTALL"})
        await admin_client.post("/api/v1/fms/equipment_history", json={"equipment_id": fms_test_equipment.id, "change_type": "REPAIR"})

        response = await client.get(f"/api/v1/fms/equipments/{fms_test_equipment.id}/history")
        assert response.status_code == 200
        history_list = response.json()
        assert len(history_list) == 2
        assert history_list[0]["change_type"] == "REPAIR"

    async def test_read_single_equipment_history(self, client: AsyncClient, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(성공) ID로 특정 설비 이력 기록 조회"""
        create_res = await admin_client.post("/api/v1/fms/equipment_history", json={"equipment_id": fms_test_equipment.id, "change_type": "TEST"})
        history_id = create_res.json()["id"]

        response = await client.get(f"/api/v1/fms/equipment_history/{history_id}")
        assert response.status_code == 200
        assert response.json()["id"] == history_id

    async def test_update_equipment_history(self, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(성공) 관리자가 설비 이력 업데이트"""
        create_res = await admin_client.post("/api/v1/fms/equipment_history", json={"equipment_id": fms_test_equipment.id, "change_type": "INITIAL"})
        history_id = create_res.json()["id"]
        update_data = {"description": "상세 설명 업데이트"}
        response = await admin_client.put(f"/api/v1/fms/equipment_history/{history_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["description"] == update_data["description"]

    async def test_delete_equipment_history(self, admin_client: AsyncClient, fms_test_equipment: fms_models.Equipment):
        """(성공) 관리자가 설비 이력 삭제"""
        create_res = await admin_client.post("/api/v1/fms/equipment_history", json={"equipment_id": fms_test_equipment.id, "change_type": "TO_DELETE"})
        history_id = create_res.json()["id"]
        response = await admin_client.delete(f"/api/v1/fms/equipment_history/{history_id}")
        assert response.status_code == 204
