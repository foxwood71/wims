# tests/domains/test_corp_n.py

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from io import BytesIO

from app.domains.corp import models as corp_models

#  API 경로를 정확하게 수정합니다.
API_PREFIX = "/api/v1/corp"
#  범용 파일 업로드 API 경로 (가정)
FILES_API_PREFIX = "/api/v1/shared/files/upload"


@pytest.mark.asyncio
async def test_get_company_info_initially(authorized_client: AsyncClient, db_session: AsyncSession):
    """
    최초로 회사 정보를 조회할 때 기본값이 생성되는지 테스트합니다.
    """
    response = await authorized_client.get(f"{API_PREFIX}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "기본 회사명"
    assert data["id"] == 1
    assert data["logo"] is None  # 최초에는 로고가 없음


@pytest.mark.asyncio
async def test_update_company_info(admin_client: AsyncClient, db_session: AsyncSession):
    """
    회사 정보를 성공적으로 수정하는지 테스트합니다.
    """
    #  먼저 정보 생성을 위해 한 번 호출
    await admin_client.get(f"{API_PREFIX}/")

    update_data = {
        "name": "새로운 주식회사",
        "ceo_name": "홍길동",
    }
    response = await admin_client.patch(f"{API_PREFIX}/", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "새로운 주식회사"
    assert data["ceo_name"] == "홍길동"

    db_info = await db_session.get(corp_models.CompanyInfo, 1)
    assert db_info.name == "새로운 주식회사"


@pytest.mark.asyncio
async def test_update_company_logo_via_file_upload(
    admin_client: AsyncClient, db_session: AsyncSession
):
    """
    [개선된 로직] 파일을 업로드하고, 반환된 ID로 회사 로고를 갱신하는 과정을 테스트합니다.
    """
    #  1. Given: 먼저 회사 정보가 존재하는지 확인/생성합니다.
    await admin_client.get(f"{API_PREFIX}/")

    #  2. Given: 테스트용 이미지 파일을 범용 파일 업로드 API에 전송합니다.
    file_content = b"fake image data"
    files = {"upload_file": ("logo.png", BytesIO(file_content), "image/png")}

    #  [1단계: 파일 업로드]
    upload_response = await admin_client.post(FILES_API_PREFIX, files=files)
    assert upload_response.status_code == 201  # 파일 생성 성공

    uploaded_file_data = upload_response.json()
    logo_file_id = uploaded_file_data["id"]

    #  3. When: 위에서 받은 파일 ID를 사용하여 회사 정보를 갱신합니다.
    update_data = {"logo_file_id": logo_file_id}

    #  [2단계: 정보 갱신]
    update_response = await admin_client.patch(
        f"{API_PREFIX}/", json=update_data
    )

    #  4. Then: 최종 응답을 검증합니다.
    assert update_response.status_code == 200
    final_data = update_response.json()
    assert final_data["logo_file_id"] == logo_file_id

    #  5. Then: DB에서 직접 확인하여 최종적으로 검증합니다.
    company_info = await db_session.get(corp_models.CompanyInfo, 1)
    assert company_info.logo_file_id == logo_file_id
