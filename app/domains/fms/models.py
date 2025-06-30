# app/domains/fms/models.py

"""
'fms' 도메인 (PostgreSQL 'fms' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.

이 모듈은 'fms' 스키마에 속하는 모든 테이블에 대한 SQLModel 클래스를 포함합니다.
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, date, UTC
from sqlalchemy import Numeric, ForeignKey, Integer
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel, Column


#  다른 도메인의 모델을 참조해야 할 경우 (순환 임포트 방지)
if TYPE_CHECKING:
    from app.domains.loc.models import Facility, Location
    from app.domains.usr.models import User
    from app.domains.ven.models import Vendor
    from app.domains.inv.models import Material, MaterialTransaction
    from app.domains.lims.models import Parameter, CalibrationRecord


# =============================================================================
# 1. fms.equipment_category_spec_definitions (다대다 연결 테이블)
#    - cascade 오류를 해결하기 위해 내부 Relationship을 제거하고,
#      link_model로만 사용되도록 구조를 단순화합니다.
# =============================================================================
class EquipmentCategorySpecDefinition(SQLModel, table=True):  #
    """
    EquipmentCategory와 EquipmentSpecDefinition의 다대다 관계를 위한 연결 테이블 모델.
    link_model로 사용될 때는 아래의 두 FK 컬럼만으로 충분합니다.
    """
    __tablename__ = "equipment_category_spec_definitions"
    __table_args__ = {'schema': 'fms'}

    equipment_category_id: int = Field(
        default=None,
        foreign_key="fms.equipment_categories.id",
        primary_key=True
    )
    spec_definition_id: int = Field(
        default=None,
        foreign_key="fms.equipment_spec_definitions.id",
        primary_key=True
    )
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 생성 일시"
    )


# =============================================================================
# 2. fms.equipment_spec_definitions 테이블 모델
# =============================================================================
class EquipmentSpecDefinitionBase(SQLModel):
    name: str = Field(max_length=100, unique=True, description="스펙 항목의 내부 코드명")
    display_name: str = Field(max_length=100, description="스펙 항목의 표시 명칭 (UI용)")
    unit: Optional[str] = Field(default=None, max_length=50)
    data_type: str = Field(max_length=50, description="'text', 'numeric', 'boolean', 'jsonb'")
    description: Optional[str] = Field(default=None)
    is_required: bool = Field(default=False)
    default_value: Optional[str] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)


class EquipmentSpecDefinition(EquipmentSpecDefinitionBase, table=True):
    __tablename__ = "equipment_spec_definitions"
    __table_args__ = {'schema': 'fms'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    # --- 관계 정의 (다대다) ---
    categories: List["EquipmentCategory"] = Relationship(
        back_populates="spec_definitions",
        link_model=EquipmentCategorySpecDefinition
    )


# =============================================================================
# 3. fms.equipment_categories 테이블 모델
# =============================================================================
class EquipmentCategoryBase(SQLModel):
    name: str = Field(max_length=100, unique=True)
    description: Optional[str] = Field(default=None)
    korean_useful_life_years: Optional[int] = Field(default=None)


class EquipmentCategory(EquipmentCategoryBase, table=True):
    __tablename__ = "equipment_categories"
    __table_args__ = {'schema': 'fms'}

    id: Optional[int] = Field(default=None, primary_key=True)
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
    # --- 관계 정의 ---
    # 일대다 관계
    equipments: List["Equipment"] = Relationship(back_populates="equipment_category")

    # 다대다 관계
    spec_definitions: List["EquipmentSpecDefinition"] = Relationship(
        back_populates="categories",
        link_model=EquipmentCategorySpecDefinition
    )


# =============================================================================
# 4. fms.equipments 테이블 모델
# =============================================================================
class EquipmentBase(SQLModel):
    facility_id: int = Field(foreign_key="loc.facilities.id")
    equipment_category_id: int = Field(foreign_key="fms.equipment_categories.id")
    current_location_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("loc.locations.id", ondelete="RESTRICT"), nullable=True)
        # nullability는 기존 Optional[int]와 동일하게 nullable=True로 설정
    )
    name: str = Field(max_length=100)
    model_number: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100, unique=True)
    manufacturer: Optional[str] = Field(default=None, max_length=100)
    installation_date: Optional[date] = Field(default=None)
    purchase_date: Optional[date] = Field(default=None)
    purchase_price: Optional[float] = Field(default=None, sa_column=Column(Numeric(18, 2)))
    expected_lifespan_years: Optional[int] = Field(default=None)
    status: str = Field(default='OPERATIONAL', max_length=50)
    asset_tag: Optional[str] = Field(default=None, max_length=100, unique=True)
    notes: Optional[str] = Field(default=None)


class Equipment(EquipmentBase, table=True):
    __tablename__ = "equipments"
    __table_args__ = {'schema': 'fms'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    # --- 관계 정의 ---
    # 다대일 관계 (cascade 제거)
    facility: "Facility" = Relationship(back_populates="equipments")
    equipment_category: "EquipmentCategory" = Relationship(back_populates="equipments")
    current_location: Optional["Location"] = Relationship(back_populates="equipments")

    # 일대일 관계 (Equipment가 삭제되면 Specs도 삭제)
    specs: Optional["EquipmentSpec"] = Relationship(
        back_populates="equipment",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    # 일대다 관계 (Equipment가 삭제되면 History도 삭제)
    history_records: List["EquipmentHistory"] = Relationship(
        back_populates="equipment",
        sa_relationship_kwargs={
            'cascade': 'all, delete-orphan',
            'foreign_keys': '[EquipmentHistory.equipment_id]'
        }
    )
    # 다른 도메인과의 관계 (cascade 제거)
    related_materials: List["Material"] = Relationship(back_populates="related_equipment")
    related_parameters: List["Parameter"] = Relationship(back_populates="instrument")
    calibration_records: List["CalibrationRecord"] = Relationship(back_populates="equipment")
    material_transactions: List["MaterialTransaction"] = Relationship(back_populates="related_equipment")


# =============================================================================
# 5. fms.equipment_specs 테이블 모델
# =============================================================================
class EquipmentSpecBase(SQLModel):
    equipment_id: int = Field(foreign_key="fms.equipments.id")  # PK로 직접 설정
    specs: Dict[str, Any] = Field(sa_column=Column(JSONB))


class EquipmentSpec(EquipmentSpecBase, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    __tablename__ = "equipment_specs"
    __table_args__ = {'schema': 'fms'}

    # id 대신 equipment_id가 PK이므로 별도 id 필드 없음
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

    # --- 관계 정의 (일대일) ---
    equipment: "Equipment" = Relationship(
        back_populates="specs",
        sa_relationship_kwargs={'uselist': False}
    )


# =============================================================================
# 6. fms.equipment_history 테이블 모델
# =============================================================================
class EquipmentHistoryBase(SQLModel):
    equipment_id: int = Field(foreign_key="fms.equipments.id")
    change_type: str = Field(max_length=50)
    change_date: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),  # datetime.utcnow 대신 datetime.now(UTC) 사용
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="레코드 변경 일시"
    )
    description: Optional[str] = Field(default=None)
    performed_by_user_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    service_provider_vendor_id: Optional[int] = Field(default=None, foreign_key="ven.vendors.id")
    outsourcing: bool = Field(default=False)
    next_service_date: Optional[datetime] = Field(default=None)
    cost: Optional[float] = Field(default=0, sa_column=Column(Numeric(19, 4)))
    replaced_by_equipment_id: Optional[int] = Field(default=None, foreign_key="fms.equipments.id")


class EquipmentHistory(EquipmentHistoryBase, table=True):
    __tablename__ = "equipment_history"
    __table_args__ = {'schema': 'fms'}

    id: Optional[int] = Field(default=None, primary_key=True)
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

    # --- 관계 정의 (모두 다대일, cascade 제거) ---
    equipment: "Equipment" = Relationship(
        back_populates="history_records",
        sa_relationship_kwargs={'foreign_keys': '[EquipmentHistory.equipment_id]'}
    )
    performed_by_user: Optional["User"] = Relationship(back_populates="equipment_history_records")
    service_provider_vendor: Optional["Vendor"] = Relationship(back_populates="equipment_history_records")
    # 교체 설비와의 관계 (자기참조와 유사)
    replaced_by_equipment: Optional["Equipment"] = Relationship(
        sa_relationship_kwargs={
            "remote_side": "Equipment.id",
            "foreign_keys": "[EquipmentHistory.replaced_by_equipment_id]"
        }
    )
