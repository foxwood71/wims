# flake8: noqa
"""
'rpt' (보고서) 도메인 관련 API 엔드포인트에 대한 통합 테스트 모듈입니다.
보고서 양식의 CRUD, 권한, 유효성 검사 등을 테스트합니다.
"""
import pytest
import pytest_asyncio  # @pytest.mark.asyncio 데코레이터 및 비동기 픽스처 사용 시 필요
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from io import BytesIO

from app.domains.shared import models as shared_models

#  API 경로 정의
REPORT_API_PREFIX = "/api/v1/rpt"
UPLOAD_API_PREFIX = "/api/v1/shared/resources"


@pytest_asyncio.fixture
async def test_resource_category_for_rpt(db_session: AsyncSession) -> shared_models.ResourceCategory:
    """테스트용 리소스 카테고리를 생성하는 픽스처"""
    category = shared_models.ResourceCategory(name="테스트 카테고리", description="테스트용입니다.")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture(scope="function")
async def test_report_template_file(
    admin_client: AsyncClient,
    test_resource_category_for_rpt: shared_models.ResourceCategory
) -> int:
    """
    테스트에 사용할 보고서 양식 파일을 미리 업로드하고 파일 ID를 반환하는 픽스처입니다.
    """
    file_content = b"this is a dummy excel file content"
    files = {
        "file": (
            "fixture_report.xlsx",
            BytesIO(file_content),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    data = {"category_id": test_resource_category_for_rpt.id, "description": "테스트 업로드"}
    upload_response = await admin_client.post(UPLOAD_API_PREFIX, files=files, data=data)
    assert upload_response.status_code == 201
    return upload_response.json()["id"]


@pytest.mark.asyncio
async def test_create_and_read_report_form(
    admin_client: AsyncClient, test_report_template_file: int
):
    """
    [성공] 관리자가 파일로 보고서 양식을 생성하고 조회하는 전체 과정을 테스트합니다.
    """
    #  Given: 보고서 양식 데이터를 준비합니다.
    form_data = {
        "name": "월간 수질 검사 보고서",
        "description": "매월 정기적으로 작성되는 수질 검사 결과 보고서 양식입니다.",
        "template_file_id": test_report_template_file,
    }

    #  When: 보고서 양식을 생성합니다.
    create_response = await admin_client.post(f"{REPORT_API_PREFIX}/", json=form_data)
    assert create_response.status_code == 201, "보고서 양식 생성에 실패했습니다."
    created_form = create_response.json()
    created_form_id = created_form["id"]

    #  Then: 생성된 보고서 양식을 ID로 조회하여 검증합니다.
    get_response = await admin_client.get(f"{REPORT_API_PREFIX}/{created_form_id}")
    assert get_response.status_code == 200, "생성된 보고서 양식 조회에 실패했습니다."
    read_form = get_response.json()

    #  Then: 최종적으로 데이터가 올바른지 확인합니다.
    assert read_form["name"] == form_data["name"]
    assert read_form["template_file_id"] == test_report_template_file


@pytest.mark.asyncio
async def test_update_report_form(
    admin_client: AsyncClient, test_report_template_file: int
):
    """
    [성공/신규] 보고서 양식의 정보를 성공적으로 수정하는지 테스트합니다.
    """
    #  Given: 수정할 보고서 양식을 미리 생성합니다.
    initial_data = {"name": "수정 전 이름", "template_file_id": test_report_template_file}
    create_res = await admin_client.post(f"{REPORT_API_PREFIX}/", json=initial_data)
    form_id = create_res.json()["id"]

    #  When: 양식의 이름과 활성 상태를 수정합니다.
    update_data = {"name": "수정된 보고서 양식", "description": "설명이 추가되었습니다."}
    update_res = await admin_client.patch(
        f"{REPORT_API_PREFIX}/{form_id}", json=update_data
    )
    assert update_res.status_code == 200

    #  Then: 수정된 정보를 다시 조회하여 확인합니다.
    get_res = await admin_client.get(f"{REPORT_API_PREFIX}/{form_id}")
    updated_form = get_res.json()
    assert updated_form["name"] == "수정된 보고서 양식"
    assert updated_form["description"] == "설명이 추가되었습니다."


@pytest.mark.asyncio
async def test_delete_report_form(
    admin_client: AsyncClient, test_report_template_file: int
):
    """
    [성공/신규] 보고서 양식을 성공적으로 삭제하는지 테스트합니다.
    """
    #  Given: 삭제할 보고서 양식을 생성합니다.
    form_data = {"name": "삭제될 양식", "template_file_id": test_report_template_file}
    create_res = await admin_client.post(f"{REPORT_API_PREFIX}/", json=form_data)
    created_form = create_res.json()
    created_form_id = created_form["id"]

    #  When: 양식을 삭제합니다.
    delete_res = await admin_client.delete(f"{REPORT_API_PREFIX}/{created_form_id}")
    assert delete_res.status_code == 204  #  No Content

    #  Then: 삭제된 양식을 다시 조회하면 404 오류가 발생해야 합니다.
    get_res = await admin_client.get(f"{REPORT_API_PREFIX}/{created_form_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_list_report_forms(admin_client: AsyncClient, test_report_template_file: int):
    """
    [성공/신규] 보고서 양식 목록을 조회하고 필터링하는 기능을 테스트합니다.
    """
    #  Given: 활성/비활성 상태의 양식을 여러 개 생성합니다.
    await admin_client.post(
        f"{REPORT_API_PREFIX}/",
        json={"name": "활성 양식 1", "template_file_id": test_report_template_file, "is_active": True},
    )
    await admin_client.post(
        f"{REPORT_API_PREFIX}/",
        json={"name": "비활성 양식", "template_file_id": test_report_template_file, "is_active": False},
    )

    #  When: is_active=true 필터로 목록을 조회합니다.
    response = await admin_client.get(f"{REPORT_API_PREFIX}/?is_active=true")
    assert response.status_code == 200
    active_forms = response.json()

    #  Then: 활성 상태인 양식만 조회되어야 합니다.
    assert len(active_forms) >= 1
    assert all(form["is_active"] for form in active_forms)
    assert not any(form["name"] == "비활성 양식" for form in active_forms)


@pytest.mark.asyncio
async def test_create_report_form_permission_denied(
    authorized_client: AsyncClient, test_report_template_file: int
):
    """
    [실패/권한] 일반 사용자가 보고서 양식 생성을 시도할 때 403 Forbidden 오류를 받는지 테스트합니다.
    """
    #  Given: 일반 사용자로 생성할 데이터를 준비합니다.
    form_data = {"name": "권한 없는 생성 시도", "template_file_id": test_report_template_file}

    #  When & Then: 생성 요청 시 403 오류가 발생해야 합니다.
    response = await authorized_client.post(f"{REPORT_API_PREFIX}/", json=form_data)
    print(f"DEBUG IN TEST: Response status code: {response.status_code}, Response text: {response.text}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_report_form_validation_error(admin_client: AsyncClient):
    """
    [실패/유효성] 필수 필드(name, template_file_id) 누락 시 422 Unprocessable Entity 오류를 받는지 테스트합니다.
    """
    #  When & Then: name이 누락된 요청
    response1 = await admin_client.post(
        f"{REPORT_API_PREFIX}/", json={"template_file_id": 999}
    )
    assert response1.status_code == 422

    #  When & Then: form_file_id가 누락된 요청
    response2 = await admin_client.post(
        f"{REPORT_API_PREFIX}/", json={"name": "파일 없는 양식"}
    )
    assert response2.status_code == 422


@pytest.mark.asyncio
async def test_create_report_form_with_nonexistent_file(admin_client: AsyncClient):
    """
    [실패/무결성] 존재하지 않는 파일 ID로 양식 생성 시 404 Not Found 오류를 받는지 테스트합니다.
    """
    non_existent_file_id = 99999
    form_data = {"name": "유령 파일 양식", "template_file_id": non_existent_file_id}
    response = await admin_client.post(f"{REPORT_API_PREFIX}/", json=form_data)
    assert response.status_code == 404