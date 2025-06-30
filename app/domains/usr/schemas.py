# app/domains/usr/schemas.py

"""
'usr' 도메인 (사용자 및 부서 관리)의 API 데이터 전송 객체(DTO)를 정의하는 모듈입니다.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import BaseModel, EmailStr

# [수정] 모델 파일에서 UserRole Enum을 임포트합니다.
from . import models as usr_models


# =============================================================================
# 1. 부서 (Department) 스키마
# =============================================================================
class DepartmentBase(SQLModel):
    code: str = Field(..., max_length=4)
    name: str = Field(..., max_length=100)
    notes: Optional[str] = None
    sort_order: Optional[int] = None
    site_list: Optional[List[int]] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(SQLModel):
    code: Optional[str] = Field(None, max_length=4)
    name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    sort_order: Optional[int] = None
    site_list: Optional[List[int]] = None


class DepartmentRead(DepartmentBase):
    id: int
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")


# =============================================================================
# 2. 사용자 (User) 스키마
# =============================================================================
class UserBase(SQLModel):
    """사용자 정보의 기본 필드를 정의하는 스키마"""
    username: str = Field(..., max_length=50)
    email: Optional[EmailStr] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    department_id: Optional[int] = None
    role: usr_models.UserRole = Field(default=usr_models.UserRole.GENERAL_USER, description="사용자 역할")
    code: Optional[str] = Field(None, max_length=16)
    is_active: bool = True


class UserCreate(UserBase):
    """사용자 생성을 위한 스키마"""
    password: str = Field(..., min_length=8)


class UserUpdate(SQLModel):
    """사용자 정보 수정을 위한 스키마"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department_id: Optional[int] = None
    role: Optional[usr_models.UserRole] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None


# [추가] 라우터에서 필요로 하던 UserRead 스키마를 정의합니다.
class UserRead(UserBase):
    """
    사용자 정보 조회를 위한 기본 스키마.
    비밀번호 해시값 등 민감한 정보는 제외됩니다.
    """
    id: int
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")


# [추가] 상세 정보 조회를 위해 부서 정보를 포함하는 스키마
class UserReadWithDetails(UserRead):
    """사용자 조회 시 소속 부서 정보까지 함께 반환하는 스키마"""
    department: Optional[DepartmentRead] = None


# =============================================================================
# 3. 인증 토큰 (Token) 스키마
# =============================================================================
class Token(BaseModel):
    """JWT 토큰 응답 스키마"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """JWT 토큰에 담길 데이터 스키마"""
    username: Optional[str] = None
