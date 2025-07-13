# app/core/security.py

"""
애플리케이션의 보안 관련 유틸리티 함수 및 의존성 주입을 정의하는 모듈입니다.

- 비밀번호 해싱 및 검증.
- JWT(JSON Web Token) 생성 및 검증.
- OAuth2 Password Bearer 스키마를 사용하여 현재 사용자 획득.
- 사용자 역할(role) 기반 권한 부여(Authorization) 검사.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext  # 비밀번호 해싱을 위한 라이브러리
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.config import settings  # 애플리케이션 설정
from app.core.database import get_session  # 데이터베이스 세션 의존성
from app.domains.usr import models as usr_models  # 사용자 모델 임포트 (충돌 방지를 위해 별칭 사용)

# API_PREFIX를 가져오기 위해 app/__init__.py 또는 main.py에서 정의된 API_PREFIX를 사용해야 합니다.
# 만약 app/__init__.py에 정의되어 있다면:
from app import API_PREFIX  # 이 라인이 필요합니다


# --- 비밀번호 해싱 설정 ---
# bcrypt 해싱 알고리즘을 사용합니다.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    일반 텍스트 비밀번호와 해싱된 비밀번호를 비교하여 일치하는지 확인합니다.
    """
    print(f"DEBUG: Verifying password for hashed: {hashed_password[:10]}...")
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    주어진 비밀번호를 해싱합니다.
    """
    print("DEBUG: Hashing password.")
    return pwd_context.hash(password)


# --- OAuth2 스키마 설정 ---
# /usr/auth/token 엔드포인트로 토큰을 요청하도록 설정합니다.
# API_PREFIX를 사용하여 Swagger UI가 올바른 경로를 찾아가도록 합니다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_PREFIX}/usr/auth/token")  # 수정된 부분


# --- JWT 토큰 생성 및 검증 ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Access Token을 생성합니다.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 설정 파일에서 ACCESS_TOKEN_EXPIRE_MINUTES를 사용합니다.
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)
    print(f"DEBUG: Access token created, expires at: {expire}")
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Refresh Token을 생성합니다.
    Refresh Token 만료 시간은 Access Token보다 훨씬 길게 설정합니다.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Refresh Token의 만료 기간을 별도로 설정하거나 Access Token보다 길게 설정합니다.
        # 예: 7일 후 만료
        expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 24 / 60 * 7)  # 대략적으로 7일로 가정
    to_encode.update({"exp": expire})
    # refresh_token에는 고유한 식별자를 포함할 수 있습니다 (예: jti)
    # to_encode.update({"jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)
    print(f"DEBUG: Refresh token created, expires at: {expire}")
    return encoded_jwt


async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session),
) -> usr_models.User:
    """
    JWT 토큰을 디코딩하고 검증하여 현재 사용자를 데이터베이스에서 가져옵니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = user_id
    except JWTError as e:
        print(f"DEBUG: JWTError: {e}")
        raise credentials_exception

    # 데이터베이스에서 사용자 조회
    statement = select(usr_models.User).where(usr_models.User.user_id == token_data)
    result = await db.execute(statement)
    user = result.scalars().one_or_none()
    if user is None:
        raise credentials_exception
    print(f"DEBUG: Current user: {user.user_id} (ID: {user.id})")
    return user


# --- 역할 기반 권한 부여 의존성 ---

def get_current_active_user(
    current_user: usr_models.User = Depends(get_current_user_from_token),
) -> usr_models.User:
    """
    현재 인증된 활성 사용자를 반환합니다.
    계정이 비활성화된 경우 400 Bad Request를 발생시킵니다.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def get_current_admin_user(
    # current_user: usr_models.User = Depends(get_current_user_from_token), ==> 이제까지 오류의 원인 token으로 받아서 꼬인거임 ㅜ.ㅜ
    current_user: usr_models.User = Depends(get_current_active_user),
) -> usr_models.User:
    """
    현재 인증된 관리자 사용자를 반환합니다 (role <= 10).
    관리자 권한이 없는 경우 403 Forbidden을 발생시킵니다.
    """
    print(f"DEBUG: get_current_admin_user called for user_id: {current_user.user_id}")
    print(f"DEBUG: current_user.role: {current_user.role} (value: {current_user.role.value})")
    print(f"DEBUG: usr_models.UserRole.ADMIN: {usr_models.UserRole.ADMIN} (value: {usr_models.UserRole.ADMIN.value})")

    # allowed_roles = [usr_models.UserRole.ADMIN, usr_models.UserRole.LAB_MANAGER,
    #                 usr_models.UserRole.FACILITY_MANAGER, usr_models.UserRole.INVENTORY_MANAGER]

    allowed_roles = [usr_models.UserRole.ADMIN]

    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    if current_user.role not in allowed_roles:
        print(f"DEBUG: Role '{current_user.role.name}' is NOT in allowed roles. Raising 403.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    print(f"DEBUG: Role '{current_user.role.name}' IS in allowed roles. Proceeding.")
    return current_user


# def get_current_superuser(
#     current_user: usr_models.User = Depends(get_current_user_from_token),
# ) -> usr_models.User:
#     """
#     현재 인증된 최고 관리자 사용자를 반환합니다 (role == 1).
#     최고 관리자 권한이 없는 경우 403 Forbidden을 발생시킵니다.
#     """
#     if not current_user.is_active:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
#     if current_user.role != 1:  # role 1 (최고관리자)
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions. Superuser role required."
#         )
#     return current_user
