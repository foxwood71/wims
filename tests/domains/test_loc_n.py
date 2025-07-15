# tests/domains/test_loc.py

"""
'loc' 도메인 (위치 정보 관리) 관련 API 엔드포인트에 대한 통합 테스트를 정의하는 모듈입니다.

- 하수처리장 관리 엔드포인트 테스트:
    - `POST /loc/facilitiess/` (생성)
    - `GET /loc/facilitiess/` (목록 조회)
    - `GET /loc/facilitiess/{id}` (단일 조회)
    - `PUT /loc/facilitiess/{id}` (업데이트)
    - `DELETE /loc/facilitiess/{id}` (삭제)
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

from typing import Any
import pytest
from httpx import AsyncClient
from sqlmodel import Session  # , select
# from fastapi.testclient import TestClient


# 다른 도메인의 모델을 참조하는 경우 필요
from app.domains.fms.models import Equipment as FmsEquipment
# from app.domains.loc import crud as loc_crud
from app.domains.loc import models as loc_models
from app.domains.loc import crud as loc_crud
# from app.domains.loc import schemas as loc_schemas

# from app.domains.loc.crud import facilities as facility_crud
# from app.domains.loc.crud import location_type as location_type_crud


# --- 하수처리장 관리 엔드포인트 테스트 ---


@pytest.mark.asyncio
async def test_create_facility_success_admin(
    admin_client: AsyncClient,  # 관리자로 인증된 클라이언트
):
    """
    관리자 권한으로 새로운 하수처리장을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_facility_success_admin ---")
    plant_data = {
        "code": "PLNT1",
        "name": "테스트하수처리장1",
        "address": "테스트 주소",
        "is_stp": True,
        "sort_order": 1,
    }
    response = await admin_client.post("/api/v1/loc/facilities/", json=plant_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_facility = response.json()
    assert created_facility["name"] == plant_data["name"]
    assert created_facility["code"] == plant_data["code"]
    assert "id" in created_facility
    print("test_create_facility_success_admin passed.")


@pytest.mark.asyncio
async def test_create_facility_duplicate_name_admin(
    admin_client: AsyncClient,
    db_session: Session,  # 데이터베이스에 플랜트 미리 생성하기 위해
):
    """
    관리자 권한으로 이미 존재하는 이름의 하수처리장을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_facility_duplicate_name_admin ---")
    existing_facility = loc_models.Facility(code="EXSTN", name="기존하수처리장")
    db_session.add(existing_facility)
    await db_session.commit()
    await db_session.refresh(existing_facility)

    plant_data = {
        "code": "NEWP",
        "name": "기존하수처리장",  # 중복 이름
    }
    response = await admin_client.post("/api/v1/loc/facilities/", json=plant_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Facility with this name already exists"
    print("test_create_facility_duplicate_name_admin passed.")


@pytest.mark.asyncio
async def test_create_facility_duplicate_code_admin(
    admin_client: AsyncClient,
    db_session: Session,
):
    """
    관리자 권한으로 이미 존재하는 코드의 하수처리장을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_create_facility_duplicate_code_admin ---")
    existing_facility = loc_models.Facility(code="EXSTN", name="코드중복테스트처리장")
    db_session.add(existing_facility)
    await db_session.commit()
    await db_session.refresh(existing_facility)

    plant_data = {
        "code": "EXSTN",  # 중복 코드
        "name": "새로운처리장_코드중복",
    }
    response = await admin_client.post("/api/v1/loc/facilities/", json=plant_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Facility with this code already exists"
    print("test_create_facility_duplicate_code_admin passed.")


@pytest.mark.asyncio
async def test_create_facility_unauthorized(
    authorized_client: AsyncClient,  # 일반 사용자로 인증된 클라이언트
    client: AsyncClient,  # 비인증 클라이언트
):
    """
    일반 사용자 및 비인증 사용자가 하수처리장 생성 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_facility_unauthorized ---")
    plant_data = {
        "code": "DENY",
        "name": "거부된하수처리장",
    }

    # 일반 사용자 시도
    response_user = await authorized_client.post("/api/v1/loc/facilities/", json=plant_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.post("/api/v1/loc/facilities/", json=plant_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_create_facility_unauthorized passed.")


@pytest.mark.asyncio
async def test_read_facilitiess_success(client: AsyncClient, db_session: Session):
    """
    모든 사용자가 하수처리장 목록을 성공적으로 조회하는지 테스트합니다.
    (권한이 필요 없는 GET 엔드포인트로 가정)
    """
    print("\n--- Running test_read_facilitiess_success ---")
    plant1 = loc_models.Facility(code="PL1", name="플랜트1")
    plant2 = loc_models.Facility(code="PL2", name="플랜트2")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    response = await client.get("/api/v1/loc/facilities/")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    assert len(response.json()) >= 2  # 최소 2개 이상 (다른 테스트에서 생성된 것 포함 가능)
    assert any(p["name"] == "플랜트1" for p in response.json())
    assert any(p["name"] == "플랜트2" for p in response.json())
    print("test_read_facilitiess_success passed.")


@pytest.mark.asyncio
async def test_read_facility_success(client: AsyncClient, db_session: Session):
    """
    특정 ID의 하수처리장 정보를 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_facility_success ---")
    facility = loc_models.Facility(code="VIEW1", name="조회대상플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    response = await client.get(f"/api/v1/loc/facilities/{facility.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    retrieved_facility = response.json()
    assert retrieved_facility["id"] == facility.id
    assert retrieved_facility["name"] == facility.name
    print("test_read_facility_success passed.")


@pytest.mark.asyncio
async def test_read_facility_not_found(client: AsyncClient):
    """
    존재하지 않는 ID의 하수처리장 조회 시 404 Not Found를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_read_facility_not_found ---")
    non_existent_id = 99999
    response = await client.get(f"/api/v1/loc/facilities/{non_existent_id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Facility not found"
    print("test_read_facility_not_found passed.")


@pytest.mark.asyncio
async def test_update_facility_success_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 하수처리장 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_facility_success_admin ---")
    facility = loc_models.Facility(code="UPDA", name="업데이트대상플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    update_data = {"name": "업데이트된플랜트명", "address": "수정된 주소"}
    response = await admin_client.put(f"/api/v1/loc/facilities/{facility.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_facility = response.json()
    assert updated_facility["id"] == facility.id
    assert updated_facility["name"] == update_data["name"]
    assert updated_facility["address"] == update_data["address"]
    print("test_update_facility_success_admin passed.")


@pytest.mark.asyncio
async def test_update_facility_duplicate_name_on_update_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 하수처리장 이름 업데이트 시, 다른 하수처리장과 이름이 중복되는 경우 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_facility_duplicate_name_on_update_admin ---")
    plant_to_update = loc_models.Facility(code="UPDN1", name="업데이트될플랜트")
    existing_facility = loc_models.Facility(code="EXST2", name="이미있는플랜트")
    db_session.add(plant_to_update)
    db_session.add(existing_facility)
    await db_session.commit()
    await db_session.refresh(plant_to_update)
    await db_session.refresh(existing_facility)

    update_data = {"name": existing_facility.name}  # 기존 플랜트의 이름으로 변경 시도
    response = await admin_client.put(f"/api/v1/loc/facilities/{plant_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Another facility with this name already exists."
    print("test_update_facility_duplicate_name_on_update_admin passed.")


@pytest.mark.asyncio
async def test_update_facility_duplicate_code_on_update_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 하수처리장 코드 업데이트 시, 다른 하수처리장과 코드가 중복되는 경우 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_facility_duplicate_code_on_update_admin ---")
    plant_to_update = loc_models.Facility(code="UPDC1", name="업데이트될코드플랜트")
    existing_facility = loc_models.Facility(code="EXST2", name="이미있는코드플랜트")
    db_session.add(plant_to_update)
    db_session.add(existing_facility)
    await db_session.commit()
    await db_session.refresh(plant_to_update)
    await db_session.refresh(existing_facility)

    update_data = {"code": existing_facility.code}  # 기존 플랜트의 코드로 변경 시도
    response = await admin_client.put(f"/api/v1/loc/facilities/{plant_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Another facility with this code already exists."
    print("test_update_facility_duplicate_code_on_update_admin passed.")


@pytest.mark.asyncio
async def test_update_facility_unauthorized(
    authorized_client: AsyncClient, client: AsyncClient, db_session: Session
):
    """
    일반 사용자 및 비인증 사용자가 하수처리장 업데이트 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_update_facility_unauthorized ---")
    facility = loc_models.Facility(code="NOUP", name="권한없음업데이트플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    update_data = {"name": "권한없이업데이트시도"}

    # 일반 사용자 시도
    response_user = await authorized_client.put(f"/api/v1/loc/facilities/{facility.id}", json=update_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.put(f"/api/v1/loc/facilities/{facility.id}", json=update_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_update_facility_unauthorized passed.")


@pytest.mark.asyncio
async def test_delete_facility_success_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 하수처리장을 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_facility_success_admin ---")
    facility = loc_models.Facility(code="DEL", name="삭제대상플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    response = await admin_client.delete(f"/api/v1/loc/facilities/{facility.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_facility = await loc_crud.facility.get(db_session, id=facility.id)
    assert deleted_facility is None
    print("test_delete_facility_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_facility_unauthorized(
    authorized_client: AsyncClient, client: AsyncClient, db_session: Session
):
    """
    일반 사용자 및 비인증 사용자가 하수처리장 삭제 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_delete_facility_unauthorized ---")
    facility = loc_models.Facility(code="NODEL", name="권한없음삭제플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    # 일반 사용자 시도
    response_user = await authorized_client.delete(f"/api/v1/loc/facilities/{facility.id}")
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.delete(f"/api/v1/loc/facilities/{facility.id}")
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_delete_facility_unauthorized passed.")


@pytest.mark.asyncio
async def test_delete_facility_restrict_by_location(admin_client: AsyncClient, db_session: Session):
    """
    하수처리장에 연결된 장소가 있을 때 하수처리장 삭제 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    (ON DELETE RESTRICT 제약 조건 검증)
    """
    print("\n--- Running test_delete_facility_restrict_by_location ---")
    facility = loc_models.Facility(code="RSTR1", name="제한삭제플랜트")
    # plant와 location을 같은 세션에서 추가하고 한번에 커밋하여 관계를 강력하게 보장
    db_session.add(facility)
    await db_session.flush()  # plant의 ID를 확보하기 위해 flush

    # 이 하수처리장을 참조하는 장소 생성
    # location_type_id가 nullable이므로 None으로 두거나, 테스트용 location_type을 생성하여 할당
    # 여기서는 간단히 name만 설정합니다.
    location = loc_models.Location(facility_id=facility.id, name="제한된위치")
    db_session.add(location)

    await db_session.commit()  # plant와 location을 한 번에 커밋
    await db_session.refresh(facility)
    await db_session.refresh(location)

    # 이 시점에서 plant와 location이 DB에 제대로 저장되었는지 다시 확인
    retrieved_facility = await loc_crud.facility.get(db_session, id=facility.id)
    retrieved_location = await loc_crud.location.get(db_session, id=location.id)
    print(f"DEBUG: Retrieved Plant: {retrieved_facility.id if retrieved_facility else 'None'}, Code: {retrieved_facility.code if retrieved_facility else 'N/A'}")
    print(f"DEBUG: Retrieved Location: {retrieved_location.id if retrieved_location else 'None'}, Plant ID: {retrieved_location.facility_id if retrieved_location else 'N/A'}")

    # 이 시점에서 db_session을 강제로 닫고 다시 열어 세션 독립성을 확보하는 시도 (옵션)
    # await db_session.close()
    # db_session = await get_db_session_dependency() # 새 세션 가져오기

    response = await admin_client.delete(f"/api/v1/loc/facilities/{facility.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete this facility as it has associated locations."

    # 데이터베이스에서 실제로 삭제되지 않았는지 확인
    assert await loc_crud.facility.get(db_session, id=facility.id) is not None
    print("test_delete_facility_restrict_by_location passed.")


@pytest.mark.asyncio
async def test_delete_facility_restrict_by_equipment(admin_client: AsyncClient, db_session: Session, test_equipment_category: Any):
    """
    하수처리장에 연결된 설비가 있을 때 하수처리장 삭제 시도 시 삭제가 제한되는지 테스트합니다.
    (ON DELETE RESTRICT 제약 조건 검증)

    """
    print("\n--- Running test_delete_facility_restrict_by_equipment ---")
    facility = loc_models.Facility(code="RESTQ", name="설비제한삭제플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    # 이 플랜트를 참조하는 설비 생성
    equipment = FmsEquipment(
        facility_id=facility.id,
        equipment_category_id=test_equipment_category.id,
        name="제한된설비_플랜트",
        code="EQP_P",
        model_name="모델X",
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    response = await admin_client.delete(f"/api/v1/loc/facilities/{facility.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete this facility as it has associated equipment."
    assert await loc_crud.facility.get(db_session, id=facility.id) is not None
    print("test_delete_facility_restrict_by_equipment passed.")


# --- 장소 유형 관리 엔드포인트 테스트 (보완) ---


@pytest.mark.asyncio
async def test_create_location_type_success_admin(
    admin_client: AsyncClient,
):
    """
    관리자 권한으로 새로운 장소 유형을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_type_success_admin ---")
    loc_type_data = {"name": "테스트유형1", "description": "테스트용 장소 유형입니다."}
    response = await admin_client.post("/api/v1/loc/location_types/", json=loc_type_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_type = response.json()
    assert created_type["name"] == loc_type_data["name"]
    assert "id" in created_type
    print("test_create_location_type_success_admin passed.")


@pytest.mark.asyncio
async def test_create_location_type_duplicate_name_admin(admin_client: AsyncClient, db_session: Session):
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
async def test_create_location_type_unauthorized(authorized_client: AsyncClient, client: AsyncClient):
    """
    일반 사용자 및 비인증 사용자가 장소 유형 생성 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_type_unauthorized ---")
    loc_type_data = {
        "name": "권한없음유형",
    }

    # 일반 사용자 시도
    response_user = await authorized_client.post("/api/v1/loc/location_types/", json=loc_type_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.post("/api/v1/loc/location_types/", json=loc_type_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_create_location_type_unauthorized passed.")


@pytest.mark.asyncio
async def test_read_location_types_success(client: AsyncClient, db_session: Session):
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


@pytest.mark.asyncio
async def test_read_location_type_success(client: AsyncClient, db_session: Session):
    """
    특정 ID의 장소 유형 정보를 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_location_type_success ---")
    loc_type = loc_models.LocationType(name="조회대상유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)

    response = await client.get(f"/api/v1/loc/location_types/{loc_type.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    retrieved_type = response.json()
    assert retrieved_type["id"] == loc_type.id
    assert retrieved_type["name"] == loc_type.name
    print("test_read_location_type_success passed.")


@pytest.mark.asyncio
async def test_read_location_type_not_found(client: AsyncClient):
    """
    존재하지 않는 ID의 장소 유형 조회 시 404 Not Found를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_read_location_type_not_found ---")
    non_existent_id = 99999
    response = await client.get(f"/api/v1/loc/location_types/{non_existent_id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Location type not found"
    print("test_read_location_type_not_found passed.")


@pytest.mark.asyncio
async def test_update_location_type_success_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 장소 유형 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_location_type_success_admin ---")
    loc_type = loc_models.LocationType(name="업데이트대상유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)

    update_data = {"name": "업데이트된유형명", "description": "수정된 설명"}
    response = await admin_client.put(f"/api/v1/loc/location_types/{loc_type.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_type = response.json()
    assert updated_type["id"] == loc_type.id
    assert updated_type["name"] == update_data["name"]
    assert updated_type["description"] == update_data["description"]
    print("test_update_location_type_success_admin passed.")


@pytest.mark.asyncio
async def test_update_location_type_duplicate_name_on_update_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 장소 유형 이름 업데이트 시, 다른 장소 유형과 이름이 중복되는 경우 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_location_type_duplicate_name_on_update_admin ---")
    type_to_update = loc_models.LocationType(name="업데이트될유형")
    existing_type = loc_models.LocationType(name="이미있는유형")
    db_session.add(type_to_update)
    db_session.add(existing_type)
    await db_session.commit()
    await db_session.refresh(type_to_update)
    await db_session.refresh(existing_type)

    update_data = {"name": existing_type.name}  # 기존 유형의 이름으로 변경 시도
    response = await admin_client.put(f"/api/v1/loc/location_types/{type_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Another location type with this name already exists."
    print("test_update_location_type_duplicate_name_on_update_admin passed.")


@pytest.mark.asyncio
async def test_update_location_type_unauthorized(
    authorized_client: AsyncClient, client: AsyncClient, db_session: Session
):
    """
    일반 사용자 및 비인증 사용자가 장소 유형 업데이트 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_update_location_type_unauthorized ---")
    loc_type = loc_models.LocationType(name="권한없음업데이트유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)

    update_data = {"name": "권한없이업데이트시도"}

    # 일반 사용자 시도
    response_user = await authorized_client.put(f"/api/v1/loc/location_types/{loc_type.id}", json=update_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.put(f"/api/v1/loc/location_types/{loc_type.id}", json=update_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_update_location_type_unauthorized passed.")


@pytest.mark.asyncio
async def test_delete_location_type_success_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 장소 유형을 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_location_type_success_admin ---")
    loc_type = loc_models.LocationType(name="삭제대상유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)

    response = await admin_client.delete(f"/api/v1/loc/location_types/{loc_type.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_type = await loc_crud.location_type.get(db_session, id=loc_type.id)
    assert deleted_type is None
    print("test_delete_location_type_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_location_type_unauthorized(
    authorized_client: AsyncClient, client: AsyncClient, db_session: Session
):
    """
    일반 사용자 및 비인증 사용자가 장소 유형 삭제 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_delete_location_type_unauthorized ---")
    loc_type = loc_models.LocationType(name="권한없음삭제유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)

    # 일반 사용자 시도
    response_user = await authorized_client.delete(f"/api/v1/loc/location_types/{loc_type.id}")
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.delete(f"/api/v1/loc/location_types/{loc_type.id}")
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_delete_location_type_unauthorized passed.")


@pytest.mark.asyncio
async def test_delete_location_type_restrict_by_location(
    admin_client: AsyncClient, db_session: Session, test_facility: loc_models.Facility
):
    """
    장소 유형에 연결된 장소가 있을 때 장소 유형 삭제 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    (ON DELETE RESTRICT 제약 조건 검증)
    """
    print("\n--- Running test_delete_location_type_restrict_by_location ---")
    loc_type = loc_models.LocationType(name="제한삭제유형")
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(loc_type)

    location = loc_models.Location(
        facility_id=test_facility.id,
        location_type_id=loc_type.id,
        name="제한된장소"
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)

    response = await admin_client.delete(f"/api/v1/loc/location_types/{loc_type.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete this location type as it is currently in use by locations."

    # 데이터베이스에서 실제로 삭제되지 않았는지 확인
    # 이제 db_session은 라우터가 사용하는 세션과 동일하므로, 직접 조회 가능.
    assert await loc_crud.location_type.get(db_session, id=loc_type.id) is not None

    print("test_delete_location_type_restrict_by_location passed.")


# --- 실제 장소 관리 엔드포인트 테스트 (보완) ---
@pytest.mark.asyncio
async def test_create_location_success_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 새로운 장소를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_success_admin ---")
    facility = loc_models.Facility(code="PLANT", name="장소테스트플랜트")
    loc_type = loc_models.LocationType(name="창고")
    db_session.add(facility)
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(facility)
    await db_session.refresh(loc_type)

    location_data = {
        "facility_id": facility.id,
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
    assert created_location["facility_id"] == facility.id
    assert "id" in created_location
    print("test_create_location_success_admin passed.")


@pytest.mark.asyncio
async def test_create_location_duplicate_name_in_plant_admin(admin_client: AsyncClient, db_session: Session):
    """
    동일 처리장 내에서 중복 이름의 장소 (및 상위 위치가 동일한) 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_create_location_duplicate_name_in_plant_admin ---")
    facility = loc_models.Facility(code="DUPPL", name="중복이름테스트플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    # 첫 번째 장소 생성
    loc_data1 = {
        "facility_id": facility.id,
        "name": "중복 장소",
        "parent_location_id": None,  # 명시적으로 None 지정
        "description": "첫 번째 중복 장소",
    }
    response1 = await admin_client.post("/api/v1/loc/locations/", json=loc_data1)
    assert response1.status_code == 201

    # 두 번째 장소 생성 (중복 이름, 동일 facility_id, 동일 parent_location_id)
    loc_data2 = {
        "facility_id": facility.id,
        "name": "중복 장소",
        "parent_location_id": None,  # 명시적으로 None 지정
        "description": "두 번째 중복 장소",
    }
    response2 = await admin_client.post("/api/v1/loc/locations/", json=loc_data2)
    print(f"Response status code: {response2.status_code}")
    print(f"Response JSON: {response2.json()}")

    assert response2.status_code == 400
    assert response2.json()["detail"] == "Location with this name and parent already exists in this facility."
    print("test_create_location_duplicate_name_in_plant_admin passed.")


@pytest.mark.asyncio
async def test_create_location_with_nonexistent_plant_admin(
    admin_client: AsyncClient,
):
    """
    관리자 권한으로 존재하지 않는 처리장 ID로 장소 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_create_location_with_nonexistent_plant_admin ---")
    location_data = {
        "facility_id": 9999,  # 존재하지 않는 ID
        "name": "가짜 장소",
    }
    response = await admin_client.post("/api/v1/loc/locations/", json=location_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Facility not found for the given ID"
    print("test_create_location_with_nonexistent_plant_admin passed.")


@pytest.mark.asyncio
async def test_create_location_unauthorized(
    authorized_client: AsyncClient, client: AsyncClient, db_session: Session, test_facility: loc_models.Facility
):
    """
    일반 사용자 및 비인증 사용자가 장소 생성 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_location_unauthorized ---")
    location_data = {
        "facility_id": test_facility.id,
        "name": "권한없음장소",
    }

    # 일반 사용자 시도
    response_user = await authorized_client.post("/api/v1/loc/locations/", json=location_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.post("/api/v1/loc/locations/", json=location_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_create_location_unauthorized passed.")


@pytest.mark.asyncio
async def test_create_location_with_nonexistent_location_type_admin(
    admin_client: AsyncClient, db_session: Session, test_facility: loc_models.Facility
):
    """
    관리자 권한으로 존재하지 않는 장소 유형 ID로 장소 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_create_location_with_nonexistent_location_type_admin ---")
    location_data = {
        "facility_id": test_facility.id,
        "location_type_id": 99999,  # 존재하지 않는 ID
        "name": "가짜 유형 장소",
    }
    response = await admin_client.post("/api/v1/loc/locations/", json=location_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Location type not found for the given ID"
    print("test_create_location_with_nonexistent_location_type_admin passed.")


@pytest.mark.asyncio
async def test_create_location_with_nonexistent_parent_location_admin(
    admin_client: AsyncClient, db_session: Session, test_facility: loc_models.Facility
):
    """
    관리자 권한으로 존재하지 않는 상위 장소 ID로 장소 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_create_location_with_nonexistent_parent_location_admin ---")
    location_data = {
        "facility_id": test_facility.id,
        "parent_location_id": 88888,  # 존재하지 않는 ID
        "name": "가짜 부모 장소",
    }
    response = await admin_client.post("/api/v1/loc/locations/", json=location_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Parent location not found for the given ID"
    print("test_create_location_with_nonexistent_parent_location_admin passed.")


@pytest.mark.asyncio
async def test_create_location_with_parent_from_different_plant_admin(
    admin_client: AsyncClient, db_session: Session
):
    """
    관리자 권한으로 다른 처리장의 상위 장소 ID로 장소 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_create_location_with_parent_from_different_plant_admin ---")
    plant1 = loc_models.Facility(code="PLT_A", name="플랜트A")
    plant2 = loc_models.Facility(code="PLT_B", name="플랜트B")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    parent_location_in_plant_a = loc_models.Location(facility_id=plant1.id, name="부모장소_A")
    db_session.add(parent_location_in_plant_a)
    await db_session.commit()
    await db_session.refresh(parent_location_in_plant_a)

    location_data = {
        "facility_id": plant2.id,  # 생성할 장소는 플랜트 B 소속
        "parent_location_id": parent_location_in_plant_a.id,  # 부모 장소는 플랜트 A 소속
        "name": "다른 플랜트 부모 장소",
    }
    response = await admin_client.post("/api/v1/loc/locations/", json=location_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Parent location must belong to the same facility."
    print("test_create_location_with_parent_from_different_plant_admin passed.")


@pytest.mark.asyncio
async def test_read_locations_by_facility_id_success(client: AsyncClient, db_session: Session):
    """
    특정 처리장 ID로 장소 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_locations_by_facility_id_success ---")
    plant1 = loc_models.Facility(code="RP1", name="조회플랜트1")
    plant2 = loc_models.Facility(code="RP2", name="조회플랜트2")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    loc1_p1 = loc_models.Location(facility_id=plant1.id, name="장소1_플1")
    loc2_p1 = loc_models.Location(facility_id=plant1.id, name="장소2_플1")
    loc1_p2 = loc_models.Location(facility_id=plant2.id, name="장소1_플2")
    db_session.add(loc1_p1)
    db_session.add(loc2_p1)
    db_session.add(loc1_p2)
    await db_session.commit()
    await db_session.refresh(loc1_p1)
    await db_session.refresh(loc2_p1)
    await db_session.refresh(loc1_p2)

    response = await client.get(f"/api/v1/loc/locations/?facility_id={plant1.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    locations = response.json()
    assert len(locations) == 2
    assert all(loc["facility_id"] == plant1.id for loc in locations)
    assert any(loc["name"] == "장소1_플1" for loc in locations)
    assert any(loc["name"] == "장소2_플1" for loc in locations)
    print("test_read_locations_by_facility_id_success passed.")


@pytest.mark.asyncio
async def test_read_locations_no_facility_id_success(client: AsyncClient, db_session: Session):
    """
    facility_id 필터 없이 모든 장소 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_locations_no_facility_id_success ---")
    plant1 = loc_models.Facility(code="PLAL1", name="모든장소조회플랜트1")
    plant2 = loc_models.Facility(code="PLAL2", name="모든장소조회플랜트2")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    loc1 = loc_models.Location(facility_id=plant1.id, name="모든장소1")
    loc2 = loc_models.Location(facility_id=plant2.id, name="모든장소2")
    db_session.add(loc1)
    db_session.add(loc2)
    await db_session.commit()
    await db_session.refresh(loc1)
    await db_session.refresh(loc2)

    response = await client.get("/api/v1/loc/locations/")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    locations = response.json()
    assert len(locations) >= 2  # 다른 테스트가 생성한 장소 포함 가능성 있음
    assert any(loc["name"] == "모든장소1" for loc in locations)
    assert any(loc["name"] == "모든장소2" for loc in locations)
    print("test_read_locations_no_facility_id_success passed.")


@pytest.mark.asyncio
async def test_read_location_success(client: AsyncClient, db_session: Session):
    """
    특정 ID의 장소 정보를 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_location_success ---")
    facility = loc_models.Facility(code="RLOC", name="장소조회플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    location = loc_models.Location(facility_id=facility.id, name="조회대상장소")
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)

    response = await client.get(f"/api/v1/loc/locations/{location.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    retrieved_location = response.json()
    assert retrieved_location["id"] == location.id
    assert retrieved_location["name"] == location.name
    print("test_read_location_success passed.")


@pytest.mark.asyncio
async def test_read_location_not_found(client: AsyncClient):
    """
    존재하지 않는 ID의 장소 조회 시 404 Not Found를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_read_location_not_found ---")
    non_existent_id = 99999
    response = await client.get(f"/api/v1/loc/locations/{non_existent_id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Location not found"
    print("test_read_location_not_found passed.")


@pytest.mark.asyncio
async def test_update_location_success_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 장소 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_location_success_admin ---")
    facility = loc_models.Facility(code="UPDL", name="업데이트대상장소플랜트")
    loc_type = loc_models.LocationType(name="업데이트유형")
    db_session.add(facility)
    db_session.add(loc_type)
    await db_session.commit()
    await db_session.refresh(facility)
    await db_session.refresh(loc_type)

    location_to_update = loc_models.Location(facility_id=facility.id, name="업데이트대상장소")
    db_session.add(location_to_update)
    await db_session.commit()
    await db_session.refresh(location_to_update)

    update_data = {"name": "업데이트된 장소명", "description": "수정된 설명", "location_type_id": loc_type.id}
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
async def test_update_location_duplicate_name_in_plant_on_update_admin(admin_client: AsyncClient, db_session: Session):
    """
    장소 이름 업데이트 시, 동일 처리장 내에서 이름 및 부모 장소 ID 조합이 중복되는 경우 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_location_duplicate_name_in_plant_on_update_admin ---")
    facility = loc_models.Facility(code="UPDUP", name="업데이트중복테스트플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    existing_location = loc_models.Location(facility_id=facility.id, name="중복될장소", parent_location_id=None)
    location_to_update = loc_models.Location(facility_id=facility.id, name="업데이트될장소", parent_location_id=None)
    db_session.add(existing_location)
    db_session.add(location_to_update)
    await db_session.commit()
    await db_session.refresh(existing_location)
    await db_session.refresh(location_to_update)

    update_data = {"name": existing_location.name}  # 기존 장소의 이름으로 변경 시도
    response = await admin_client.put(f"/api/v1/loc/locations/{location_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Another location with this name and parent already exists in the target facility."
    print("test_update_location_duplicate_name_in_plant_on_update_admin passed.")


@pytest.mark.asyncio
async def test_update_location_change_plant_to_nonexistent_admin(admin_client: AsyncClient, db_session: Session):
    """
    장소의 facility_id를 존재하지 않는 ID로 변경 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_location_change_plant_to_nonexistent_admin ---")
    facility = loc_models.Facility(code="UPPLN", name="플랜트변경테스트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    location_to_update = loc_models.Location(facility_id=facility.id, name="변경될장소")
    db_session.add(location_to_update)
    await db_session.commit()
    await db_session.refresh(location_to_update)

    update_data = {"facility_id": 99999}  # 존재하지 않는 facility_id
    response = await admin_client.put(f"/api/v1/loc/locations/{location_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "New facility not found for the given ID"
    print("test_update_location_change_plant_to_nonexistent_admin passed.")


@pytest.mark.asyncio
async def test_update_location_change_location_type_to_nonexistent_admin(admin_client: AsyncClient, db_session: Session):
    """
    장소의 location_type_id를 존재하지 않는 ID로 변경 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_location_change_location_type_to_nonexistent_admin ---")
    facility = loc_models.Facility(code="UPTYP", name="타입변경테스트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    location_to_update = loc_models.Location(facility_id=facility.id, name="변경될타입장소")
    db_session.add(location_to_update)
    await db_session.commit()
    await db_session.refresh(location_to_update)

    update_data = {"location_type_id": 88888}  # 존재하지 않는 location_type_id
    response = await admin_client.put(f"/api/v1/loc/locations/{location_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "New location type not found for the given ID"
    print("test_update_location_change_location_type_to_nonexistent_admin passed.")


@pytest.mark.asyncio
async def test_update_location_change_parent_to_nonexistent_admin(admin_client: AsyncClient, db_session: Session):
    """
    장소의 parent_location_id를 존재하지 않는 ID로 변경 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_location_change_parent_to_nonexistent_admin ---")
    facility = loc_models.Facility(code="UPPAR", name="부모변경테스트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    location_to_update = loc_models.Location(facility_id=facility.id, name="변경될부모장소")
    db_session.add(location_to_update)
    await db_session.commit()
    await db_session.refresh(location_to_update)

    update_data = {"parent_location_id": 77777}  # 존재하지 않는 parent_location_id
    response = await admin_client.put(f"/api/v1/loc/locations/{location_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "New parent location not found for the given ID"
    print("test_update_location_change_parent_to_nonexistent_admin passed.")


@pytest.mark.asyncio
async def test_update_location_change_parent_to_different_plant_admin(admin_client: AsyncClient, db_session: Session):
    """
    장소의 parent_location_id를 다른 처리장에 속한 장소로 변경 시도 시 400 Bad Request를 반환하는지 테스트합니다.

    """
    print("\n--- Running test_update_location_change_parent_to_different_plant_admin ---")
    plant1 = loc_models.Facility(code="P1", name="플랜트A_업데이트")
    plant2 = loc_models.Facility(code="P2", name="플랜트B_업데이트")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

    parent_in_plant2 = loc_models.Location(facility_id=plant2.id, name="플랜트B_부모")
    location_in_plant1_to_update = loc_models.Location(facility_id=plant1.id, name="플랜트A_자식")
    db_session.add(parent_in_plant2)
    db_session.add(location_in_plant1_to_update)
    await db_session.commit()
    await db_session.refresh(parent_in_plant2)
    await db_session.refresh(location_in_plant1_to_update)

    update_data = {"parent_location_id": parent_in_plant2.id}
    response = await admin_client.put(f"/api/v1/loc/locations/{location_in_plant1_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Parent location must belong to the same facility."
    print("test_update_location_change_parent_to_different_plant_admin passed.")


@pytest.mark.asyncio
async def test_update_location_unauthorized(
    authorized_client: AsyncClient, client: AsyncClient, db_session: Session, test_facility: loc_models.Facility
):
    """
    일반 사용자 및 비인증 사용자가 장소 업데이트 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_update_location_unauthorized ---")
    location = loc_models.Location(facility_id=test_facility.id, name="권한없음업데이트장소")
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)

    update_data = {"name": "권한없이업데이트시도"}

    # 일반 사용자 시도
    response_user = await authorized_client.put(f"/api/v1/loc/locations/{location.id}", json=update_data)
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.put(f"/api/v1/loc/locations/{location.id}", json=update_data)
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_update_location_unauthorized passed.")


@pytest.mark.asyncio
async def test_delete_location_success_admin(admin_client: AsyncClient, db_session: Session):
    """
    관리자 권한으로 장소를 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_location_success_admin ---")
    facility = loc_models.Facility(code="DELL", name="삭제대상장소플랜트")
    db_session.add(facility)
    await db_session.commit()
    await db_session.refresh(facility)

    location_to_delete = loc_models.Location(facility_id=facility.id, name="삭제대상장소")
    db_session.add(location_to_delete)
    await db_session.commit()
    await db_session.refresh(location_to_delete)

    response = await admin_client.delete(f"/api/v1/loc/locations/{location_to_delete.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_location = await loc_crud.location.get(db_session, id=location_to_delete.id)
    assert deleted_location is None
    print("test_delete_location_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_location_unauthorized(
    authorized_client: AsyncClient, client: AsyncClient, db_session: Session, test_facility: loc_models.Facility
):
    """
    일반 사용자 및 비인증 사용자가 장소 삭제 시도 시 403 Forbidden 또는 401 Unauthorized를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_delete_location_unauthorized ---")
    location = loc_models.Location(facility_id=test_facility.id, name="권한없음삭제장소")
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)

    # 일반 사용자 시도
    response_user = await authorized_client.delete(f"/api/v1/loc/locations/{location.id}")
    print(f"User response status code: {response_user.status_code}, JSON: {response_user.json()}")
    assert response_user.status_code == 403
    assert response_user.json()["detail"] == "Not enough permissions. Admin role required."

    # 비인증 사용자 시도
    response_no_auth = await client.delete(f"/api/v1/loc/locations/{location.id}")
    print(f"No auth response status code: {response_no_auth.status_code}, JSON: {response_no_auth.json()}")
    assert response_no_auth.status_code == 401
    assert response_no_auth.json()["detail"] == "Not authenticated"
    print("test_delete_location_unauthorized passed.")


@pytest.mark.asyncio
async def test_delete_location_cascade_child_locations_admin(
    admin_client: AsyncClient, db_session: Session, test_facility: loc_models.Facility
):
    """
    부모 장소 삭제 시 하위 장소도 연쇄적으로 삭제되는지 테스트합니다.
    (ON DELETE CASCADE 제약 조건 검증)
    """
    print("\n--- Running test_delete_location_cascade_child_locations_admin ---")
    parent_location = loc_models.Location(facility_id=test_facility.id, name="부모장소")
    db_session.add(parent_location)
    await db_session.commit()
    await db_session.refresh(parent_location)

    child_location1 = loc_models.Location(
        facility_id=test_facility.id, parent_location_id=parent_location.id, name="자식장소1"
    )
    child_location2 = loc_models.Location(
        facility_id=test_facility.id, parent_location_id=parent_location.id, name="자식장소2"
    )
    db_session.add(child_location1)
    db_session.add(child_location2)
    await db_session.commit()
    await db_session.refresh(child_location1)
    await db_session.refresh(child_location2)

    response = await admin_client.delete(f"/api/v1/loc/locations/{parent_location.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 부모 장소가 삭제되었는지 확인
    assert await loc_crud.location.get(db_session, id=parent_location.id) is None
    # 자식 장소도 함께 삭제되었는지 확인
    assert await loc_crud.location.get(db_session, id=child_location1.id) is None
    assert await loc_crud.location.get(db_session, id=child_location2.id) is None
    print("test_delete_location_cascade_child_locations_admin passed.")


@pytest.mark.asyncio
async def test_delete_location_restrict_by_equipment(
    admin_client: AsyncClient,
    db_session: Session,
    test_facility: loc_models.Facility,
    test_equipment_category: Any,  # EquipmentCategory 픽스처 필요
):
    """
    장소에 연결된 설비가 있을 때 장소 삭제 시도 시 삭제가 제한되는지 테스트합니다.
    (ON DELETE RESTRICT 제약 조건 검증)

    """
    print("\n--- Running test_delete_location_restrict_by_equipment ---")
    location = loc_models.Location(facility_id=test_facility.id, name="설비제한장소")
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)

    # 이 장소를 참조하는 설비 생성
    equipment = FmsEquipment(
        facility_id=test_facility.id,
        equipment_category_id=test_equipment_category.id,  # 실제 유효한 ID 필요
        current_location_id=location.id,
        name="제한된설비",
        code="EQP_L",
        model_name="모델Y",
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    response = await admin_client.delete(f"/api/v1/loc/locations/{location.id}")
    print(f"Response status code: {response.status_code}")

    # 그리고 assert는 별도로 처리합니다.
    assert response.status_code == 400  # 또는 409 Conflict 등 데이터베이스 제약 조건 위반에 따른 적절한 코드
    assert response.json()["detail"] == "Cannot delete location due to existing related data."
    # 데이터베이스에서 실제로 삭제되지 않았는지 확인
    assert await loc_crud.location.get(db_session, id=location.id) is not None
    print("test_delete_location_restrict_by_equipment passed.")
