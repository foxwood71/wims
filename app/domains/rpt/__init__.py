# app/domains/rpt/__init__.py

"""
FastAPI 애플리케이션의 'rpt' (Report) 도메인 패키지입니다.

이 패키지는 보고서 양식(Report Form)의 메타데이터를 관리합니다.
실제 엑셀 템플릿 파일 자체는 'shared' 도메인을 통해 업로드 및 관리되며,
'rpt' 도메인은 해당 파일의 참조 ID를 포함하여 보고서의 이름, 설명 등의 정보를 저장합니다.

이를 통해 보고서의 종류와 실제 파일 템플릿을 분리하여 유연하게 관리할 수 있습니다.

주요 서브모듈:
- `models.py`: 'rpt' 스키마의 테이블에 매핑되는 SQLModel 정의.
- `schemas.py`: 'rpt' 스키마 데이터에 대한 Pydantic 모델 (요청/응답 유효성 검사).
- `crud.py`: 'rpt' 스키마 테이블에 대한 CRUD 로직.
- `router.py`: 'rpt' 스키마 데이터에 접근하기 위한 FastAPI API 엔드포인트 정의.
"""


from . import models, schemas, router, crud  # noqa: F401

# 패키지 메타데이터
__title__ = "WIMS Report Domain"
__description__ = "Manages report form metadata, linking to actual template files in the shared domain."
__version__ = "0.1.0"
__all__ = ["models", "schemas", "router", "crud"]
