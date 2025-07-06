# tests/test_corp.py

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.domains.corp.models import CompanyInfo

API_PREFIX = "/api/v1/corp/company-info"


def test_get_company_info_initially(client: TestClient):
    """
    최초로 회사 정보를 조회할 때 기본값이 생성되는지 테스트합니다.
    """
    #  When: 회사 정보 조회를 요청하면
    response = client.get(f"{API_PREFIX}/")
    data = response.json()

    #  Then: 정상 응답(200)을 받고, 기본 회사명이 설정되어 있어야 합니다.
    assert response.status_code == 200
    assert data["name"] == "기본 회사명"
    assert data["id"] == 1


def test_update_company_info(client: TestClient, db: Session):
    """
    회사 정보를 성공적으로 수정하는지 테스트합니다.
    """
    #  Given: 수정할 새로운 회사 정보를 준비합니다.
    update_data = {
        "name": "새로운 주식회사",
        "ceo_name": "홍길동",
        "contact_email": "test@newcorp.com",
        "address": "서울시 강남구 테헤란로",
    }

    #  When: 회사 정보 수정을 요청하면
    response = client.patch(f"{API_PREFIX}/", json=update_data)
    data = response.json()

    #  Then: 정상 응답(200)을 받고, 정보가 올바르게 수정되어야 합니다.
    assert response.status_code == 200
    assert data["name"] == "새로운 주식회사"
    assert data["ceo_name"] == "홍길동"
    assert data["contact_email"] == "test@newcorp.com"
    assert data["address"] == "서울시 강남구 테헤란로"

    #  And: 데이터베이스에도 실제 반영되었는지 확인합니다.
    db_info = db.get(CompanyInfo, 1)
    assert db_info.name == "새로운 주식회사"


def test_update_company_info_partially(client: TestClient, db: Session):
    """
    회사 정보의 일부만 성공적으로 수정하는지 테스트합니다.
    """
    #  Given: 기존 회사 정보를 생성하고, 일부만 수정할 데이터를 준비합니다.
    client.get(f"{API_PREFIX}/")  # Ensure initial data exists
    partial_update_data = {"logo_url": "https://new.logo/image.png"}

    #  When: 회사 정보 부분 수정을 요청하면
    response = client.patch(f"{API_PREFIX}/", json=partial_update_data)
    data = response.json()

    #  Then: 정상 응답(200)을 받고, 로고 URL만 수정되어야 합니다.
    assert response.status_code == 200
    assert data["logo_url"] == "https://new.logo/image.png"

    #  And: 기존 이름은 그대로 유지되어야 합니다.
    assert data["name"] == "기본 회사명"


def test_update_company_info_with_empty_data(client: TestClient):
    """
    수정할 데이터 없이 요청했을 때 400 에러가 발생하는지 테스트합니다.
    """
    #  When: 빈 JSON으로 수정을 요청하면
    response = client.patch(f"{API_PREFIX}/", json={})

    #  Then: 400 Bad Request 응답을 받아야 합니다.
    assert response.status_code == 400
