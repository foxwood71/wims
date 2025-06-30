# tests/domains/test_loc.py

"""
'loc' 도메인 (위치 정보 관리) 관련 API 엔드포인트에 대한 통합 테스트를 정의하는 모듈입니다.

- 하수처리장 관리 엔드포인트 테스트:
    - `POST /loc/wastewater_plants/` (생성)
    - `GET /loc/wastewater_plants/` (목록 조회)
    - `GET /loc/wastewater_plants/{id}` (단일 조회)
    - `PUT /loc/wastewater_plants/{id}` (업데이트)
    - `DELETE /loc/wastewater_plants/{id}` (삭제)
- 장소 유형 관리 엔드포인트 테스트:
    - `POST /loc/location_types/` (생성)
    - `GET /loc/location_types/` (목록 조회)
    - `GET /loc/location_types/{id}` (단일 조회)
    - `PUT /loc/location_types/{id}` (업데이트)
    - `DELETE /loc/location_types/{id}` (삭제)
- 실제 장소 관리 엔드포인트 테스트:
    - `POST /loc/locations/` (생성)
    - `GET /loc/locations/` (목록 조회, 처리장별 필터링)
    - `GET /loc/locations/{id}` (단일 조회)
    - `PUT /loc/locations/{id}` (업데이트)
    - `DELETE /loc/locations/{id}` (삭제)

다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
인증 및 권한 부여 로직을 검증합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.domains.loc import models as loc_models
from app.domains.loc import schemas as loc_schemas
from app.domains.loc.crud import wastewater_plant as wastewater_plant_crud  # CRUD 직접 사용 (테스트 셋업용)
from app.domains.loc.crud import location_type as location_type_crud
from app.domains.loc.crud import location as location_crud


# --- 하수처리장 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_wastewater_plant_success_admin(
    admin_client: TestClient,  # 관리자로 인증된 클라이언트
):
    """
    관리자 권한으로 새로운 하수처리장을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_wastewater_plant_success_admin ---")
    plant_data = {
        "code": "PLNT1",
        "name": "테스트하수처리장1",
        "address": "테스트 주소",
        "is_stp": True,
        "sort_order": 1
    }
    response = await admin_client.post("/api/v1/loc/wastewater_plants/", json=plant_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_plant = response.json()
    assert created_plant["name"] == plant_data["name"]
    assert created_plant["code"] == plant_data["code"]
    assert "id" in created_plant
    print("test_create_wastewater_plant_success_admin passed.")


@pytest.mark.asyncio
async def test_create_wastewater_plant_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session  # 데이터베이스에 플랜트 미리 생성하기 위해
):
    """
    관리자 권한으로 이미 존재하는 이름의 하수처리장을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_wastewater_plant_duplicate_name_admin ---")
    existing_plant = loc_models.facility(code="EXIST", name="기존하수처리장")
    db_session.add(existing_plant)
    await db_session.commit()
    await db_session.refresh(existing_plant)

    plant_data = {
        "code": "NEWP",
        "name": "기존하수처리장",  # 중복 이름
    }
    response = await admin_client.post("/api/v1/loc/wastewater_plants/", json=plant_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Wastewater plant with this name already exists"
    print("test_create_wastewater_plant_duplicate_name_admin passed.")


@pytest.mark.asyncio
async def test_create_wastewater_plant_unauthorized(
    authorized_client: TestClient,  # 일반 사용자로 인증된 클라이언트
    client: TestClient  # 비인증 클라이언트
):
    """
    일반 사용자 및 비인증 사용자가 하수처리장 생성 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_wastewater_plant_unauthorized ---")
    plant_data = {
        "code": "DENY",
        "name": "거부된하수처리장",
    }

    # 일반 사용자 시도
    response_user = await authorized_client.post("/api/v1/loc/wastewater_plants/", json=plant_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.post("/api/v1/loc/wastewater_plants/", json=plant_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_create_wastewater_plant_unauthorized passed.")


@pytest.mark.asyncio
async def test_read_wastewater_plants_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 하수처리장 목록을 성공적으로 조회하는지 테스트합니다.
    (권한이 필요 없는 GET 엔드포인트로 가정)
    """
    print("\n--- Running test_read_wastewater_plants_success ---")
    plant1 = loc_models.facility(code="PL1", name="플랜트1")
    plant2 = loc_models.facility(code="PL2", name="플랜트2")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    response = await client.get("/api/v1/loc/wastewater_plants/")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    assert len(response.json()) >= 2  # 최소 2개 이상 (다른 테스트에서 생성된 것 포함 가능)
    assert any(p["name"] == "플랜트1" for p in response.json())
    assert any(p["name"] == "플랜트2" for p in response.json())
    print("test_read_wastewater_plants_success passed.")


@pytest.mark.asyncio
async def test_update_wastewater_plant_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 하수처리장 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_wastewater_plant_success_admin ---")
    plant = loc_models.facility(code="UPDA", name="업데이트대상플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    update_data = {"name": "업데이트된플랜트명", "address": "수정된 주소"}
    response = await admin_client.put(f"/api/v1/loc/wastewater_plants/{plant.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_plant = response.json()
    assert updated_plant["id"] == plant.id
    assert updated_plant["name"] == update_data["name"]
    assert updated_plant["address"] == update_data["address"]
    print("test_update_wastewater_plant_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_wastewater_plant_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 하수처리장을 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_wastewater_plant_success_admin ---")
    plant = loc_models.facility(code="DEL", name="삭제대상플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    response = await admin_client.delete(f"/api/v1/loc/wastewater_plants/{plant.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_plant = await wastewater_plant_crud.get(db_session, id=plant.id)
    assert deleted_plant is None
    print("test_delete_wastewater_plant_success_admin passed.")


# --- 장소 유형 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_location_type_success_admin(
    admin_client: TestClient,
):
    """
    관리자 권한으로 새로운 장소 유형을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_type_success_admin ---")
    loc_type_data = {
        "name": "테스트유형1",
        "description": "테스트용 장소 유형입니다."
    }
    response = await admin_client.post("/api/v1/loc/location_types/", json=loc_type_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_type = response.json()
    assert created_type["name"] == loc_type_data["name"]
    assert "id" in created_type
    print("test_create_location_type_success_admin passed.")


@pytest.mark.asyncio
async def test_create_location_type_duplicate_name_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 존재하는 이름의 장소 유형 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_type_duplicate_name_admin ---")
    existing_type = loc_models.LocationType(name="기존유형")
    db_session.add(existing_type)
    await db_session.commit()
    await db_session.refresh(existing_type)

    loc_type_data = {
        "name": "기존유형",  # 중복 이름
    }
    response = await admin_client.post("/api/v1/loc/location_types/", json=loc_type_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Location type with this name already exists"
    print("test_create_location_type_duplicate_name_admin passed.")


@pytest.mark.asyncio
async def test_read_location_types_success(client: TestClient, db_session: Session):
    """
    모든 사용자가 장소 유형 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_location_types_success ---")
    type1 = loc_models.LocationType(name="유형A")
    type2 = loc_models.LocationType(name="유형B")
    db_session.add(type1)
    db_session.add(type2)
    await db_session.commit()
    await db_session.refresh(type1)
    await db_session.refresh(type2)

    response = await client.get("/api/v1/loc/location_types/")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    assert len(response.json()) >= 2
    assert any(t["name"] == "유형A" for t in response.json())
    assert any(t["name"] == "유형B" for t in response.json())
    print("test_read_location_types_success passed.")


# --- 실제 장소 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_location_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 새로운 장소를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_success_admin ---")
    plant = loc_models.facility(code="PLANT", name="장소테스트플랜트")
    loc_type = loc_models.LocationType(name="창고")
    db_session.add(plant)
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(plant)
    await db_session.refresh(loc_type)

    location_data = {
        "plant_id": plant.id,
        "location_type_id": loc_type.id,
        "name": "메인 창고",
        "description": "자재 보관 창고",
    }
    response = await admin_client.post("/api/v1/loc/locations/", json=location_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_location = response.json()
    assert created_location["name"] == location_data["name"]
    assert created_location["plant_id"] == plant.id
    assert "id" in created_location
    print("test_create_location_success_admin passed.")


@pytest.mark.asyncio
async def test_create_location_duplicate_name_in_plant_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    동일 처리장 내에서 중복 이름의 장소 (및 상위 위치가 동일한) 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_duplicate_name_in_plant_admin ---")
    plant = loc_models.facility(code="DUPPL", name="중복이름테스트플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    # 첫 번째 장소 생성
    loc_data1 = {
        "plant_id": plant.id,
        "name": "중복 장소",
        "description": "첫 번째 중복 장소",
    }
    response1 = await admin_client.post("/api/v1/loc/locations/", json=loc_data1)
    assert response1.status_code == 201

    # 두 번째 장소 생성 (중복 이름)
    loc_data2 = {
        "plant_id": plant.id,
        "name": "중복 장소",
        "description": "두 번째 중복 장소",
    }
    response2 = await admin_client.post("/api/v1/loc/locations/", json=loc_data2)
    print(f"Response status code: {response2.status_code}")
    print(f"Response JSON: {response2.json()}")

    assert response2.status_code == 400
    assert response2.json()["detail"] == "Location with this name and parent already exists in this plant."
    print("test_create_location_duplicate_name_in_plant_admin passed.")


@pytest.mark.asyncio
async def test_create_location_with_nonexistent_plant_admin(
    admin_client: TestClient,
):
    """
    관리자 권한으로 존재하지 않는 처리장 ID로 장소 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_with_nonexistent_plant_admin ---")
    location_data = {
        "plant_id": 9999,  # 존재하지 않는 ID
        "name": "가짜 장소",
    }
    response = await admin_client.post("/api/v1/loc/locations/", json=location_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Wastewater plant not found for the given ID"
    print("test_create_location_with_nonexistent_plant_admin passed.")


@pytest.mark.asyncio
async def test_read_locations_by_plant_id_success(client: TestClient, db_session: Session):
    """
    특정 처리장 ID로 장소 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_locations_by_plant_id_success ---")
    plant1 = loc_models.facility(code="RP1", name="조회플랜트1")
    plant2 = loc_models.facility(code="RP2", name="조회플랜트2")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    loc1_p1 = loc_models.Location(plant_id=plant1.id, name="장소1_플1")
    loc2_p1 = loc_models.Location(plant_id=plant1.id, name="장소2_플1")
    loc1_p2 = loc_models.Location(plant_id=plant2.id, name="장소1_플2")
    db_session.add(loc1_p1)
    db_session.add(loc2_p1)
    db_session.add(loc1_p2)
    await db_session.commit()
    await db_session.refresh(loc1_p1)
    await db_session.refresh(loc2_p1)
    await db_session.refresh(loc1_p2)

    response = await client.get(f"/api/v1/loc/locations/?plant_id={plant1.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    locations = response.json()
    assert len(locations) == 2
    assert all(loc["plant_id"] == plant1.id for loc in locations)
    assert any(loc["name"] == "장소1_플1" for loc in locations)
    assert any(loc["name"] == "장소2_플1" for loc in locations)
    print("test_read_locations_by_plant_id_success passed.")


@pytest.mark.asyncio
async def test_update_location_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 장소 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_location_success_admin ---")
    plant = loc_models.facility(code="UPDL", name="업데이트대상장소플랜트")
    loc_type = loc_models.LocationType(name="업데이트유형")
    db_session.add(plant)
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(plant)
    await db_session.refresh(loc_type)

    location_to_update = loc_models.Location(plant_id=plant.id, name="업데이트대상장소")
    db_session.add(location_to_update)
    await db_session.commit()
    await db_session.refresh(location_to_update)

    update_data = {
        "name": "업데이트된 장소명",
        "description": "수정된 설명",
        "location_type_id": loc_type.id
    }
    response = await admin_client.put(f"/api/v1/loc/locations/{location_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_location = response.json()
    assert updated_location["id"] == location_to_update.id
    assert updated_location["name"] == update_data["name"]
    assert updated_location["description"] == update_data["description"]
    assert updated_location["location_type_id"] == loc_type.id
    print("test_update_location_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_location_success_admin(
    admin_client: TestClient,
    db_session: Session
):
    """
    관리자 권한으로 장소를 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_location_success_admin ---")
    plant = loc_models.facility(code="DELL", name="삭제대상장소플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    location_to_delete = loc_models.Location(plant_id=plant.id, name="삭제대상장소")
    db_session.add(location_to_delete)
    await db_session.commit()
    await db_session.refresh(location_to_delete)

    response = await admin_client.delete(f"/api/v1/loc/locations/{location_to_delete.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_location = await location_crud.get(db_session, id=location_to_delete.id)
    assert deleted_location is None
    print("test_delete_location_success_admin passed.")
