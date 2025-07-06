# app/core/dependencies.py

"""
FastAPI 애플리케이션의 의존성 주입(Dependency Injection)을 정의하는 모듈입니다.

- 데이터베이스 세션 관리 (get_db_session_dependency).
- 현재 인증된 사용자 정보 획득 (get_current_user, get_current_active_user 등).
- 사용자 역할(role) 기반 권한 부여를 위한 헬퍼 함수.
"""

from typing import AsyncGenerator
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from jose import jwt, JWTError
# from pydantic import ValidationError
# from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession  # AsyncSession 임포트

# 애플리케이션 설정 임포트 (ALGORITHM, SECRET_KEY 등을 가져오기 위함)
# from app.core.config import settings

# 실제 데이터베이스 세션 제너레이터 임포트
from app.core.database import get_session as get_main_app_session

# 보안 관련 유틸리티 함수 임포트 (비밀번호 해싱/검증 등)
# flake8: noqa
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    oauth2_scheme,  # OAuth2PasswordBearer 인스턴스
    get_current_user_from_token,  # 토큰에서 사용자 정보를 가져오는 함수
    get_current_active_user,  # 활성 사용자 확인 함수
    get_current_admin_user,  # 관리자 사용자 확인 함수
    get_current_superuser  # 최고 관리자 확인 함수
)
# 사용자 모델 임포트 (타입 힌팅에 필요)
from app.domains.usr.models import User as UsrUser

# --- 인증 관련 의존성 (사용자 역할 기반 권한 부여) ---


# get_current_user_from_token, get_current_active_user, get_current_admin_user, get_current_superuser
# 함수들은 app/core/security.py에 정의되어 있으므로 여기서는 import만 합니다.
# 이 함수들을 직접 사용하려면, security.py 파일이 정확히 구현되어 있어야 합니다.


# 예시: 특정 엔드포인트에서 관리자 권한이 필요한 경우
# @router.get("/some_admin_route/")
# async def some_admin_route(current_admin_user: UsrUser = Depends(get_current_admin_user)):
#     return {"message": f"Welcome, admin {current_admin_user.username}!"}


# --- 데이터베이스 세션 의존성 주입 ---
# get_session 의존성을 직접 노출 (get_main_app_session은 app.core.db의 get_session)
# routers에서 get_db_session_dependency 대신 get_session을 직접 사용하도록 권장합니다.
# get_db_session_dependency = get_main_app_session  # 호환성을 위해 별칭 유지
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:  # 타입을 AsyncSession으로 명시
    """
    FastAPI 의존성 주입을 위한 비동기 데이터베이스 세션 제너레이터입니다.
    app.core.database.get_session을 래핑하여 사용합니다.
    """
    async for session in get_main_app_session():
        yield session
