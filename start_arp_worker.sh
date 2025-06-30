#!/bin/bash

# ARQ 워커 실행용 스크립트
#
# 사용법:
#   bash scripts/start_arq_worker.sh           # 포그라운드에서 실행 (터미널에 로그 출력)
#   nohup bash scripts/start_arq_worker.sh &   # 백그라운드에서 실행 (nohup.out 파일에 로그 출력)
#   bash scripts/start_arq_worker.sh > logs/arq_worker.log 2>&1 & # 백그라운드에서 실행 및 특정 로그 파일에 출력

# 1. 환경 변수 로드 (선택 사항: .env 파일 사용 시)
#    FastAPI 애플리케이션의 .env 파일과 동일한 환경을 사용하는 것이 좋습니다.
#    프로젝트 루트에 .env 파일이 있다면 dotenv를 사용하여 로드할 수 있습니다.
#    (이 스크립트가 실행되는 쉘에 이미 환경 변수가 설정되어 있다면 이 부분은 필요 없습니다.)
# if [ -f ".env" ]; then
#   export $(cat .env | xargs)
# fi

# 2. 가상 환경 활성화 (선택 사항: 가상 환경을 사용하는 경우)
#    프로젝트의 가상 환경 경로를 여기에 지정하세요.
#    예: .venv 또는 venv
VIRTUAL_ENV_PATH=".py312" # 또는 "venv" 등으로 변경

if [ -d "${VIRTUAL_ENV_PATH}" ]; then
  echo "가상 환경 활성화: ${VIRTUAL_ENV_PATH}"
  source "${VIRTUAL_ENV_PATH}/bin/activate"
else
  echo "경고: 가상 환경 '${VIRTUAL_ENV_PATH}'를 찾을 수 없습니다."
  echo "전역 Python 환경에서 실행을 시도합니다. 이는 권장되지 않습니다."
fi

# 3. ARQ 워커 실행
echo "ARQ 워커를 시작합니다..."
echo "설정 파일: app.main.ArqWorkerSettings"

# arq 명령어를 사용하여 워커 실행.
# -l info: 정보 레벨 로그 출력
# --poll-delay 0.5: Redis에서 새 작업을 폴링하는 간격 (초), 기본값은 0.5
# --keep-empty: 큐에 작업이 없어도 워커를 계속 실행합니다.
arq app.main.ArqWorkerSettings -l info --poll-delay 0.5

echo "ARQ 워커 실행이 종료되었습니다."

# 가상 환경 비활성화 (스크립트 종료 시 자동 비활성화되거나 수동으로 실행 가능)
# deactivate