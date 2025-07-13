# app/domains/corp/schemas.py

from typing import Optional
from sqlmodel import SQLModel, Field

from app.domains.shared import schemas as shared_schemas


class CompanyInfoBase(SQLModel):
    """
    회사 정보의 기본 속성을 정의하는 Pydantic Base 스키마입니다.
    """
    name: str = Field(..., max_length=100, description="회사명")
    ceo_name: Optional[str] = Field(None, max_length=50, description="대표자 이름")
    address: Optional[str] = Field(None, max_length=255, description="사업장 주소")
    business_registration_number: Optional[str] = Field(None, description="사업자 등록번호")
    contact_phone: Optional[str] = Field(None, max_length=20, description="대표 전화")
    contact_email: Optional[str] = Field(None, max_length=100, description="대표 이메일")
    contact_person: Optional[str] = Field(None, max_length=50, description="담당자 이름")

    class Config:
        from_attributes = True  # ORM 모드 활성화


# --- API Schemas ---
class CompanyInfoCreate(CompanyInfoBase):
    name: str


class CompanyInfoRead(CompanyInfoBase):
    id: int
    logo_file_id: Optional[int] = None


class CompanyInfoReadWithLogo(CompanyInfoRead):
    logo: Optional[shared_schemas.ResourceRead] = None


class CompanyInfoUpdate(SQLModel):
    """
    회사 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    name: Optional[str] = Field(None, max_length=100, description="회사명")
    ceo_name: Optional[str] = Field(None, max_length=50, description="대표자 이름")
    address: Optional[str] = Field(None, max_length=255, description="사업장 주소")
    business_registration_number: Optional[str] = Field(None, description="사업자 등록번호")
    contact_phone: Optional[str] = Field(None, max_length=20, description="대표 전화")
    contact_email: Optional[str] = Field(None, max_length=100, description="대표 이메일")
    contact_person: Optional[str] = Field(None, max_length=50, description="담당자 이름")
    logo_file_id: Optional[int] = None
