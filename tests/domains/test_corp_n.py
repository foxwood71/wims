# tests/domains/test_corp_n.py

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from io import BytesIO

from app.domains.corp import models as corp_models

#  API 경로를 정확하게 수정합니다.
API_PREFIX = "/api/v1/corp"


@pytest.mark.asyncio
async def test_get_company_info_initially(client: AsyncClient, db_session: AsyncSession):
    """
    최초로 회사 정보를 조회할 때 기본값이 생성되는지 테스트합니다.
    """
    response = await client.get(f"{API_PREFIX}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "기본 회사명"
    assert data["id"] == 1
    assert data["logo"] is None  # 최초에는 로고가 없음


@pytest.mark.asyncio
async def test_update_company_info(authorized_client: AsyncClient, db_session: AsyncSession):
    """
    회사 정보를 성공적으로 수정하는지 테스트합니다.
    """
    #  먼저 정보 생성을 위해 한 번 호출
    await authorized_client.get(f"{API_PREFIX}/")

    update_data = {
        "name": "새로운 주식회사",
        "ceo_name": "홍길동",
    }
    response = await authorized_client.patch(f"{API_PREFIX}/", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "새로운 주식회사"
    assert data["ceo_name"] == "홍길동"

    db_info = await db_session.get(corp_models.CompanyInfo, 1)
    assert db_info.name == "새로운 주식회사"


@pytest.mark.asyncio
async def test_upload_company_logo(
    authorized_client: AsyncClient, db_session: AsyncSession
):
    """
    [신규] 회사 로고를 성공적으로 업로드하고, 정보가 갱신되는지 테스트합니다.
    """
    #  1. Given: 먼저 GET 요청으로 회사 정보를 생성/조회합니다.
    await authorized_client.get(f"{API_PREFIX}/")
        response = await client.get(f"{API_PREFIX}/")
    response = await client.get(f"{API_PREFIX}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "기본 회사명"
    assert data["id"] == 1
    assert data["logo"] is None  # 최초에는 로고가 없음

    #  2. Given: 테스트용 이미지 파일을 준비합니다.
    file_content = b"fake image data"
    files = {
        "upload_file": (
            "test_logo.png",
            BytesIO(file_content),
            "image/png",
        )
    }

    #  3. When: 로고 업로드 API를 호출합니다.
    response = await authorized_client.post(f"{API_PREFIX}/logo", files=files)

    #  4. Then: 응답을 검증합니다.
    assert response.status_code == 200
    data = response.json()
    assert "logo" in data
    assert data["logo"] is not None
    assert data["logo"]["name"] == "test_logo.png"
    assert "url" in data["logo"]
    assert data["logo_file_id"] == data["logo"]["id"]

    #  DB에서 직접 확인하여 최종적으로 검증합니다.
    company_info = await db_session.get(corp_models.CompanyInfo, 1)
    assert company_info.logo_file_id == data["logo"]["id"]
