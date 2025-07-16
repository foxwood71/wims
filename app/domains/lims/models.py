# app/domains/lims/models.py

"""
'lims' 도메인 (PostgreSQL 'lims' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, date, time, UTC

from sqlalchemy import Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP, REAL

from sqlmodel import Field, Relationship, SQLModel, Column

# 순환 임포트 방지를 위한 TYPE_CHECKING
if TYPE_CHECKING:
    from app.domains.fms.models import Equipment
    from app.domains.loc.models import Facility, Location
    from app.domains.usr.models import Department, User
    # ops.models에서 DailyPlantOperation, Line, OpsView, DailyLineOperation 모델 임포트 추가
    # from app.domains.ops.models import DailyPlantOperation, Line, OpsView, DailyLineOperation


# =============================================================================
# 1. lims.parameters 테이블 모델
# =============================================================================
class ParameterBase(SQLModel):
    code: str = Field(max_length=5, unique=True, description="분석 항목 코드")
    analysis_group: Optional[str] = Field(default=None, max_length=50, description="동일 분석 항목 그룹")
    name: str = Field(max_length=255, description="분석 항목명")
    units: Optional[str] = Field(default=None, max_length=255, description="측정 단위")
    method: Optional[str] = Field(default=None, max_length=255, description="분석 방법")
    detection_limit_low: Optional[float] = Field(default=None, sa_column=Column(Numeric(28, 8)), description="하한 검출 한계")
    detection_limit_high: Optional[float] = Field(default=None, sa_column=Column(Numeric(28, 8)), description="상한 검출 한계")
    quantification_limit: Optional[float] = Field(default=None, sa_column=Column(Numeric(28, 8)), description="정량 한계")
    default_value0: Optional[str] = Field(default=None, max_length=255, description="분석 기본값 - 미생물 시험 불검출등")
    default_value1: Optional[str] = Field(default=None, max_length=255, description="분석 기본값 - 관능 시험 무색")
    default_value2: Optional[str] = Field(default=None, max_length=255, description="분석 기본값 - 정량 분석시 ND, <0.01등")
    instrument_id: Optional[int] = Field(default=None, foreign_key="fms.equipments.id", description="관련 장비 ID (FK)")
    price: Optional[float] = Field(default=None, sa_column=Column(Numeric(19, 4)), description="분석 비용")
    description: Optional[str] = Field(default=None, description="설명")
    sort_order: int = Field(default=None, description="정렬순서")
    is_active: bool = Field(default=True, description="활성 여부 - 삭제시 Fase")


class Parameter(ParameterBase, table=True):
    __tablename__ = "parameters"
    __table_args__ = {'schema': 'lims'}

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

    # --- 관계 정의 ---
    instrument: Optional["Equipment"] = Relationship(back_populates="related_parameters")
    aliquot_samples: List["AliquotSample"] = Relationship(back_populates="parameter")
    analysis_results: List["AnalysisResult"] = Relationship(back_populates="parameter")
    standard_samples: List["StandardSample"] = Relationship(
        back_populates="parameter", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    calibration_records: List["CalibrationRecord"] = Relationship(back_populates="parameter")
    qc_sample_results: List["QcSampleResult"] = Relationship(back_populates="parameter")


# =============================================================================
# 2. lims.projects 테이블 모델
# =============================================================================
class ProjectBase(SQLModel):
    code: str = Field(max_length=4, unique=True)
    name: str = Field(max_length=255)
    start_date: date
    end_date: date
    description: Optional[str] = Field(default=None)


class Project(ProjectBase, table=True):
    __tablename__ = "projects"
    __table_args__ = {'schema': 'lims'}
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

    test_requests: List["TestRequest"] = Relationship(
        back_populates="project", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )


# =============================================================================
# 3. lims.sample_containers 테이블 모델
# =============================================================================
class SampleContainer(SQLModel, table=True):
    __tablename__ = "sample_containers"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: int = Field(unique=True)
    name: str = Field(max_length=255, unique=True)
    capacity_ml: Optional[float] = Field(default=None, sa_column=Column(REAL), description="용기 용량(mL)")
    memo: Optional[str] = Field(default=None)
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
    samples: List["Sample"] = Relationship(back_populates="container")


# =============================================================================
# 4. lims.sample_types 테이블 모델
# =============================================================================
class SampleType(SQLModel, table=True):
    __tablename__ = "sample_types"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: int = Field(unique=True)
    name: str = Field(max_length=255, unique=True)
    memo: Optional[str] = Field(default=None)
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
    samples: List["Sample"] = Relationship(back_populates="sample_type")


# =============================================================================
# 5. lims.sampling_points 테이블 모델
# =============================================================================
class SamplingPoint(SQLModel, table=True):
    __tablename__ = "sampling_points"
    __table_args__ = {'schema': 'lims'}

    id: Optional[int] = Field(default=None, primary_key=True)
    code: Optional[str] = Field(default=None, max_length=10, unique=True)
    name: Optional[str] = Field(default=None, max_length=255)
    facility_id: Optional[int] = Field(default=None, foreign_key="loc.facilities.id")
    memo: Optional[str] = Field(default=None)
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

    facility: Optional["Facility"] = Relationship(back_populates="sampling_points")
    samples: List["Sample"] = Relationship(back_populates="sampling_point")


# =============================================================================
# 6. lims.weather_conditions 테이블 모델
# =============================================================================
class WeatherCondition(SQLModel, table=True):
    __tablename__ = "weather_conditions"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: int = Field(unique=True)
    status: str = Field(max_length=255, unique=True)
    memo: Optional[str] = Field(default=None)
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
    test_requests: List["TestRequest"] = Relationship(back_populates="sampling_weather")
    # samples: List["Sample"] = Relationship(back_populates="sampling_weather")


# =============================================================================
# 7. lims.test_requests 테이블 모델
# =============================================================================
class TestRequest(SQLModel, table=True):
    __tablename__ = "test_requests"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    request_code: Optional[str] = Field(default=None, max_length=20, unique=True)
    request_date: date
    project_id: int = Field(foreign_key="lims.projects.id")
    department_id: int = Field(foreign_key="usr.departments.id")
    requester_login_id: int = Field(foreign_key="usr.users.id")
    title: str = Field(max_length=255)
    label_printed: bool = Field(default=False)
    memo: Optional[str] = Field(default=None)
    sampling_date: Optional[date] = Field(default=None)
    sampling_time_from: Optional[time] = Field(default=None)
    sampling_time_to: Optional[time] = Field(default=None)
    sampling_weather_id: Optional[int] = Field(default=None, foreign_key="lims.weather_conditions.id")
    sampler: Optional[str] = Field(default=None, max_length=32)
    water_temp: Optional[float] = Field(default=None, sa_column=Column(REAL))
    air_temp: Optional[float] = Field(default=None, sa_column=Column(REAL))
    # requested_parameters: Dict[str, Any] = Field(sa_column=Column(JSONB)) -> sample에 이동 개별 sample마다 분석 파라메터가 틀리수 있기에
    submitted_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="제출 일시"
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

    # --- 관계 정의 ---
    project: "Project" = Relationship(back_populates="test_requests")
    department: "Department" = Relationship(back_populates="test_requests")
    requester_user: "User" = Relationship(back_populates="test_requests_created")
    sampling_weather: Optional["WeatherCondition"] = Relationship(back_populates="test_requests")
    samples: List["Sample"] = Relationship(
        back_populates="request", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )


# =============================================================================
# 8. lims.samples 테이블 모델
# =============================================================================
class Sample(SQLModel, table=True):
    __tablename__ = "samples"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    sample_code: Optional[str] = Field(default=None, max_length=24, unique=True)
    request_id: int = Field(foreign_key="lims.test_requests.id")
    request_sheet_index: Optional[int] = Field(default=None)
    sampling_point_id: int = Field(foreign_key="lims.sampling_points.id")
    sampling_date: date
    sampling_time: Optional[time] = Field(default=None)
    # sampling_weather_id: Optional[int] = Field(default=None, foreign_key="lims.weather_conditions.id") 의뢰서와 중복으로 삭제..
    sampler: Optional[str] = Field(default=None, max_length=32)
    sample_temp: Optional[float] = Field(default=None, sa_column=Column(REAL))
    sample_type_id: int = Field(foreign_key="lims.sample_types.id")
    container_id: int = Field(foreign_key="lims.sample_containers.id")
    parameters_for_analysis: Dict[str, Any] = Field(sa_column=Column(JSONB))
    amount: int = Field(default=1)
    storage_location_id: Optional[int] = Field(default=None, foreign_key="loc.locations.id")
    analysis_status: str = Field(default='Pending', max_length=20)
    request_date: Optional[date] = Field(default=None)
    collected_date: Optional[date] = Field(default=None)
    analyze_date: Optional[date] = Field(default=None)
    complete_date: Optional[date] = Field(default=None)
    disposal_date: Optional[date] = Field(default=None)
    storage_period: Optional[int] = Field(default=None)
    collector_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    collector: Optional[str] = Field(default=None, max_length=255)
    manager: Optional[str] = Field(default=None, max_length=255)
    memo: Optional[str] = Field(default=None)
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

    # --- 관계 정의 ---
    request: "TestRequest" = Relationship(back_populates="samples")
    sampling_point: "SamplingPoint" = Relationship(back_populates="samples")
    sample_type: "SampleType" = Relationship(back_populates="samples")
    container: "SampleContainer" = Relationship(back_populates="samples")
    # sampling_weather: Optional["WeatherCondition"] = Relationship(back_populates="samples")
    storage_location: Optional["Location"] = Relationship(back_populates="samples")
    aliquot_samples: List["AliquotSample"] = Relationship(
        back_populates="parent_sample", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    collector_user: Optional["User"] = Relationship(back_populates="samples_collected")


# =============================================================================
# 9. lims.aliquot_samples 테이블 모델
# =============================================================================
class AliquotSample(SQLModel, table=True):
    __tablename__ = "aliquot_samples"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_sample_id: int = Field(foreign_key="lims.samples.id")
    aliquot_code: Optional[str] = Field(default=None, max_length=50, unique=True)
    parameter_id: int = Field(foreign_key="lims.parameters.id")
    used_volume: Optional[float] = Field(default=None, sa_column=Column(REAL), description="분석에 사용된 시료 용량(mL)")
    analysis_status: str = Field(default='Pending', max_length=20)
    analysis_date: Optional[date] = Field(default=None)
    analyst_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    result: Optional[float] = Field(default=None, sa_column=Column(REAL))
    unit: Optional[str] = Field(default=None, max_length=50)
    qc_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    memo: Optional[str] = Field(default=None)
    disposal_date: Optional[date] = Field(default=None)
    status: str = Field(default='Active', max_length=20)
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

    # --- 관계 정의 (다대일, cascade 제거) ---
    parent_sample: "Sample" = Relationship(back_populates="aliquot_samples")
    parameter: "Parameter" = Relationship(back_populates="aliquot_samples")
    analyst: Optional["User"] = Relationship(back_populates="aliquot_samples_analyzed")

    analysis_results: List["AnalysisResult"] = Relationship(
        back_populates="aliquot_sample", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    qc_sample_results: List["QcSampleResult"] = Relationship(
        back_populates="aliquot_sample", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )


# =============================================================================
# 10. lims.worksheets, worksheet_items, worksheet_data 테이블 모델
# =============================================================================
class Worksheet(SQLModel, table=True):
    __tablename__ = "worksheets"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=255, unique=True)
    name: str = Field(max_length=255, unique=True)
    memo: Optional[str] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)

    data_start_row: Optional[int] = Field(default=None, description="데이터가 시작되는 행 번호")
    header_layout: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB), description="표제부 항목들의 셀 주소 레이아웃")

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

    items: List["WorksheetItem"] = Relationship(
        back_populates="worksheet", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    data_records: List["WorksheetData"] = Relationship(
        back_populates="worksheet", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )
    analysis_results: List["AnalysisResult"] = Relationship(back_populates="worksheet")


class WorksheetItem(SQLModel, table=True):
    __tablename__ = "worksheet_items"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    worksheet_id: int = Field(foreign_key="lims.worksheets.id")

    item_type: Optional[str] = Field(default='ROW', max_length=20, description="항목 유형 (HEADER 또는 ROW)")

    code: str = Field(max_length=255)
    priority_order: int
    xls_cell_address: Optional[str] = Field(default=None, max_length=24)
    name: str = Field(max_length=255)
    label: str = Field(max_length=255)
    type: int

    # <<< [수정] 항목의 활성 상태를 관리하는 필드 추가 >>>
    is_active: bool = Field(default=True, description="항목 활성 여부")

    format: Optional[str] = Field(default=None, max_length=255)
    unit: Optional[str] = Field(default=None, max_length=8)
    memo: Optional[str] = Field(default=None)
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
    worksheet: "Worksheet" = Relationship(back_populates="items")


class WorksheetData(SQLModel, table=True):
    __tablename__ = "worksheet_data"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    worksheet_id: int = Field(foreign_key="lims.worksheets.id")
    data_date: date
    analyst_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    verified_by_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    verified_at: Optional[datetime] = Field(default=None)
    is_verified: bool = Field(default=False)
    notes: Optional[str] = Field(default=None)
    raw_data: Dict[str, Any] = Field(sa_column=Column(JSONB))
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

    worksheet: "Worksheet" = Relationship(back_populates="data_records")
    analyst: Optional["User"] = Relationship(
        back_populates="worksheets_analyzed",
        sa_relationship_kwargs={'foreign_keys': '[WorksheetData.analyst_login_id]'}
    )
    verifier: Optional["User"] = Relationship(
        back_populates="worksheets_verified",
        sa_relationship_kwargs={'foreign_keys': '[WorksheetData.verified_by_login_id]'}
    )

    analysis_results: List["AnalysisResult"] = Relationship(
        back_populates="worksheet_data", sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
    )


# =============================================================================
# 13. lims.analysis_results 테이블 모델
# =============================================================================
class AnalysisResult(SQLModel, table=True):
    __tablename__ = "analysis_results"
    __table_args__ = (UniqueConstraint('aliquot_sample_id', 'parameter_id', 'worksheet_data_id'), {'schema': 'lims'})
    id: Optional[int] = Field(default=None, primary_key=True)
    aliquot_sample_id: int = Field(foreign_key="lims.aliquot_samples.id")
    parameter_id: int = Field(foreign_key="lims.parameters.id")
    worksheet_id: int = Field(foreign_key="lims.worksheets.id")
    worksheet_data_id: int = Field(foreign_key="lims.worksheet_data.id")
    result_value: Optional[float] = Field(default=None, sa_column=Column(REAL))
    unit: Optional[str] = Field(default=None, max_length=50)
    analysis_date: Optional[date] = Field(default=None)
    analyst_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    approved_by_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    approved_at: Optional[datetime] = Field(default=None)
    is_approved: bool = Field(default=False)
    notes: Optional[str] = Field(default=None)
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

    aliquot_sample: "AliquotSample" = Relationship(back_populates="analysis_results")
    parameter: "Parameter" = Relationship(back_populates="analysis_results")
    worksheet: "Worksheet" = Relationship(back_populates="analysis_results")
    worksheet_data: "WorksheetData" = Relationship(back_populates="analysis_results")
    analyst: Optional["User"] = Relationship(
        back_populates="analysis_results_analyzed",
        sa_relationship_kwargs={'foreign_keys': '[AnalysisResult.analyst_login_id]'}
    )
    approver: Optional["User"] = Relationship(
        back_populates="analysis_results_approved",
        sa_relationship_kwargs={'foreign_keys': '[AnalysisResult.approved_by_login_id]'}
    )

# ... (TestRequestTemplate, PrView, StandardSample, CalibrationRecord, QcSampleResult 모델도 유사한 패턴으로 수정) ...


class TestRequestTemplate(SQLModel, table=True):
    __tablename__ = "test_request_templates"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    login_id: int = Field(foreign_key="usr.users.id")
    serialized_text: Dict[str, Any] = Field(sa_column=Column(JSONB))
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
    user: "User" = Relationship(back_populates="test_request_templates")


class StandardSample(SQLModel, table=True):
    __tablename__ = "standard_samples"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True)
    name: str = Field(max_length=255)
    parameter_id: int = Field(foreign_key="lims.parameters.id")
    concentration: Optional[float] = Field(default=None, sa_column=Column(REAL))
    preparation_date: Optional[date] = Field(default=None)
    expiration_date: Optional[date] = Field(default=None)
    lot_number: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None)
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
    parameter: "Parameter" = Relationship(back_populates="standard_samples")
    calibration_records: List["CalibrationRecord"] = Relationship(back_populates="standard_sample")


class CalibrationRecord(SQLModel, table=True):
    __tablename__ = "calibration_records"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="fms.equipments.id")
    parameter_id: int = Field(foreign_key="lims.parameters.id")
    # calibration_date: datetime
    calibration_date: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="교정 일시"
    )
    # next_calibration_date: Optional[date] = Field(default=None)
    next_calibration_date: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
        description="차기 교정 일시"
    )
    calibrated_by_login_id: Optional[int] = Field(default=None, foreign_key="usr.users.id")
    standard_sample_id: Optional[int] = Field(default=None, foreign_key="lims.standard_samples.id")
    calibration_curve_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    acceptance_criteria_met: Optional[bool] = Field(default=None)
    notes: Optional[str] = Field(default=None)
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

    equipment: "Equipment" = Relationship(back_populates="calibration_records")
    parameter: "Parameter" = Relationship(back_populates="calibration_records")
    calibrated_by_user: Optional["User"] = Relationship(
        back_populates="calibration_records",
        sa_relationship_kwargs={'foreign_keys': '[CalibrationRecord.calibrated_by_login_id]'}
    )
    standard_sample: Optional["StandardSample"] = Relationship(back_populates="calibration_records")


class QcSampleResult(SQLModel, table=True):
    __tablename__ = "qc_sample_results"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    aliquot_sample_id: Optional[int] = Field(default=None, foreign_key="lims.aliquot_samples.id")
    parameter_id: int = Field(foreign_key="lims.parameters.id")
    qc_type: str = Field(max_length=50)
    expected_value: Optional[float] = Field(default=None, sa_column=Column(REAL))
    measured_value: Optional[float] = Field(default=None, sa_column=Column(REAL))
    recovery: Optional[float] = Field(default=None, sa_column=Column(REAL))
    rpd: Optional[float] = Field(default=None, sa_column=Column(REAL))
    acceptance_criteria: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    passed_qc: Optional[bool] = Field(default=None)
    analysis_date: date
    analyst_login_id: int = Field(foreign_key="usr.users.id")
    notes: Optional[str] = Field(default=None)
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

    aliquot_sample: Optional["AliquotSample"] = Relationship(back_populates="qc_sample_results")
    parameter: "Parameter" = Relationship(back_populates="qc_sample_results")
    analyst: "User" = Relationship(
        back_populates="qc_sample_results",
        sa_relationship_kwargs={'foreign_keys': '[QcSampleResult.analyst_login_id]'}
    )


class PrView(SQLModel, table=True):
    __tablename__ = "pr_views"
    __table_args__ = {'schema': 'lims'}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    login_id: int = Field(foreign_key="usr.users.id")
    facility_id: int = Field(foreign_key="loc.facilities.id")
    facility_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB))
    sampling_point_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB))
    parameter_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB))
    memo: Optional[str] = Field(default=None)
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
    user: "User" = Relationship(back_populates="pr_views")
    facility: "Facility" = Relationship(back_populates="pr_views")
