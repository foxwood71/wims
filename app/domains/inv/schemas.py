# app/domains/inv/schemas.py

"""
'inv' 도메인 (PostgreSQL 'inv' 스키마)의 Pydantic 스키마를 정의하는 모듈입니다.
"""

from typing import Optional, Dict, Any  # List,
from datetime import datetime, date
from pydantic import Field  # BaseModel,
from sqlmodel import SQLModel


# =============================================================================
# 1. inv.material_categories 테이블 스키마
# =============================================================================
class MaterialCategoryBase(SQLModel):
    code: str = Field(..., max_length=50, description="카테고리 코드 (사람이 식별하는 용도)")
    name: str = Field(..., max_length=100, description="자재 카테고리 명칭")
    description: Optional[str] = Field(None, description="카테고리에 대한 설명")


class MaterialCategoryCreate(MaterialCategoryBase):
    pass


class MaterialCategoryUpdate(SQLModel):
    name: Optional[str] = Field(None, max_length=100, description="자재 카테고리 명칭")
    description: Optional[str] = Field(None, description="카테고리에 대한 설명")


class MaterialCategoryResponse(MaterialCategoryBase):
    id: int = Field(..., description="자재 카테고리 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 2. inv.material_spec_definitions 테이블 스키마
# =============================================================================
class MaterialSpecDefinitionBase(SQLModel):
    name: str = Field(..., max_length=100, description="스펙 항목의 내부 코드명 (예: 'ph_value')")
    display_name: str = Field(..., max_length=100, description="UI에 표시될 이름 (예: 'pH 값')")
    unit: Optional[str] = Field(None, max_length=50, description="단위 (예: 'pH', 'mg/L')")
    data_type: str = Field(..., max_length=50, description="값의 데이터 타입 (text, numeric, boolean, jsonb)")
    description: Optional[str] = Field(None, description="스펙 항목에 대한 설명")
    is_required: bool = Field(False, description="해당 스펙 항목이 필수 입력인지 여부")
    default_value: Optional[str] = Field(None, description="기본값 (텍스트 형태, 사용 시 타입 변환)")
    sort_order: Optional[int] = Field(None, description="정렬 순서")


class MaterialSpecDefinitionCreate(MaterialSpecDefinitionBase):
    pass


class MaterialSpecDefinitionUpdate(SQLModel):  # 기존 SQLModel을 상속하도록 변경
    name: Optional[str] = Field(None, max_length=100, description="스펙 항목의 내부 코드명")
    display_name: Optional[str] = Field(None, max_length=100, description="UI에 표시될 이름")
    unit: Optional[str] = Field(None, max_length=50, description="단위 (예: 'pH', 'mg/L')")
    data_type: Optional[str] = Field(None, max_length=50, description="값의 데이터 타입 (text, numeric, boolean, jsonb)")
    description: Optional[str] = Field(None, description="스펙 항목에 대한 설명")
    is_required: Optional[bool] = Field(None, description="해당 스펙 항목이 필수 입력인지 여부")
    default_value: Optional[str] = Field(None, description="기본값 (텍스트 형태, 사용 시 타입 변환)")
    sort_order: Optional[int] = Field(None, description="정렬 순서")


class MaterialSpecDefinitionResponse(MaterialSpecDefinitionBase):
    id: int = Field(..., description="스펙 정의 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 3. inv.material_category_spec_definitions 테이블 스키마 (연결 테이블)
# =============================================================================
class MaterialCategorySpecDefinitionBase(SQLModel):
    material_category_id: int = Field(..., description="자재 카테고리 ID (FK)")
    spec_definition_id: int = Field(..., description="스펙 정의 ID (FK)")


class MaterialCategorySpecDefinitionCreate(MaterialCategorySpecDefinitionBase):
    pass


class MaterialCategorySpecDefinitionResponse(MaterialCategorySpecDefinitionBase):
    created_at: datetime = Field(..., description="레코드 생성 일시")

    class Config:
        from_attributes = True


class MaterialCategorySpecDefinitionUpdate(MaterialCategorySpecDefinitionCreate):
    """
    자재 카테고리와 스펙 정의의 연결 관계를 업데이트하기 위한 스키마입니다.
    현재로서는 특별한 업데이트 로직이 없으므로 Create 스키마를 상속합니다.
    """
    pass


# =============================================================================
# 4. inv.materials 테이블 스키마
# =============================================================================
class MaterialBase(SQLModel):
    code: str = Field(..., max_length=50, description="자재 코드 (사람이 식별하는 용도)")
    material_category_id: int = Field(..., description="자재 카테고리 ID (FK)")
    name: str = Field(..., max_length=100, description="자재명")
    unit_of_measure: str = Field(..., max_length=20, description="측정 단위 (예: EA, L, KG)")
    min_stock_level: Optional[float] = Field(0.0, description="최소 재고 수량")
    max_stock_level: Optional[float] = Field(0.0, description="최대 재고 수량")
    msds_link: Optional[str] = Field(None, max_length=255, description="MSDS 문서 링크")
    msds_data: Optional[Dict[str, Any]] = Field(None, description="MSDS 주요 정보 (JSONB)")
    discontinued: bool = Field(False, description="단종 여부")
    reorder_level: Optional[int] = Field(None, description="재주문 레벨 (일반 재고 관리용)")
    related_equipment_id: Optional[int] = Field(None, description="관련 설비 ID (FK)")
    replacement_cycle: Optional[float] = Field(0.0, description="설비의 관련 자재 교체 주기 값")
    replacement_cycle_unit: Optional[str] = Field("시간", max_length=255, description="교체 주기 단위 (예: 시간, 일, 월)")
    notes: Optional[str] = Field(None, description="비고")


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(SQLModel):
    material_category_id: Optional[int] = Field(None, description="자재 카테고리 ID (FK)")
    name: Optional[str] = Field(None, max_length=100, description="자재명")
    unit_of_measure: Optional[str] = Field(None, max_length=20, description="측정 단위")
    min_stock_level: Optional[float] = Field(None, description="최소 재고 수량")
    max_stock_level: Optional[float] = Field(None, description="최대 재고 수량")
    msds_link: Optional[str] = Field(None, max_length=255, description="MSDS 문서 링크")
    msds_data: Optional[Dict[str, Any]] = Field(None, description="MSDS 주요 정보 (JSONB)")
    discontinued: Optional[bool] = Field(None, description="단종 여부")
    reorder_level: Optional[int] = Field(None, description="재주문 레벨 (일반 재고 관리용)")
    related_equipment_id: Optional[int] = Field(None, description="관련 설비 ID (FK)")
    replacement_cycle: Optional[float] = Field(None, description="설비의 관련 자재 교체 주기 값")
    replacement_cycle_unit: Optional[str] = Field(None, description="교체 주기 단위")
    notes: Optional[str] = Field(None, description="비고")


class MaterialResponse(MaterialBase):
    id: int = Field(..., description="자재 품목 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 5. inv.materials_specs 테이블 스키마
# =============================================================================
class MaterialSpecBase(SQLModel):
    materials_id: int = Field(..., description="관련 자재 품목 ID (FK)")
    specs: Dict[str, Any] = Field(..., description="자재 스펙 (JSONB 형식의 키-값 쌍)")


class MaterialSpecCreate(MaterialSpecBase):
    pass


class MaterialSpecUpdate(SQLModel):
    specs: Optional[Dict[str, Any]] = Field(None, description="업데이트할 자재 스펙 (JSONB 형식의 키-값 쌍)")


class MaterialSpecResponse(MaterialSpecBase):
    # [수정] 요청하신 대로 id 필드를 다시 추가합니다.
    id: int = Field(..., description="스펙 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 6. inv.material_batches 테이블 스키마
# =============================================================================
class MaterialBatchBase(SQLModel):
    material_id: int = Field(..., description="관련 자재 품목 ID (FK)")
    facility_id: int = Field(..., description="보관 처리장 ID (FK)")
    storage_location_id: Optional[int] = Field(None, description="보관 위치 ID (FK)")
    lot_number: Optional[str] = Field(None, max_length=100, description="로트 번호")
    quantity: float = Field(..., description="재고 수량 (0 이상)")
    unit_cost: Optional[float] = Field(None, description="단가 (NUMERIC(18, 2))")
    received_date: Optional[datetime] = Field(None, description="입고 일시 (지정하지 않으면 현재 시각)")
    expiration_date: Optional[date] = Field(None, description="만료일")
    vendor_id: Optional[int] = Field(None, description="공급업체 ID (FK)")
    notes: Optional[str] = Field(None, description="비고")


class MaterialBatchCreate(MaterialBatchBase):
    pass


class MaterialBatchUpdate(MaterialBatchBase):
    quantity: Optional[float] = Field(None, description="재고 수량")


class MaterialBatchResponse(MaterialBatchBase):
    id: int = Field(..., description="배치 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 7. inv.material_transactions 테이블 스키마
# =============================================================================
class MaterialTransactionBase(SQLModel):
    material_id: int = Field(..., description="관련 자재 품목 ID (FK)")
    facility_id: int = Field(..., description="거래 발생 처리장 ID (FK)")
    transaction_type: str = Field(..., max_length=50, description="거래 유형 (PURCHASE, USAGE, RETURN, ADJUSTMENT)")
    quantity_change: float = Field(..., description="수량 변경 (양수: 입고, 음수: 출고/사용)")
    transaction_date: Optional[datetime] = Field(None, description="거래 발생 일시 (지정하지 않으면 현재 시각)")
    related_equipment_id: Optional[int] = Field(None, description="관련 설비 ID (FK)")
    related_equipment_history_id: Optional[int] = Field(None, description="관련 설비 이력 ID (FK)")
    source_batch_id: Optional[int] = Field(None, description="사용된 배치 ID (FK)")
    performed_by_user_id: Optional[int] = Field(None, description="거래 수행 사용자 ID (FK)")
    vendor_id: Optional[int] = Field(None, description="관련 공급업체 ID (FK, 구매 시)")
    unit_price: Optional[float] = Field(0.0, description="단가 (구매 시) (NUMERIC(19, 4))")
    notes: Optional[str] = Field(None, description="비고")


class MaterialTransactionCreate(MaterialTransactionBase):
    pass


class MaterialTransactionUpdate(MaterialTransactionBase):
    transaction_type: Optional[str] = Field(None, max_length=50, description="거래 유형")
    quantity_change: Optional[float] = Field(None, description="수량 변경")


class MaterialTransactionResponse(MaterialTransactionBase):
    id: int = Field(..., description="거래 이력 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True
