FastApi와 SqlModel, Postgresql로 만든 하수처리장 정보관리 시스템이야
Domain별로 pytest를 이용한 테스트를 실시할 예정인대 첨부 문서를 참고해서
다음 질문부터 답해줘

FastApi와 SqlModel, Postgresql로 만든 하수처리장 정보관리 시스템이야
첨부된 도메인 테스트는 모드 성공했는데 첨부 문서를 참고해서 누락되었거나 보완할 테스트 항목이 있으면
테스트 파일을 수정해줘

수정할 파일의 전체 소스를 보여줘

정규식
at least two spaces before inline comment (\S)(\s)(#) $1  $3
expected 2 blank lines, found 1             ^(?!\s*\n)(def\s+\w+\s*\(?.*\)?:|class\s+\w+\s*\(?.*\)?:|@router.*)        \n$1
blank line contains whitespace              ^[ \t]+$
inline comment should start with '# ' #\s\* #
trailing whitespace \s+$

# python debugging

import pdb; pdb.set_trace() - 디버거 대상 윗줄에 삽입
breakpoint() - python 3.7+ 사용가능
n (next): 다음 줄로 이동 (함수 내부로 들어가지 않음)
s (step): 다음 줄로 이동 (함수 내부로 들어감)
c (continue): 다음 중단점까지 또는 프로그램 끝까지 실행
q (quit): 디버거 종료 및 프로그램 종료
p <variable> (print): 변수 값 출력 (예: p my_variable)
l (list): 현재 코드 주변 라인 표시
w (where): 현재 스택 트레이스 표시
h (help): 도움말 표시
h <command>: 특정 명령어에 대한 도움말 (예: h p)

- python logging
  import logging

# 로거 인스턴스 생성: 파일의 최상단에 위치하여 모듈 전체에서 사용 가능하도록 합니다.

logger = logging.getLogger(**name**)
logger.error(f"IntegrityError during wastewater plant deletion: {e}") # e 변수 사용

# 데이터 베이스 마이그레이션

- 초기화
  migrations 디렉토리에서, alembic init versions 명령실행
  @ 비동기 처리를 위해 migrations/versions/env.py를 migrations/env.py로 대체
  . init: 새 프로젝트를 시작할 때 딱 한 번만 쓰는 환경 생성 명령어입니다. (현재 폴더를 중심으로 만듬.)
  . revision: 이미 만들어진 환경 안에서 새로운 마이그레이션 파일을 만드는 명령어입니다.

# 비어있는 폴더 생성

mkdir -p migrations/versions

# 이 폴더를 파이썬 패키지로 인식시키기 위해 **init**.py 파일 생성 (좋은 습관입니다)

touch migrations/versions/**init**.py

- 데이터 베이스 완전 초기화
  alembic downgrade base
  DROP TABLE alembic_version;
  rm migrations/versions/\*.py
  touch migrations/versions/**init**.py

- "설계도" 작성 **Python 모델 코드(SQLModel)**와 실제 데이터베이스의 테이블 상태를 비교
  alembic revision --autogenerate -m "Create initial tables"
  => @ versions 디렉토리에 1a2b3c4d_create_initial_tables.py류의 파일 신규 생성

- "설계도"(마이그레이션 스크립트)를 보고 실제 데이터베이스에 변경사항을 적용
  alembic upgrade head
  ```head`는 가장 최신 버전의 마이그레이션을 의미합니다. 이 명령어를 실행하면 데이터베이스에 접속하여 마이그레이션 스크립트에 정의된 `CREATE TABLE` 등의 SQL 구문이 실행됩니다.

- 갱신 시
  alembic revision --autogenerate -m "Add ON DELETE RESTRICT to fms.equipments.current_location_id"

# services 디렉토리 (서비스 계층):

역할: API 엔드포인트(라우터)로부터 요청을 받아, 애플리케이션의 핵심 비즈니스 로직을 수행합니다.
실행 시점: 사용자의 HTTP 요청이 들어왔을 때, 실시간으로 호출됩니다.
예시: "사용자 가입" 요청을 받으면, UserService가 데이터베이스에 사용자를 생성하고, 환영 이메일을 보내는 등의 작업을 처리합니다.
특징: 실행 중인 FastAPI 애플리케이션의 일부로 동작합니다.

# scripts 디렉토리 (스크립트):

역할: 데이터베이스 마이그레이션, 데이터 초기화, 주기적인 정리 작업 등 관리 및 유지보수를 위한 독립적인 스크립트를 보관합니다.
실행 시점: 사용자의 요청과 무관하게, 개발자가 필요할 때 직접 실행하거나 cron 같은 스케줄러를 통해 주기적으로 실행됩니다.
예시: cleanup_unused_images.py 처럼 "매일 새벽에 한 번씩 사용하지 않는 파일을 정리하는" 작업입니다.
특징: FastAPI 애플리케이션의 실행 여부와 관계없이 독립적으로 동작할 수 있습니다.

# tasks (ARQ Worker Bacgraound 작업)

ARQ 워커 실행:
프로젝트 루트 디렉터리에서 다음 명령어를 실행하여 ARQ 워커를 시작합니다.

Bash
arq app.main.ArqWorkerSettings

# 보완사항

wwst를 단순 center로 변경: WastewaterPlant를 Facility 오류 무한 발생중
역할 기반 접근 제어(RBAC): 사진관련 시설 및 자재 관련 사진은 소유자가 아니라도 변경이 가능해야 함. -> 완료
loc.facility.id -> loc.facility.id

material_spec_definitions에 정의된 속성이 변경(추가, 또는 삭제, 명칭변경) 된 경우 관련 material의 spec도반영되는지 확인해주고 기능이 없으면 생성해줘 생성시 추가 속성의 기본값은 nuill 이고 기본적으로 기타 속성을 추가하여 속성표에 없는 속성값을 임시로 기록 할수 있게 해줘

현재 inv 도메인의 crud.py에는 \_validate_specs라는 강력한 유효성 검사 로직이 있습니다. 이 로직은 자재 카테고리에 미리 정의된 스펙 키 외에는 specs에 추가할 수 없도록 막습니다.
따라서 '기타 속성'을 자유롭게 추가하는 대신, misc_notes와 같은 이름으로 '기타 특이사항'용 MaterialSpecDefinition을 하나 생성하고, 이 스펙을 필요한 자재 카테고리에 연결하여 사용하는 방식을 권장합니다.

equipment_spec_definitions에 정의된 속성이 변경(추가, 또는 삭제, 명칭변경) 된 경우 관련 equipment의 spec도반영되는지 확인해주고 기능이 없으면 생성해줘 생성시 추가 속성의 기본값은 nuill 이고 기본적으로 기타 속성을 추가하여 속성표에 없는 속성값을 임시로 기록 할수 있게 해줘

자재 파트에 있는 \_validate_specs라는 강력한 유효성 검사 로직을 적용해서 설비 카테고리에 미리 정의된 스펙 키 외에는 specs에 추가할 수 없도록 해줘

# HTTP 상태 코드

1. 성공 응답 (2xx)

   - 200 OK : 요청이 성공적으로 처리됨
   - 201 Created : 리소스 생성 완료 (예: POST 요청)
   - 202 Accepted : 요청 접수, 처리 결과는 비동기적으로 전달

2. 리다이렉트 (3xx)

   - 301 Moved Permanently : 영구적 URL 이동 (SEO에 영향)
   - 302 Found : 일시적 URL 이동 (로봇에 영향 없음)
   - 304 Not Modified : 캐시된 콘텐츠 사용 가능

3. 클라이언트 오류 (4xx)

   - 400 Bad Request : 요청이 잘못됨 (예: 유효하지 않은 URL)
   - 401 Unauthorized : 인증 필요
   - 404 Not Found : 요청한 리소스가 없음

4. 서버 오류 (5xx)

   - 500 Internal Server Error : 서버 내부 오류 (예: 코드 버그)
   - 503 Service Unavailable : 서버 과부하 또는 유지보수 중

5. 기타

   - 226 IM Used : HTTP 델타 인코딩 시 사용 (리소스 변경 반영)
   - 307 Temporary Redirect : 일시적 리다이렉트 (메소드 변경 불가)

# 테스트 오류

ERROR tests/domains/test_lims_n.py::TestWorksheetAndItems::test_create_worksheet_item_success
ERROR tests/domains/test_lims_n.py::TestWorksheetAndItems::test_soft_delete_worksheet_item
FAILED tests/domains/test_lims_n.py::test_soft_delete_parameter_success_admin
FAILED tests/domains/test_lims_n.py::test_create_test_request_with_auto_user_id
FAILED tests/domains/test_lims_n.py::test_create_sample_success
FAILED tests/domains/test_lims_n.py::test_create_aliquot_sample_success
FAILED tests/domains/test_lims_n.py::test_read_aliquot_samples_with_filter
FAILED tests/domains/test_lims_n.py::test_update_aliquot_sample_status_triggers_parent_update
FAILED tests/domains/test_lims_n.py::test_create_analysis_result_success_user
FAILED tests/domains/test_lims_n.py::test_crud_sample_container
FAILED tests/domains/test_lims_n.py::test_crud_weather_condition
