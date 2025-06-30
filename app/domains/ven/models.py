# app/domains/ven/models.py

"""
'ven' 도메인 (PostgreSQL 'ven' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.

이 모듈은 'ven' 스키마에 속하는 모든 테이블 (vendor_categories, vendors,
vendor_vendor_categories, vendor_contacts)에 대한 SQLModel 클래스를 포함합니다.
각 클래스는 해당 PostgreSQL 테이블의 구조와 컬럼을 Python 객체로 매핑하며,
SQLModel의 Field 및 Relationship을 사용하여 데이터베이스 제약 조건 및 관계를 정의합니다.
"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, UTC
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP


#  다른 도메인의 모델을 참조해야 할 경우 (예: fms.equipment_history, inv.material_batches, inv.material_transactions)
#  TYPE_CHECKING을 사용하여 순환 임포트 문제를 방지합니다.
if TYPE_CHECKING:
    from app.domains.fms.models import EquipmentHistory
    from app.domains.inv.models import MaterialBatch, MaterialTransaction


# =============================================================================
# 1. ven.vendor_vendor_categories (다대다 관계를 위한 연결 테이블 모델)
# =============================================================================
class VendorVendorCategory(SQLModel, table=True):
    """
    Vendor와 VendorCategory의 다대다 관계를 위한 연결(link) 테이블 모델입니다.
    SQLModel의 link_model 방식으로 사용될 경우, 이 모델은 FK 컬럼만 정의하면 됩니다.
    """
    __tablename__ = "vendor_vendor_categories"
    __table_args__ = {'schema': 'ven'}

    vendor_id: int = Field(
        default=None,
        foreign_key="ven.vendors.id",
        primary_key=True,
        description="공급업체 ID (FK, 복합 PK)"
    )
    vendor_category_id: int = Field(
        default=None,
        foreign_key="ven.vendor_categories.id",
        primary_key=True,
        description="공급업체 카테고리 ID (FK, 복합 PK)"
    )

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 생성 일시"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="레코드 마지막 업데이트 일시"
    )
    #  참고: 이 연결 모델 자체에는 Relationship을 정의할 필요가 없습니다.
    #  SQLModel이 link_model을 통해 자동으로 처리합니다.


# =============================================================================
# 2. ven.vendor_categories 테이블 모델
# =============================================================================
class VendorCategoryBase(SQLModel):
    """
    ven.vendor_categories 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, description="카테고리 명칭")
    description: Optional[str] = Field(default=None, description="설명")

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    )


class VendorCategory(VendorCategoryBase, table=True):
    """
    PostgreSQL의 ven.vendor_categories 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "vendor_categories"
    __table_args__ = {'schema': 'ven'}

    #  관계 정의: Vendor와의 다대다 관계를 link_model을 사용하여 정의합니다.
    vendors: List["Vendor"] = Relationship(
        back_populates="categories",  # Vendor 모델의 'categories' 속성과 연결
        link_model=VendorVendorCategory
    )


# =============================================================================
# 3. ven.vendors 테이블 모델
# =============================================================================
class VendorBase(SQLModel):
    """
    ven.vendors 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, description="공급업체명")
    business_number: Optional[str] = Field(default=None, max_length=50, unique=True)
    address: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    website: Optional[str] = Field(default=None, max_length=255)
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


class Vendor(VendorBase, table=True):
    """
    PostgreSQL의 ven.vendors 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "vendors"
    __table_args__ = {'schema': 'ven'}

    # --- 관계 정의 ---

    #  1. VendorCategory와의 다대다 관계 (link_model 사용)
    categories: List["VendorCategory"] = Relationship(
        back_populates="vendors",  # VendorCategory 모델의 'vendors' 속성과 연결
        link_model=VendorVendorCategory
    )

    #  2. VendorContact와의 일대다 관계
    contacts: List["VendorContact"] = Relationship(
        back_populates="vendor",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}  # 공급업체 삭제 시 담당자 연락처도 모두 삭제
    )

    #  3. 다른 도메인과의 일대다 관계
    equipment_history_records: List["EquipmentHistory"] = Relationship(back_populates="service_provider_vendor")
    material_batches: List["MaterialBatch"] = Relationship(back_populates="vendor")
    material_transactions: List["MaterialTransaction"] = Relationship(back_populates="vendor")


# =============================================================================
# 4. ven.vendor_contacts 테이블 모델
# =============================================================================
class VendorContactBase(SQLModel):
    """
    ven.vendor_contacts 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="ven.vendors.id", description="소속 공급업체 ID (FK)")
    name: str = Field(max_length=100, description="담당자 이름")
    title: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)

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


class VendorContact(VendorContactBase, table=True):
    """
    PostgreSQL의 ven.vendor_contacts 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "vendor_contacts"
    __table_args__ = {'schema': 'ven'}

    #  관계 정의: Vendor와의 다대일 관계
    vendor: "Vendor" = Relationship(back_populates="contacts")
