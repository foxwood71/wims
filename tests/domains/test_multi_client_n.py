# tests/domains/test_client_n.py

"""
'usr' 도메인 (사용자 및 부서 관리) 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.
"""

from httpx import AsyncClient
from typing import AsyncGenerator, Callable

from app.domains.usr import models as usr_models
# from app.core.security import verify_password


async def test_multi_client_authentication(
    authorized_client_factory: Callable[..., AsyncGenerator[AsyncClient, None]],
    test_admin_user: usr_models.User,
    test_lab_manager: usr_models.User,
    test_lab_analyst: usr_models.User,
    test_facility_manager: usr_models.User,
    test_inventory_manager: usr_models.User,
    test_user: usr_models.User
):

    # 1. 관리자 클라이언트로 테스트
    async with authorized_client_factory(user=test_admin_user, password="sysadmpass123") as admin_client:
        print("Testing with Admin Client...")
        response = await admin_client.get("/api/v1/usr/auth/me")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["login_id"] == test_admin_user.login_id
        assert response_data["id"] == test_admin_user.id
        assert "password_hash" not in response_data
        print()

    # 2. 실험실 관리자 클라이언트로 테스트
    async with authorized_client_factory(user=test_lab_manager, password="labmgrpass123") as lab_manager_client:
        print("Testing with lab manager Client...")
        response = await lab_manager_client.get("/api/v1/usr/auth/me")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["login_id"] == test_lab_manager.login_id
        assert response_data["id"] == test_lab_manager.id
        assert "password_hash" not in response_data

    # 3. 실험실 분석자 클라이언트로 테스트
    async with authorized_client_factory(user=test_lab_analyst, password="labanalystpass123") as lab_analyst_client:
        print("Testing with lab analyst Client...")
        response = await lab_analyst_client.get("/api/v1/usr/auth/me")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["login_id"] == test_lab_analyst.login_id
        assert response_data["id"] == test_lab_analyst.id
        assert "password_hash" not in response_data
        print()

    # 4. 설비 관리자 클라이언트로 테스트
    async with authorized_client_factory(user=test_facility_manager, password="fmspass123") as facility_manager_client:
        print("Testing with facility manager Client...")
        response = await facility_manager_client.get("/api/v1/usr/auth/me")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["login_id"] == test_facility_manager.login_id
        assert response_data["id"] == test_facility_manager.id
        assert "password_hash" not in response_data

    # 5. 자재 관리자 클라이언트로 테스트
    async with authorized_client_factory(user=test_inventory_manager, password="invpass123") as inventory_manager_client:
        print("Testing with inventory manager Client...")
        response = await inventory_manager_client.get("/api/v1/usr/auth/me")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["login_id"] == test_inventory_manager.login_id
        assert response_data["id"] == test_inventory_manager.id
        assert "password_hash" not in response_data

    # 6. 일반 사용자 클라이언트로 테스트
    async with authorized_client_factory(user=test_user, password="testpass123") as user_client:
        print("Testing with Normal User Client...")
        response = await user_client.get("/api/v1/usr/auth/me")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["login_id"] == test_user.login_id
        assert response_data["id"] == test_user.id
        assert "password_hash" not in response_data
