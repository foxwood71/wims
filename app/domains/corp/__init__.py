# app/domains/corp/__init__.py

"""
FastAPI 애플리케이션의 'corp' 도메인 패키지입니다.

이 패키지는 PostgreSQL의 'corp' 스키마에 해당하는 데이터 모델과
관련된 비즈니스 로직 및 API 엔드포인트를 포함합니다.

'corp' 도메인은 시스템을 운영하는 단일 회사에 대한 정보,
즉 회사명, 로고, 주소, 대표 연락처 등 고유한 프로필 데이터를
관리하는 역할을 합니다. 이 테이블은 항상 하나의 행만 유지합니다.

주요 서브모듈:
- `models.py`: 'corp' 스키마의 테이블에 매핑되는 SQLModel 정의.
- `schemas.py`: 'corp' 스키마 데이터에 대한 Pydantic 모델 (요청 및 응답 유효성 검사).
- `crud.py`: 'corp' 스키마 테이블에 대한 CRUD (Create, Read, Update, Delete) 로직. (선택적)
- `router.py`: 'corp' 스키마 데이터에 접근하기 위한 FastAPI API 엔드포인트 정의.

이 `__init__.py` 파일은 'corp' 패키지를 Python 패키지로 인식하게 하며,
패키지의 목적을 문서화합니다.
"""

# __flake8: noqa -> 해당 파일 전체
# from . import models, schemas, router  # noqa: F401

# 패키지 메타데이터
__title__ = "WIMS Corporation Info Domain"
__description__ = "Manages the operating company's information (name, logo, contact details)."
__version__ = "0.1.0"
__all__ = ["models", "schemas", "router", "crud"]

# (선택 사항) 이 패키지에서 다른 패키지로 공통 모델이나 스키마를 노출할 수 있습니다.
# from .models import CompanyInfo
# from .schemas import CompanyInfoRead

# 하지만, 일반적으로 명시적인 임포트 (예: from app.domains.corp.models import CompanyInfo)가 권장됩니다.
