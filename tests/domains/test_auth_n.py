# tests/domains/test_auth.py

"""
'usr' 도메인 내의 인증 관련 API 엔드포인트에 대한 통합 테스트를 정의하는 모듈입니다.
"""

import pytest
# 타입 힌트를 위해 httpx의 AsyncClient를 임포트합니다.
from httpx import AsyncClient
# 타입 힌트를 위해 비동기 세션을 임포트합니다.
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.usr.models import User as UsrUser
from app.core.security import get_password_hash

# conftest.py에서 정의된 픽스처들을 Pytest가 자동으로 감지하여 사용할 수 있습니다.


@pytest.mark.asyncio
async def test_login_for_access_token_success(  # Flake8: E128, E501
    client: AsyncClient,  # Flake8: E128
    test_user: UsrUser,  # Flake8: E128
):
    """
    올바른 사용자명과 비밀번호로 로그인하여 액세스 토큰을 성공적으로 발급받는지 테스트합니다.
    """
    login_data = {  # Flake8: E121
        "username": test_user.username,  # Flake8: E121
        "password": "testpassword123"  # conftest.py에서 test_user 생성 시 사용한 비밀번호  # Flake8: E121
    }

    response = await client.post("/api/v1/usr/auth/token",  # Flake8: E121, E501
                                 data=login_data)  # Flake8: E121

    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_for_access_token_wrong_password(  # Flake8: E128, E501
    client: AsyncClient,  # Flake8: E128
    test_user: UsrUser,  # Flake8: E128
):
    """
    잘못된 비밀번호로 로그인 시도 시 401 UNAUTHORIZED 응답을 받는지 테스트합니다.
    """
    response = await client.post(  # Flake8: E121
        "/api/v1/usr/auth/token",  # Flake8: E121
        data={  # Flake8: E121
            "username": test_user.username,  # Flake8: E121
            "password": "wrong_password"  # Flake8: E121
        },  # Flake8: E121
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_for_access_token_nonexistent_user(  # Flake8: E128, E501
    client: AsyncClient,  # Flake8: E128
):
    """
    존재하지 않는 사용자명으로 로그인 시도 시 401 UNAUTHORIZED 응답을 받는지 테스트합니다.
    """
    response = await client.post(  # Flake8: E121
        "/api/v1/usr/auth/token",  # Flake8: E121
        data={  # Flake8: E121
            "username": "nonexistent_user",  # Flake8: E121
            "password": "any_password"  # Flake8: E121
        },  # Flake8: E121
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_for_access_token_inactive_user(  # Flake8: E128, E501
    client: AsyncClient,  # Flake8: E128
    db_session: AsyncSession,  # Flake8: E128
):
    """
    비활성 상태의 사용자로 로그인 시도 시 400 BAD REQUEST 응답을 받는지 테스트합니다.
    """
    # 비활성 사용자 생성
    hashed_password = get_password_hash("testpassword123")
    inactive_user = UsrUser(  # Flake8: E121
        username="inactiveuser",  # Flake8: E121
        email="inactive@example.com",  # Flake8: E121
        password_hash=hashed_password,  # Flake8: E121
        is_active=False  # Flake8: E121
    )
    db_session.add(inactive_user)
    await db_session.commit()

    response = await client.post(  # Flake8: E121
        "/api/v1/usr/auth/token",  # Flake8: E121
        data={  # Flake8: E121
            "username": inactive_user.username,  # Flake8: E121
            "password": "testpassword123"  # Flake8: E121
        },  # Flake8: E121
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_read_users_me_success(  # Flake8: E128, E501
    authorized_client: AsyncClient,  # Flake8: E128
    test_user: UsrUser  # Flake8: E128
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
    response = await client.get(  # Flake8: E121
        "/api/v1/usr/auth/me",  # Flake8: E121
        headers={"Authorization": f"Bearer {invalid_token}"}  # Flake8: E121
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
