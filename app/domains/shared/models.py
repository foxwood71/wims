# app/domains/shared/models.py

"""
'shared' 도메인 (PostgreSQL 'shared' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.

이 모듈은 'shared' 스키마에 속하는 모든 테이블에 대한 SQLModel 클래스를 포함합니다.
각 클래스는 해당 PostgreSQL 테이블의 구조와 컬럼을 Python 객체로 매핑하며,
SQLModel의 Field 및 Relationship을 사용하여 데이터베이스 제약 조건 및 관계를 정의합니다.
"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, date, UTC
from sqlalchemy import ForeignKey, UniqueConstraint
# from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel, Column

# 다른 도메인의 모델을 참조해야 할 경우 (예: User 모델)
# TYPE_CHECKING을 사용하여 순환 임포트 문제를 방지합니다.
if TYPE_CHECKING:
    from app.domains.usr.models import User, Department  # User 모델 참조


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
# 2. shared.image_types 테이블 모델
# =============================================================================
class ImageTypeBase(SQLModel):
    """
    shared.image_types 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="이미지 유형 고유 ID")
    name: str = Field(max_length=100, sa_column_kwargs={"unique": True}, description="이미지 유형 명칭 (예: 설비 사진, 도면)")
    description: Optional[str] = Field(default=None, description="설명")

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


class ImageType(ImageTypeBase, table=True):
    """
    PostgreSQL의 shared.image_types 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "image_types"
    __table_args__ = {'schema': 'shared'}  # 'app' 대신 'shared' 스키마 명시

    # 관계 정의: ImageType은 여러 Image를 가질 수 있습니다. (일대다 관계)
    images: List["Image"] = Relationship(back_populates="image_type")


# =============================================================================
# 3. shared.images 테이블 모델
# =============================================================================
class ImageBase(SQLModel):
    """
    shared.images 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    image_type_id: Optional[int] = Field(
        default=None,
        sa_column=Column(ForeignKey("shared.image_types.id", onupdate="CASCADE", ondelete="RESTRICT")),  # 'shared' 스키마 참조
        description="이미지 유형 ID (FK)"
    )
    file_name: str = Field(max_length=255, description="파일 이름")
    file_path: str = Field(max_length=255, description="파일 저장 경로")
    file_size_kb: Optional[int] = Field(default=None, description="파일 크기 (KB)")
    mime_type: Optional[str] = Field(default=None, max_length=50, description="파일 MIME 타입")
    description: Optional[str] = Field(default=None, description="이미지에 대한 설명")
    # uploaded_by_user_id는 User 모델과의 관계를 위해 여기에 정의 (아래 Image 클래스에서 Relationship)
    uploaded_by_user_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("usr.users.id", onupdate="CASCADE", ondelete="SET NULL")  # usr 스키마 참조
        ),
        description="이미지를 업로드한 사용자 ID (FK)"
    )
    department_id: Optional[int] = Field(
        default=None,
        foreign_key="usr.departments.id",
        description="이미지 소유 부서 ID (FK)"
    )
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),  #
        description="이미지 업로드 일시"
    )


class Image(ImageBase, table=True):
    """
    PostgreSQL의 shared.images 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "images"
    __table_args__ = {'schema': 'shared'}  # 'app' 대신 'shared' 스키마 명시
    id: Optional[int] = Field(default=None, primary_key=True, description="이미지 고유 ID")
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

    # 관계 정의:
    # ImageType과의 관계 (다대일)
    image_type: Optional["ImageType"] = Relationship(back_populates="images")  # 전방 참조
    # User(usr.users)와의 관계 (다대일)
    uploaded_by_user: Optional["User"] = Relationship(
        back_populates="uploaded_images",  # User 모델의 'uploaded_images' 속성과 일치
        sa_relationship_kwargs={
            "foreign_keys": "Image.uploaded_by_user_id",  # 명시적인 foreign_key 지정
            "cascade": "all"
        }
    )
    department: Optional["Department"] = Relationship()
    # EntityImage와의 관계 (일대다)
    entity_images: List["EntityImage"] = Relationship(back_populates="image")


# =============================================================================
# 4. shared.entity_images 테이블 모델
# =============================================================================
class EntityImageBase(SQLModel):
    """
    shared.entity_images 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    image_id: int = Field(
        sa_column=Column(
            ForeignKey("shared.images.id", ondelete="CASCADE")
        ),
        description="연결할 이미지 ID (필수)",
    )  # 'shared' 스키마 참조
    entity_type: str = Field(max_length=50, description="연결된 엔티티 유형 (예: EQUIPMENT, MATERIAL)")
    entity_id: int = Field(description="연결된 엔티티의 ID")
    is_main_image: bool = Field(default=False, description="대표 이미지 여부")


class EntityImage(EntityImageBase, table=True):
    """
    PostgreSQL의 shared.entity_images 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "entity_images"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "image_id"),
        {'schema': 'shared'}
    )
    id: Optional[int] = Field(default=None, primary_key=True, description="연결 고유 ID")
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
    # 관계 정의:
    # Image와의 관계 (다대일)
    image: "Image" = Relationship(back_populates="entity_images")  # 전방 참조

    # Note: entity_type과 entity_id는 폴리모픽(polymorphic) 관계를 나타내므로,
    # 직접적인 ORM Relationship을 정의하기 어렵습니다.
    # 이 부분은 애플리케이션 로직(services/crud)에서 처리되어야 합니다.
    # 예: fms.equipments, inv.materials, loc.locations, ven.vendors, lims.samples, lims.test_requests 등
