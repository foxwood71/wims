# app/domains/corp/schemas.py

from typing import Optional
from pydantic import BaseModel, Field


class CompanyInfoBase(BaseModel):
    """
    회사 정보의 기본 속성을 정의하는 Pydantic Base 스키마입니다.
    """
    name: str = Field(..., max_length=100, description="회사명")
    logo_url: Optional[str] = Field(
        None, max_length=255, description="회사 로고 이미지 URL"
    )
    ceo_name: Optional[str] = Field(None, max_length=50, description="대표자 이름")
    contact_person: Optional[str] = Field(
        None, max_length=50, description="담당자 이름"
    )
    contact_phone: Optional[str] = Field(
        None, max_length=20, description="대표 연락처"
    )
    contact_email: Optional[str] = Field(
        None, max_length=100, description="대표 이메일"
    )
    address: Optional[str] = Field(None, max_length=255, description="사업장 주소")

    class Config:
        from_attributes = True  # ORM 모드 활성화


class CompanyInfoRead(CompanyInfoBase):
    """
    회사 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int


class CompanyInfoUpdate(BaseModel):
    """
    회사 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    name: Optional[str] = Field(None, max_length=100, description="회사명")
    logo_url: Optional[str] = Field(
        None, max_length=255, description="회사 로고 이미지 URL"
    )
    ceo_name: Optional[str] = Field(None, max_length=50, description="대표자 이름")
    contact_person: Optional[str] = Field(
        None, max_length=50, description="담당자 이름"
    )
    contact_phone: Optional[str] = Field(
        None, max_length=20, description="대표 연락처"
    )
    contact_email: Optional[str] = Field(
        None, max_length=100, description="대표 이메일"
    )
    address: Optional[str] = Field(None, max_length=255, description="사업장 주소")
