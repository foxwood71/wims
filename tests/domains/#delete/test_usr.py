# tests/domains/test_usr.py

"""
'usr' 도메인 (사용자 및 부서 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.usr import models as usr_models
from app.domains.usr.crud import department as department_crud


# --- 부서 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_department_success_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
):
    """
    관리자 권한으로 새로운 부서를 성공적으로 생성하는지 테스트합니다.
    """
    department_data = {  # Flake8: E121
        "code": "TEST",  # Flake8: E121
        "name": "테스트 부서",  # Flake8: E121
        "notes": "테스트용 부서입니다.",  # Flake8: E121
        "sort_order": 10  # Flake8: E121
    }
    response = await admin_client.post("/api/v1/usr/departments",  # Flake8: E121, E501
                                       json=department_data)

    assert response.status_code == 201
    created_department = response.json()
    assert created_department["name"] == department_data["name"]
    assert created_department["code"] == department_data["code"]


@pytest.mark.asyncio
async def test_create_department_duplicate_name_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    이미 존재하는 이름의 부서 생성 시 400 에러를 반환하는지 테스트합니다.
    """
    existing_dept = usr_models.Department(code="EXST",  # Flake8: E121
                                          name="기존 부서")
    db_session.add(existing_dept)
    await db_session.commit()

    department_data = {"code": "NEWC",  # Flake8: E121
                       "name": "기존 부서"}
    response = await admin_client.post("/api/v1/usr/departments",  # Flake8: E121, E501
                                       json=department_data)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_department_unauthorized(  # Flake8: E128
    authorized_client: AsyncClient,  # Flake8: E128
    client: AsyncClient,  # Flake8: E128
):
    """
    권한 없는 사용자의 부서 생성 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    department_data = {"code": "DENY",  # Flake8: E121
                       "name": "거부된 부서"}
    response_user = await authorized_client.post("/api/v1/usr/departments",  # Flake8: E121, E501
                                                 json=department_data)
    assert response_user.status_code == 403  # 관리자 권한 필요 명시

    response_no_auth = await client.post("/api/v1/usr/departments",  # Flake8: E121, E501
                                         json=department_data)
    assert response_no_auth.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_read_departments_success(client: AsyncClient, db_session: AsyncSession):
    """
    부서 목록을 성공적으로 조회하는지 테스트합니다. (인증 불필요 또는 모든 인증 사용자)
    """
    dept1 = usr_models.Department(code="D1",  # Flake8: E121
                                  name="부서1")
    dept2 = usr_models.Department(code="D2",  # Flake8: E121
                                  name="부서2")
    db_session.add_all([dept1, dept2])
    await db_session.commit()

    response = await client.get("/api/v1/usr/departments")  # 보안 명시 없음 (누구나 조회 가능)
    assert response.status_code == 200
    departments_list = response.json()
    assert len(departments_list) >= 2
    assert any(d["name"] == "부서1" for d in departments_list)
    assert any(d["name"] == "부서2" for d in departments_list)


@pytest.mark.asyncio
async def test_read_department_by_id_success_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    관리자 권한으로 특정 부서를 성공적으로 조회하는지 테스트합니다.
    """
    dept = usr_models.Department(
        code="VIEW",  # Flake8: E121
        name="조회 대상 부서"
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    response = await admin_client.get(f"/api/v1/usr/departments/{dept.id}")  # Flake8: E121, E501
    assert response.status_code == 200
    assert response.json()["name"] == dept.name


@pytest.mark.asyncio
async def test_read_department_by_id_success_user(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    일반 사용자 권한으로 특정 부서를 성공적으로 조회하는지 테스트합니다.
    (OpenAPI 문서에 따르면 특정 부서 조회는 인증만 되면 가능. 역할 제한 없음)
    """
    dept = usr_models.Department(
        code="VWSU",  # Flake8: E121
        name="사용자 조회 부서"
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    response = await authorized_client.get(f"/api/v1/usr/departments/{dept.id}")  # Flake8: E121, E501
    assert response.status_code == 200
    assert response.json()["name"] == dept.name


@pytest.mark.asyncio
async def test_read_department_by_id_unauthorized(  # Flake8: E128
    client: AsyncClient,  # Flake8: E128
):
    """
    비인증 사용자가 특정 부서 조회 시 401 Unauthorized를 반환하는지 테스트합니다.
    """
    response = await client.get("/api/v1/usr/departments/999")  # Flake8: E121
    assert response.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_update_department_success_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    관리자 권한으로 부서 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    dept = usr_models.Department(
        code="UPDA",  # Flake8: E121
        name="업데이트 대상 부서"
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    update_data = {"name": "업데이트된 부서명",  # Flake8: E121
                   "notes": "수정된 비고"}
    response = await admin_client.put(f"/api/v1/usr/departments/{dept.id}",  # Flake8: E121, E501
                                      json=update_data)
    assert response.status_code == 200
    updated_dept = response.json()
    assert updated_dept["name"] == update_data["name"]
    assert updated_dept["notes"] == update_data["notes"]


@pytest.mark.asyncio
async def test_update_department_unauthorized(  # Flake8: E128
    authorized_client: AsyncClient,  # Flake8: E128
    client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    권한 없는 사용자의 부서 업데이트 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    dept = usr_models.Department(
        code="UAUT",  # Flake8: E121
        name="업데이트 권한 없는 부서"
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    update_data = {"name": "변경된 이름"}

    response_user = await authorized_client.put(f"/api/v1/usr/departments/{dept.id}",  # Flake8: E121, E501
                                                json=update_data)
    assert response_user.status_code == 403  # 관리자 권한 필요 명시

    response_no_auth = await client.put(f"/api/v1/usr/departments/{dept.id}",  # Flake8: E121, E501
                                        json=update_data)
    assert response_no_auth.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_delete_department_success_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    관리자 권한으로 부서를 성공적으로 삭제하는지 테스트합니다.
    """
    dept = usr_models.Department(
        code="DEL",  # Flake8: E121
        name="삭제 대상 부서"
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    response = await admin_client.delete(f"/api/v1/usr/departments/{dept.id}")  # Flake8: E121, E501
    assert response.status_code == 204

    deleted_dept = await department_crud.get(db_session, id=dept.id)
    assert deleted_dept is None


@pytest.mark.asyncio
async def test_delete_department_unauthorized(  # Flake8: E128
    authorized_client: AsyncClient,  # Flake8: E128
    client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    권한 없는 사용자의 부서 삭제 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    dept_user = usr_models.Department(code="DELU",  # Flake8: E121
                                      name="사용자 삭제 시도")
    dept_no_auth = usr_models.Department(code="DELN",  # Flake8: E121
                                         name="비인증 삭제 시도")
    db_session.add_all([dept_user, dept_no_auth])
    await db_session.commit()
    await db_session.refresh(dept_user)
    await db_session.refresh(dept_no_auth)

    response_user = await authorized_client.delete(f"/api/v1/usr/departments/{dept_user.id}")  # Flake8: E121, E501
    assert response_user.status_code == 403  # 관리자 권한 필요 명시

    response_no_auth = await client.delete(f"/api/v1/usr/departments/{dept_no_auth.id}")  # Flake8: E121, E501
    assert response_no_auth.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_delete_department_with_associated_users(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession,  # Flake8: E128
    get_password_hash_fixture
):
    """
    연관된 사용자가 있는 부서 삭제 시 400 Bad Request (또는 409 Conflict)를 반환하는지 테스트합니다.
    (DB 제약 조건에 따라 달라질 수 있음)
    """
    dept_with_users = usr_models.Department(
        code="DEPW",  # Flake8: E121
        name="사용자 있는 부서",
    )
    db_session.add(dept_with_users)
    await db_session.commit()
    await db_session.refresh(dept_with_users)

    user_in_dept = usr_models.User(  # Flake8: E121
        username="userindept",  # Flake8: E121
        email="userindept@example.com",  # Flake8: E121
        password_hash=get_password_hash_fixture("password"),  # Flake8: E121
        department_id=dept_with_users.id  # Flake8: E121
    )
    db_session.add(user_in_dept)
    await db_session.commit()
    await db_session.refresh(user_in_dept)

    response = await admin_client.delete(f"/api/v1/usr/departments/{dept_with_users.id}")  # Flake8: E121, E501

    # OpenAPI 문서에 "ON DELETE RESTRICT 정책에 따라 삭제가 실패합니다" 명시
    # 따라서 400 또는 409가 예상됩니다.
    assert response.status_code == 400 or response.status_code == 409
    assert "Cannot delete department" in response.json()["detail"] or \
           "violates foreign key constraint" in response.json()["detail"]


# --- 사용자 관리 엔드포인트 테스트 ---

@pytest.mark.asyncio
async def test_create_user_success_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession,  # Flake8: E128
    test_department: usr_models.Department,  # 기존 픽스처 활용
    get_password_hash_fixture
):
    """
    관리자 권한으로 새로운 사용자를 성공적으로 생성하는지 테스트합니다.
    """
    user_data = {  # Flake8: E121
        "username": "newuseradmin",  # Flake8: E121
        "password": "newpassword123",  # Flake8: E121
        "email": "newuseradmin@example.com",  # Flake8: E121
        "full_name": "New User Admin",  # Flake8: E121
        "department_id": test_department.id,  # Flake8: E121
        "role": 100  # Flake8: E121
    }
    response = await admin_client.post("/api/v1/usr/users",  # Flake8: E121, E501
                                       json=user_data)

    assert response.status_code == 201
    created_user = response.json()
    assert created_user["username"] == user_data["username"]
    db_user = await db_session.get(usr_models.User, created_user["id"])
    assert db_user is not None
    assert get_password_hash_fixture(user_data["password"])


@pytest.mark.asyncio
async def test_create_user_unauthorized(  # Flake8: E128
    authorized_client: AsyncClient,  # Flake8: E128
    client: AsyncClient,  # Flake8: E128
    test_department: usr_models.Department  # 기존 픽스처 활용
):
    """
    권한 없는 사용자의 사용자 생성 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    user_data = {  # Flake8: E121
        "username": "unauthuser",  # Flake8: E121
        "password": "password123",  # Flake8: E121
        "email": "unauth@example.com",  # Flake8: E121
        "full_name": "Unauthorized User",  # Flake8: E121
        "department_id": test_department.id,  # Flake8: E121
        "role": 100  # Flake8: E121
    }

    response_user = await authorized_client.post("/api/v1/usr/users",  # Flake8: E121, E501
                                                 json=user_data)
    assert response_user.status_code == 403  # 관리자 권한 필요 명시

    response_no_auth = await client.post("/api/v1/usr/users",  # Flake8: E121, E501
                                         json=user_data)
    assert response_no_auth.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_read_users_success_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User,  # Flake8: E128
    test_admin_user: usr_models.User,  # Flake8: E128
    db_session: AsyncSession,  # Flake8: E128
    get_password_hash_fixture
):
    """
    관리자가 모든 사용자 목록을 성공적으로 조회하는지 테스트합니다.
    """
    # 추가 사용자 생성 (이미 픽스처로 test_user, test_admin_user 존재)
    another_user = usr_models.User(  # Flake8: E121
        username="anotheruser",  # Flake8: E121
        email="another@example.com",  # Flake8: E121
        password_hash=get_password_hash_fixture("password"),  # Flake8: E121
        role=100  # Flake8: E121
    )
    db_session.add(another_user)
    await db_session.commit()
    await db_session.refresh(another_user)

    response = await admin_client.get("/api/v1/usr/users")
    assert response.status_code == 200
    users_list = response.json()
    assert len(users_list) >= 3  # test_user, test_admin_user, another_user 포함
    assert any(u["username"] == test_user.username for u in users_list)
    assert any(u["username"] == test_admin_user.username for u in users_list)
    assert any(u["username"] == another_user.username for u in users_list)


@pytest.mark.asyncio
async def test_read_users_success_user_self(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User,  # Flake8: E128
    test_admin_user: usr_models.User  # 다른 사용자 존재 확인용
):
    """
    일반 사용자가 자신의 사용자 정보만 조회하는지 테스트합니다.
    (GET /api/v1/usr/users는 일반 사용자의 경우 자신의 정보만 반환)
    """
    response = await authorized_client.get("/api/v1/usr/users")
    assert response.status_code == 200
    users_list = response.json()
    assert len(users_list) == 1
    assert users_list[0]["username"] == test_user.username
    assert users_list[0]["id"] == test_user.id
    assert not any(u["username"] == test_admin_user.username for u in users_list)


@pytest.mark.asyncio
async def test_read_users_unauthorized(client: AsyncClient):
    """
    비인증 사용자가 모든 사용자 조회 시 401 Unauthorized를 반환하는지 테스트합니다.
    """
    response = await client.get("/api/v1/usr/users")
    assert response.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_read_user_by_id_success_admin(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User,  # Flake8: E128
    test_admin_user: usr_models.User  # Flake8: E128
):
    """
    관리자가 특정 사용자의 정보를 성공적으로 조회하는지 테스트합니다. (자신 포함)
    """
    # 관리자가 자신의 정보 조회
    response_self = await admin_client.get(f"/api/v1/usr/users/{test_admin_user.id}")  # Flake8: E121, E501
    assert response_self.status_code == 200
    assert response_self.json()["username"] == test_admin_user.username

    # 관리자가 다른 사용자 정보 조회
    response_other = await admin_client.get(f"/api/v1/usr/users/{test_user.id}")  # Flake8: E121, E501
    assert response_other.status_code == 200
    assert response_other.json()["username"] == test_user.username


@pytest.mark.asyncio
async def test_read_user_by_id_success_user_self(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User  # Flake8: E128
):
    """
    일반 사용자가 자신의 ID로 자신의 정보를 성공적으로 조회하는지 테스트합니다.
    """
    response = await authorized_client.get(f"/api/v1/usr/users/{test_user.id}")  # Flake8: E121, E501
    assert response.status_code == 200
    assert response.json()["username"] == test_user.username


@pytest.mark.asyncio
async def test_read_user_forbidden_user_other(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    test_admin_user: usr_models.User  # Flake8: E128
):
    """
    일반 사용자가 다른 사용자의 정보 조회 시 403 Forbidden을 반환하는지 테스트합니다.
    """
    response = await authorized_client.get(f"/api/v1/usr/users/{test_admin_user.id}")  # Flake8: E121, E501
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_read_user_by_id_unauthorized(client: AsyncClient):
    """
    비인증 사용자가 특정 사용자 조회 시 401 Unauthorized를 반환하는지 테스트합니다.
    """
    response = await client.get("/api/v1/usr/users/1")  # Flake8: E121
    assert response.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_update_user_success_user_self(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    일반 사용자가 자신의 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    update_data = {"email": "updated_user@example.com",  # Flake8: E121
                   "full_name": "Updated User Name"}
    response = await authorized_client.put(f"/api/v1/usr/users/{test_user.id}",  # Flake8: E121, E501
                                           json=update_data)
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["email"] == update_data["email"]
    assert updated_user["full_name"] == update_data["full_name"]

    # DB에서 실제 업데이트 확인
    db_updated_user = await db_session.get(usr_models.User, test_user.id)
    assert db_updated_user.email == update_data["email"]


@pytest.mark.asyncio
async def test_update_user_success_admin_other_user(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    관리자가 다른 사용자의 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    update_data = {"email": "updated_by_admin@example.com",  # Flake8: E121
                   "full_name": "User Updated by Admin",  # Flake8: E121
                   "is_active": False}
    response = await admin_client.put(f"/api/v1/usr/users/{test_user.id}",  # Flake8: E121, E501
                                      json=update_data)
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["email"] == update_data["email"]
    assert updated_user["is_active"] == update_data["is_active"]

    # DB에서 실제 업데이트 확인
    db_updated_user = await db_session.get(usr_models.User, test_user.id)
    assert db_updated_user.email == update_data["email"]


@pytest.mark.asyncio
async def test_update_user_forbidden_user_other(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    test_admin_user: usr_models.User  # Flake8: E128
):
    """
    일반 사용자가 다른 사용자의 정보 업데이트 시 403 Forbidden을 반환하는지 테스트합니다.
    """
    update_data = {"email": "not_allowed@example.com"}
    response = await authorized_client.put(f"/api/v1/usr/users/{test_admin_user.id}",  # Flake8: E121, E501
                                           json=update_data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_unauthorized(client: AsyncClient):
    """
    비인증 사용자가 사용자 정보 업데이트 시 401 Unauthorized를 반환하는지 테스트합니다.
    """
    update_data = {"email": "unauth_update@example.com"}
    response = await client.put("/api/v1/usr/users/1",  # Flake8: E121
                                json=update_data)
    assert response.status_code == 401  # 보안: OAuth2PasswordBearer


@pytest.mark.asyncio
async def test_delete_user_success_superuser(  # Flake8: E128, E501
    superuser_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User,  # Flake8: E128
    db_session: AsyncSession  # Flake8: E128
):
    """
    최고 관리자 권한으로 사용자를 성공적으로 삭제하는지 테스트합니다.
    """
    response = await superuser_client.delete(f"/api/v1/usr/users/{test_user.id}")  # Flake8: E121, E501
    assert response.status_code == 204

    deleted_user = await db_session.get(usr_models.User, test_user.id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_delete_user_admin_no_permission(  # Flake8: E128, E501
    admin_client: AsyncClient,  # Flake8: E128
    test_user: usr_models.User  # test_user는 삭제되지 않고 남아있어야 함
):
    """
    관리자 권한으로 사용자 삭제 시도 시 403 Forbidden을 반환하는지 테스트합니다.
    (최고 관리자만 삭제 가능)
    """
    response = await admin_client.delete(f"/api/v1/usr/users/{test_user.id}")  # Flake8: E121, E501
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_forbidden_user(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    test_admin_user: usr_models.User  # test_admin_user는 삭제되지 않고 남아있어야 함
):
    """
    일반 사용자가 사용자 삭제 시도 시 403 Forbidden을 반환하는지 테스트합니다.
    """
    response = await authorized_client.delete(f"/api/v1/usr/users/{test_admin_user.id}")  # Flake8: E121, E501
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_unauthorized(client: AsyncClient):
    """
    비인증 사용자가 사용자 삭제 시도 시 401 Unauthorized를 반환하는지 테스트합니다.
    """
    response = await client.delete("/api/v1/usr/users/1")  # Flake8: E121
    assert response.status_code == 401  # 보안: OAuth2PasswordBearer
