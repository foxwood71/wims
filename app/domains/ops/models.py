# app/domains/ops/models.py

"""
'ops' 도메인 (PostgreSQL 'ops' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.

이 모듈은 'ops' 스키마에 속하는 모든 테이블 (lines, daily_plant_operations,
daily_line_operations, views)에 대한 SQLModel 클래스를 포함합니다.
각 클래스는 해당 PostgreSQL 테이블의 구조와 컬럼을 Python 객체로 매핑하며,
SQLModel의 Field 및 Relationship을 사용하여 데이터베이스 제약 조건 및 관계를 정의합니다.
"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, date, UTC
import uuid  # uuid 모듈 임포트 추가 (Python의 UUID 타입)

from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import ForeignKey, UniqueConstraint  # UniqueConstraint 임포트 추가
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID  # PostgreSQL의 UUID 타입 (별칭 사용)
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP, REAL
from pydantic import ConfigDict  # Pydantic의 ConfigDict 임포트


# 런타임에 필요한 다른 도메인의 모델들을 직접 임포트합니다.
# 특히 Relationship의 타입 힌팅에서 사용되는 모델은 여기에 포함되어야 합니다.
from app.domains.loc.models import Facility
from app.domains.usr.models import User


# =============================================================================
# 1. ops.lines 테이블 모델
# =============================================================================
class LineBase(SQLModel):
    """
    ops.lines 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    code: str = Field(max_length=10, sa_column_kwargs={"unique": True}, description="처리 계열 코드")
    name: str = Field(max_length=255, description="계열명")
    capacity: int = Field(default=0, description="계열 처리 용량")
    facility_id: int = Field(
        sa_column=Column(ForeignKey("loc.facilities.id", onupdate="CASCADE", ondelete="RESTRICT")),  # ForeignKey 객체 사용
        description="소속 처리시설 ID (FK)"
    )
    memo: Optional[str] = Field(default=None, description="메모")
    sort_order: Optional[int] = Field(default=None, description="정렬 순서")


class Line(LineBase, table=True):
    """
    PostgreSQL의 ops.lines 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "lines"
    __table_args__ = {'schema': 'ops'}

    id: Optional[int] = Field(default=None, primary_key=True, description="계열 고유 ID")

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
    # Facility(loc.facility)와의 관계 (다대일)
    facility: "Facility" = Relationship(
        back_populates="lines",  # Facility 모델의 `lines` 관계와 역참조
        sa_relationship_kwargs={
            "foreign_keys": "Line.facility_id",  # 명시적인 foreign_key 지정
            "cascade": "all"
        }
    )
    # Line은 여러 DailyLineOperation을 가질 수 있습니다. (일대다 관계)
    daily_operations: List["DailyLineOperation"] = Relationship(
        back_populates="line",
        sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )


# =============================================================================
# 2. ops.daily_plant_operations 테이블 모델
# =============================================================================
class DailyPlantOperationBase(SQLModel):
    """
    ops.daily_plant_operations 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    facility_id: int = Field(
        sa_column=Column(ForeignKey("loc.facilities.id", onupdate="CASCADE", ondelete="RESTRICT")),  # ForeignKey 객체 사용
        description="처리시설 ID (FK)"
    )
    op_date: date = Field(description="운영 일자")
    influent: int = Field(default=0, description="총 유입량")
    effluent: int = Field(default=0, description="총 방류량")
    offload: int = Field(default=0, description="부하분산-연계량")
    rainfall: int = Field(default=0, description="강우량")
    influent_ph: float = Field(default=0.0, sa_column=Column(REAL), description="유입 하수 수소이온 농도 (pH)")
    effluent_ph: float = Field(default=0.0, sa_column=Column(REAL), description="처리수 수소이온 농도 (pH)")
    memo: Optional[str] = Field(default=None, description="메모")


class DailyPlantOperation(DailyPlantOperationBase, table=True):
    """
    PostgreSQL의 ops.daily_plant_operations 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "daily_plant_operations"
    __table_args__ = (
        UniqueConstraint('facility_id', 'op_date'),  # UniqueConstraint 객체로 변경
        {'schema': 'ops'}
    )

    id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}, description="레코드 고유 ID")
    # global_id의 타입 힌팅을 Python의 uuid.UUID로 변경합니다.
    global_id: Optional[uuid.UUID] = Field(  # uuid.UUID 타입 사용
        default_factory=uuid.uuid4,  # uuid.uuid4() 사용 (Python UUID 생성)
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=False, default=func.gen_random_uuid(), unique=True),
        description="테이블 전체에서 고유한 UUID 식별자 (FK 참조용, UNIQUE)"
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

    # Pydantic v2에서 SQLAlchemy UUID 타입을 처리하도록 허용합니다.
    model_config = ConfigDict(arbitrary_types_allowed=True)  # ConfigDict로 변경, 올바른 위치

    # 관계 정의:
    # Facility(loc.facility)와의 관계 (다대일)
    facility: "Facility" = Relationship(
        back_populates="daily_plant_operations",  # Facility 모델의 `daily_plant_operations` 관계와 역참조
        sa_relationship_kwargs={
            "foreign_keys": "DailyPlantOperation.facility_id",  # 명시적인 foreign_key 지정
            "cascade": "all"
        }
    )
    # DailyPlantOperation은 여러 DailyLineOperation을 가질 수 있습니다. (일대다 관계)
    daily_line_operations: List["DailyLineOperation"] = Relationship(back_populates="daily_plant_operation")


# =============================================================================
# 3. ops.daily_line_operations 테이블 모델
# =============================================================================
class DailyLineOperationBase(SQLModel):
    """
    ops.daily_line_operations 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    # daily_plant_op_id의 타입 힌팅을 Python의 uuid.UUID로 변경합니다.
    daily_plant_op_id: uuid.UUID = Field(  # uuid.UUID 타입 사용
        sa_column=Column(ForeignKey("ops.daily_plant_operations.global_id", onupdate="CASCADE", ondelete="RESTRICT")),  # ForeignKey 객체 사용
        description="관련 일일 처리장 운영 레코드 ID (FK)"
    )
    line_id: int = Field(
        sa_column=Column(ForeignKey("ops.lines.id", onupdate="CASCADE", ondelete="RESTRICT")),  # ForeignKey 객체 사용
        description="계열 ID (FK)"
    )
    op_date: date = Field(description="운영 일자 (daily_plant_op_id의 날짜와 일치해야 함)")
    influent: int = Field(default=0, description="계열별 유입량")
    reject_water: int = Field(default=0, description="반류량")
    sv30: Optional[float] = Field(default=None, sa_column=Column(REAL), description="30분 후 슬러지 침강률")
    mlss: Optional[int] = Field(default=None, description="폭기조 내 현탁물질 농도")
    svi: Optional[int] = Field(default=None, description="슬러지 용량 지수")
    fm_rate: Optional[float] = Field(default=None, sa_column=Column(REAL), description="유기물 대 미생물 비")
    return_mlss: Optional[int] = Field(default=None, description="반송 MLSS")
    excess_sludge: Optional[int] = Field(default=None, description="잉여 슬러지")
    srt: Optional[float] = Field(default=None, sa_column=Column(REAL), description="고형물 체류 시간")
    return_sludge: Optional[int] = Field(default=None, description="반송량")
    ml_do: Optional[float] = Field(default=None, sa_column=Column(REAL), description="반응조 내 용존 산소")
    water_temp: Optional[float] = Field(default=None, sa_column=Column(REAL), description="수온")
    hrt: Optional[int] = Field(default=None, description="수리학적 체류 시간")
    moisture: Optional[float] = Field(default=None, sa_column=Column(REAL), description="함수율")
    memo: Optional[str] = Field(default=None, description="메모")


class DailyLineOperation(DailyLineOperationBase, table=True):
    """
    PostgreSQL의 ops.daily_line_operations 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "daily_line_operations"
    __table_args__ = (
        UniqueConstraint('line_id', 'op_date'),  # UniqueConstraint 객체로 변경
        {'schema': 'ops'}
    )

    id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}, description="레코드 고유 ID")
    # global_id의 타입 힌팅을 Python의 uuid.UUID로 변경합니다.
    global_id: Optional[uuid.UUID] = Field(  # uuid.UUID 타입 사용
        default_factory=uuid.uuid4,  # uuid.uuid4() 사용 (Python UUID 생성)
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=False, default=func.gen_random_uuid(), unique=True),
        description="테이블 전체에서 고유한 UUID 식별자 (FK 참조용, UNIQUE)"
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

    # Pydantic v2에서 SQLAlchemy UUID 타입을 처리하도록 허용합니다.
    model_config = ConfigDict(arbitrary_types_allowed=True)  # ConfigDict로 변경

    # 관계 정의:
    # DailyPlantOperation(ops.daily_plant_operations)와의 관계 (다대일)
    daily_plant_operation: "DailyPlantOperation" = Relationship(
        back_populates="daily_line_operations",
        sa_relationship_kwargs={
            "foreign_keys": "DailyLineOperation.daily_plant_op_id",  # 명시적인 foreign_key 지정 (global_id를 FK로 사용)
            "cascade": "all"
        }
    )
    # Line(ops.lines)와의 관계 (다대일)
    line: "Line" = Relationship(back_populates="daily_operations")


# =============================================================================
# 4. ops.views 테이블 모델
# =============================================================================
class OpsViewBase(SQLModel):
    """
    ops.views 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    name: str = Field(max_length=255, description="운영 데이터 보기 이름")
    user_id: int = Field(
        sa_column=Column(ForeignKey("usr.users.id", onupdate="CASCADE", ondelete="RESTRICT")),  # ForeignKey 객체 사용
        description="운영 데이터 보기 사용자 ID (FK)"
    )
    facility_id: int = Field(
        sa_column=Column(ForeignKey("loc.facilities.id", onupdate="CASCADE", ondelete="RESTRICT")),
        description="단일 필터용 처리시설 ID (FK)"
    )
    facility_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB), description="운영 데이터 보기 처리시설 ID 목록 (JSONB 배열)")
    line_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB), description="운영 데이터 보기 라인 ID 목록 (JSONB 배열)")
    sampling_point_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB), description="운영 데이터 보기 샘플 위치 ID 목록 (JSONB 배열)")
    memo: Optional[str] = Field(default=None, description="메모")


class OpsView(OpsViewBase, table=True):
    """
    PostgreSQL의 ops.views 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "views"  # 테이블 이름은 'views' (SQL 덤프에 따라)
    __table_args__ = {'schema': 'ops'}

    id: Optional[int] = Field(default=None, primary_key=True, description="레코드 고유 ID")

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

    # Pydantic v2에서 SQLAlchemy UUID 타입을 처리하도록 허용합니다.
    # 이 모델에는 UUID 필드가 직접 없지만, 다른 모델의 UUID 필드를 통해 참조될 가능성이 있다면
    # 안전을 위해 추가해둘 수 있습니다. (여기서는 필요 없을 가능성 높음)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # 관계 정의:
    # User(usr.users)와의 관계 (다대일)
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "OpsView.user_id",  # 명시적인 foreign_key 지정
            "cascade": "all"
        }
    )
