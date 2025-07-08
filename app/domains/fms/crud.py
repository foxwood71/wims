# app/domains/fms/crud.py

"""
'fms' 도메인 (설비 관리 시스템)과 관련된 CRUD 로직을 담당하는 모듈입니다.
"""

from typing import List, Optional, Any, Dict
from datetime import date, datetime, UTC

from sqlalchemy import text
from sqlalchemy.sql import func
from sqlalchemy.orm import selectinload

from sqlmodel import select, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import HTTPException, status

#  공통 CRUDBase 및 FMS 도메인의 모델, 스키마 임포트
from app.core.crud_base import CRUDBase
from . import models as fms_models
from . import schemas as fms_schemas
from . import tasks as fms_tasks


# =============================================================================
# 1. 설비 카테고리 (EquipmentCategory) CRUD
# =============================================================================
class CRUDEquipmentCategory(
    CRUDBase[
        fms_models.EquipmentCategory,
        fms_schemas.EquipmentCategoryCreate,
        fms_schemas.EquipmentCategoryUpdate
    ]
):
    def __init__(self):
        super().__init__(model=fms_models.EquipmentCategory)

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[fms_models.EquipmentCategory]:
        """카테고리명으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)  #
        result = await db.execute(statement)  #
        return result.scalars().one_or_none()  #

    async def create(self, db: AsyncSession, *, obj_in: fms_schemas.EquipmentCategoryCreate) -> fms_models.EquipmentCategory:
        """이름 중복을 확인하고 생성합니다."""
        if await self.get_by_name(db, name=obj_in.name):  #
            raise HTTPException(status_code=400, detail="Equipment category with this name already exists.")  #
        return await super().create(db, obj_in=obj_in)  #


equipment_category = CRUDEquipmentCategory()


# =============================================================================
# 2. 설비 스펙 정의 (EquipmentSpecDefinition) CRUD
# =============================================================================
class CRUDEquipmentSpecDefinition(
    CRUDBase[
        fms_models.EquipmentSpecDefinition,
        fms_schemas.EquipmentSpecDefinitionCreate,
        fms_schemas.EquipmentSpecDefinitionUpdate
    ]
):
    def __init__(self):
        super().__init__(model=fms_models.EquipmentSpecDefinition)

    async def create(self, db: AsyncSession, *, obj_in: fms_schemas.EquipmentSpecDefinitionCreate) -> fms_models.EquipmentSpecDefinition:
        """이름 중복을 확인하고 생성합니다."""
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Equipment spec definition with this name already exists.")
        return await super().create(db, obj_in=obj_in)

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: fms_models.EquipmentSpecDefinition,
        obj_in: fms_schemas.EquipmentSpecDefinitionUpdate,
        arq_redis_pool: Any = None  # ARQ Redis pool을 인자로 받음
    ) -> fms_models.EquipmentSpecDefinition:
        """
        업데이트 시 이름 중복을 확인하고, 이름 변경 시 관련 EquipmentSpec 동기화 작업을
        백그라운드 큐에 추가합니다. 관련 데이터가 없는 경우 즉시 반영합니다.
        """
        if obj_in.name is not None and obj_in.name != db_obj.name:
            existing_by_name = await self.get_by_name(db, name=obj_in.name)
            if existing_by_name and existing_by_name.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Equipment spec definition with this name already exists.")

            old_spec_name = db_obj.name
            new_spec_name = obj_in.name

            # 관련 EquipmentSpec 데이터가 있는지 확인
            # f-string 접두사 'f'를 제거했습니다.
            check_query = text("SELECT 1 FROM fms.equipment_specs WHERE specs ? :old_spec_name LIMIT 1;")
            result = await db.execute(check_query, {"old_spec_name": old_spec_name})
            has_related_specs = result.scalar_one_or_none() is not None

            if has_related_specs:
                # 관련 데이터가 있는 경우에만 비동기 작업 큐에 스펙 이름 변경 동기화 작업 추가
                if arq_redis_pool:
                    await arq_redis_pool.enqueue_job(
                        fms_tasks.sync_equipment_specs_on_spec_definition_name_change.__name__,
                        db_obj.id,
                        old_spec_name,
                        new_spec_name,
                    )
                    print(f"ARQ Job enqueued: sync_equipment_specs_on_spec_definition_name_change for SpecDef ID {db_obj.id}")
                else:
                    print("ARQ Redis pool not available, skipping background task for spec name change. (Related data exists)")
                    # 프로덕션에서는 이 경우 에러를 발생시키거나 경고 로깅을 해야 합니다.
            else:
                print("No related EquipmentSpec data found for name change, immediate reflection.")
                # 관련 데이터가 없으므로 동기화 태스크 불필요

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)

    async def remove(
        self,
        db: AsyncSession,
        *,
        id: int,
        arq_redis_pool: Any = None  # ARQ Redis pool을 인자로 받음
    ) -> fms_models.EquipmentSpecDefinition:
        """
        ID를 기준으로 스펙 정의를 삭제하고, 관련된 EquipmentSpec 동기화 작업을
        백그라운드 큐에 추가합니다. 관련 데이터가 없는 경우 즉시 반영합니다.
        """
        db_obj = await self.get(db, id)
        if not db_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EquipmentSpecDefinition not found")

        spec_name_to_remove = db_obj.name

        # 관련 EquipmentSpec 데이터가 있는지 확인
        # f-string 접두사 'f'를 제거했습니다.
        check_query = text("SELECT 1 FROM fms.equipment_specs WHERE specs ? :spec_name_to_remove LIMIT 1;")
        result = await db.execute(check_query, {"spec_name_to_remove": spec_name_to_remove})
        has_related_specs = result.scalar_one_or_none() is not None

        await super().remove(db, id=id)  # 먼저 스펙 정의 자체를 삭제

        if has_related_specs:
            #  관련 데이터가 있는 경우에만 비동기 작업 큐에 스펙 삭제 동기화 작업 추가
            if arq_redis_pool:
                await arq_redis_pool.enqueue_job(
                    fms_tasks.sync_equipment_specs_on_spec_definition_delete.__name__,
                    id,
                    spec_name_to_remove,
                )
                print(f"ARQ Job enqueued: sync_equipment_specs_on_spec_definition_delete for SpecDef ID {id}")
            else:
                print("ARQ Redis pool not available, skipping background task for spec delete. (Related data exists)")
                #  프로덕션에서는 이 경우 에러를 발생시키거나 경고 로깅을 해야 합니다.
        else:
            print("No related EquipmentSpec data found for delete, immediate reflection.")
            #  관련 데이터가 없으므로 동기화 태스크 불필요

        return db_obj


equipment_spec_definition = CRUDEquipmentSpecDefinition()


# =============================================================================
# 3. 설비 (Equipment) CRUD
# =============================================================================
class CRUDEquipment(
    CRUDBase[
        fms_models.Equipment,
        fms_schemas.EquipmentCreate,
        fms_schemas.EquipmentUpdate
    ]
):
    def __init__(self):
        super().__init__(model=fms_models.Equipment)

    async def get_by_serial_number(self, db: AsyncSession, *, serial_number: str) -> Optional[fms_models.Equipment]:
        """시리얼 번호로 설비를 조회합니다."""
        statement = select(self.model).where(self.model.serial_number == serial_number)  #
        result = await db.execute(statement)  #
        return result.scalars().one_or_none()  #

    async def get_by_asset_tag(self, db: AsyncSession, *, asset_tag: str) -> Optional[fms_models.Equipment]:
        """자산 태그로 설비를 조회합니다."""
        statement = select(self.model).where(self.model.asset_tag == asset_tag)  #
        result = await db.execute(statement)  #
        return result.scalars().one_or_none()  #

    async def get_by_facility_id(self, db: AsyncSession, *, facility_id: int, skip: int = 0, limit: int = 100) -> List[fms_models.Equipment]:
        """특정 처리장의 설비 목록을 조회합니다."""
        statement = select(self.model).where(self.model.facility_id == facility_id).offset(skip).limit(limit)  #
        result = await db.execute(statement)  #
        return result.scalars().all()  #

    async def get_by_location_id(self, db: AsyncSession, *, location_id: int, skip: int = 0, limit: int = 100) -> List[fms_models.Equipment]:
        """특정 장소의 설비 목록을 조회합니다."""
        statement = select(self.model).where(self.model.current_location_id == location_id).offset(skip).limit(limit)  #
        result = await db.execute(statement)  #
        return result.scalars().all()  #

    async def create(self, db: AsyncSession, *, obj_in: fms_schemas.EquipmentCreate) -> fms_models.Equipment:
        """FK 유효성 및 시리얼 번호 중복을 확인하고 생성합니다."""
        #  순환참조를 피하기 위해 함수 내에서 임포트
        from app.domains.loc.crud import facility, location

        if not await facility.get(db, id=obj_in.facility_id):
            raise HTTPException(status_code=404, detail="Facility not found.")  #
        if not await equipment_category.get(db, id=obj_in.equipment_category_id):
            raise HTTPException(status_code=404, detail="Equipment category not found.")  #
        if obj_in.current_location_id and not await location.get(db, id=obj_in.current_location_id):
            raise HTTPException(status_code=404, detail="Location not found.")  #
        if obj_in.serial_number and await self.get_by_serial_number(db, serial_number=obj_in.serial_number):
            raise HTTPException(status_code=400, detail="Equipment with this serial number already exists.")  #
        if obj_in.asset_tag and await self.get_by_asset_tag(db, asset_tag=obj_in.asset_tag):
            raise HTTPException(status_code=400, detail="Equipment with this asset tag already exists.")  #

        return await super().create(db, obj_in=obj_in)  #


equipment = CRUDEquipment()


# =============================================================================
# 4. 설비 이력 (EquipmentHistory) CRUD
# =============================================================================
class CRUDEquipmentHistory(
    CRUDBase[
        fms_models.EquipmentHistory,
        fms_schemas.EquipmentHistoryCreate,
        fms_schemas.EquipmentHistoryUpdate
    ]
):
    def __init__(self):
        super().__init__(model=fms_models.EquipmentHistory)

    async def get_by_equipment_id_with_paging(self, db: AsyncSession, *, equipment_id: int, skip: int = 0, limit: int = 100) -> List[fms_models.EquipmentHistory]:
        """특정 설비의 이력 기록을 조회합니다. (최신순 정렬)"""
        statement = (
            select(self.model)
            .where(self.model.equipment_id == equipment_id)
            .order_by(self.model.change_date.desc(), self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )  #
        result = await db.execute(statement)  #
        return result.scalars().all()  #


equipment_history = CRUDEquipmentHistory()


# =============================================================================
# 5. 설비 스펙 (EquipmentSpec) CRUD
# =============================================================================
class CRUDEquipmentSpec(
    CRUDBase[
        fms_models.EquipmentSpec,
        fms_schemas.EquipmentSpecCreate,
        fms_schemas.EquipmentSpecUpdate
    ]
):
    def __init__(self):
        super().__init__(model=fms_models.EquipmentSpec)

    async def _validate_specs_for_equipment(
        self, db: AsyncSession, *, equipment_id: int, specs_to_validate: Dict[str, Any]
    ):
        """
        설비의 스펙을 검증합니다.
        설비가 속한 카테고리에 정의된 스펙 키만 허용합니다.
        """
        stmt = (
            select(fms_models.EquipmentSpecDefinition.name)
            .join(fms_models.EquipmentCategorySpecDefinition, fms_models.EquipmentSpecDefinition.id == fms_models.EquipmentCategorySpecDefinition.spec_definition_id)
            .join(fms_models.Equipment, fms_models.Equipment.equipment_category_id == fms_models.EquipmentCategorySpecDefinition.equipment_category_id)
            .where(fms_models.Equipment.id == equipment_id)
        )
        result = await db.execute(stmt)
        allowed_spec_names = set(result.scalars().all())

        for key in specs_to_validate.keys():
            if key not in allowed_spec_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid spec key: '{key}'. This key is not defined for the equipment's category."
                )

    async def get_by_equipment_id(self, db: AsyncSession, *, equipment_id: int) -> Optional[fms_models.EquipmentSpec]:
        """특정 설비의 스펙 정보를 조회합니다."""
        statement = select(self.model).where(self.model.equipment_id == equipment_id)  #
        result = await db.execute(statement)  #
        return result.scalars().one_or_none()  #

    async def create(self, db: AsyncSession, *, obj_in: fms_schemas.EquipmentSpecCreate) -> fms_models.EquipmentSpec:
        """스펙 유효성 검사를 추가한 후 스펙을 생성합니다."""
        await self._validate_specs_for_equipment(
            db, equipment_id=obj_in.equipment_id, specs_to_validate=obj_in.specs
        )
        return await super().create(db, obj_in=obj_in)

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: fms_models.EquipmentSpec,
        obj_in: fms_schemas.EquipmentSpecUpdate
    ) -> fms_models.EquipmentSpec:
        """스펙 유효성 검사를 추가한 후 스펙을 업데이트합니다."""
        update_data = obj_in.model_dump(exclude_unset=True)

        if 'specs' in update_data:
            await self._validate_specs_for_equipment(
                db, equipment_id=db_obj.equipment_id, specs_to_validate=update_data['specs']
            )

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


equipment_spec = CRUDEquipmentSpec()


# =============================================================================
# 6. 설비 카테고리 - 스펙 정의 연결 (EquipmentCategorySpecDefinition) CRUD
# =============================================================================
class CRUDEquipmentCategorySpecDefinition(
    CRUDBase[
        fms_models.EquipmentCategorySpecDefinition,
        fms_schemas.EquipmentCategorySpecDefinitionCreate,
        fms_schemas.EquipmentCategorySpecDefinitionCreate
    ]
):
    def __init__(self):
        super().__init__(model=fms_models.EquipmentCategorySpecDefinition)

    async def add_spec_to_category_and_update_equipment(
        self, db: AsyncSession, *, link_create: fms_schemas.EquipmentCategorySpecDefinitionCreate, spec_name: str
    ) -> fms_models.EquipmentCategorySpecDefinition:
        """카테고리에 스펙 정의를 연결하고, 해당 카테고리의 모든 설비에 스펙 필드를 추가합니다."""
        link = await super().create(db=db, obj_in=link_create)  #

        equipment_ids_result = await db.execute(
            select(fms_models.Equipment.id).where(fms_models.Equipment.equipment_category_id == link_create.equipment_category_id)
        )  #
        equipment_ids = equipment_ids_result.scalars().all()  #

        if not equipment_ids:
            return link  #

        #  설비 스펙에 null 값으로 새 키를 추가하는 로직
        #  (이미 스펙 레코드가 없는 설비를 위해 upsert 방식 고려 가능)
        update_statement = (
            fms_models.EquipmentSpec.__table__.update()
            .where(fms_models.EquipmentSpec.equipment_id.in_(equipment_ids))
            .values(specs=func.jsonb_set(fms_models.EquipmentSpec.specs, text(f"'{{{spec_name}}}'"), text("'null'::jsonb"), True))
        )  #
        await db.execute(update_statement)  #

        return link  #

    async def remove_spec_from_category_and_update_equipment(
        self, db: AsyncSession, *, equipment_category_id: int, spec_definition_id: int, spec_name: str
    ) -> Optional[fms_models.EquipmentCategorySpecDefinition]:
        """카테고리-스펙 정의 연결을 삭제하고, 해당 카테고리의 모든 설비에서 스펙 필드를 제거합니다."""
        db_obj = await self.get_link(db, equipment_category_id=equipment_category_id, spec_definition_id=spec_definition_id)  #
        if not db_obj:
            return None  #

        await db.delete(db_obj)  #

        equipment_ids_result = await db.execute(
            select(fms_models.Equipment.id).where(fms_models.Equipment.equipment_category_id == equipment_category_id)
        )  #
        equipment_ids = equipment_ids_result.scalars().all()  #

        if not equipment_ids:
            return db_obj  #

        update_statement = text(
            """
            UPDATE fms.equipment_specs
            SET specs = specs - :spec_name
            WHERE equipment_id = ANY(:equipment_ids)
            """
        )  #
        await db.execute(update_statement, {"spec_name": spec_name, "equipment_ids": equipment_ids})  #

        return db_obj  #

    async def get_link(self, db: AsyncSession, *, equipment_category_id: int, spec_definition_id: int) -> Optional[fms_models.EquipmentCategorySpecDefinition]:
        """특정 카테고리와 스펙 정의 간의 연결을 조회합니다."""
        statement = select(self.model).where(
            self.model.equipment_category_id == equipment_category_id,
            self.model.spec_definition_id == spec_definition_id
        )  #
        result = await db.execute(statement)  #
        return result.scalars().one_or_none()  #

    async def get_by_category_id(self, db: AsyncSession, *, equipment_category_id: int) -> List[fms_models.EquipmentSpecDefinition]:
        """특정 설비 카테고리에 연결된 모든 스펙 정의를 조회합니다."""
        statement = select(fms_models.EquipmentSpecDefinition).join(
            fms_models.EquipmentCategorySpecDefinition,
            fms_models.EquipmentSpecDefinition.id == fms_models.EquipmentCategorySpecDefinition.spec_definition_id
        ).where(
            fms_models.EquipmentCategorySpecDefinition.equipment_category_id == equipment_category_id
        )  #
        result = await db.execute(statement)  #
        return result.scalars().all()  #


equipment_category_spec_definition = CRUDEquipmentCategorySpecDefinition()
