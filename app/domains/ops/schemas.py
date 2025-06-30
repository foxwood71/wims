# app/domains/ops/schemas.py

"""
'ops' 도메인 (PostgreSQL 'ops' 스키마)의 Pydantic 스키마를 정의하는 모듈입니다.

이 모듈은 처리 계열, 일일 처리장 운영 현황, 일일 계열 운영 현황, 사용자 정의 보기 데이터에 대한
API 요청(생성, 업데이트) 및 응답(조회)에 사용되는 데이터 유효성 검사 및 직렬화를 위한
Pydantic 모델을 포함합니다.
SQLModel의 기능을 활용하여 데이터베이스 ORM 모델과 Pydantic 모델 간의 일관성을 유지합니다.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, UUID4  # UUID4 타입 사용을 위해 임포트
from sqlmodel import SQLModel  # SQLModel 클래스 임포트


# =============================================================================
# 1. ops.lines 테이블 스키마
# =============================================================================
class LineBase(SQLModel):
    """
    처리 계열의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `ops.lines` 테이블과 매핑됩니다.
    """
    code: str = Field(..., max_length=10, description="처리 계열 코드")
    name: str = Field(..., max_length=255, description="계열명")
    capacity: Optional[int] = Field(0, description="계열 처리 용량")
    facility_id: int = Field(..., description="소속 처리시설 ID (FK)")
    memo: Optional[str] = Field(None, description="메모")
    sort_order: Optional[int] = Field(None, description="정렬 순서")


class LineCreate(LineBase):
    """
    새로운 처리 계열을 생성하기 위한 Pydantic 모델입니다.
    `code`, `name`, `facility_id`는 필수 필드입니다.
    """
    pass  # LineBase에서 이미 모든 필수 필드가 정의됨


class LineUpdate(LineBase):
    """
    기존 처리 계열 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    code: Optional[str] = Field(None, max_length=10, description="처리 계열 코드")
    name: Optional[str] = Field(None, max_length=255, description="계열명")
    facility_id: Optional[int] = Field(None, description="소속 처리시설 ID (FK)")


class LineResponse(LineBase):
    """
    처리 계열 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    데이터베이스에서 자동으로 생성되는 ID 및 타임스탬프 필드를 포함합니다.
    """
    id: int = Field(..., description="계열 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True  # ORM 모드 활성화


# =============================================================================
# 2. ops.daily_plant_operations 테이블 스키마
# =============================================================================
class DailyPlantOperationBase(SQLModel):
    """
    일일 처리장 운영 현황의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `ops.daily_plant_operations` 테이블과 매핑됩니다.
    """
    facility_id: int = Field(..., description="처리시설 ID (FK)")
    op_date: date = Field(..., description="운영 일자")
    influent: Optional[int] = Field(0, description="총 유입량")
    effluent: Optional[int] = Field(0, description="총 방류량")
    offload: Optional[int] = Field(0, description="부하분산-연계량")
    rainfall: Optional[int] = Field(0, description="강우량")
    influent_ph: Optional[float] = Field(0.0, description="유입 하수 수소이온 농도 (pH)")
    effluent_ph: Optional[float] = Field(0.0, description="처리수 수소이온 농도 (pH)")
    memo: Optional[str] = Field(None, description="메모")


class DailyPlantOperationCreate(DailyPlantOperationBase):
    """
    새로운 일일 처리장 운영 현황을 생성하기 위한 Pydantic 모델입니다.
    `facility_id`와 `op_date`는 필수 필드입니다.
    """
    pass


class DailyPlantOperationUpdate(DailyPlantOperationBase):
    """
    기존 일일 처리장 운영 현황 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    facility_id: Optional[int] = Field(None, description="처리시설 ID (FK)")  # `facility_id`를 Optional로 추가
    op_date: Optional[date] = Field(None, description="운영 일자")   # `op_date`를 Optional로 추가
    influent: Optional[int] = Field(None, description="총 유입량")
    effluent: Optional[int] = Field(None, description="총 방류량")
    offload: Optional[int] = Field(None, description="부하분산-연계량")
    rainfall: Optional[int] = Field(None, description="강우량")
    influent_ph: Optional[float] = Field(None, description="유입 하수 수소이온 농도 (pH)")
    effluent_ph: Optional[float] = Field(None, description="처리수 수소이온 농도 (pH)")
    memo: Optional[str] = Field(None, description="메모")


class DailyPlantOperationResponse(DailyPlantOperationBase):
    """
    일일 처리장 운영 현황 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    데이터베이스에서 자동으로 생성되는 ID, global_id 및 타임스탬프 필드를 포함합니다.
    """
    id: int = Field(..., description="레코드 고유 ID")
    global_id: UUID4 = Field(..., description="테이블 전체에서 고유한 UUID 식별자 (FK 참조용)")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 3. ops.daily_line_operations 테이블 스키마
# =============================================================================
class DailyLineOperationBase(SQLModel):
    """
    일일 계열별 운영 현황의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `ops.daily_line_operations` 테이블과 매핑됩니다.
    """
    daily_plant_op_id: UUID4 = Field(..., description="관련 일일 처리장 운영 레코드 ID (FK)")
    line_id: int = Field(..., description="계열 ID (FK)")
    op_date: date = Field(..., description="운영 일자 (daily_plant_op_id의 날짜와 일치해야 함)")
    influent: Optional[int] = Field(0, description="계열별 유입량")
    reject_water: Optional[int] = Field(0, description="반류량")
    sv30: Optional[float] = Field(None, description="30분 후 슬러지 침강률")
    mlss: Optional[int] = Field(None, description="폭기조 내 현탁물질 농도")
    svi: Optional[int] = Field(None, description="슬러지 용량 지수")
    fm_rate: Optional[float] = Field(None, description="유기물 대 미생물 비")
    return_mlss: Optional[int] = Field(None, description="반송 MLSS")
    excess_sludge: Optional[int] = Field(None, description="잉여 슬러지")
    srt: Optional[float] = Field(None, description="고형물 체류 시간")
    return_sludge: Optional[int] = Field(None, description="반송량")
    ml_do: Optional[float] = Field(None, description="반응조 내 용존 산소")
    water_temp: Optional[float] = Field(None, description="수온")
    hrt: Optional[int] = Field(None, description="수리학적 체류 시간")
    moisture: Optional[float] = Field(None, description="함수율")
    memo: Optional[str] = Field(None, description="메모")


class DailyLineOperationCreate(DailyLineOperationBase):
    """
    새로운 일일 계열별 운영 현황을 생성하기 위한 Pydantic 모델입니다.
    `daily_plant_op_id`, `line_id`, `op_date`는 필수 필드입니다.
    """
    pass


class DailyLineOperationUpdate(DailyLineOperationBase):
    """
    기존 일일 계열별 운영 현황 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    influent: Optional[int] = Field(None, description="계열별 유입량")
    reject_water: Optional[int] = Field(None, description="반류량")


class DailyLineOperationResponse(DailyLineOperationBase):
    """
    일일 계열별 운영 현황 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    데이터베이스에서 자동으로 생성되는 ID, global_id 및 타임스탬프 필드를 포함합니다.
    """
    id: int = Field(..., description="레코드 고유 ID")
    global_id: UUID4 = Field(..., description="테이블 전체에서 고유한 UUID 식별자 (FK 참조용)")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 4. ops.views 테이블 스키마
# =============================================================================
class OpsViewBase(SQLModel):
    """
    사용자 정의 운영 데이터 보기 설정의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `ops.views` 테이블과 매핑됩니다.
    """
    name: str = Field(..., max_length=255, description="운영 데이터 보기 이름")
    user_id: int = Field(..., description="운영 데이터 보기 사용자 ID (FK)")
    facility_id: int = Field(..., description="단일 필터용 처리시설 ID (FK)")  # <--- 이 라인 추가
    facility_ids: Optional[List[int]] = Field(None, description="운영 데이터 보기 처리시설 ID 목록 (JSONB 배열)")
    line_ids: Optional[List[int]] = Field(None, description="운영 데이터 보기 라인 ID 목록 (JSONB 배열)")
    sampling_point_ids: Optional[List[int]] = Field(None, description="운영 데이터 보기 샘플 위치 ID 목록 (JSONB 배열)")
    memo: Optional[str] = Field(None, description="메모")


class OpsViewCreate(OpsViewBase):
    """
    새로운 사용자 정의 운영 데이터 보기 설정을 생성하기 위한 Pydantic 모델입니다.
    `name`, `user_id`는 필수 필드입니다.
    """
    pass


class OpsViewUpdate(OpsViewBase):
    """
    기존 사용자 정의 운영 데이터 보기 설정을 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    name: Optional[str] = Field(None, max_length=255, description="운영 데이터 보기 이름")
    user_id: Optional[int] = Field(None, description="운영 데이터 보기 사용자 ID (FK)") # <-- 이 라인 추가
    facility_id: Optional[int] = Field(None, description="단일 필터용 처리시설 ID (FK)") # <-- 이 라인 추가
    facility_ids: Optional[List[int]] = Field(None, description="운영 데이터 보기 처리시설 ID 목록")
    memo: Optional[str] = Field(None, description="메모") # memo도 Optional로 해주는 것이 좋습니다.


class OpsViewResponse(OpsViewBase):
    """
    사용자 정의 운영 데이터 보기 설정 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="레코드 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True
