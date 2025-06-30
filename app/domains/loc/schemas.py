# app/domains/loc/schemas.py

"""
'loc' 도메인 (PostgreSQL 'loc' 스키마)의 Pydantic 스키마를 정의하는 모듈입니다.

이 모듈은 하수처리장, 장소 유형, 그리고 처리장 내의 특정 장소 데이터에 대한
API 요청(생성, 업데이트) 및 응답(조회)에 사용되는 데이터 유효성 검사 및 직렬화를 위한
Pydantic 모델을 포함합니다.
SQLModel의 기능을 활용하여 데이터베이스 ORM 모델과 Pydantic 모델 간의 일관성을 유지합니다.
"""

from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field
from sqlmodel import SQLModel  # SQLModel 클래스 임포트


# =============================================================================
# 1. loc.facility 테이블 스키마
# =============================================================================
class FacilityBase(SQLModel):
    """
    하수처리장의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `loc.facility` 테이블과 매핑됩니다.
    """
    code: Optional[str] = Field(None, max_length=5, description="시설 코드")
    name: str = Field(..., max_length=100, description="시설 명칭")
    address: Optional[str] = Field(None, max_length=255, description="주소")
    contact_person: Optional[str] = Field(None, max_length=100, description="담당자")
    contact_phone: Optional[str] = Field(None, max_length=50, description="연락처")
    latitude: Optional[float] = Field(None, description="위도 (NUMERIC(10, 7))")
    longitude: Optional[float] = Field(None, description="경도 (NUMERIC(10, 7))")
    description: Optional[str] = Field(None, description="설명")
    is_stp: bool = Field(True, description="하수처리장 여부 (true: 하수, false: 폐수 등)")
    sort_order: Optional[int] = Field(None, description="정렬 순서")

    created_at: Optional[datetime] = Field(
        default_factory=datetime.now,  # 또는 datetime.utcnow
        description="레코드 생성 일시"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.now,  # 또는 datetime.utcnow
        description="레코드 마지막 업데이트 일시"
    )


class FacilityCreate(FacilityBase):
    """
    새로운 하수처리장 정보를 생성하기 위한 Pydantic 모델입니다.
    `name`은 필수 필드입니다.
    """
    # code는 Optional이지만, Unique 제약이 있으므로 실제 생성 시에는 클라이언트가 제공하는 것이 좋음
    pass


class FacilityUpdate(FacilityBase):
    """
    기존 시설 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    code: Optional[str] = Field(None, max_length=5, description="시설 코드")
    name: Optional[str] = Field(None, max_length=100, description="시설 현장 호칭 명칭")


class FacilityRead(FacilityBase):
    """
    시설 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    데이터베이스에서 자동으로 생성되는 ID 및 타임스탬프 필드를 포함합니다.
    """
    id: int = Field(..., description="시설 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True  # ORM 모드 활성화


# =============================================================================
# 2. loc.location_types 테이블 스키마
# =============================================================================
class LocationTypeBase(SQLModel):
    """
    장소 유형의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `loc.location_types` 테이블과 매핑됩니다.
    """
    name: str = Field(..., max_length=100, description="장소 유형 명칭 (예: 유입동, 창고)")
    description: Optional[str] = Field(None, description="설명")


class LocationTypeCreate(LocationTypeBase):
    """
    새로운 장소 유형을 생성하기 위한 Pydantic 모델입니다.
    `name`은 필수 필드입니다.
    """
    pass


class LocationTypeUpdate(LocationTypeBase):
    """
    기존 장소 유형 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    name: Optional[str] = Field(None, max_length=100, description="장소 유형 명칭")


class LocationTypeRead(LocationTypeBase):
    """
    장소 유형 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="장소 유형 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 3. loc.locations 테이블 스키마
# =============================================================================
class LocationBase(SQLModel):
    """
    장소의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `loc.locations` 테이블과 매핑됩니다.
    """
    facility_id: int = Field(..., description="소속 시설 ID (FK)")
    location_type_id: Optional[int] = Field(None, description="장소 유형 ID (FK)")
    name: str = Field(..., max_length=100, description="장소 현장 호칭 명칭 (예: 반응조 A, 펌프실 1)")
    description: Optional[str] = Field(None, description="설명")
    parent_location_id: Optional[int] = Field(None, description="상위 장소 ID (계층 구조를 위해)")


class LocationCreate(LocationBase):
    """
    새로운 장소 정보를 생성하기 위한 Pydantic 모델입니다.
    `facility_id`와 `name`은 필수 필드입니다.
    """
    pass


class LocationUpdate(LocationBase):
    """
    기존 장소 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    facility_id: Optional[int] = Field(None, description="소속 시설 ID")
    name: Optional[str] = Field(None, max_length=100, description="장소 현장 호칭 명칭")


class LocationRead(LocationBase):
    """
    장소 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="장소 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True
