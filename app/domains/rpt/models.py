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

    #  shared.file 테이블의 id를 외래 키로 참조합니다.
    template_file_id: int = Field(foreign_key="shared.files.id", description="템플릿 파일 ID")


class ReportForm(ReportFormBase, table=True):
    """
    rpt.report_form 테이블 모델을 정의하는 클래스입니다.
    """
    __tablename__ = "rpt_report_form"

    id: int = Field(default=None, primary_key=True)

    #  shared.File 모델과의 관계를 설정합니다.
    template_file: "File" = Relationship(back_populates="report_forms")
