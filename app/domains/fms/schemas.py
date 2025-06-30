# app/domains/fms/schemas.py

"""
'fms' 도메인 (PostgreSQL 'fms' 스키마)의 Pydantic 스키마를 정의하는 모듈입니다.

이 모듈은 설비 카테고리, 설비 스펙 정의, 설비, 설비 스펙, 설비 이력 데이터에 대한
API 요청(생성, 업데이트) 및 응답(조회)에 사용되는 데이터 유효성 검사 및 직렬화를 위한
Pydantic 모델을 포함합니다.
SQLModel의 기능을 활용하여 데이터베이스 ORM 모델과 Pydantic 모델 간의 일관성을 유지합니다.
"""

from typing import Optional, Dict, Any
from datetime import datetime, date

from sqlmodel import SQLModel

from pydantic import Field

from .models import EquipmentStatus


# =============================================================================
# 1. fms.equipment_categories 테이블 스키마
# =============================================================================
class EquipmentCategoryBase(SQLModel):
    """
    설비 카테고리의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `fms.equipment_categories` 테이블과 매핑됩니다.
    """
    name: str = Field(..., max_length=100, description="카테고리 명칭 (예: 모터, 수질계측기)")
    description: Optional[str] = Field(None, description="카테고리에 대한 설명")
    korean_useful_life_years: Optional[int] = Field(None, description="한국 정부 권장 내용연수 (년)")


class EquipmentCategoryCreate(EquipmentCategoryBase):
    """
    새로운 설비 카테고리를 생성하기 위한 Pydantic 모델입니다.
    `name`은 필수 필드입니다.
    """
    pass  # EquipmentCategoryBase에서 이미 모든 필수 필드가 정의됨


class EquipmentCategoryUpdate(EquipmentCategoryBase):
    """
    기존 설비 카테고리 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    name: Optional[str] = Field(None, max_length=100, description="카테고리 명칭")


class EquipmentCategoryResponse(EquipmentCategoryBase):
    """
    설비 카테고리 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    데이터베이스에서 자동으로 생성되는 ID 및 타임스탬프 필드를 포함합니다.
    """
    id: int = Field(..., description="설비 카테고리 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True  # ORM 모드 활성화


# =============================================================================
# 2. fms.equipment_spec_definitions 테이블 스키마
# =============================================================================
class EquipmentSpecDefinitionBase(SQLModel):
    """
    설비 스펙 항목 정의의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `fms.equipment_spec_definitions` 테이블과 매핑됩니다.
    """
    name: str = Field(..., max_length=100, description="스펙 항목의 내부 코드명 (예: 'power_kw')")
    display_name: str = Field(..., max_length=100, description="UI에 표시될 이름 (예: '정격 출력 (kW)')")
    unit: Optional[str] = Field(None, max_length=50, description="단위 (예: 'kW', 'V')")
    data_type: str = Field(..., max_length=50, description="값의 데이터 타입 (text, numeric, boolean, jsonb)")
    description: Optional[str] = Field(None, description="스펙 항목에 대한 설명")
    is_required: bool = Field(False, description="해당 스펙 항목이 필수 입력인지 여부")
    default_value: Optional[str] = Field(None, description="기본값 (텍스트 형태, 사용 시 타입 변환)")
    sort_order: Optional[int] = Field(None, description="정렬 순서")


class EquipmentSpecDefinitionCreate(EquipmentSpecDefinitionBase):
    """
    새로운 설비 스펙 정의를 생성하기 위한 Pydantic 모델입니다.
    `name`, `display_name`, `data_type`은 필수 필드입니다.
    """
    pass


class EquipmentSpecDefinitionUpdate(EquipmentSpecDefinitionBase):
    """
    기존 설비 스펙 정의 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    name: Optional[str] = Field(None, max_length=100, description="스펙 항목의 내부 코드명")
    display_name: Optional[str] = Field(None, max_length=100, description="UI에 표시될 이름")
    data_type: Optional[str] = Field(None, max_length=50, description="값의 데이터 타입")


class EquipmentSpecDefinitionResponse(EquipmentSpecDefinitionBase):
    """
    설비 스펙 정의 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="스펙 정의 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 3. fms.equipment_category_spec_definitions 테이블 스키마 (연결 테이블)
# =============================================================================
class EquipmentCategorySpecDefinitionBase(SQLModel):
    """
    설비 카테고리와 스펙 정의 연결의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `fms.equipment_category_spec_definitions` 테이블과 매핑됩니다.
    """
    equipment_category_id: int = Field(..., description="설비 카테고리 ID (FK)")
    spec_definition_id: int = Field(..., description="스펙 정의 ID (FK)")


class EquipmentCategorySpecDefinitionCreate(EquipmentCategorySpecDefinitionBase):
    """
    설비 카테고리에 스펙 정의를 연결하기 위한 Pydantic 모델입니다.
    `equipment_category_id`와 `spec_definition_id`는 필수 필드입니다.
    """
    pass


class EquipmentCategorySpecDefinitionResponse(EquipmentCategorySpecDefinitionBase):
    """
    설비 카테고리-스펙 정의 연결 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    created_at: datetime = Field(..., description="레코드 생성 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 4. fms.equipments 테이블 스키마
# =============================================================================
class EquipmentBase(SQLModel):
    """
    설비의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `fms.equipments` 테이블과 매핑됩니다.
    """
    facility_id: int = Field(..., description="소속 처리장 ID (FK)")
    equipment_category_id: int = Field(..., description="설비 카테고리 ID (FK)")
    current_location_id: Optional[int] = Field(None, description="현재 설치 위치 ID (FK)")
    name: str = Field(..., max_length=100, description="설비의 현장 호칭 명칭")
    model_number: Optional[str] = Field(None, max_length=100, description="모델 번호")
    serial_number: Optional[str] = Field(None, max_length=100, description="일련 번호 (고유)")
    manufacturer: Optional[str] = Field(None, max_length=100, description="제조사")
    installation_date: Optional[date] = Field(None, description="설치일")
    purchase_date: Optional[date] = Field(None, description="구입일")
    purchase_price: Optional[float] = Field(None, description="구입 가격 (NUMERIC(18, 2))")
    expected_lifespan_years: Optional[int] = Field(None, description="예상 수명 (년)")
    # status: str = Field("OPERATIONAL", max_length=50, description="설비 상태 (OPERATIONAL, UNDER_MAINTENANCE, OUT_OF_SERVICE, SCRAPPED)")
    status: EquipmentStatus = EquipmentStatus.ACTIVE
    asset_tag: Optional[str] = Field(None, max_length=100, description="자산 태그 (고유)")
    notes: Optional[str] = Field(None, description="비고")


class EquipmentCreate(EquipmentBase):
    """
    새로운 설비를 생성하기 위한 Pydantic 모델입니다.
    `facility_id`, `equipment_category_id`, `name`은 필수 필드입니다.
    """
    pass


class EquipmentUpdate(EquipmentBase):
    """
    기존 설비 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    facility_id: Optional[int] = Field(None, description="소속 처리장 ID")
    equipment_category_id: Optional[int] = Field(None, description="설비 카테고리 ID")
    name: Optional[str] = Field(None, max_length=100, description="설비의 현장 호칭 명칭")
    status: Optional[str] = Field(None, max_length=50, description="설비 상태")  # 상태 변경용


class EquipmentResponse(EquipmentBase):
    """
    설비 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="설비 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 5. fms.equipment_specs 테이블 스키마
# =============================================================================
class EquipmentSpecBase(SQLModel):
    """
    설비 스펙의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `fms.equipment_specs` 테이블과 매핑됩니다.
    """
    equipment_id: int = Field(..., description="관련 설비 ID (FK)")
    specs: Dict[str, Any] = Field(..., description="설비 스펙 (JSONB 형식의 키-값 쌍)")  # JSONB 타입


class EquipmentSpecCreate(EquipmentSpecBase):
    """
    새로운 설비 스펙을 생성하기 위한 Pydantic 모델입니다.
    `equipment_id`와 `specs`는 필수 필드입니다.
    이 스키마는 업데이트에도 재사용될 수 있습니다 (upsert 로직).
    """
    pass


class EquipmentSpecUpdate(EquipmentSpecBase):
    """
    기존 설비 스펙 정보를 업데이트하기 위한 Pydantic 모델입니다.
    `specs` 필드만 업데이트 가능하도록 설계하거나, 다른 필드도 Optional로 설정.
    """
    specs: Optional[Dict[str, Any]] = Field(None, description="업데이트할 설비 스펙 (JSONB 형식의 키-값 쌍)")


class EquipmentSpecResponse(EquipmentSpecBase):
    """
    설비 스펙 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="스펙 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 6. fms.equipment_history 테이블 스키마
# =============================================================================
class EquipmentHistoryBase(SQLModel):
    """
    설비 이력의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    `fms.equipment_history` 테이블과 매핑됩니다.
    """
    equipment_id: int = Field(..., description="관련 설비 ID (FK)")
    change_type: str = Field(..., max_length=50, description="변경 유형 (예: NEW_INSTALLATION, REPAIR, MAINTENANCE)")
    change_date: Optional[datetime] = Field(None, description="변경 발생 일시 (지정하지 않으면 현재 시각)")
    description: Optional[str] = Field(None, description="변경 내용 상세")
    performed_by_user_id: Optional[int] = Field(None, description="작업 수행 사용자 ID (FK)")
    service_provider_vendor_id: Optional[int] = Field(None, description="서비스 제공 공급업체 ID (FK)")
    outsourcing: bool = Field(False, description="외주 여부")
    next_service_date: Optional[date] = Field(None, description="다음 서비스 예정일")
    cost: Optional[float] = Field(0.0, description="발생 비용 (NUMERIC(19, 4))")
    replaced_by_equipment_id: Optional[int] = Field(None, description="교체된 설비 ID (FK, 자기 참조)")


class EquipmentHistoryCreate(EquipmentHistoryBase):
    """
    새로운 설비 이력 기록을 생성하기 위한 Pydantic 모델입니다.
    `equipment_id`와 `change_type`은 필수 필드입니다.
    """
    # change_date는 Optional이므로, 클라이언트에서 제공하지 않으면 백엔드에서 현재 시각 사용
    pass


class EquipmentHistoryUpdate(EquipmentHistoryBase):
    """
    기존 설비 이력 기록을 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    equipment_id: Optional[int] = Field(None, description="관련 설비 ID (FK)")
    change_type: Optional[str] = Field(None, max_length=50, description="변경 유형")
    change_date: Optional[datetime] = Field(None, description="변경 발생 일시 (지정하지 않으면 현재 시각)")
    description: Optional[str] = Field(None, description="변경 내용 상세")
    performed_by_user_id: Optional[int] = Field(None, description="작업 수행 사용자 ID (FK)")
    service_provider_vendor_id: Optional[int] = Field(None, description="서비스 제공 공급업체 ID (FK)")
    outsourcing: Optional[bool] = Field(None, description="외주 여부")
    next_service_date: Optional[date] = Field(None, description="다음 서비스 예정일")
    cost: Optional[float] = Field(None, description="발생 비용 (NUMERIC(19, 4))")
    replaced_by_equipment_id: Optional[int] = Field(None, description="교체된 설비 ID (FK, 자기 참조)")


class EquipmentHistoryResponse(EquipmentHistoryBase):
    """
    설비 이력 기록 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="이력 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True
