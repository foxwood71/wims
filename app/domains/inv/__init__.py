# app/domains/inv/__init__.py

"""
FastAPI 애플리케이션의 'inv' 도메인 패키지입니다.

이 패키지는 PostgreSQL의 'inv' 스키마에 해당하는 데이터 모델과
관련된 비즈니스 로직 및 API 엔드포인트를 포함합니다.

'inv' 도메인은 자재 카테고리(MaterialCategory), 자재 스펙 정의(MaterialSpecDefinition),
자재 품목(Material), 자재 스펙(MaterialSpec), 자재 배치(MaterialBatch),
그리고 자재 거래 이력(MaterialTransaction)과 같은 자재 및 재고 관리 데이터를
관리하는 역할을 합니다. 특히, FIFO(선입선출) 방식의 재고 차감 로직을 포함합니다.

주요 서브모듈:
- `models.py`: 'inv' 스키마의 테이블에 매핑되는 SQLModel 정의.
- `schemas.py`: 'inv' 스키마 데이터에 대한 Pydantic 모델 (요청 및 응답 유효성 검사).
- `crud.py`: 'inv' 스키마 테이블에 대한 비동기 CRUD (Create, Read, Update, Delete) 로직 및 재고 차감 로직.
- `routers.py`: 'inv' 스키마 데이터에 접근하기 위한 FastAPI API 엔드포인트 정의.

이 `__init__.py` 파일은 'inv' 패키지를 Python 패키지로 인식하게 하며,
패키지의 목적을 문서화합니다.
"""

# from . import models, schemas, router, crud  # noqa: F401

# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS Inventory Domain"
__description__ = "Manages material and inventory information, including FIFO stock deduction."
__version__ = "0.1.0"  # inv 도메인 패키지의 버전
__all__ = []  # 'from app.domains.inv import *' 시 내보낼 이름 목록. 일반적으로 비워둡니다.

# (선택 사항) 이 패키지에서 다른 패키지로 공통 모델이나 스키마를 노출할 수 있습니다.
# 예를 들어, Material 모델이 다른 도메인에서 자주 참조된다면 여기서 노출할 수 있습니다.
# from .models import Material, MaterialCategory, MaterialBatch, MaterialTransaction
# from .schemas import MaterialResponse, MaterialBatchResponse

# 하지만, 일반적으로 명시적인 임포트 (예: from app.domains.inv.models import Material)가 권장됩니다.
