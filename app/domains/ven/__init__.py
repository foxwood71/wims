# app/domains/ven/__init__.py

"""
FastAPI 애플리케이션의 'ven' 도메인 패키지입니다.

이 패키지는 PostgreSQL의 'ven' 스키마에 해당하는 데이터 모델과
관련된 비즈니스 로직 및 API 엔드포인트를 포함합니다.

'ven' 도메인은 공급업체(Vendor) 정보, 공급업체 카테고리(VendorCategory),
그리고 공급업체 담당자(VendorContact)와 같은 공급업체 관련 데이터를
관리하는 역할을 합니다. 또한, 공급업체와 카테고리 간의 다대다 연결도 처리합니다.

주요 서브모듈:
- `models.py`: 'ven' 스키마의 테이블에 매핑되는 SQLModel 정의.
- `schemas.py`: 'ven' 스키마 데이터에 대한 Pydantic 모델 (요청 및 응답 유효성 검사).
- `crud.py`: 'ven' 스키마 테이블에 대한 비동기 CRUD (Create, Read, Update, Delete) 로직.
- `routers.py`: 'ven' 스키마 데이터에 접근하기 위한 FastAPI API 엔드포인트 정의.

이 `__init__.py` 파일은 'ven' 패키지를 Python 패키지로 인식하게 하며,
패키지의 목적을 문서화합니다.
"""


# from . import models, schemas, router, crud  # noqa: F401
# 패키지 메타데이터 (선택 사항)# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS Vendor Domain"
__description__ = "Manages vendor information, categories, and contacts."
__version__ = "0.1.0"  # ven 도메인 패키지의 버전
__all__ = []  # 'from app.domains.ven import *' 시 내보낼 이름 목록. 일반적으로 비워둡니다.

# (선택 사항) 이 패키지에서 다른 패키지로 공통 모델이나 스키마를 노출할 수 있습니다.
# 예를 들어, Vendor 모델이 다른 도메인에서 자주 참조된다면 여기서 노출할 수 있습니다.
# from .models import Vendor, VendorCategory, VendorContact, VendorVendorCategory
# from .schemas import VendorResponse, VendorCategoryResponse, VendorContactResponse

# 하지만, 일반적으로 명시적인 임포트 (예: from app.domains.ven.models import Vendor)가 권장됩니다.
