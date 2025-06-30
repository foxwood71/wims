# app/domains/usr/models.py

"""
'usr' 도메인 (PostgreSQL 'usr' 스키마)의 데이터베이스 ORM 모델을 정의하는 모듈입니다.

이 모듈은 'usr' 스키마에 속하는 모든 테이블 (departments, users)에 대한 SQLModel 클래스를 포함합니다.
각 클래스는 해당 PostgreSQL 테이블의 구조와 컬럼을 Python 객체로 매핑하며,
SQLModel의 Field 및 Relationship을 사용하여 데이터베이스 제약 조건 및 관계를 정의합니다.
"""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, UTC
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from enum import IntEnum  # [추가] IntEnum을 임포트합니다.


# 다른 도메인의 모델을 참조해야 할 경우
# TYPE_CHECKING을 사용하여 순환 임포트 문제를 방지합니다.
if TYPE_CHECKING:
    from app.domains.shared.models import Image
    from app.domains.lims.models import TestRequest, Sample, AliquotSample, WorksheetData, AnalysisResult, TestRequestTemplate, PrView, CalibrationRecord, QcSampleResult
    from app.domains.fms.models import EquipmentHistory
    from app.domains.inv.models import MaterialTransaction
    from app.domains.ops.models import OpsView


# =============================================================================
# [신규] 사용자 역할(RBAC)을 Enum으로 정의하여 코드의 가독성과 안정성을 높입니다.
# =============================================================================
class UserRole(IntEnum):
    """
    사용자 역할을 정의하는 정수형 Enum 클래스입니다.
    DB에는 정수 값으로 저장되지만, 코드에서는 명시적인 역할 이름으로 사용할 수 있습니다.
    """
    SUPERUSER = 1           # 최고 관리자
    ADMIN = 10              # 시스템 관리자
    FACILITY_MANAGER = 50   # 설비 관리자
    INVENTORY_MANAGER = 60  # 자재 관리자
    LAB_MANAGER = 70        # 실험실 관리자
    LAB_ANALYST = 80        # 실험 분석가
    GENERAL_USER = 100      # 일반 사용자


# =============================================================================
# 1. usr.departments 테이블 모델
# =============================================================================
class DepartmentBase(SQLModel):
    """
    usr.departments 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="부서 고유 ID")
    code: str = Field(max_length=4, sa_column_kwargs={"unique": True}, description="부서 코드 (예: HR, LAB)")
    name: str = Field(max_length=100, sa_column_kwargs={"unique": True}, description="부서명")
    notes: Optional[str] = Field(default=None, description="비고")
    sort_order: Optional[int] = Field(default=None, description="정렬 순서")
    site_list: Optional[List[int]] = Field(default=None, sa_column=Column(JSONB), description="관할 처리시설 목록 (JSONB 형식, 예: [1, 2, 3])")

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


class Department(DepartmentBase, table=True):
    """
    PostgreSQL의 usr.departments 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "departments"
    __table_args__ = {'schema': 'usr'}

    users: List["User"] = Relationship(back_populates="department")
    test_requests: List["TestRequest"] = Relationship(back_populates="department")


# =============================================================================
# 2. usr.users 테이블 모델
# =============================================================================
class UserBase(SQLModel):
    """
    usr.users 테이블의 기본 속성을 정의하는 SQLModel Base 클래스입니다.
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="사용자 고유 ID")
    username: str = Field(max_length=50, sa_column_kwargs={"unique": True}, description="로그인 사용자명")
    password_hash: str = Field(max_length=255, description="해싱된 비밀번호")
    email: Optional[str] = Field(default=None, max_length=100, sa_column_kwargs={"unique": True}, description="사용자 이메일")
    full_name: Optional[str] = Field(default=None, max_length=100, description="사용자 전체 이름")
    department_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("usr.departments.id", onupdate="CASCADE", ondelete="RESTRICT")
        ),
        description="소속 부서 ID (FK)"
    )
    # [수정] role 필드의 타입을 int 대신 새로 정의한 UserRole Enum으로 변경하고 기본값을 설정합니다.
    role: UserRole = Field(default=UserRole.GENERAL_USER, description="사용자 역할 (권한)")
    code: Optional[str] = Field(default=None, max_length=16, sa_column_kwargs={"unique": True}, description="사번 등 사용자 고유 코드")
    is_active: bool = Field(default=True, description="계정 활성 여부")

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


class User(UserBase, table=True):
    """
    PostgreSQL의 usr.users 테이블에 매핑되는 SQLModel ORM 클래스입니다.
    """
    __tablename__ = "users"
    __table_args__ = {'schema': 'usr'}

    # 관계 정의:
    department: Optional["Department"] = Relationship(
        back_populates="users",
        sa_relationship_kwargs={"foreign_keys": "User.department_id"}
    )

    uploaded_images: List["Image"] = Relationship(
        back_populates="uploaded_by_user",
        sa_relationship_kwargs={"foreign_keys": "[Image.uploaded_by_user_id]"}
    )

    equipment_history_records: List["EquipmentHistory"] = Relationship(back_populates="performed_by_user")
    material_transactions: List["MaterialTransaction"] = Relationship(back_populates="performed_by_user")

    # LIMS 도메인 관련 관계들
    test_requests_created: List["TestRequest"] = Relationship(back_populates="requester_user", sa_relationship_kwargs={'foreign_keys': '[TestRequest.requester_user_id]'})
    samples_collected: List["Sample"] = Relationship(back_populates="collector_user", sa_relationship_kwargs={'foreign_keys': '[Sample.collector_user_id]'})
    aliquot_samples_analyzed: List["AliquotSample"] = Relationship(back_populates="analyst", sa_relationship_kwargs={'foreign_keys': '[AliquotSample.analyst_user_id]'})
    worksheets_analyzed: List["WorksheetData"] = Relationship(back_populates="analyst", sa_relationship_kwargs={'foreign_keys': '[WorksheetData.analyst_user_id]'})
    worksheets_verified: List["WorksheetData"] = Relationship(back_populates="verifier", sa_relationship_kwargs={'foreign_keys': '[WorksheetData.verified_by_user_id]'})
    analysis_results_analyzed: List["AnalysisResult"] = Relationship(back_populates="analyst", sa_relationship_kwargs={'foreign_keys': '[AnalysisResult.analyst_user_id]'})
    analysis_results_approved: List["AnalysisResult"] = Relationship(back_populates="approver", sa_relationship_kwargs={'foreign_keys': '[AnalysisResult.approved_by_user_id]'})
    test_request_templates: List["TestRequestTemplate"] = Relationship(back_populates="user")
    pr_views: List["PrView"] = Relationship(back_populates="user")
    calibration_records: List["CalibrationRecord"] = Relationship(back_populates="calibrated_by_user", sa_relationship_kwargs={'foreign_keys': '[CalibrationRecord.calibrated_by_user_id]'})
    qc_sample_results: List["QcSampleResult"] = Relationship(back_populates="analyst", sa_relationship_kwargs={'foreign_keys': '[QcSampleResult.analyst_user_id]'})

    # Ops 도메인 관련 관계들
    ops_views: List["OpsView"] = Relationship(back_populates="user")
