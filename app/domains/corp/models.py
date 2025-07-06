# app/domains/corp/models.py

from typing import Optional
from sqlmodel import Field, SQLModel


class CompanyInfoBase(SQLModel):
    """
    회사 정보 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    name: str = Field(max_length=100, description="회사명")
    logo_url: Optional[str] = Field(
        default=None, max_length=255, description="회사 로고 이미지 URL"
    )
    ceo_name: Optional[str] = Field(
        default=None, max_length=50, description="대표자 이름"
    )
    contact_person: Optional[str] = Field(
        default=None, max_length=50, description="담당자 이름"
    )
    contact_phone: Optional[str] = Field(
        default=None, max_length=20, description="대표 연락처"
    )
    contact_email: Optional[str] = Field(
        default=None, max_length=100, description="대표 이메일"
    )
    address: Optional[str] = Field(
        default=None, max_length=255, description="사업장 주소"
    )


class CompanyInfo(CompanyInfoBase, table=True):
    """
    corp.company_info 테이블 모델을 정의하는 클래스입니다.
    이 테이블은 항상 단 하나의 행만 유지합니다.
    """
    __tablename__ = "corp_company_info"  # 테이블명 지정

    id: int = Field(default=1, primary_key=True, description="고유 ID (항상 1)")
