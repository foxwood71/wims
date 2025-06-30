# app/domains/ven/crud.py

"""
'ven' 도메인 (PostgreSQL 'ven' 스키마)의 CRUD(Create, Read, Update, Delete)
작업을 담당하는 모듈입니다.

이 모듈은 'ven' 스키마의 테이블들 (vendor_categories, vendors,
vendor_vendor_categories, vendor_contacts)에 대한 데이터베이스 상호작용 로직을 캡슐화합니다.
SQLModel의 비동기 세션을 사용하여 비동기적으로 데이터베이스 쿼리를 실행합니다.
"""

from typing import List, Optional, Type, Any
from sqlmodel import Session, select, SQLModel
from datetime import datetime

# 'ven' 도메인의 모델과 스키마를 임포트합니다.
from app.domains.ven import models as ven_models
from app.domains.ven import schemas as ven_schemas


# =============================================================================
# 공통 CRUD Base 클래스 (모든 도메인의 crud.py 파일에서 재사용)
# =============================================================================
class CRUDBase[ModelType: SQLModel, CreateSchemaType: SQLModel, UpdateSchemaType: SQLModel]:
    """
    제네릭 CRUD 작업을 위한 기본 클래스입니다.
    이 클래스를 상속받아 특정 모델에 대한 CRUD를 구현합니다.
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """ID로 단일 레코드를 조회합니다."""
        statement = select(self.model).where(self.model.id == id)
        result = await db.execute(statement)
        # return result.first()  # 변경 전
        return result.scalars().first()  # 변경된 라인

    async def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """여러 레코드를 조회합니다."""
        statement = select(self.model).offset(skip).limit(limit)
        result = await db.execute(statement)
        #  return result.all()
        return result.scalars().all()

    async def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """새로운 레코드를 생성합니다."""
        db_obj = self.model.model_validate(obj_in)  # Pydantic v2 .model_validate
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType) -> Optional[ModelType]:
        """기존 레코드를 업데이트합니다."""
        update_data = obj_in.model_dump(exclude_unset=True)  # 변경된 필드만 추출
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: Session, id: Any) -> Optional[ModelType]:
        """ID로 레코드를 삭제합니다."""
        db_obj = await self.get(db, id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj


# =============================================================================
# 1. ven.vendor_categories 테이블 CRUD
# =============================================================================
class CRUDVendorCategory(CRUDBase[ven_models.VendorCategory, ven_schemas.VendorCategoryCreate, ven_schemas.VendorCategoryUpdate]):
    def __init__(self):
        super().__init__(ven_models.VendorCategory)

    async def get_vendor_category_by_name(self, db: Session, name: str) -> Optional[ven_models.VendorCategory]:
        """카테고리명으로 공급업체 카테고리를 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        # return result.first()  # 변경 전
        return result.scalars().first()  # 변경된 라인


# CRUD 인스턴스 생성
vendor_category = CRUDVendorCategory()


# =============================================================================
# 2. ven.vendors 테이블 CRUD
# =============================================================================
class CRUDVendor(CRUDBase[ven_models.Vendor, ven_schemas.VendorCreate, ven_schemas.VendorUpdate]):
    def __init__(self):
        super().__init__(ven_models.Vendor)

    async def get_vendor_by_name(self, db: Session, name: str) -> Optional[ven_models.Vendor]:
        """공급업체명으로 공급업체를 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        # return result.first()  # 변경 전
        return result.scalars().first()  # 변경된 라인

    async def get_vendor_by_business_number(self, db: Session, business_number: str) -> Optional[ven_models.Vendor]:
        """사업자 등록 번호로 공급업체를 조회합니다."""
        statement = select(self.model).where(self.model.business_number == business_number)
        result = await db.execute(statement)
        # return result.first()  # 변경 전
        return result.scalars().first()  # 변경된 라인S


# CRUD 인스턴스 생성
vendor = CRUDVendor()


# =============================================================================
# 3. ven.vendor_vendor_categories 테이블 CRUD (연결 테이블)
# =============================================================================
class CRUDVendorVendorCategory(CRUDBase[ven_models.VendorVendorCategory, ven_schemas.VendorVendorCategoryCreate, ven_schemas.VendorVendorCategoryRead]):
    def __init__(self):
        super().__init__(ven_models.VendorVendorCategory)

    async def get_link(self, db: Session, vendor_id: int, category_id: int) -> Optional[ven_models.VendorVendorCategory]:
        """공급업체 ID와 카테고리 ID로 연결 정보를 조회합니다."""
        statement = select(self.model).where(
            self.model.vendor_id == vendor_id,
            self.model.vendor_category_id == category_id
        )
        result = await db.execute(statement)
        # return result.first()
        link_obj = result.scalar_one_or_none()  # for debug
        print(f"DEBUG: get_link result: {link_obj}")
        return link_obj

    async def delete_link(self, db: Session, vendor_id: int, category_id: int) -> Optional[ven_models.VendorVendorCategory]:
        """공급업체와 카테고리 간의 특정 연결을 삭제합니다 (복합 PK)."""
        db_obj = await self.get_link(db, vendor_id, category_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj

    async def get_categories_for_vendor(self, db: Session, vendor_id: int) -> List[ven_models.VendorCategory]:
        """특정 공급업체에 연결된 모든 카테고리 목록을 조회합니다."""
        # Vendor 모델의 Relationship을 활용하여 JOIN 없이 직접 관련된 카테고리 조회
        # ORM 관계를 사용하지 않고 명시적으로 JOIN하는 방법도 가능
        statement = (
            select(ven_models.VendorCategory)
            .join(ven_models.VendorVendorCategory)
            .where(ven_models.VendorVendorCategory.vendor_id == vendor_id)
        )
        result = await db.execute(statement)
        #  return result.all()
        return result.scalars().all()

    async def get_links_by_category(self, db: Session, category_id: int) -> List[ven_models.VendorVendorCategory]:
        """특정 카테고리에 연결된 모든 벤더-카테고리 연결 레코드를 조회합니다."""
        statement = select(self.model).where(self.model.vendor_category_id == category_id)
        result = await db.execute(statement)
        return result.scalars().all()


# CRUD 인스턴스 생성
vendor_vendor_category = CRUDVendorVendorCategory()


# =============================================================================
# 4. ven.vendor_contacts 테이블 CRUD
# =============================================================================
class CRUDVendorContact(
    CRUDBase[
        ven_models.VendorContact,
        ven_schemas.VendorContactCreate,
        ven_schemas.VendorContactUpdate
    ]
):
    def __init__(self):
        super().__init__(ven_models.VendorContact)

    async def get_contacts_by_vendor(self, db: Session, vendor_id: int, skip: int = 0, limit: int = 100) -> List[ven_models.VendorContact]:
        """특정 공급업체에 속한 모든 담당자 목록을 조회합니다."""
        statement = select(self.model).where(self.model.vendor_id == vendor_id).offset(skip).limit(limit)
        result = await db.execute(statement)
        #  return result.all()
        return result.scalars().all()


# CRUD 인스턴스 생성
vendor_contact = CRUDVendorContact()
