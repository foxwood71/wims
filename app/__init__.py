# app/__init__.py

"""
WIMS FastAPI 애플리케이션의 메인 패키지입니다.

이 패키지는 애플리케이션의 핵심 로직과 도메인별 모듈을 포함합니다.
FastAPI 애플리케이션의 진입점 (main.py)과
공통 설정, 데이터베이스 연결, 보안 관련 유틸리티를 담는 core 서브패키지,
그리고 각 비즈니스 도메인을 대표하는 domains 서브패키지로 구성됩니다.
"""

# 패키지 레벨에서 사용할 수 있는 공통 상수나 설정을 정의할 수 있습니다.
# 예를 들어, 애플리케이션의 기본 버전이나 이름 등을 설정할 수 있습니다.
APP_NAME = "WIMS FastAPI API"
APP_VERSION = "0.1.0"
API_PREFIX = "/api/v1"  # API 라우트의 공통 접두사 (main.py에서 적용)

# 패키지가 임포트될 때 초기화될 수 있는 로직이나
# 하위 모듈/서브패키지를 직접 노출할 수 있습니다.
# 예를 들어, 핵심 설정 객체를 패키지 레벨에서 바로 접근할 수 있도록 할 수 있습니다.
# from .core.config import settings
# print(f"[{APP_NAME}] Initializing application with environment: {settings.APP_ENV}")


# PEP 440 (Version Identification and Dependency Specification)을 따르는 버전 정보
# 이 정보는 setuptools (setup.py/pyproject.toml)에서 사용될 수 있습니다.
__version__ = APP_VERSION
__title__ = APP_NAME
__description__ = "Wastewater Information Management System (WIMS) API backend."
__author__ = "Your Team Name"  # 팀/개인 이름
__license__ = "MIT"  # 프로젝트 라이선스 (예: MIT, Apache 2.0)
__all__ = []  # 패키지에서 'from app import *' 시 내보낼 이름 목록.
# 일반적으로 사용하지 않거나, 특정 공용 API만 노출할 때 사용합니다.
