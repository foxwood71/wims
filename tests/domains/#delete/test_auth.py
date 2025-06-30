# tests/domains/test_auth.py

"""
'usr' 도메인 내의 인증 관련 API 엔드포인트에 대한 통합 테스트를 정의하는 모듈입니다.
"""

import pytest
# [수정] 타입 힌트를 위해 httpx의 AsyncClient를 임포트합니다.
from httpx import AsyncClient
# [수정] 타입 힌트를 위해 비동기 세션을 임포트합니다.
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.usr.models import User as UsrUser
from app.core.security import get_password_hash

# conftest.py에서 정의된 픽스처들을 Pytest가 자동으로 감지하여 사용할 수 있습니다.


@pytest.mark.asyncio
async def test_login_for_access_token_success(
    client: AsyncClient,
    test_user: UsrUser,
):
    """
    올바른 사용자명과 비밀번호로 로그인하여 액세스 토큰을 성공적으로 발급받는지 테스트합니다.
    """
    login_data = {
        "username": test_user.username,
        "password": "testpassword123"  # conftest.py에서 test_user 생성 시 사용한 비밀번호
    }
    
    # [수정] await 추가 및 전체 URL 경로 사용
    response = await client.post("/api/v1/usr/auth/token", data=login_data)

    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_for_access_token_wrong_password(
    client: AsyncClient,
    test_user: UsrUser,
):
    """
    잘못된 비밀번호로 로그인 시도 시 401 UNAUTHORIZED 응답을 받는지 테스트합니다.
    """
    response = await client.post(
        "/api/v1/usr/auth/token",
        data={
            "username": test_user.username,
            "password": "wrong_password"
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_for_access_token_nonexistent_user(
    client: AsyncClient,
):
    """
    존재하지 않는 사용자명으로 로그인 시도 시 401 UNAUTHORIZED 응답을 받는지 테스트합니다.
    """
    response = await client.post(
        "/api/v1/usr/auth/token",
        data={
            "username": "nonexistent_user",
            "password": "any_password"
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_for_access_token_inactive_user(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    비활성 상태의 사용자로 로그인 시도 시 400 BAD REQUEST 응답을 받는지 테스트합니다.
    """
    # 비활성 사용자 생성
    hashed_password = get_password_hash("testpassword123")
    inactive_user = UsrUser(
        username="inactiveuser",
        email="inactive@example.com",
        password_hash=hashed_password,
        is_active=False
    )
    db_session.add(inactive_user)
    await db_session.commit()

    response = await client.post(
        "/api/v1/usr/auth/token",
        data={
            "username": inactive_user.username,
            "password": "testpassword123"
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_read_users_me_success(
    authorized_client: AsyncClient,
    test_user: UsrUser
):
    """
    유효한 토큰으로 '/api/v1/usr/auth/me' 엔드포인트에 접근하여 사용자 정보를 조회하는지 테스트합니다.
    """
    response = await authorized_client.get("/api/v1/usr/auth/me")

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["username"] == test_user.username
    assert response_data["id"] == test_user.id
    assert "password_hash" not in response_data


@pytest.mark.asyncio
async def test_read_users_me_no_token(client: AsyncClient):
    """
    토큰 없이 '/api/v1/usr/auth/me' 엔드포인트에 접근 시 401 UNAUTHORIZED 응답을 받는지 테스트합니다.
    """
    response = await client.get("/api/v1/usr/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_read_users_me_invalid_token(client: AsyncClient):
    """
    유효하지 않은 토큰으로 '/api/v1/usr/auth/me' 엔드포인트에 접근 시 401 UNAUTHORIZED 응답을 받는지 테스트합니다.
    """
    invalid_token = "invalid.jwt.token"
    response = await client.get(
        "/api/v1/usr/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"