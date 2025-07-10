# tests/test_rpt.py

import pytest
from httpx import AsyncClient
from io import BytesIO

API_PREFIX = "/api/v1/rpt"
# 파일 업로드 API 경로
UPLOAD_API_PREFIX = "/api/v1/shared"


@pytest.mark.asyncio
async def test_create_and_read_report_form(client: AsyncClient):
    """
    파일 업로드 후, 해당 파일로 보고서 양식을 생성하고 조회하는 전체 과정을 테스트합니다.
    """
    # Given 1: 가짜 엑셀 파일을 업로드합니다.
    file_content = b"this is a dummy excel file content"
    files = {
        "upload_file": (
            "test_report.xlsx",
            BytesIO(file_content),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    upload_response = await client.post(f"{UPLOAD_API_PREFIX}/files/upload", files=files)
    assert upload_response.status_code == 201
    uploaded_file_data = upload_response.json()
    template_file_id = uploaded_file_data["id"]

    # Given 2: 생성할 보고서 양식 정보를 준비합니다.
    form_data = {
        "name": "월간 운영 보고서",
        "description": "매월 운영 실적을 정리하는 보고서",
        "template_file_id": template_file_id,
    }

    # When: 보고서 양식 생성을 요청합니다.
    create_response = await client.post(f"{API_PREFIX}/", json=form_data)
    assert create_response.status_code == 201
    created_data = create_response.json()
    assert created_data["name"] == form_data["name"]
    form_id = created_data["id"]

    # When: 생성된 보고서 양식의 상세 정보를 조회합니다.
    read_response = await client.get(f"{API_PREFIX}/{form_id}")
    assert read_response.status_code == 200
    read_data = read_response.json()

    # Then: 업로드했던 파일 정보가 포함되어 있어야 합니다.
    assert read_data["name"] == form_data["name"]
    assert "template_file" in read_data
    assert read_data["template_file"]["id"] == template_file_id
    assert "test_report.xlsx" in read_data["template_file"]["name"]
