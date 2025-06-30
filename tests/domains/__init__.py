# tests/domains/__init__.py

"""
FastAPI 애플리케이션의 도메인별 테스트 스위트 패키지입니다.

이 패키지는 애플리케이션의 핵심 비즈니스 도메인(예: shared, usr, loc 등)별로
관련된 모든 테스트 파일들을 그룹화합니다.
각 도메인 서브패키지 내에는 해당 도메인의 모델, CRUD, 라우터, 서비스 등의
기능을 검증하는 테스트 모듈들이 포함됩니다.

주요 하위 디렉토리 (각 도메인별 테스트 서브패키지):
- `shared/`: 'shared' 도메인 (app 스키마)에 대한 테스트.
- `usr/`: 'usr' 도메인 (사용자 및 부서 관리)에 대한 테스트.
- `loc/`: 'loc' 도메인 (위치 정보)에 대한 테스트.
- `ven/`: 'ven' 도메인 (공급업체 관리)에 대한 테스트.
- `fms/`: 'fms' 도메인 (설비 관리 시스템)에 대한 테스트.
- `inv/`: 'inv' 도메인 (자재 및 재고 관리)에 대한 테스트.
- `lims/`: 'lims' 도메인 (실험실 정보 관리 시스템 및 QA/QC)에 대한 테스트.
- `ops/`: 'ops' 도메인 (운영 데이터 관리)에 대한 테스트.

이 `__init__.py` 파일은 'domains' 디렉토리를 Python 패키지로 인식하게 하여,
`pytest`와 같은 테스트 러너가 하위 도메인별 테스트 모듈들을 올바르게 발견하고
실행할 수 있도록 합니다.
대부분의 경우, 이 파일은 비어 있거나 간단한 문서화만 포함합니다.
"""

# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS Domain Tests"
__description__ = "Categorized tests for each business domain in WIMS FastAPI application."
__version__ = "0.1.0" # 도메인 테스트 패키지의 내부 버전
__all__ = [] # 이 패키지에서 'from tests.domains import *' 시 내보낼 이름 목록.