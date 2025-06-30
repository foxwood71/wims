# app/domains/ven/schemas.py

"""
'ven' 도메인 (공급업체 관리)의 API 데이터 전송 객체(DTO)를 정의하는 모듈입니다.
응답 스키마는 다른 도메인과의 일관성을 위해 '...Read' 패턴을 사용합니다.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import EmailStr


# =============================================================================
# 1. 공급업체 카테고리 (VendorCategory) 스키마
# =============================================================================
class VendorCategoryBase(SQLModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class VendorCategoryCreate(VendorCategoryBase):
    pass


class VendorCategoryUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None


# [수정] VendorCategoryResponse -> VendorCategoryRead 로 이름 변경
class VendorCategoryRead(VendorCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:  # Pydantic이 ORM 객체의 속성에서 데이터를 가져와 스키마를 구성
        from_attributes = True  # SQLModel (Pydantic v2)에서는 from_attributes = True 를 사용
                                # Pydantic v1 에서는 orm_mode = True 를 사용


# =============================================================================
# 2. 공급업체 담당자 (VendorContact) 스키마
# =============================================================================
class VendorContactBase(SQLModel):
    vendor_id: int
    name: str = Field(..., max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None


class VendorContactCreate(VendorContactBase):
    pass


class VendorContactUpdate(SQLModel):
    name: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


# [수정] VendorContactResponse -> VendorContactRead 로 이름 변경
class VendorContactRead(VendorContactBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:  # Pydantic이 ORM 객체의 속성에서 데이터를 가져와 스키마를 구성
        from_attributes = True  # SQLModel (Pydantic v2)에서는 from_attributes = True 를 사용
                                # Pydantic v1 에서는 orm_mode = True 를 사용


# =============================================================================
# 3. 공급업체 (Vendor) 스키마
# =============================================================================
class VendorBase(SQLModel):
    name: str = Field(..., max_length=100)
    business_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(SQLModel):
    name: Optional[str] = None
    business_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    description: Optional[str] = None


# [수정] VendorResponse -> VendorRead 로 이름 변경
class VendorRead(VendorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:  # Pydantic이 ORM 객체의 속성에서 데이터를 가져와 스키마를 구성
        from_attributes = True  # SQLModel (Pydantic v2)에서는 from_attributes = True 를 사용
                    # Pydantic v1 에서는 orm_mode = True 를 사용


# [추가] 상세 정보 조회를 위해 담당자 목록을 포함하는 스키마
class VendorReadWithDetails(VendorRead):
    contacts: List[VendorContactRead] = []
    # 카테고리 정보도 포함하고 싶다면 아래와 같이 추가할 수 있습니다.
    # categories: List[VendorCategoryRead] = []


# =============================================================================
# 4. 공급업체-카테고리 연결 (VendorVendorCategory) 스키마
# =============================================================================
class VendorVendorCategoryBase(SQLModel):
    vendor_id: int
    vendor_category_id: int


class VendorVendorCategoryCreate(VendorVendorCategoryBase):
    pass


# [수정] VendorVendorCategoryResponse -> VendorVendorCategoryRead 로 이름 변경
class VendorVendorCategoryRead(VendorVendorCategoryBase):
    created_at: datetime
    updated_at: datetime

    class Config:  # Pydantic이 ORM 객체의 속성에서 데이터를 가져와 스키마를 구성
        from_attributes = True  # SQLModel (Pydantic v2)에서는 from_attributes = True 를 사용
                                # Pydantic v1 에서는 orm_mode = True 를 사용
