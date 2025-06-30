# app/domains/usr/__init__.py

"""
FastAPI 애플리케이션의 'usr' 도메인 패키지입니다.

이 패키지는 PostgreSQL의 'usr' 스키마에 해당하는 데이터 모델과
관련된 비즈니스 로직 및 API 엔드포인트를 포함합니다.

'usr' 도메인은 시스템 사용자, 부서 정보, 그리고 인증/권한 부여와 관련된
핵심 데이터를 관리하는 역할을 합니다.

주요 서브모듈:
- `models.py`: 'usr' 스키마의 테이블에 매핑되는 SQLModel 정의.
- `schemas.py`: 'usr' 스키마 데이터에 대한 Pydantic 모델 (요청 및 응답 유효성 검사, 인증 스키마 포함).
- `crud.py`: 'usr' 스키마 테이블에 대한 비동기 CRUD (Create, Read, Update, Delete) 로직 및 사용자 인증 로직.
- `routers.py`: 'usr' 스키마 데이터에 접근하기 위한 FastAPI API 엔드포인트 정의 (로그인, 사용자/부서 관리).

이 `__init__.py` 파일은 'usr' 패키지를 Python 패키지로 인식하게 하며,
패키지의 목적을 문서화합니다.
"""

# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS User Domain"
__description__ = "Manages user and department data, and handles authentication."
__version__ = "0.1.0"  # usr 도메인 패키지의 버전
__all__ = []  # 'from app.domains.usr import *' 시 내보낼 이름 목록. 일반적으로 비워둡니다.

# (선택 사항) 이 패키지에서 다른 패키지로 공통 모델이나 스키마를 노출할 수 있습니다.
# 예를 들어, User 모델이 다른 도메인에서 자주 참조된다면 여기서 노출할 수 있습니다.
# from .models import User, Department
# from .schemas import UserResponse, DepartmentResponse

# 하지만, 일반적으로 명시적인 임포트 (예: from app.domains.usr.models import User)가 권장됩니다.
