# app/core/__init__.py

"""
FastAPI 애플리케이션의 핵심 구성 요소 패키지입니다.

이 패키지는 애플리케이션 전반에 걸쳐 사용되는 공통적이고 핵심적인 기능들을 캡슐화합니다.
주요 서브모듈은 다음과 같습니다:

- `config.py`: 애플리케이션의 설정 및 환경 변수 관리 (Pydantic Settings).
- `db.py`: 데이터베이스 연결, 세션 관리 (SQLModel 및 AsyncSQLAlchemy).
- `security.py`: 사용자 인증, 권한 부여, 비밀번호 해싱 등 보안 관련 유틸리티.
- `dependencies.py`: FastAPI의 의존성 주입 시스템에서 사용될 공통 의존성 함수들.

이 `__init__.py` 파일은 패키지 로딩 시 특정 초기화 로직을 수행하거나,
핵심 구성 요소들을 패키지 레벨에서 직접 접근할 수 있도록 노출할 수 있습니다.
"""

# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS Core"
__description__ = "Core components for WIMS FastAPI application."
__version__ = "0.1.0"  # core 패키지의 버전
__all__ = []  # 'from app.core import *' 시 내보낼 이름 목록. 일반적으로 비워둡니다.

# (선택 사항) 패키지 초기화 로직
# 예: 설정 로드 시점에 환경 변수 상태 확인 등
# from .config import settings
# print(f"[Core] Initializing core components for environment: {settings.APP_ENV}")

# (선택 사항) 패키지 레벨에서 핵심 객체들을 직접 노출
# 이렇게 하면 'from app.core import settings, get_session' 과 같이 바로 임포트할 수 있습니다.
# 하지만 명시적인 임포트 경로(예: from app.core.config import settings)를 선호하는 경우도 많습니다.
# from .config import settings
# from .db import get_session, engine
# from .security import verify_password, get_password_hash
# from .dependencies import get_db_session_dependency # 예시 의존성 함수
