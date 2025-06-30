#!/bin/bash

# 1. .env 파일 존재 여부 확인 (개발 환경에서 필수)
if [ ! -f ".env" ]; then
    echo "경고: '.env' 파일이 존재하지 않습니다."
    echo "애플리케이션이 올바르게 실행되지 않을 수 있습니다. '.env' 파일을 생성하고 필요한 환경 변수를 설정하세요."
    # 개발 환경에서는 경고 후 진행하고, 프로덕션 환경에서는 exit 1 로 강제 종료할 수 있습니다.
fi

# 2. FastAPI 애플리케이션 실행
echo "FastAPI 애플리케이션을 Uvicorn으로 실행합니다."
echo "접속 주소: http://localhost:8000 (또는 WSL2의 경우 내부 IP)"

# uvicorn 실행 (기본 호스트: 0.0.0.0, 포트: 8000, 개발 중 자동 재시작: --reload)
# 운영 환경에서는 --reload 옵션을 제거해야 합니다.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo "FastAPI 애플리케이션 실행이 종료되었습니다."