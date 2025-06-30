# app/domains/loc/models.py

"""
'loc' 도메인 (PostgreSQL 'loc' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.
 - loc 도메인은 처리장(Facility) -> 장소(Location) 계층 구조
 - 구역(Area) 은 Location하위 구조

이 모듈은 'loc' 스키마에 속하는 모든 테이블 (facility, location_types, locations)에 대한
SQLModel 클래스를 포함합니다.
각 클래스는 해당 PostgreSQL 테이블의 구조와 컬럼을 Python 객체로 매핑하며,
SQLModel의 Field 및 Relationship을 사용하여 데이터베이스 제약 조건 및 관계를 정의합니다.
"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, UTC
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import ForeignKey, UniqueConstraint  # UniqueConstraint 임포트 추가
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP  # , REAL
from sqlalchemy import Numeric


# 다른 도메인의 모델을 참조해야 할 경우 (예: fms.equipments)
# TYPE_CHECKING을 사용하여 순환 임포트 문제를 방지합니다.
if TYPE_CHECKING:
    from app.domains.fms.models import Equipment
    from app.domains.inv.models import MaterialBatch
    from app.domains.lims.models import Sample, SamplingPoint
    from app.domains.ops.models import DailyPlantOperation, Line  # DailyPlantOperation, Line 추가
    from app.domains.inv.models import MaterialTransaction  # MaterialTransaction 추가
    from app.domains.lims.models import PrView  # PrView 추가


# =============================================================================
# 1. loc.facility 테이블 모델
# =============================================================================
class FacilityBase(SQLModel):
    """
    loc.facility 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="하수처리장 고유 ID")
    code: Optional[str] = Field(default=None, max_length=5, sa_column_kwargs={"unique": True}, description="하수처리장 코드")
    name: str = Field(max_length=100, sa_column_kwargs={"unique": True}, description="하수처리장 현장 호칭 명칭")
    address: Optional[str] = Field(default=None, max_length=255, description="주소")
    contact_person: Optional[str] = Field(default=None, max_length=100, description="담당자")
    contact_phone: Optional[str] = Field(default=None, max_length=50, description="연락처")
    latitude: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 7)), description="위도 (NUMERIC(10, 7))")
    longitude: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 7)), description="경도 (NUMERIC(10, 7))")
    description: Optional[str] = Field(default=None, description="설명")
    is_stp: bool = Field(default=True, description="하수처리장 여부 (true: 하수, false: 폐수 등)")
    sort_order: Optional[int] = Field(default=None, description="정렬 순서")

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


class Facility(FacilityBase, table=True):
    """
    PostgreSQL의 loc.facility 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "facilities"
    __table_args__ = {'schema': 'loc'}

    # 관계 정의:
    # Facility는 여러 Location을 가질 수 있습니다. (일대다 관계)
    locations: List["Location"] = Relationship(back_populates="facility")
    # Facility는 여러 Equipment를 가질 수 있습니다. (일대다 관계)
    equipments: List["Equipment"] = Relationship(back_populates="facility")
    # Facility는 여러 MaterialBatch를 가질 수 있습니다. (일대다 관계)
    material_batches: List["MaterialBatch"] = Relationship(back_populates="facility")
    # Facility는 여러 SamplingPoint를 가질 수 있습니다. (일대다 관계)
    sampling_points: List["SamplingPoint"] = Relationship(back_populates="facility")
    # Facility는 여러 DailyPlantOperation을 가질 수 있습니다. (일대다 관계)
    # ops.daily_plant_operations 테이블은 loc.facilities.id를 참조
    # 이 역관계는 ops 도메인 모델에서 정의되어야 합니다.
    daily_plant_operations: List["DailyPlantOperation"] = Relationship(
        back_populates="facility",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    lines: List["Line"] = Relationship(
        back_populates="facility",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    # inv.material_transactions의 facility_id 참조
    material_transactions: List["MaterialTransaction"] = Relationship(back_populates="facility")
    # lims.pr_views의 plant 관계 참조
    pr_views: List["PrView"] = Relationship(back_populates="facility")


# =============================================================================
# 2. loc.location_types 테이블 모델
# =============================================================================
class LocationTypeBase(SQLModel):
    """
    loc.location_types 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="장소 유형 고유 ID")
    name: str = Field(max_length=100, sa_column_kwargs={"unique": True}, description="장소 유형 명칭 (예: 유입동, 창고)")
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


class LocationType(LocationTypeBase, table=True):
    """
    PostgreSQL의 loc.location_types 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "location_types"
    __table_args__ = {'schema': 'loc'}

    # 관계 정의: LocationType은 여러 Location을 가질 수 있습니다. (일대다 관계)
    locations: List["Location"] = Relationship(back_populates="location_type")


# =============================================================================
# 3. loc.locations 테이블 모델
# =============================================================================
class LocationBase(SQLModel):
    """
    loc.locations 테이블의 기본 속성을 정의하는 SQLModel Base 스키마입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="장소 고유 ID")
    # facility_id 필드의 foreign_key 정의를 Column(ForeignKey(...))로 명시하여 ondelete='RESTRICT'를 추가합니다.
    facility_id: int = Field(
        sa_column=Column(ForeignKey("loc.facilities.id", onupdate="CASCADE", ondelete="RESTRICT")),  # ForeignKey 객체 사용
        description="소속 시설 ID (FK)"
    )
    location_type_id: Optional[int] = Field(
        default=None,
        sa_column=Column(ForeignKey("loc.location_types.id", onupdate="CASCADE", ondelete="RESTRICT")),  # ForeignKey 객체 사용
        description="장소 유형 ID (FK)"
    )
    name: str = Field(max_length=100, description="장소 현장 호칭 명칭 (예: 반응조 A, 펌프실 1)")
    description: Optional[str] = Field(default=None, description="설명")
    parent_location_id: Optional[int] = Field(
        default=None,
        sa_column=Column(ForeignKey("loc.locations.id", onupdate="CASCADE", ondelete="CASCADE")),  # ForeignKey 객체 사용
        description="상위 장소 ID (계층 구조를 위해)"
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


class Location(LocationBase, table=True):
    """
    PostgreSQL의 loc.locations 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint('facility_id', 'name', 'parent_location_id'),  # UniqueConstraint 객체로 변경
        {'schema': 'loc'}
    )

    # 관계 정의:
    # Facility와의 관계 (다대일)
    facility: "Facility" = Relationship(back_populates="locations")
    # LocationType과의 관계 (다대일)
    location_type: Optional["LocationType"] = Relationship(
        back_populates="locations",
        sa_relationship_kwargs={
            "foreign_keys": "Location.location_type_id",
            # "cascade": "all"  # === 오류 발생 원인: 이 부분을 제거합니다. ===
        }
    )

    # 계층 관계: 자기 자신을 참조
    # parent_location은 다대일 관계. delete-orphan cascade는 일대다 관계에 적용해야 함.
    parent_location: Optional["Location"] = Relationship(
        back_populates="child_locations",
        sa_relationship_kwargs={
            "remote_side": "Location.id",
            "foreign_keys": "Location.parent_location_id",
            # "cascade": "all, delete-orphan "  # === 오류 발생 원인: 이 부분을 제거합니다. ===
        }
    )
    # child_locations는 일대다 관계. 여기에 delete-orphan cascade를 적용합니다.
    child_locations: List["Location"] = Relationship(
        back_populates="parent_location",
        sa_relationship_kwargs={
            "foreign_keys": "Location.parent_location_id",
            "cascade": "all, delete-orphan"  # === 여기에 delete-orphan cascade를 추가합니다. ===
        }
    )

    # 다른 도메인 테이블과의 관계:
    # Equipment(fms.equipments)의 current_location_id가 loc.locations.id를 참조
    equipments: List["Equipment"] = Relationship(
        back_populates="current_location",
        # cascade="all, delete-orphan" 또는 다른 삭제 cascade 옵션이 있다면 제거해야 함
        # ON DELETE RESTRICT는 cascade와 상충됩니다.
        # cascade가 없으면 기본적으로 RESTRICT처럼 동작하거나, DB 제약에 따릅니다.
    )
    # MaterialBatch(inv.material_batches)의 storage_location_id가 loc.locations.id를 참조
    material_batches: List["MaterialBatch"] = Relationship(back_populates="storage_location")
    # Sample(lims.samples)의 storage_location_id가 loc.locations.id를 참조
    samples: List["Sample"] = Relationship(back_populates="storage_location")
    # SamplingPoint(lims.sampling_points)의 plant_id는 Facility와 이미 관계 정의.
    # 필요하다면 특정 장소와 채수 지점 간의 관계도 추가 가능.
