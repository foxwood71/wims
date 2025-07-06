# app/utils/__init__.py

"""
FastAPI 애플리케이션의 'utils' 패키지입니다.

이 패키지는 특정 비즈니스 도메인에 속하지 않는,
프로젝트 전반에서 재사용될 수 있는 범용 유틸리티 함수들을 포함합니다.
이러한 함수들은 애플리케이션의 여러 부분에서 공통적으로 필요한 기능을 제공하여
코드 중복을 줄이고 유지보수성을 향상시키는 역할을 합니다.

주요 서브모듈:
- `files.py`: 파일 업로드, 저장, 경로 처리 등 파일 관련 유틸리티 함수.
- (향후 추가 가능) `formatters.py`: 날짜, 숫자, 문자열 등 데이터 형식 변환 유틸리티.
- (향후 추가 가능) `validators.py`: 복잡한 데이터 유효성 검사 유틸리티.

이 `__init__.py` 파일은 'utils' 패키지를 Python 패키지로 인식하게 하며,
패키지의 목적을 문서화합니다.
"""

# flake8: noqa
# 서브모듈을 임포트하여 `from app.utils import files` 형태로 사용할 수 있게 합니다.
from . import files

# 패키지 메타데이터
__title__ = "WIMS Application Utilities"
__description__ = "Provides common, reusable utility functions for the application."
__version__ = "0.1.0"
__all__ = ["files"]