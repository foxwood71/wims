# app/domains/rpt/models.py

from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

# 'shared' 도메인의 Image 모델을 타입 힌팅을 위해 임포트합니다.
# 순환 참조를 방지하기 위해 TYPE_CHECKING 블록을 사용합니다.
if TYPE_CHECKING:
    from app.domains.shared.models import File


class ReportFormBase(SQLModel):
    """
    보고서 양식 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    name: str = Field(index=True, max_length=100, description="보고서 양식 이름")
    description: Optional[str] = Field(default=None, description="보고서 양식에 대한 설명")

    #  default=True로 설정하여 기본적으로 활성화 상태가 되도록 합니다.
    is_active: bool = Field(default=True, nullable=False, description="활성화 여부")

    #  shared.file 테이블의 id를 외래 키로 참조합니다.
    template_file_id: int = Field(description="템플릿 파일 ID")


class ReportForm(ReportFormBase, table=True):
    """
    rpt.report_form 테이블 모델을 정의하는 클래스입니다.
    """
    __tablename__ = "rpt_report_form"
    __table_args__ = {"schema": "rpt", "comment": "보고서 양식"}

    id: int = Field(default=None, primary_key=True)

    #  데이터베이스 제약조건(Foreign Key)과 관계(Relationship)는 테이블 모델에서 명확히 정의합니다.
    #  Base의 template_file_id를 오버라이드하여 foreign_key를 추가합니다.
    template_file_id: int = Field(foreign_key="shared.files.id")

    #  shared.File 모델과의 관계를 설정합니다.
    #  back_populates는 File 모델에 'report_forms'라는 이름의 관계가 정의되어 있다고 가정합니다.
    template_file: "File" = Relationship(back_populates="report_forms")
