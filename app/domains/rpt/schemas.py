# app/domains/rpt/schemas.py

from typing import Optional
from pydantic import BaseModel, Field

# shared 스키마를 참조하여 응답에 파일 정보를 포함시킬 수 있습니다.
from app.domains.shared import schemas as shared_schemas


class ReportFormBase(BaseModel):
    """
    보고서 양식의 기본 속성을 정의하는 Pydantic Base 스키마입니다.
    """
    name: str = Field(..., max_length=100, description="보고서 양식 이름")
    description: Optional[str] = Field(None, description="보고서 양식에 대한 설명")
    template_file_id: int = Field(..., description="템플릿으로 사용할 파일의 ID (shared.file.id)")
    is_active: bool = Field(True, description="활성화 여부")


class ReportFormCreate(ReportFormBase):
    """
    새로운 보고서 양식을 생성하기 위한 Pydantic 모델입니다.
    """
    pass


class ReportFormUpdate(BaseModel):
    """
    기존 보고서 양식 정보를 업데이트하기 위한 Pydantic 모델입니다.
    """
    name: Optional[str] = Field(None, max_length=100, description="보고서 양식 이름")
    description: Optional[str] = Field(None, description="보고서 양식에 대한 설명")
    template_file_id: Optional[int] = Field(None, description="템플릿으로 사용할 파일의 ID")


class ReportFormRead(ReportFormBase):
    """
    보고서 양식 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int

    class Config:
        from_attributes = True  # ORM 모드 활성화


class ReportFormReadWithTemplate(ReportFormRead):
    """
    보고서 양식 정보와 연결된 템플릿 파일 정보를 함께 응답하기 위한 모델입니다.
    """
    template_file: shared_schemas.ResourceRead
