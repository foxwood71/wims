# tests/test_main.py

"""
FastAPI 애플리케이션의 메인 엔드포인트에 대한 통합 테스트를 정의하는 모듈입니다.

- 애플리케이션의 루트 경로 (`/`) 응답을 테스트합니다.
- 데이터베이스 연결 헬스 체크 엔드포인트 (`/health-check`)를 테스트합니다.
"""

import pytest
from fastapi.testclient import TestClient

# conftest.py에서 정의된 'client' 픽스처를 Pytest가 자동으로 감지하여 사용할 수 있습니다.
# 따라서 여기서 TestClient를 직접 임포트할 필요는 없지만, 타입 힌팅을 위해 명시할 수 있습니다.


def test_read_root(client: TestClient):
    """
    루트 엔드포인트 (`GET /`)가 올바르게 응답하는지 테스트합니다.
    - 응답 상태 코드가 200 OK인지 확인합니다.
    - 응답 JSON에 올바른 환영 메시지가 포함되어 있는지 확인합니다.
    """
    print("\n--- Running test_read_root ---")
    response = client.get("/")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to WIMS API. Visit /docs for interactive API documentation."}
    print("test_read_root passed.")


@pytest.mark.asyncio # 비동기 픽스처를 사용하는 테스트 함수에 필요 (pytest-asyncio)
async def test_health_check(client: TestClient):
    """
    헬스 체크 엔드포인트 (`GET /health-check`)가 데이터베이스 연결 상태를 올바르게 반환하는지 테스트합니다.
    - 응답 상태 코드가 200 OK인지 확인합니다.
    - 응답 JSON에 "status": "ok" 및 "database_connection": "successful" 메시지가 포함되어 있는지 확인합니다.
    """
    print("\n--- Running test_health_check ---")
    response = client.get("/health-check")
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database_connection": "successful"}
    print("test_health_check passed.")

# 추가적인 메인 앱 관련 테스트는 여기에 추가할 수 있습니다.
# 예를 들어, CORS 설정이 제대로 작동하는지, 전역 미들웨어 등이 테스트될 수 있습니다.