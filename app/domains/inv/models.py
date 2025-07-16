# app/domains/inv/models.py

"""
'inv' 도메인 (PostgreSQL 'inv' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.

"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, date, UTC
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP, REAL, DATE


# 순환 임포트 방지를 위한 TYPE_CHECKING
if TYPE_CHECKING:
    from app.domains.fms.models import Equipment  # , EquipmentHistory
    from app.domains.loc.models import Facility, Location
    from app.domains.usr.models import User
    from app.domains.ven.models import Vendor


# =============================================================================
# 1. inv.material_category_spec_definitions (다대다 연결 테이블)
# =============================================================================
class MaterialCategorySpecDefinition(SQLModel, table=True):
    """
    MaterialCategory와 MaterialSpecDefinition의 다대다 관계를 위한 연결 테이블 모델.
    """
    __tablename__ = "material_category_spec_definitions"
    __table_args__ = {'schema': 'inv'}

    material_category_id: int = Field(
        default=None,
        foreign_key="inv.material_categories.id",
        primary_key=True
    )
    spec_definition_id: int = Field(
        default=None,
        foreign_key="inv.material_spec_definitions.id",
        primary_key=True
    )
    # [수정] Response 스키마와의 일관성을 위해 created_at 필드 추가
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 생성 일시"
    )


# =============================================================================
# 2. inv.material_spec_definitions 테이블 모델
# =============================================================================
class MaterialSpecDefinitionBase(SQLModel):
    name: str = Field(max_length=100, unique=True, description="스펙 항목의 내부 코드명 (사람이 식별)")
    display_name: str = Field(max_length=100, description="스펙 항목의 표시 명칭 (UI용)")
    unit: Optional[str] = Field(default=None, max_length=50)
    data_type: str = Field(max_length=50, description="'text', 'numeric', 'boolean', 'jsonb'")
    description: Optional[str] = Field(default=None)
    is_required: bool = Field(default=False)
    default_value: Optional[str] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)


class MaterialSpecDefinition(MaterialSpecDefinitionBase, table=True):
    __tablename__ = "material_spec_definitions"
    __table_args__ = {'schema': 'inv'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    material_categories: List["MaterialCategory"] = Relationship(
        back_populates="spec_definitions",
        link_model=MaterialCategorySpecDefinition
    )


# =============================================================================
# 3. inv.material_categories 테이블 모델
# =============================================================================
class MaterialCategoryBase(SQLModel):
    # [추가] 사람이 읽을 수 있는 고유 코드
    code: str = Field(max_length=50, unique=True, index=True, description="카테고리 코드 (사람이 식별하는 용도)")
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None)


class MaterialCategory(MaterialCategoryBase, table=True):
    __tablename__ = "material_categories"
    __table_args__ = {'schema': 'inv'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    materials: List["Material"] = Relationship(back_populates="material_category")
    spec_definitions: List["MaterialSpecDefinition"] = Relationship(
        back_populates="material_categories",
        link_model=MaterialCategorySpecDefinition
    )


# =============================================================================
# 4. inv.materials 테이블 모델
# =============================================================================
class MaterialBase(SQLModel):
    # [추가] 사람이 읽을 수 있는 고유 코드
    code: str = Field(max_length=50, unique=True, index=True, description="자재 코드 (사람이 식별하는 용도)")
    material_category_id: int = Field(foreign_key="inv.material_categories.id")
    name: str = Field(max_length=100)
    unit_of_measure: str = Field(max_length=20, description="EA, L, KG 등")
    min_stock_level: Optional[float] = Field(default=0, sa_column=Column(Numeric(18, 2)))
    max_stock_level: Optional[float] = Field(default=0, sa_column=Column(Numeric(18, 2)))
    msds_link: Optional[str] = Field(default=None, max_length=255)
    msds_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    discontinued: bool = Field(default=False)
    reorder_level: Optional[int] = Field(default=None)
    related_equipment_id: Optional[int] = Field(default=None, foreign_key="fms.equipments.id")
    replacement_cycle: Optional[float] = Field(default=0, sa_column=Column(REAL))
    replacement_cycle_unit: Optional[str] = Field(default='시간', max_length=255)
    notes: Optional[str] = Field(default=None)


class Material(MaterialBase, table=True):
    __tablename__ = "materials"
    __table_args__ = {'schema': 'inv'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    material_category: "MaterialCategory" = Relationship(back_populates="materials")
    related_equipment: Optional["Equipment"] = Relationship(back_populates="related_materials")
    specs: Optional["MaterialSpec"] = Relationship(
        back_populates="material",
        sa_relationship_kwargs={
            "uselist": False,  # 1. specs가 리스트가 아닌 단일 객체임을 명시
            'cascade': 'all, delete-orphan'
        }
    )
    batches: List["MaterialBatch"] = Relationship(
        back_populates="material",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    transactions: List["MaterialTransaction"] = Relationship(
        back_populates="material",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )


# =============================================================================
# 5. inv.materials_specs 테이블 모델
# =============================================================================
class MaterialSpecBase(SQLModel):
    # [수정] materials_id는 이제 고유 외래 키(Foreign Key) 역할만 합니다.
    materials_id: int = Field(
        foreign_key="inv.materials.id",
        unique=True,  # 하나의 자재는 하나의 스펙만 가지도록 보장
        index=True
    )
    specs: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))


class MaterialSpec(MaterialSpecBase, table=True):
    __tablename__ = "materials_specs"
    __table_args__ = {'schema': 'inv'}

    # [추가] 고유한 정수형 id를 기본 키로 추가합니다.
    id: Optional[int] = Field(default=None, primary_key=True)

    # [수정] PrimaryKey 제약조건을 id 필드로 옮겼으므로, materials_id에서는 제거합니다.
    # materials_id: int = Field(foreign_key="inv.materials.id", primary_key=True) # 기존 코드

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

    material: "Material" = Relationship(
        back_populates="specs"
    )


# =============================================================================
# 6. inv.material_batches 테이블 모델
# =============================================================================
class MaterialBatchBase(SQLModel):
    material_id: int = Field(foreign_key="inv.materials.id")
    facility_id: int = Field(foreign_key="loc.facilities.id")
    storage_location_id: Optional[int] = Field(default=None, foreign_key="loc.locations.id")
    lot_number: Optional[str] = Field(default=None, max_length=100)
    quantity: Decimal = Field(sa_column=Column(Numeric(18, 2)))
    unit_cost: Optional[float] = Field(default=None, sa_column=Column(Numeric(18, 2)))
    # [수정] received_date 필드에 sa_column을 추가하여 타임존을 명시적으로 처리합니다.
    received_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True))
    )

    # [수정] expiration_date도 명시적으로 DATE 타입을 지정해주는 것이 좋습니다.
    expiration_date: Optional[date] = Field(
        default=None,
        sa_column=Column(DATE)
    )
    vendor_id: Optional[int] = Field(default=None, foreign_key="ven.vendors.id")
    notes: Optional[str] = Field(default=None)


class MaterialBatch(MaterialBatchBase, table=True):
    __tablename__ = "material_batches"
    __table_args__ = {'schema': 'inv'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    material: "Material" = Relationship(back_populates="batches")
    facility: "Facility" = Relationship(back_populates="material_batches")
    storage_location: Optional["Location"] = Relationship(back_populates="material_batches")
    vendor: Optional["Vendor"] = Relationship(back_populates="material_batches")


# =============================================================================
# 7. inv.material_transactions 테이블 모델
# =============================================================================
class MaterialTransactionBase(SQLModel):
    material_id: int = Field(foreign_key="inv.materials.id")
    facility_id: int = Field(foreign_key="loc.facilities.id")
    transaction_type: str = Field(max_length=50)
    quantity_change: Decimal = Field(..., sa_column=Column(Numeric(19, 4)))
    transaction_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    related_equipment_id: Optional[int] = Field(default=None, foreign_key="fms.equipments.id")
    related_equipment_history_id: Optional[int] = Field(default=None, foreign_key="fms.equipment_history.id")
    source_batch_id: Optional[int] = Field(default=None, foreign_key="inv.material_batches.id")
    performed_by_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    vendor_id: Optional[int] = Field(default=None, foreign_key="ven.vendors.id")
    unit_price: Optional[float] = Field(default=0, sa_column=Column(Numeric(19, 4)))
    notes: Optional[str] = Field(default=None)


class MaterialTransaction(MaterialTransactionBase, table=True):
    __tablename__ = "material_transactions"
    __table_args__ = {'schema': 'inv'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    material: "Material" = Relationship(back_populates="transactions")
    facility: "Facility" = Relationship(back_populates="material_transactions")
    related_equipment: Optional["Equipment"] = Relationship(back_populates="material_transactions")
    performed_by_user: Optional["User"] = Relationship(back_populates="material_transactions")
    vendor: Optional["Vendor"] = Relationship(back_populates="material_transactions")
