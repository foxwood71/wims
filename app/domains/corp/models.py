# app/domains/corp/models.py

from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

# 순환 참조 방지를 위해 TYPE_CHECKING 블록 내에서만 임포트합니다.
if TYPE_CHECKING:
    from app.domains.shared.models import Resource


class CompanyInfo(SQLModel, table=True):
    """
    corp.company_info 테이블 모델을 정의하는 클래스입니다.
    이 테이블은 항상 단 하나의 행만 유지합니다.
    """
    __tablename__ = "company_info"  # 테이블명 지정
    __table_args__ = {'schema': 'corp'}

    id: int = Field(default=1, primary_key=True, description="고유 ID (항상 1)")
    name: str = Field(index=True, max_length=100, description="회사명")
    ceo_name: Optional[str] = Field(default=None, max_length=50, description="대표자명")
    address: Optional[str] = Field(default=None, max_length=255, description="사업장 주소")
    business_registration_number: Optional[str] = Field(default=None, description="사업자 등록번호")
    contact_person: Optional[str] = Field(default=None, max_length=50, description="담당자 이름")
    contact_phone: Optional[str] = Field(default=None, max_length=20, description="대표 전화")
    contact_email: Optional[str] = Field(default=None, max_length=100, description="대표 이메일")

    logo_file_id: Optional[int] = Field(
        default=None, foreign_key="shared.resources.id", description="로고 파일 ID"
    )

    # shared domain 관계 정의
    logo: Optional["Resource"] = Relationship(back_populates="company_logo")
