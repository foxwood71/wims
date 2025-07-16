# tests/domains/test_usr_n.py

"""
'usr' 도메인 (사용자 및 부서 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import status

from app.domains.usr import models as usr_models
from app.domains.usr import crud as usr_crud
# from app.core.security import verify_password


# =============================================================================
# 1. 인증 (Authentication) 엔드포인트 테스트 -> test_auth_n.py로 이동
# =============================================================================


# =============================================================================
# 2. 부서 (Department) 관리 엔드포인트 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_department_success_admin(
    admin_client: AsyncClient,
):
    """
    관리자 권한으로 새로운 부서를 성공적으로 생성하는지 테스트합니다.
    """
    department_data = {
        "code": "TEST",
        "name": "테스트 부서",
        "notes": "테스트용 부서입니다.",
        "sort_order": 10
    }
    response = await admin_client.post("/api/v1/usr/departments",
                                       json=department_data)

    assert response.status_code == 201
    created_department = response.json()
    assert created_department["name"] == department_data["name"]
    assert created_department["code"] == department_data["code"]


@pytest.mark.asyncio
async def test_create_department_unauthorized(
    authorized_client: AsyncClient,
    client: AsyncClient,
):
    """
    권한 없는 사용자의 부서 생성 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    department_data = {"code": "DENY", "name": "거부된 부서"}
    response_user = await authorized_client.post("/api/v1/usr/departments",
                                                 json=department_data)
    assert response_user.status_code == 403

    response_no_auth = await client.post("/api/v1/usr/departments",
                                         json=department_data)
    assert response_no_auth.status_code == 401


@pytest.mark.asyncio
async def test_read_departments_success(client: AsyncClient, db_session: AsyncSession):
    """
    부서 목록을 성공적으로 조회하는지 테스트합니다. (인증 불필요 또는 모든 인증 사용자)
    """
    dept1 = usr_models.Department(code="D1", name="부서1")
    dept2 = usr_models.Department(code="D2", name="부서2")
    db_session.add_all([dept1, dept2])
    await db_session.commit()

    response = await client.get("/api/v1/usr/departments")
    assert response.status_code == 200
    departments_list = response.json()
    assert len(departments_list) >= 2
    assert any(d["name"] == "부서1" for d in departments_list)


@pytest.mark.asyncio
async def test_read_departments_pagination(client: AsyncClient, db_session: AsyncSession):
    """
    부서 목록 페이징 기능이 올바르게 작동하는지 테스트합니다.
    """
    for i in range(1, 11):
        dept = usr_models.Department(code=f"DP{i:02d}", name=f"부서_{i}")
        db_session.add(dept)
    await db_session.commit()

    response = await client.get("/api/v1/usr/departments?limit=5")
    assert response.status_code == 200
    departments = response.json()
    assert len(departments) == 5
    assert departments[0]["name"] == "부서_1"

    response = await client.get("/api/v1/usr/departments?skip=5&limit=5")
    assert response.status_code == 200
    departments = response.json()
    assert len(departments) == 5
    assert departments[0]["name"] == "부서_6"

    response = await client.get("/api/v1/usr/departments?skip=10&limit=5")
    assert response.status_code == 200
    departments = response.json()
    assert len(departments) == 0


@pytest.mark.asyncio
async def test_read_department_by_id_success_admin(
    admin_client: AsyncClient,
    db_session: AsyncSession
):
    """
    관리자 권한으로 특정 부서를 성공적으로 조회하는지 테스트합니다.
    """
    dept = usr_models.Department(code="VIEW", name="조회 대상 부서")
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    response = await admin_client.get(f"/api/v1/usr/departments/{dept.id}")
    assert response.status_code == 200
    assert response.json()["name"] == dept.name


@pytest.mark.asyncio
async def test_read_department_by_id_success_user(
    authorized_client: AsyncClient,
    db_session: AsyncSession
):
    """
    일반 사용자 권한으로 특정 부서를 성공적으로 조회하는지 테스트합니다.
    """
    dept = usr_models.Department(code="VWSU", name="사용자 조회 부서")
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    response = await authorized_client.get(f"/api/v1/usr/departments/{dept.id}")
    assert response.status_code == 200
    assert response.json()["name"] == dept.name


@pytest.mark.asyncio
async def test_read_department_by_id_unauthorized(client: AsyncClient):
    """
    비인증 사용자가 특정 부서 조회 시 401 Unauthorized를 반환하는지 테스트합니다.
    """
    response = await client.get("/api/v1/usr/departments/999")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_department_success_admin(
    admin_client: AsyncClient,
    db_session: AsyncSession
):
    """
    관리자 권한으로 부서 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    dept = usr_models.Department(code="UPDA", name="업데이트 대상 부서")
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    update_data = {"name": "업데이트된 부서명", "notes": "수정된 비고"}
    response = await admin_client.put(f"/api/v1/usr/departments/{dept.id}",
                                      json=update_data)
    assert response.status_code == 200
    updated_dept = response.json()
    assert updated_dept["name"] == update_data["name"]
    assert updated_dept["notes"] == update_data["notes"]


@pytest.mark.asyncio
async def test_update_department_duplicate_name_admin(
    admin_client: AsyncClient,
    db_session: AsyncSession
):
    """
    관리자 권한으로 부서 업데이트 시, 다른 부서의 이름과 중복되는 경우 400 에러를 반환하는지 테스트합니다.
    """
    existing_dept1 = usr_models.Department(code="EXD1", name="기존 부서명1")
    existing_dept2 = usr_models.Department(code="EXD2", name="기존 부서명2")
    db_session.add_all([existing_dept1, existing_dept2])
    await db_session.commit()
    await db_session.refresh(existing_dept1)
    await db_session.refresh(existing_dept2)

    update_data = {"name": existing_dept2.name}
    response = await admin_client.put(f"/api/v1/usr/departments/{existing_dept1.id}", json=update_data)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_department_duplicate_code_admin(
    admin_client: AsyncClient,
    db_session: AsyncSession
):
    """
    관리자 권한으로 부서 업데이트 시, 다른 부서의 코드와 중복되는 경우 400 에러를 반환하는지 테스트합니다.
    """
    existing_dept1 = usr_models.Department(code="ECD1", name="코드중복대상1")
    existing_dept2 = usr_models.Department(code="ECD2", name="코드중복대상2")
    db_session.add_all([existing_dept1, existing_dept2])
    await db_session.commit()
    await db_session.refresh(existing_dept1)
    await db_session.refresh(existing_dept2)

    update_data = {"code": existing_dept2.code}
    response = await admin_client.put(f"/api/v1/usr/departments/{existing_dept1.id}", json=update_data)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_department_unauthorized(
    authorized_client: AsyncClient,
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    권한 없는 사용자의 부서 업데이트 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    dept = usr_models.Department(code="UAUT", name="업데이트 권한 없는 부서")
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    update_data = {"name": "변경된 이름"}

    response_user = await authorized_client.put(f"/api/v1/usr/departments/{dept.id}",
                                                json=update_data)
    assert response_user.status_code == 403

    response_no_auth = await client.put(f"/api/v1/usr/departments/{dept.id}",
                                        json=update_data)
    assert response_no_auth.status_code == 401


@pytest.mark.asyncio
async def test_delete_department_success_admin(
    admin_client: AsyncClient,
    db_session: AsyncSession
):
    """
    관리자 권한으로 부서를 성공적으로 삭제하는지 테스트합니다.
    """
    dept = usr_models.Department(code="DEL", name="삭제 대상 부서")
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    response = await admin_client.delete(f"/api/v1/usr/departments/{dept.id}")
    assert response.status_code == 204

    deleted_dept = await usr_crud.department.get(db_session, id=dept.id)
    assert deleted_dept is None


@pytest.mark.asyncio
async def test_delete_department_unauthorized(
    authorized_client: AsyncClient,
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    권한 없는 사용자의 부서 삭제 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    dept_user = usr_models.Department(code="DELU", name="사용자 삭제 시도")
    dept_no_auth = usr_models.Department(code="DELN", name="비인증 삭제 시도")
    db_session.add_all([dept_user, dept_no_auth])
    await db_session.commit()
    await db_session.refresh(dept_user)
    await db_session.refresh(dept_no_auth)

    response_user = await authorized_client.delete(f"/api/v1/usr/departments/{dept_user.id}")
    assert response_user.status_code == 403

    response_no_auth = await client.delete(f"/api/v1/usr/departments/{dept_no_auth.id}")
    assert response_no_auth.status_code == 401


@pytest.mark.asyncio
async def test_delete_department_with_associated_users(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    get_password_hash_fixture
):
    """
    연관된 사용자가 있는 부서 삭제 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    dept_with_users = usr_models.Department(code="DEPW", name="사용자 있는 부서")
    db_session.add(dept_with_users)
    await db_session.commit()
    await db_session.refresh(dept_with_users)

    user_in_dept = usr_models.User(
        login_id="userindept",
        email="userindept@example.com",
        password_hash=get_password_hash_fixture("password"),
        department_id=dept_with_users.id,
        role=usr_models.UserRole.GENERAL_USER  # [수정] Enum 사용
    )
    db_session.add(user_in_dept)
    await db_session.commit()
    await db_session.refresh(user_in_dept)

    response = await admin_client.delete(f"/api/v1/usr/departments/{dept_with_users.id}")

    assert response.status_code == 400
    assert "Cannot delete department" in response.json()["detail"]


# =============================================================================
# 3. 사용자 (User) 관리 엔드포인트 테스트
# =============================================================================
@pytest.mark.asyncio
async def test_create_user_success_admin(admin_client: AsyncClient):
    """
    관리자 권한으로 새로운 사용자를 성공적으로 생성하는지 테스트합니다.
    """
    user_data = {
        "login_id": "newbie",
        "password": "new_password_123",
        "email": "newbie@example.com",
        "name": "신입사원",
        "role": usr_models.UserRole.GENERAL_USER,
    }
    response = await admin_client.post("/api/v1/usr/users", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    created_user = response.json()
    assert created_user["login_id"] == user_data["login_id"]
    assert "password_hash" not in created_user  # 응답에 비밀번호 해시가 없는지 확인


@pytest.mark.asyncio
async def test_create_user_duplicate_login_id_fail(
    admin_client: AsyncClient,
    test_user: usr_models.User
):
    """
    중복된 login_id로 사용자 생성 시 400 에러를 반환하는지 테스트합니다.
    """
    user_data = {
        "login_id": test_user.login_id,  # 기존 사용자와 동일한 ID
        "password": "another_password",
        "email": "another@example.com",
        "role": usr_models.UserRole.GENERAL_USER,
    }
    response = await admin_client.post("/api/v1/usr/users", json=user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Username already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_duplicate_email_admin(
    admin_client: AsyncClient,
    test_user: usr_models.User,
):
    """
    관리자 권한으로 사용자 생성 시, 중복 이메일로 400 에러를 반환하는지 테스트합니다.
    """
    user_data = {
        "login_id": "anotherusername",
        "password": "newpassword",
        "email": test_user.email,  # 기존 사용자와 동일한 ID
        "role": usr_models.UserRole.GENERAL_USER
    }
    response = await admin_client.post("/api/v1/usr/users", json=user_data)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_unauthorized(
    authorized_client: AsyncClient,
    client: AsyncClient,
):
    """
    권한 없는 사용자의 사용자 생성 시도를 테스트합니다. (일반 사용자, 비인증 사용자)
    """
    user_data = {
        "login_id": "unauthuser",
        "password": "password123",
        "email": "unauth@example.com",
        "role": usr_models.UserRole.GENERAL_USER
    }
    response_user = await authorized_client.post("/api/v1/usr/users", json=user_data)
    assert response_user.status_code == 403

    response_no_auth = await client.post("/api/v1/usr/users", json=user_data)
    assert response_no_auth.status_code == 401


@pytest.mark.asyncio
async def test_read_users_success_admin(
    admin_client: AsyncClient,
    test_user: usr_models.User,
    test_admin_user: usr_models.User
):
    """
    관리자가 모든 사용자 목록을 성공적으로 조회하는지 테스트합니다.
    """
    response = await admin_client.get("/api/v1/usr/users")
    assert response.status_code == 200
    users_list = response.json()
    assert len(users_list) >= 2
    assert any(u["login_id"] == test_user.login_id for u in users_list)
    assert any(u["login_id"] == test_admin_user.login_id for u in users_list)


@pytest.mark.asyncio
async def test_read_users_pagination_user_self(
    authorized_client: AsyncClient,
    test_user: usr_models.User
):
    """
    일반 사용자가 자신의 사용자 정보에 대해 페이징을 시도하는 경우, 항상 자신의 정보만 반환하는지 테스트합니다.
    """
    response = await authorized_client.get("/api/v1/usr/users?skip=10&limit=1")
    assert response.status_code == 200
    users_list = response.json()
    assert len(users_list) == 1
    assert users_list[0]["id"] == test_user.id


@pytest.mark.asyncio
async def test_read_user_by_id_success_admin(
    admin_client: AsyncClient,
    test_user: usr_models.User,
    test_admin_user: usr_models.User
):
    """
    관리자가 특정 사용자의 정보를 성공적으로 조회하는지 테스트합니다.
    """
    response_other = await admin_client.get(f"/api/v1/usr/users/{test_user.id}")
    assert response_other.status_code == 200
    assert response_other.json()["login_id"] == test_user.login_id


@pytest.mark.asyncio
async def test_read_user_by_id_success_user_self(
    authorized_client: AsyncClient,
    test_user: usr_models.User
):
    """
    일반 사용자가 자신의 ID로 자신의 정보를 성공적으로 조회하는지 테스트합니다.
    """
    response = await authorized_client.get(f"/api/v1/usr/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["login_id"] == test_user.login_id


@pytest.mark.asyncio
async def test_read_user_forbidden_user_other(
    authorized_client: AsyncClient,
    test_admin_user: usr_models.User
):
    """
    일반 사용자가 다른 사용자의 정보 조회 시 403 Forbidden을 반환하는지 테스트합니다.
    """
    response = await authorized_client.get(f"/api/v1/usr/users/{test_admin_user.id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_success_user_self(
    authorized_client: AsyncClient,
    test_user: usr_models.User,
    db_session: AsyncSession
):
    """
    일반 사용자가 자신의 정보를 성공적으로 업데이트하는지 테스트합니다.
    """
    update_data = {"name": "Updated User Name"}
    response = await authorized_client.put(f"/api/v1/usr/users/{test_user.id}", json=update_data)
    assert response.status_code == 200
    db_updated_user = await db_session.get(usr_models.User, test_user.id)
    assert db_updated_user.name == update_data["name"]


@pytest.mark.asyncio
async def test_update_user_prevent_admin_role_change(
    authorized_client: AsyncClient,
    test_admin_user: usr_models.User,
    db_session: AsyncSession
):
    """
    관리자 이하 계정이 관리자 계정의 역할을 변경하려고 시도할 때 403 에러를 반환하는지 테스트합니다.
    """
    update_data = {"role": usr_models.UserRole.GENERAL_USER}  # [수정] Enum 사용
    response = await authorized_client.put(f"/api/v1/usr/users/{test_admin_user.id}", json=update_data)
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]
    db_admin_user = await db_session.get(usr_models.User, test_admin_user.id)
    assert db_admin_user.role == usr_models.UserRole.ADMIN


@pytest.mark.asyncio
async def test_update_user_prevent_admin_deactivation(
    admin_client: AsyncClient,
    test_admin_user: usr_models.User,
    db_session: AsyncSession
):
    """
    관리자 계정을 비활성화하려고 시도할 때 400 에러를 반환하는지 테스트합니다.
    """
    update_data = {"is_active": False}
    response = await admin_client.put(f"/api/v1/usr/users/{test_admin_user.id}", json=update_data)
    assert response.status_code == 400
    assert "Cannot deactivate" in response.json()["detail"]
    db_superuser = await db_session.get(usr_models.User, test_admin_user.id)
    assert db_superuser.is_active is True


@pytest.mark.asyncio
async def test_update_user_prevent_promote_to_admin(
    admin_client: AsyncClient,
    test_user: usr_models.User,
    db_session: AsyncSession
):
    """
    일반 사용자를 관리자로 역할 변경 시도 시 403 에러를 반환하는지 테스트합니다.
    """
    update_data = {"role": usr_models.UserRole.ADMIN}  # [수정] Enum 사용
    response = await admin_client.put(f"/api/v1/usr/users/{test_user.id}", json=update_data)
    assert response.status_code == 403
    assert "Only a admin can" in response.json()["detail"]
    db_user = await db_session.get(usr_models.User, test_user.id)
    assert db_user.role == usr_models.UserRole.GENERAL_USER


@pytest.mark.asyncio
async def test_delete_user_success_admin(
    admin_client: AsyncClient,
    test_user: usr_models.User,
    db_session: AsyncSession
):
    """
    관리자 권한으로 사용자를 성공적으로 삭제하는지 테스트합니다.
    """
    response = await admin_client.delete(f"/api/v1/usr/users/{test_user.id}")
    assert response.status_code == 204
    deleted_user = await db_session.get(usr_models.User, test_user.id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_delete_user_authorized_user_no_permission(
    authorized_client: AsyncClient,
    test_user: usr_models.User
):
    """
    일반 권한으로 사용자 삭제 시도 시 403 Forbidden을 반환하는지 테스트합니다.
    """
    response = await authorized_client.delete(f"/api/v1/usr/users/{test_user.id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_superuser_self_attempt(
    admin_client: AsyncClient,
    test_admin_user: usr_models.User
):
    """
    최고 관리자가 자신의 계정을 삭제 시도 시 400 Bad Request를 반환하는지 테스트합니다.
    """
    response = await admin_client.delete(f"/api/v1/usr/users/{test_admin_user.id}")
    assert response.status_code == 400
    assert "Cannot delete your own superuser account" in response.json()["detail"]
