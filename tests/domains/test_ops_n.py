# tests/domains/test_ops.py

"""
'ops' 도메인 (운영 데이터 관리) 관련 API 엔드포인트에 대한 통합 테스트를 정의하는 모듈입니다.

- 처리 계열 관리 엔드포인트 테스트:
    - `POST /api/v1/ops/lines/` (생성)
    - `GET /api/v1/ops/lines/` (목록 조회)
    - `GET /api/v1/ops/lines/{id}` (단일 조회)
    - `PUT /api/v1/ops/lines/{id}` (업데이트)
    - `DELETE /api/v1/ops/lines/{id}` (삭제)
- 일일 처리장 운영 현황 관리 엔드포인트 테스트:
    - `POST /api/v1/ops/daily_plant_operations/` (생성)
    - `GET /api/v1/ops/daily_plant_operations/` (목록 조회)
    - `GET /api/v1/ops/daily_plant_operations/{id}` (ID 기준 단일 조회)
    - `GET /api/v1/ops/daily_plant_operations/by_global_id/{global_id}` (Global ID 기준 단일 조회)
    - `PUT /api/v1/ops/daily_plant_operations/{id}` (업데이트)
    - `DELETE /api/v1/ops/daily_plant_operations/{id}` (삭제)
- 일일 계열별 운영 현황 관리 엔드포인트 테스트:
    - `POST /api/v1/ops/daily_line_operations/` (생성)
    - `GET /api/v1/ops/daily_line_operations/` (목록 조회)
    - `GET /api/v1/ops/daily_line_operations/{id}` (ID 기준 단일 조회)
    - `GET /api/v1/ops/daily_line_operations/by_global_id/{global_id}` (Global ID 기준 단일 조회)
    - `PUT /api/v1/ops/daily_line_operations/{id}` (업데이트)
    - `DELETE /api/v1/ops/daily_line_operations/{id}` (삭제)
- 사용자 정의 운영 데이터 보기 엔드포인트 테스트:
    - `POST /api/v1/ops/views/` (생성)
    - `GET /api/v1/ops/views/` (목록 조회)
    - `GET /api/v1/ops/views/{id}` (단일 조회)
    - `PUT /api/v1/ops/views/{id}` (업데이트)
    - `DELETE /api/v1/ops/views/{id}` (삭제)

다양한 사용자 역할(관리자, 일반 사용자, 비인증 사용자)에 따른
인증 및 권한 부여 로직을 검증합니다.
"""
import uuid  # UUID 타입 비교용
import pytest
from datetime import date, timedelta, datetime
from httpx import AsyncClient

from sqlmodel import Session
# from fastapi.testclient import TestClient

from app.domains.ops import models as ops_models
from app.domains.ops import schemas as ops_schemas
from app.domains.ops.crud import line as line_crud  # CRUD 직접 사용 (테스트 셋업용)
from app.domains.ops.crud import daily_plant_operation as daily_plant_operation_crud
from app.domains.ops.crud import daily_line_operation as daily_line_operation_crud
from app.domains.ops.crud import ops_view as ops_view_crud
from app.domains.loc import models as loc_models
from app.domains.loc import crud as loc_crud   # FK 확인 및 생성용
from app.domains.usr.models import User as UsrUser  # 사용자 모델 (권한 검증용)

# conftest.py에서 정의된 픽스처들을 Pytest가 자동으로 감지하여 사용할 수 있습니다.
# client, db_session, test_user, test_admin_user, test_superuser,
# authorized_client, admin_client, superuser_client


# --- 처리 계열 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_line_success_admin(
    admin_client: AsyncClient,  # 관리자로 인증된 클라이언트
    db_session: Session  # 처리장 생성을 위해
):
    """
    관리자 권한으로 새로운 처리 계열을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_line_success_admin ---")
    plant = loc_models.Facility(code="P01", name="테스트 처리장 01")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    line_data = {
        "code": "LINE1",
        "name": "계열 1",
        "capacity": 1000,
        "plant_id": plant.id
    }
    response = await admin_client.post("/api/v1/ops/lines", json=line_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_line = response.json()
    assert created_line["name"] == line_data["name"]
    assert created_line["code"] == line_data["code"]
    assert created_line["plant_id"] == plant.id
    assert "id" in created_line
    print("test_create_line_success_admin passed.")


@pytest.mark.asyncio
async def test_create_line_duplicate_code_admin(
    admin_client: AsyncClient,
    db_session: Session
):
    """
    관리자 권한으로 이미 존재하는 코드의 처리 계열을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_line_duplicate_code_admin ---")
    plant = loc_models.Facility(code="P02", name="테스트 처리장 02")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    existing_line = ops_models.Line(code="DUPCODE", name="중복 계열", plant_id=plant.id)
    db_session.add(existing_line)
    await db_session.commit()
    await db_session.refresh(existing_line)

    line_data = {
        "code": "DUPCODE",  # 중복 코드
        "name": "새로운 계열",
        "plant_id": plant.id
    }
    response = await admin_client.post("/api/v1/ops/lines", json=line_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Line with this code already exists."
    print("test_create_line_duplicate_code_admin passed.")


@pytest.mark.asyncio
async def test_read_lines_success(client: AsyncClient, db_session: Session):
    """
    모든 사용자가 처리 계열 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_lines_success ---")
    plant = loc_models.Facility(code="P03", name="테스트 처리장 03")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    line1 = ops_models.Line(code="L1A", name="계열1", plant_id=plant.id)
    line2 = ops_models.Line(code="L1B", name="계열2", plant_id=plant.id)
    db_session.add(line1)
    db_session.add(line2)
    await db_session.commit()
    await db_session.refresh(line1)
    await db_session.refresh(line2)

    response = await client.get(f"/api/v1/ops/lines?plant_id={plant.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    lines_list = response.json()
    assert len(lines_list) >= 2  # 다른 테스트에서 생성된 라인 포함 가능
    assert any(line1["name"] == "계열1" for line1 in lines_list)
    assert any(line2["name"] == "계열2" for line2 in lines_list)
    print("test_read_lines_success passed.")


@pytest.mark.asyncio
async def test_update_line_success_admin(
    admin_client: AsyncClient,
    db_session: Session
):
    """
    관리자 권한으로 처리 계열 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_line_success_admin ---")
    plant = loc_models.Facility(code="UPDA", name="업데이트 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    line = ops_models.Line(code="LINE_UP", name="업데이트 대상 계열", plant_id=plant.id)
    db_session.add(line)
    await db_session.commit()
    await db_session.refresh(line)

    update_data = {"name": "업데이트된 계열명", "capacity": 1200}
    response = await admin_client.put(f"/api/v1/ops/lines/{line.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_line = response.json()
    assert updated_line["id"] == line.id
    assert updated_line["name"] == update_data["name"]
    assert updated_line["capacity"] == update_data["capacity"]
    print("test_update_line_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_line_success_admin(
    admin_client: AsyncClient,
    db_session: Session
):
    """
    관리자 권한으로 처리 계열을 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_line_success_admin ---")
    plant = loc_models.Facility(code="DELP", name="삭제 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    line = ops_models.Line(code="LINE_DEL", name="삭제 대상 계열", plant_id=plant.id)
    db_session.add(line)
    await db_session.commit()
    await db_session.refresh(line)

    response = await admin_client.delete(f"/api/v1/ops/lines/{line.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_line = await line_crud.get(db_session, id=line.id)
    assert deleted_line is None
    print("test_delete_line_success_admin passed.")


# --- 일일 처리장 운영 현황 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_daily_plant_operation_success_user(
    authorized_client: AsyncClient,  # 일반 사용자 권한
    db_session: Session
):
    """
    일반 사용자 권한으로 새로운 일일 처리장 운영 현황을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_daily_plant_operation_success_user ---")
    plant = loc_models.Facility(code="PLTOP", name="운영 현황 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    op_date = date.today()
    op_data = {
        "plant_id": plant.id,
        "op_date": str(op_date),  # Pydantic date는 str으로 직렬화됨
        "influent": 10000,
        "effluent": 8000
    }
    response = await authorized_client.post("/api/v1/ops/daily_plant_operations", json=op_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_op = response.json()
    assert created_op["plant_id"] == op_data["plant_id"]
    assert created_op["op_date"] == str(op_date)
    assert "id" in created_op
    assert "global_id" in created_op
    assert isinstance(uuid.UUID(created_op["global_id"]), uuid.UUID)  # UUID 형식 검증
    print("test_create_daily_plant_operation_success_user passed.")


@pytest.mark.asyncio
async def test_create_daily_plant_operation_duplicate_date_admin(
    admin_client: AsyncClient,
    db_session: Session
):
    """
    관리자 권한으로 동일한 처리장과 날짜의 운영 현황을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_daily_plant_operation_duplicate_date_admin ---")
    plant = loc_models.Facility(code="DUPOP", name="중복 운영 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    op_date = date.today() - timedelta(days=1)  # 전날 날짜 사용
    existing_op = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=op_date, influent=5000)
    db_session.add(existing_op)
    await db_session.commit()
    await db_session.refresh(existing_op)

    op_data = {
        "plant_id": plant.id,
        "op_date": str(op_date),  # 중복 날짜
        "influent": 6000
    }
    response = await admin_client.post("/api/v1/ops/daily_plant_operations", json=op_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Daily plant operation record already exists for this plant and date."
    print("test_create_daily_plant_operation_duplicate_date_admin passed.")


@pytest.mark.asyncio
async def test_read_daily_plant_operations_by_plant_and_date_range(
    client: AsyncClient,
    db_session: Session
):
    """
    특정 처리장 ID와 날짜 범위로 일일 처리장 운영 현황 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_daily_plant_operations_by_plant_and_date_range ---")
    plant = loc_models.Facility(code="FILTP", name="필터링 테스트 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    op1 = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date(2025, 5, 28), influent=100)
    op2 = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date(2025, 5, 29), influent=200)
    op3 = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date(2025, 5, 30), influent=300)
    db_session.add(op1)
    db_session.add(op2)
    db_session.add(op3)
    await db_session.commit()
    await db_session.refresh(op1)
    await db_session.refresh(op2)
    await db_session.refresh(op3)

    response = await client.get(
        f"/api/v1/ops/daily_plant_operations?plant_id={plant.id}&start_date=2025-05-29&end_date=2025-05-30"
    )
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    ops_list = response.json()
    assert len(ops_list) == 2
    assert ops_list[0]["op_date"] == "2025-05-30"  # CRUD에서 내림차순 정렬 가정
    assert ops_list[1]["op_date"] == "2025-05-29"
    print("test_read_daily_plant_operations_by_plant_and_date_range passed.")


@pytest.mark.asyncio
async def test_read_daily_plant_operation_by_global_id_success(
    client: AsyncClient,
    db_session: Session
):
    """
    Global ID (UUID)로 일일 처리장 운영 현황을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_daily_plant_operation_by_global_id_success ---")
    plant = loc_models.Facility(code="UUIDP", name="UUID 테스트 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    op_record = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date(2025, 6, 1), influent=1000)
    db_session.add(op_record)
    await db_session.commit()
    await db_session.refresh(op_record)  # global_id가 생성됨

    response = await client.get(f"/api/v1/ops/daily_plant_operations/by_global_id/{op_record.global_id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    retrieved_op = response.json()
    assert retrieved_op["global_id"] == str(op_record.global_id)
    assert retrieved_op["plant_id"] == plant.id
    print("test_read_daily_plant_operation_by_global_id_success passed.")


@pytest.mark.asyncio
async def test_update_daily_plant_operation_success_admin(
    admin_client: AsyncClient,
    db_session: Session
):
    """
    관리자 권한으로 일일 처리장 운영 현황 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_daily_plant_operation_success_admin ---")
    plant = loc_models.Facility(code="UPDOP", name="업데이트 운영 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    op_date = date.today()
    op_record = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=op_date, influent=500, effluent=400)
    db_session.add(op_record)
    await db_session.commit()
    await db_session.refresh(op_record)

    update_data = {"influent": 700, "effluent": 600, "memo": "업데이트된 메모"}
    response = await admin_client.put(f"/api/v1/ops/daily_plant_operations/{op_record.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_op = response.json()
    assert updated_op["id"] == op_record.id
    assert updated_op["influent"] == update_data["influent"]
    assert updated_op["effluent"] == update_data["effluent"]
    assert updated_op["memo"] == update_data["memo"]
    print("test_update_daily_plant_operation_success_admin passed.")


@pytest.mark.asyncio
async def test_delete_daily_plant_operation_success_admin(
    admin_client: AsyncClient,
    db_session: Session
):
    """
    관리자 권한으로 일일 처리장 운영 현황을 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_daily_plant_operation_success_admin ---")
    plant = loc_models.Facility(code="DELOP", name="삭제 운영 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    op_record = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date.today(), influent=100)
    db_session.add(op_record)
    await db_session.commit()
    await db_session.refresh(op_record)

    response = await admin_client.delete(f"/api/v1/ops/daily_plant_operations/{op_record.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_op = await daily_plant_operation_crud.get(db_session, id=op_record.id)
    assert deleted_op is None
    print("test_delete_daily_plant_operation_success_admin passed.")


# --- 일일 계열별 운영 현황 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_daily_line_operation_success_user(
    authorized_client: AsyncClient,  # 일반 사용자 권한
    db_session: Session
):
    """
    일반 사용자 권한으로 새로운 일일 계열별 운영 현황을 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_daily_line_operation_success_user ---")
    # plant 코드 "PLN_LINE"은 8글자로 VARCHAR(5) 제약 조건에 걸리므로, 5글자 이하로 수정합니다.
    plant = loc_models.Facility(code="PLN_L", name="계열 운영 플랜트")
    line = ops_models.Line(code="LINE_OP", name="운영 계열", plant_id=plant.id)
    daily_plant_op = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date.today(), influent=5000)
    db_session.add(plant)
    db_session.add(line)
    db_session.add(daily_plant_op)
    await db_session.commit()
    await db_session.refresh(plant)
    await db_session.refresh(line)
    await db_session.refresh(daily_plant_op)

    op_date = date.today()
    op_data = {
        "daily_plant_op_id": str(daily_plant_op.global_id),
        "line_id": line.id,
        "op_date": str(op_date),
        "influent": 1200,
        "mlss": 2500
    }
    response = await authorized_client.post("/api/v1/ops/daily_line_operations", json=op_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_op = response.json()
    assert created_op["line_id"] == op_data["line_id"]
    assert created_op["op_date"] == str(op_date)
    assert "id" in created_op
    assert "global_id" in created_op
    assert isinstance(uuid.UUID(created_op["global_id"]), uuid.UUID)
    print("test_create_daily_line_operation_success_user passed.")


@pytest.mark.asyncio
async def test_create_daily_line_operation_duplicate_date_admin(
    admin_client: AsyncClient,
    db_session: Session
):
    """
    관리자 권한으로 동일한 계열과 날짜의 운영 현황을 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_daily_line_operation_duplicate_date_admin ---")
    plant = loc_models.Facility(code="DUPLP", name="중복 계열 운영 플랜트")
    line = ops_models.Line(code="DUP_L", name="중복 계열", plant_id=plant.id)
    daily_plant_op = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date.today(), influent=100)
    db_session.add(plant)
    db_session.add(line)
    db_session.add(daily_plant_op)
    await db_session.commit()
    await db_session.refresh(plant)
    await db_session.refresh(line)
    await db_session.refresh(daily_plant_op)

    op_date = date.today()
    existing_op = ops_models.DailyLineOperation(
        daily_plant_op_id=daily_plant_op.global_id,
        line_id=line.id,
        op_date=op_date,
        influent=1000
    )
    db_session.add(existing_op)
    await db_session.commit()
    await db_session.refresh(existing_op)

    op_data = {
        "daily_plant_op_id": str(daily_plant_op.global_id),
        "line_id": line.id,
        "op_date": str(op_date),  # 중복 날짜
        "influent": 1100
    }
    response = await admin_client.post("/api/v1/ops/daily_line_operations", json=op_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Daily line operation record already exists for this line and date."
    print("test_create_daily_line_operation_duplicate_date_admin passed.")


@pytest.mark.asyncio
async def test_read_daily_line_operations_by_line_id(
    client: AsyncClient,
    db_session: Session
):
    """
    특정 계열 ID로 일일 계열별 운영 현황 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_daily_line_operations_by_line_id ---")
    plant = loc_models.Facility(code="FILTL", name="필터링 계열 플랜트")
    line = ops_models.Line(code="FILT_LINE", name="필터링 계열", plant_id=plant.id)
    daily_plant_op = ops_models.DailyPlantOperation(plant_id=plant.id, op_date=date.today(), influent=100)
    db_session.add(plant)
    db_session.add(line)
    db_session.add(daily_plant_op)
    await db_session.commit()
    await db_session.refresh(plant)
    await db_session.refresh(line)
    await db_session.refresh(daily_plant_op)

    op1 = ops_models.DailyLineOperation(daily_plant_op_id=daily_plant_op.global_id, line_id=line.id, op_date=date.today(), influent=100)
    op2 = ops_models.DailyLineOperation(daily_plant_op_id=daily_plant_op.global_id, line_id=line.id, op_date=date.today() - timedelta(days=1), influent=200)
    db_session.add(op1)
    db_session.add(op2)
    await db_session.commit()
    await db_session.refresh(op1)
    await db_session.refresh(op2)

    response = await client.get(f"/api/v1/ops/daily_line_operations?line_id={line.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    ops_list = response.json()
    assert len(ops_list) == 2
    assert all(o["line_id"] == line.id for o in ops_list)
    print("test_read_daily_line_operations_by_line_id passed.")


# --- 사용자 정의 운영 데이터 보기 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_ops_view_success_user(
    authorized_client: AsyncClient,  # 일반 사용자 권한
    test_user: UsrUser,  # 사용자 ID 확인용
    db_session: Session  # 처리장 생성을 위해
):
    """
    일반 사용자 권한으로 새로운 사용자 정의 운영 데이터 보기를 성공적으로 생성하는지 테스트합니다.
    """
    print("\n--- Running test_create_ops_view_success_user ---")
    plant = loc_models.Facility(code="VW_PL", name="보기 테스트 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    view_data = {
        "name": "내 맞춤 보기",
        "login_id": test_user.id,
        "plant_id": plant.id,
        "plant_ids": [plant.id],
        "memo": "자주 보는 데이터 모음"
    }

    response = await authorized_client.post("/api/v1/ops/views", json=view_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 201
    created_view = response.json()
    assert created_view["name"] == view_data["name"]
    assert created_view["login_id"] == test_user.id
    assert created_view["plant_ids"] == [plant.id]
    assert "id" in created_view
    print("test_create_ops_view_success_user passed.")


@pytest.mark.asyncio
async def test_create_ops_view_duplicate_name_for_user(
    authorized_client: AsyncClient,
    test_user: UsrUser,
    db_session: Session
):
    """
    동일한 사용자가 중복 이름의 운영 데이터 보기를 생성 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    print("\n--- Running test_create_ops_view_duplicate_name_for_user ---")
    plant = loc_models.Facility(code="DVWP", name="중복 보기 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    existing_view = ops_models.OpsView(name="기존 보기", login_id=test_user.id, plant_ids=[plant.id])
    db_session.add(existing_view)
    await db_session.commit()
    await db_session.refresh(existing_view)

    view_data = {
        "name": "기존 보기",  # 중복 이름
        "login_id": test_user.id,
        "plant_id": plant.id,
        "plant_ids": [plant.id]
    }
    response = await authorized_client.post("/api/v1/ops/views", json=view_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 400
    assert response.json()["detail"] == "User defined view with this name already exists for this user."
    print("test_create_ops_view_duplicate_name_for_user passed.")


@pytest.mark.asyncio
async def test_read_ops_views_by_login_id(
    client: AsyncClient,
    test_user: UsrUser,
    test_admin_user: UsrUser,
    db_session: Session
):
    """
    특정 사용자 ID로 사용자 정의 운영 데이터 보기 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_ops_views_by_login_id ---")
    plant1 = loc_models.Facility(code="VW_P1", name="보기용 플랜트1")
    plant2 = loc_models.Facility(code="VW_P2", name="보기용 플랜트2")
    db_session.add(plant1)
    db_session.add(plant2)
    await db_session.commit()
    await db_session.refresh(plant1)
    await db_session.refresh(plant2)

     # ops_models.OpsView 객체 생성 시 plant_id 필드 추가
    view_user1_a = ops_models.OpsView(name="뷰1", login_id=test_user.id, plant_id=plant1.id, plant_ids=[plant1.id])
    view_user1_b = ops_models.OpsView(name="뷰2", login_id=test_user.id, plant_id=plant2.id, plant_ids=[plant2.id])
    view_admin1 = ops_models.OpsView(name="관리자뷰", login_id=test_admin_user.id, plant_id=plant1.id, plant_ids=[plant1.id])
    db_session.add(view_user1_a)
    db_session.add(view_user1_b)
    db_session.add(view_admin1)
    await db_session.commit()
    await db_session.refresh(view_user1_a)
    await db_session.refresh(view_user1_b)
    await db_session.refresh(view_admin1)

    response = await client.get(f"/api/v1/ops/views?login_id={test_user.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    views_list = response.json()
    assert len(views_list) == 2
    assert all(v["login_id"] == test_user.id for v in views_list)
    assert any(v["name"] == "뷰1" for v in views_list)
    assert any(v["name"] == "뷰2" for v in views_list)
    print("test_read_ops_views_by_login_id passed.")


@pytest.mark.asyncio
async def test_read_ops_views_by_plant_id(
    client: AsyncClient,
    test_user: UsrUser,
    db_session: Session
):
    """
    특정 plant_id를 포함하는 사용자 정의 운영 데이터 보기 목록을 성공적으로 조회하는지 테스트합니다.
    """
    print("\n--- Running test_read_ops_views_by_plant_id ---")
    plant_a = loc_models.Facility(code="PLA", name="플랜트 A")
    plant_b = loc_models.Facility(code="PLB", name="플랜트 B")
    db_session.add(plant_a)
    db_session.add(plant_b)
    await db_session.commit()
    await db_session.refresh(plant_a)
    await db_session.refresh(plant_b)

    # 뷰 생성
    view_plant_a = ops_models.OpsView(name="A 플랜트 뷰", login_id=test_user.id, plant_id=plant_a.id, plant_ids=[plant_a.id])
    view_plant_b = ops_models.OpsView(name="B 플랜트 뷰", login_id=test_user.id, plant_id=plant_b.id, plant_ids=[plant_b.id])
    view_plant_ab = ops_models.OpsView(name="AB 플랜트 뷰", login_id=test_user.id, plant_id=plant_a.id, plant_ids=[plant_a.id, plant_b.id])
    db_session.add(view_plant_a)
    db_session.add(view_plant_b)
    db_session.add(view_plant_ab)
    await db_session.commit()
    await db_session.refresh(view_plant_a)
    await db_session.refresh(view_plant_b)
    await db_session.refresh(view_plant_ab)

    # plant_a.id를 포함하는 뷰 조회
    response = await client.get(f"/api/v1/ops/views?plant_id={plant_a.id}")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    views_list = response.json()
    assert len(views_list) == 2  # "A 플랜트 뷰", "AB 플랜트 뷰"
    assert any(v["name"] == "A 플랜트 뷰" for v in views_list)
    assert any(v["name"] == "AB 플랜트 뷰" for v in views_list)
    print("test_read_ops_views_by_plant_id passed.")


@pytest.mark.asyncio
async def test_update_ops_view_success_user_self(
    authorized_client: AsyncClient,  # 일반 사용자로 인증된 클라이언트
    test_user: UsrUser,
    db_session: Session
):
    """
    일반 사용자가 자신의 운영 데이터 보기 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    print("\n--- Running test_update_ops_view_success_user_self ---")
    plant = loc_models.Facility(code="UPV_P", name="업데이트 보기 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    view_to_update = ops_models.OpsView(name="업데이트 대상 보기", login_id=test_user.id, plant_id=plant.id, plant_ids=[plant.id])
    db_session.add(view_to_update)
    await db_session.commit()
    await db_session.refresh(view_to_update)

    update_data = {"name": "업데이트된 내 보기", "memo": "새로운 메모입니다."}
    response = await authorized_client.put(f"/api/v1/ops/views/{view_to_update.id}", json=update_data)
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    updated_view = response.json()
    assert updated_view["id"] == view_to_update.id
    assert updated_view["name"] == update_data["name"]
    assert updated_view["memo"] == update_data["memo"]
    print("test_update_ops_view_success_user_self passed.")


@pytest.mark.asyncio
async def test_delete_ops_view_success_user_self(
    authorized_client: AsyncClient,
    test_user: UsrUser,
    db_session: Session
):
    """
    일반 사용자가 자신의 운영 데이터 보기를 성공적으로 삭제하는지 테스트합니다.
    """
    print("\n--- Running test_delete_ops_view_success_user_self ---")
    plant = loc_models.Facility(code="DELVP", name="삭제 보기 플랜트")
    db_session.add(plant)
    await db_session.commit()
    await db_session.refresh(plant)

    view_to_delete = ops_models.OpsView(name="삭제 대상 보기", login_id=test_user.id, plant_id=plant.id, plant_ids=[plant.id])
    db_session.add(view_to_delete)
    await db_session.commit()
    await db_session.refresh(view_to_delete)

    response = await authorized_client.delete(f"/api/v1/ops/views/{view_to_delete.id}")
    print(f"Response status code: {response.status_code}")

    assert response.status_code == 204  # No Content

    # 삭제되었는지 확인
    deleted_view = await ops_view_crud.get(db_session, id=view_to_delete.id)
    assert deleted_view is None
    print("test_delete_ops_view_success_user_self passed.")
