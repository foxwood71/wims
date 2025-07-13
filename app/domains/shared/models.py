# app/domains/shared/models.py

"""
'shared' 도메인 (PostgreSQL 'shared' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.

이 모듈은 'shared' 스키마에 속하는 모든 테이블에 대한 SQLModel 클래스를 포함합니다.
각 클래스는 해당 PostgreSQL 테이블의 구조와 컬럼을 Python 객체로 매핑하며,
SQLModel의 Field 및 Relationship을 사용하여 데이터베이스 제약 조건 및 관계를 정의합니다.
"""

from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from datetime import datetime, date, UTC

from sqlalchemy import UniqueConstraint, String

from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel, Column

# 다른 도메인의 모델을 참조해야 할 경우 (예: usr_models.User 모델)
# TYPE_CHECKING을 사용하여 순환 임포트 문제를 방지합니다.
if TYPE_CHECKING:
    from app.domains.usr.models import User, Department  # User 모델 참조
    from app.domains.corp.models import CompanyInfo  # CompanyInfo 모델 참조
    from app.domains.rpt.models import ReportForm  # ReportForm 모델 참조


# =============================================================================
# 1. shared.versions 테이블 모델
# =============================================================================
class VersionBase(SQLModel):
    """
    shared.versions 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="버전 고유 ID")
    version: Optional[str] = Field(max_length=50, sa_column_kwargs={"unique": True}, description="애플리케이션 버전 번호")
    publish_date: Optional[date] = Field(default=None, description="버전 배포일")
    notes: Optional[str] = Field(default=None, description="비고")

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 생성 일시"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="레코드 마지막 업데이트 일시"
    )


class Version(VersionBase, table=True):
    """
    PostgreSQL의 shared.versions 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "versions"
    __table_args__ = {'schema': 'shared'}  # 'app' 대신 'shared' 스키마 명시

    # Note: shared.versions 테이블에는 직접적인 외래 키 관계가 없습니다.


# =============================================================================
# 2. shared.ResourceCategory 테이블 모델
# =============================================================================
class ResourceCategory(SQLModel, table=True):
    __tablename__ = "resource_categories"
    __table_args__ = {'schema': 'shared'}

    id: Optional[int] = Field(default=None, primary_key=True, description="리소스 유형 고유 ID")
    name: str = Field(max_length=100, unique=True, description="리소스 유형 명칭 (예: 설비 사진, 시험 성적서)")
    description: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 생성 일시"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="레코드 마지막 업데이트 일시"
    )

    # shared domain 내부 관계 정의
    resources: List["Resource"] = Relationship(back_populates="category")


# =============================================================================
# 3. shared.Resource 테이블 모델
# =============================================================================
class ResourceType(str, Enum):
    """리소스의 유형을 정의하는 Enum"""
    IMAGE = "IMAGE"
    FILE = "FILE"
    LOGO = "LOGO"
    # 나중에 VIDEO, DOCUMENT 등 추가 가능


class Resource(SQLModel, table=True):
    __tablename__ = "resources"
    __table_args__ = {'schema': 'shared'}

    id: Optional[int] = Field(default=None, primary_key=True)
    type: ResourceType = Field(sa_column=Column(String), description="리소스 유형 (IMAGE, FILE 등)")
    category_id: int = Field(foreign_key="shared.resource_categories.id", description="리소스 카테고리 ID")

    # 공통 필드
    name: str = Field(description="리소스 명칭")
    path: str = Field(unique=True, description="서버 상대 경로 (고유 리소스명)")
    size_kb: int = Field(description="리소스 크기 (KB)")
    content_type: str = Field(description="파일 MIME 타입")
    description: Optional[str] = Field(default=None)

    # 관계 필드
    uploader_id: Optional[int] = Field(default=None, foreign_key="usr.users.id", description="업로더 ID")
    department_id: Optional[int] = Field(default=None, foreign_key="usr.departments.id", description="소속 부서 ID")

    # 타임스탬프

    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),  #
        description="이미지 업로드 일시"
    )
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 생성 일시"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="레코드 마지막 업데이트 일시"
    )

    # shared domain 내부 관계 정의
    category: Optional["ResourceCategory"] = Relationship(back_populates="resources")
    entity_links: List["EntityResource"] = Relationship(
        back_populates="resource",
        cascade_delete="all, delete-orphan"
    )
    # usr domain 관계 정의
    uploader: Optional["User"] = Relationship(back_populates="uploaded_resources")
    department: Optional["Department"] = Relationship(back_populates="uploaded_resources")
    # corp domain 관계 정의 단일 이미지
    company_logo: Optional["CompanyInfo"] = Relationship(back_populates="logo")
    # rpt domain 관계 정의
    report_forms: List["ReportForm"] = Relationship(back_populates="template_file")


# =============================================================================
# 4. shared.entity_resource 테이블 모델
# =============================================================================
class EntityResource(SQLModel, table=True):
    __tablename__ = "entity_resources"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "resource_id"), {'schema': 'shared'})

    id: int = Field(default=None, primary_key=True)
    resource_id: int = Field(foreign_key="shared.resources.id", description="연결할 리소스 ID")
    entity_type: str = Field(description="연결된 엔티티 유형 (예: EQUIPMENT)")
    entity_id: int = Field(description="연결된 엔티티의 ID")
    is_main: bool = Field(default=False, description="대표 리소스 여부")

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 생성 일시"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="레코드 마지막 업데이트 일시"
    )

    # shared domain 내부 관계 정의
    resource: "Resource" = Relationship(back_populates="entity_links")
