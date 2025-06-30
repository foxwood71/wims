# app/domains/shared/__init__.py

"""
FastAPI 애플리케이션의 'shared' 도메인 패키지입니다.

이 패키지는 PostgreSQL의 'app' 스키마에 해당하는 데이터 모델과
관련된 비즈니스 로직 및 API 엔드포인트를 포함합니다.

'shared' 도메인은 애플리케이션의 여러 부분에서 공통적으로 사용되는
데이터 (예: 시스템 버전 정보, 업로드된 이미지, 이미지 유형, 엔티티-이미지 연결 등)를
관리하는 역할을 합니다.

주요 서브모듈:
- `models.py`: 'app' 스키마의 테이블에 매핑되는 SQLModel 정의.
- `schemas.py`: 'app' 스키마 데이터에 대한 Pydantic 모델 (요청 및 응답 유효성 검사).
- `crud.py`: 'app' 스키마 테이블에 대한 비동기 CRUD (Create, Read, Update, Delete) 로직.
- `routers.py`: 'app' 스키마 데이터에 접근하기 위한 FastAPI API 엔드포인트 정의.

이 `__init__.py` 파일은 'shared' 패키지를 Python 패키지로 인식하게 하며,
패키지의 목적을 문서화합니다.
"""

# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS Shared Domain"
__description__ = "Manages common application data (e.g., versions, images)."
__version__ = "0.1.0" # shared 도메인 패키지의 버전
__all__ = [] # 'from app.domains.shared import *' 시 내보낼 이름 목록. 일반적으로 비워둡니다.

# (선택 사항) 이 패키지에서 다른 패키지로 공통 모델을 노출할 수 있습니다.
# 예를 들어, 다른 도메인에서 `Image` 모델을 자주 사용한다면 여기서 노출할 수 있습니다.
# from .models import Image, ImageType, EntityImage, Version

# 하지만, 일반적으로 명시적인 임포트 (예: from app.domains.shared.models import Image)가 권장됩니다.