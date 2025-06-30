# app/domains/inv/crud.py

"""
'inv' 도메인 (자재 및 재고 관리)과 관련된 CRUD 로직을 담당하는 모듈입니다.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException, status, Request
from datetime import datetime, UTC
from sqlalchemy.sql import text

from app.core.crud_base import CRUDBase
from . import models as inv_models
from . import schemas as inv_schemas

# ARQ 태스크 임포트
from app.tasks import inv_tasks


# =============================================================================
# 1. 자재 카테고리 (MaterialCategory) CRUD
# =============================================================================
class CRUDMaterialCategory(
    CRUDBase[
        inv_models.MaterialCategory,
        inv_schemas.MaterialCategoryCreate,
        inv_schemas.MaterialCategoryUpdate
    ]
):
    def __init__(self):
        super().__init__(model=inv_models.MaterialCategory)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[inv_models.MaterialCategory]:
        """카테고리 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: inv_schemas.MaterialCategoryCreate) -> inv_models.MaterialCategory:
        """코드 중복을 확인하고 생성합니다."""
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=400, detail="Material category with this code already exists.")
        return await super().create(db, obj_in=obj_in)


material_category = CRUDMaterialCategory()


# =============================================================================
# 2. 자재 스펙 정의 (MaterialSpecDefinition) CRUD
# =============================================================================
class CRUDMaterialSpecDefinition(
    CRUDBase[
        inv_models.MaterialSpecDefinition,
        inv_schemas.MaterialSpecDefinitionCreate,
        inv_schemas.MaterialSpecDefinitionUpdate
    ]
):
    def __init__(self):
        super().__init__(model=inv_models.MaterialSpecDefinition)

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[inv_models.MaterialSpecDefinition]:
        """스펙 정의명으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: inv_schemas.MaterialSpecDefinitionCreate) -> inv_models.MaterialSpecDefinition:
        """이름 중복을 확인하고 생성합니다."""
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=400, detail="Material spec definition with this name already exists.")
        return await super().create(db, obj_in=obj_in)

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: inv_models.MaterialSpecDefinition,
        obj_in: inv_schemas.MaterialSpecDefinitionUpdate,
        arq_redis_pool: Any = None
    ) -> inv_models.MaterialSpecDefinition:
        """
        스펙 정의를 업데이트합니다.
        만약 이름(name)이 변경되면, 연결된 모든 MaterialSpec의 키를 재귀적으로 업데이트합니다.
        """
        old_name = db_obj.name
        update_data = obj_in.model_dump(exclude_unset=True)
        new_name = update_data.get("name")

        # 부모 클래스의 update 메소드를 먼저 호출하여 스펙 정의 자체를 업데이트
        updated_db_obj = await super().update(db, db_obj=db_obj, obj_in=obj_in)

        # 이름이 변경된 경우에만 스펙 전파 로직 수행
        if new_name and old_name != new_name:
            # 이 스펙 정의를 사용하는 모든 카테고리 ID를 조회
            category_links = await db.execute(
                select(inv_models.MaterialCategorySpecDefinition.material_category_id)
                .where(inv_models.MaterialCategorySpecDefinition.spec_definition_id == db_obj.id)
            )
            category_ids = category_links.scalars().all()

            #  관련 MaterialSpec 데이터가 있는지 확인
            #  (해당 카테고리에 속한 Material의 MaterialSpec 중 old_name을 포함하는 것이 있는지)
            check_query = text("""
                SELECT 1 FROM inv.materials_specs AS ms
                JOIN inv.materials AS m ON ms.materials_id = m.id
                WHERE m.material_category_id = ANY(:category_ids) AND ms.specs ? :old_name
                LIMIT 1;
            """)
            result = await db.execute(check_query, {"category_ids": category_ids, "old_name": old_name})
            has_related_specs = result.scalar_one_or_none() is not None

            if category_ids:
                if has_related_specs:
                    #  관련 데이터가 있는 경우에만 비동기 작업 큐에 스펙 이름 변경 동기화 작업 추가
                    if arq_redis_pool:
                        await arq_redis_pool.enqueue_job(
                            inv_tasks.sync_material_specs_on_spec_definition_name_change.__name__,
                            updated_db_obj.id,
                            old_name,
                            new_name,
                            category_ids  # 카테고리 ID 목록 전달
                        )
                        print(f"ARQ Job enqueued: sync_material_specs_on_spec_definition_name_change for SpecDef ID {updated_db_obj.id}")
                    else:
                        print("ARQ Redis pool not available, skipping background task for spec name change. (Related data exists)")
                        #  프로덕션에서는 이 경우 에러를 발생시키거나 경고 로깅을 해야 합니다.
                else:
                    print("No related MaterialSpec data found for name change, immediate reflection (no sync needed).")
            else:
                print("No categories linked to this spec definition, no MaterialSpec sync needed.")

        return updated_db_obj

        # if category_ids:
        #     # 해당 카테고리들에 속한 모든 자재와 그 스펙을 조회
        #     stmt = (
        #         select(inv_models.Material)
        #         .where(inv_models.Material.material_category_id.in_(category_ids))
        #         .options(selectinload(inv_models.Material.specs))
        #     )
        #     materials_to_update = (await db.execute(stmt)).scalars().all()

        #     for material in materials_to_update:
        #         if material.specs and old_name in material.specs.specs:
        #             # 기존 키의 값을 가져와 새 키로 변경하고, 기존 키는 삭제
        #             material.specs.specs[new_name] = material.specs.specs.pop(old_name)
        #             flag_modified(material.specs, "specs")

        # # 부모 클래스의 update 메소드를 호출하여 스펙 정의 자체를 업데이트
        # return await super().update(db, db_obj=db_obj, obj_in=obj_in)


material_spec_definition = CRUDMaterialSpecDefinition()


# =============================================================================
# 3. 자재 카테고리 - 스펙 정의 연결 (MaterialCategorySpecDefinition) CRUD
# =============================================================================
class CRUDMaterialCategorySpecDefinition(
    CRUDBase[
        inv_models.MaterialCategorySpecDefinition,
        inv_schemas.MaterialCategorySpecDefinitionCreate,
        inv_schemas.MaterialCategorySpecDefinitionCreate
    ]
):
    def __init__(self):
        super().__init__(model=inv_models.MaterialCategorySpecDefinition)

    async def get_link(self, db: AsyncSession, *, material_category_id: int, spec_definition_id: int) -> Optional[inv_models.MaterialCategorySpecDefinition]:
        statement = select(self.model).where(
            self.model.material_category_id == material_category_id,
            self.model.spec_definition_id == spec_definition_id
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_spec_definitions_for_category(self, db: AsyncSession, *, material_category_id: int) -> List[inv_models.MaterialSpecDefinition]:
        statement = select(inv_models.MaterialSpecDefinition).join(
            inv_models.MaterialCategorySpecDefinition
        ).where(
            inv_models.MaterialCategorySpecDefinition.material_category_id == material_category_id
        )
        result = await db.execute(statement)
        return result.scalars().all()

    # async def create(self, db: AsyncSession, *, obj_in: inv_schemas.MaterialCategorySpecDefinitionCreate) -> inv_models.MaterialCategorySpecDefinition:
    #     if await self.get_link(db, material_category_id=obj_in.material_category_id, spec_definition_id=obj_in.spec_definition_id):
    #         raise HTTPException(status_code=400, detail="This link already exists.")
    #     return await super().create(db, obj_in=obj_in)

    # async def create(
    #     self,
    #     db: AsyncSession,
    #     *,
    #     obj_in: inv_schemas.MaterialCategorySpecDefinitionCreate,
    #     arq_redis_pool: Any = None  # ARQ Redis pool을 인자로 받음
    # ) -> inv_models.MaterialCategorySpecDefinition:
    #     """
    #     카테고리에 스펙 정의를 연결하고, 관련된 모든 자재의 스펙에 해당 키를 null 값으로
    #     자동 추가하는 작업을 비동기 큐에 추가합니다.
    #     """
    #     if await self.get_link(db, material_category_id=obj_in.material_category_id, spec_definition_id=obj_in.spec_definition_id):
    #         raise HTTPException(status_code=400, detail="This link already exists.")

    #     created_link = await super().create(db, obj_in=obj_in)

    #     #  연결된 MaterialSpecDefinition의 이름을 가져옵니다.
    #     spec_def = await material_spec_definition.get(db, id=obj_in.spec_definition_id)
    #     if spec_def:
    #         new_spec_name = spec_def.name
    #         target_category_id = obj_in.material_category_id

    #         #  동기화 작업을 비동기 큐에 추가
    #         if arq_redis_pool:
    #             #  MaterialSpec에 새 스펙 필드 추가 작업을 위한 새로운 태스크 정의가 필요합니다.
    #             #  (예: app.tasks.inv_material_tasks.add_new_spec_to_material_specs)
    #             #  현재는 이 로직이 라우터에 직접 구현되어 있으므로,
    #             #  해당 로직을 태스크 함수로 옮긴 후 호출해야 합니다.
    #             print("ARQ: New spec field addition to MaterialSpecs is not yet implemented as a background task.")
    #             print("Proceeding with direct sync for MaterialCategorySpecDefinition link creation.")
    #         else:
    #             print("ARQ Redis pool not available, proceeding with direct sync for MaterialCategorySpecDefinition link creation.")

    #         #  현재는 라우터에서 동기적으로 처리하던 로직을 그대로 유지
    #         #  (이 부분도 대량 데이터 시 태스크로 전환하는 것을 권장)
    #         stmt = (
    #             select(inv_models.Material)
    #             .where(inv_models.Material.material_category_id == target_category_id)
    #             .options(selectinload(inv_models.Material.specs))
    #         )
    #         materials = (await db.execute(stmt)).scalars().all()

    #         for material_obj in materials:  # 'material'이 예약어와 겹칠 수 있으므로 'material_obj'로 변경
    #             if material_obj.specs:
    #                 if new_spec_name not in material_obj.specs.specs:
    #                     material_obj.specs.specs[new_spec_name] = None
    #                     flag_modified(material_obj.specs, "specs")
    #             else:
    #                 new_spec = inv_models.MaterialSpec(materials_id=material_obj.id, specs={new_spec_name: None})
    #                 db.add(new_spec)
    #         await db.commit()  # for 루프 밖에서 한 번만 커밋

    #     return created_link

    # async def delete_link(self, db: AsyncSession, *, material_category_id: int, spec_definition_id: int) -> Optional[inv_models.MaterialCategorySpecDefinition]:
    #     db_obj = await self.get_link(db, material_category_id=material_category_id, spec_definition_id=spec_definition_id)
    #     if not db_obj:
    #         return None
    #     await db.delete(db_obj)
    #     await db.commit()
    #     return db_obj

    # async def delete_link(
    #     self,
    #     db: AsyncSession,
    #     *,
    #     material_category_id: int,
    #     spec_definition_id: int,
    #     arq_redis_pool: Any = None  # ARQ Redis pool을 인자로 받음
    # ) -> Optional[inv_models.MaterialCategorySpecDefinition]:
    #     """
    #     카테고리와 스펙 정의 연결을 해제하고, 관련된 모든 자재의 스펙에서 해당 키를 삭제합니다.
    #     관련 데이터가 없는 경우 즉시 반영합니다.
    #     """
    #     db_obj = await self.get_link(db, material_category_id=material_category_id, spec_definition_id=spec_definition_id)
    #     if not db_obj:
    #         return None

    #     #  연결된 MaterialSpecDefinition의 이름을 가져옵니다.
    #     spec_def_to_delete = await material_spec_definition.get(db, id=spec_definition_id)
    #     if not spec_def_to_delete:
    #         raise HTTPException(status_code=404, detail="Spec definition to remove not found.")
    #     key_to_remove = spec_def_to_delete.name

    #     #  관련 MaterialSpec 데이터가 있는지 확인
    #     #  (해당 카테고리에 속한 Material의 MaterialSpec 중 key_to_remove를 포함하는 것이 있는지)
    #     check_query = text(f"""
    #         SELECT 1 FROM inv.materials_specs AS ms
    #         JOIN inv.materials AS m ON ms.materials_id = m.id
    #         WHERE m.material_category_id = :material_category_id AND ms.specs ? :key_to_remove
    #         LIMIT 1;
    #     """)
    #     result = await db.execute(check_query, {"material_category_id": material_category_id, "key_to_remove": key_to_remove})
    #     has_related_specs = result.scalar_one_or_none() is not None

    #     #  먼저 연결 자체를 삭제 (이것은 항상 빠르게 수행됨)
    #     await db.delete(db_obj)
    #     await db.commit()

    #     if has_related_specs:
    #         #  관련 데이터가 있는 경우에만 비동기 작업 큐에 스펙 삭제 동기화 작업 추가
    #         if arq_redis_pool:
    #             await arq_redis_pool.enqueue_job(
    #                 inv_tasks.sync_material_specs_on_spec_definition_delete.__name__,
    #                 spec_definition_id,
    #                 key_to_remove,
    #                 [material_category_id]  # 단일 카테고리 ID를 리스트로 전달
    #             )
    #             print(f"ARQ Job enqueued: sync_material_specs_on_spec_definition_delete for SpecDef ID {spec_definition_id}")
    #         else:
    #             print("ARQ Redis pool not available, skipping background task for spec delete. (Related data exists)")
    #             #  프로덕션에서는 이 경우 에러를 발생시키거나 경고 로깅을 해야 합니다.
    #     else:
    #         print("No related MaterialSpec data found for spec key removal, immediate reflection (no sync needed).")

    #     return db_obj

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: inv_schemas.MaterialCategorySpecDefinitionCreate,
        arq_redis_pool: Any = None  # ARQ Redis pool을 인자로 받음
    ) -> inv_models.MaterialCategorySpecDefinition:
        """
        카테고리에 스펙 정의를 연결하고, 관련된 모든 자재의 스펙에 해당 키를 null 값으로
        자동 추가하는 작업을 비동기 큐에 추가합니다.
        """
        if await self.get_link(db, material_category_id=obj_in.material_category_id, spec_definition_id=obj_in.spec_definition_id):
            raise HTTPException(status_code=400, detail="This link already exists.")

        created_link = await super().create(db, obj_in=obj_in)

        #  연결된 MaterialSpecDefinition의 이름을 가져옵니다.
        spec_def = await material_spec_definition.get(db, id=obj_in.spec_definition_id)
        if spec_def:
            new_spec_name = spec_def.name
            target_category_id = obj_in.material_category_id

            #  관련 Material 데이터가 있는지 확인
            check_query = text("""
                SELECT 1 FROM inv.materials WHERE material_category_id = :material_category_id LIMIT 1;
            """)
            result = await db.execute(check_query, {"material_category_id": target_category_id})
            has_related_materials = result.scalar_one_or_none() is not None

            if has_related_materials:
                #  관련 데이터가 있는 경우에만 비동기 작업 큐에 태스크 추가
                if arq_redis_pool:
                    await arq_redis_pool.enqueue_job(
                        inv_tasks.add_spec_to_materials_in_category_task.__name__,
                        target_category_id,
                        new_spec_name
                    )
                    print(f"ARQ Job enqueued: add_spec_to_materials_in_category_task for Category ID {target_category_id}, Spec: {new_spec_name}")
                else:
                    print("ARQ Redis pool not available, skipping background task for new spec addition. (Related materials exist)")
                    #  프로덕션에서는 이 경우 에러를 발생시키거나 경고 로깅을 해야 합니다.
            else:
                print("No related Material data found for new spec addition, immediate reflection (no sync needed).")
        else:
            print("Spec definition not found, cannot enqueue add_spec_to_materials_in_category_task.")

        #  라우터에서 직접 처리하던 MaterialSpec 업데이트 로직은 이제 제거
        #  (이 로직이 이제 add_spec_to_materials_in_category_task 함수로 옮겨짐)

        return created_link

    async def delete_link(
        self,
        db: AsyncSession,
        *,
        material_category_id: int,
        spec_definition_id: int,
        arq_redis_pool: Any = None  # ARQ Redis pool을 인자로 받음
    ) -> Optional[inv_models.MaterialCategorySpecDefinition]:
        """
        카테고리와 스펙 정의 연결을 해제하고, 관련된 모든 자재의 스펙에서 해당 키를 삭제합니다.
        관련 데이터가 없는 경우 즉시 반영합니다.
        """
        db_obj = await self.get_link(db, material_category_id=material_category_id, spec_definition_id=spec_definition_id)
        if not db_obj:
            return None

        #  연결된 MaterialSpecDefinition의 이름을 가져옵니다.
        spec_def_to_delete = await material_spec_definition.get(db, id=spec_definition_id)
        if not spec_def_to_delete:
            #  스펙 정의가 이미 삭제되었을 수 있으므로 이 경우에도 링크 삭제는 진행
            print(f"Warning: Spec definition ID {spec_definition_id} not found during delete_link operation. Proceeding with link removal and potential spec key removal.")
            key_to_remove = "UNKNOWN_SPEC_NAME"  # Fallback
        else:
            key_to_remove = spec_def_to_delete.name

        #  관련 MaterialSpec 데이터가 있는지 확인
        check_query = text("""
            SELECT 1 FROM inv.materials_specs AS ms
            JOIN inv.materials AS m ON ms.materials_id = m.id
            WHERE m.material_category_id = :material_category_id AND ms.specs ? :key_to_remove
            LIMIT 1;
        """)
        result = await db.execute(check_query, {"material_category_id": material_category_id, "key_to_remove": key_to_remove})
        has_related_specs = result.scalar_one_or_none() is not None

        #  먼저 연결 자체를 삭제 (이것은 항상 빠르게 수행됨)
        await db.delete(db_obj)
        await db.commit()

        if has_related_specs:
            #  관련 데이터가 있는 경우에만 비동기 작업 큐에 스펙 삭제 동기화 작업 추가
            if arq_redis_pool:
                await arq_redis_pool.enqueue_job(
                    inv_tasks.sync_material_specs_on_spec_definition_delete.__name__,
                    spec_definition_id,
                    key_to_remove,
                    [material_category_id]  # 단일 카테고리 ID를 리스트로 전달
                )
                print(f"ARQ Job enqueued: sync_material_specs_on_spec_definition_delete for SpecDef ID {spec_definition_id}")
            else:
                print("ARQ Redis pool not available, skipping background task for spec delete. (Related data exists)")
        else:
            print("No related MaterialSpec data found for spec key removal, immediate reflection (no sync needed).")

        return db_obj


material_category_spec_definition = CRUDMaterialCategorySpecDefinition()


# =============================================================================
# 4. 자재 (Material) CRUD
# =============================================================================
class CRUDMaterial(
    CRUDBase[
        inv_models.Material,
        inv_schemas.MaterialCreate,
        inv_schemas.MaterialUpdate
    ]
):
    def __init__(self):
        super().__init__(model=inv_models.Material)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[inv_models.Material]:
        """코드로 자재를 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_materials_by_category(self, db: AsyncSession, *, category_id: int, skip: int = 0, limit: int = 100) -> List[inv_models.Material]:
        statement = select(self.model).where(self.model.material_category_id == category_id).offset(skip).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: inv_schemas.MaterialCreate) -> inv_models.Material:
        from app.domains.fms.crud import equipment as equipment_crud

        if not await material_category.get(db, id=obj_in.material_category_id):
            raise HTTPException(status_code=404, detail="Material category not found.")
        if obj_in.related_equipment_id and not await equipment_crud.get(db, id=obj_in.related_equipment_id):
            raise HTTPException(status_code=404, detail="Related equipment not found.")
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=400, detail="Material with this code already exists.")

        return await super().create(db, obj_in=obj_in)


material = CRUDMaterial()


# =============================================================================
# 5. 자재 스펙 (MaterialSpec) CRUD
# =============================================================================
class CRUDMaterialSpec(
    CRUDBase[
        inv_models.MaterialSpec,
        inv_schemas.MaterialSpecCreate,
        inv_schemas.MaterialSpecUpdate
    ]
):
    def __init__(self):
        super().__init__(model=inv_models.MaterialSpec)

    async def _validate_specs(self, db: AsyncSession, material_id: int, specs: dict):
        stmt = (
            select(inv_models.Material)
            .where(inv_models.Material.id == material_id)
            .options(
                selectinload(inv_models.Material.material_category)
                .selectinload(inv_models.MaterialCategory.spec_definitions)
            )
        )
        result = await db.execute(stmt)
        material = result.scalars().one_or_none()

        if not material or not material.material_category:
            raise HTTPException(status_code=404, detail="Material or its category not found.")

        allowed_spec_names = {spec_def.name for spec_def in material.material_category.spec_definitions}

        for key in specs.keys():
            if key not in allowed_spec_names:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid spec key '{key}'. It is not defined for this material's category."
                )

    async def get_specs_for_material(self, db: AsyncSession, *, materials_id: int) -> Optional[inv_models.MaterialSpec]:
        statement = select(self.model).where(self.model.materials_id == materials_id)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: inv_schemas.MaterialSpecCreate) -> inv_models.MaterialSpec:
        await self._validate_specs(db, material_id=obj_in.materials_id, specs=obj_in.specs)
        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: inv_models.MaterialSpec, obj_in: inv_schemas.MaterialSpecUpdate) -> inv_models.MaterialSpec:
        update_data = obj_in.model_dump(exclude_unset=True)

        if "specs" in update_data:
            await self._validate_specs(db, material_id=db_obj.materials_id, specs=update_data["specs"])

        for field, value in update_data.items():
            if field == "specs" and isinstance(db_obj.specs, dict) and isinstance(value, dict):
                for spec_key, spec_value in value.items():
                    if spec_value is None:
                        db_obj.specs.pop(spec_key, None)
                    else:
                        db_obj.specs[spec_key] = spec_value
                flag_modified(db_obj, "specs")
            else:
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


material_spec = CRUDMaterialSpec()


# =============================================================================
# 6. 자재 배치 (MaterialBatch) CRUD
# =============================================================================
class CRUDMaterialBatch(
    CRUDBase[
        inv_models.MaterialBatch,
        inv_schemas.MaterialBatchCreate,
        inv_schemas.MaterialBatchUpdate
    ]
):
    def __init__(self):
        super().__init__(model=inv_models.MaterialBatch)

    async def get_multi_by_filters(
        self, db: AsyncSession, *, material_id: Optional[int] = None, facility_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[inv_models.MaterialBatch]:
        statement = select(self.model)
        if material_id is not None:
            statement = statement.where(self.model.material_id == material_id)
        if facility_id is not None:
            statement = statement.where(self.model.facility_id == facility_id)

        statement = statement.offset(skip).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()

    async def get_batches_by_material_and_plant(self, db: AsyncSession, *, material_id: int, facility_id: int) -> List[inv_models.MaterialBatch]:
        statement = (
            select(self.model)
            .where(self.model.material_id == material_id, self.model.facility_id == facility_id, self.model.quantity > 0)
            .order_by(self.model.received_date)
        )
        result = await db.execute(statement)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: inv_schemas.MaterialBatchCreate) -> inv_models.MaterialBatch:
        # [수정] 'wastewater_plant' -> 'facility'
        from app.domains.loc.crud import facility, location
        from app.domains.ven.crud import vendor

        if not await material.get(db, id=obj_in.material_id):
            raise HTTPException(status_code=404, detail="Material not found.")
        # [수정] 'wastewater_plant' -> 'facility'
        if not await facility.get(db, id=obj_in.facility_id):
            raise HTTPException(status_code=404, detail="Wastewater plant not found.")
        if obj_in.storage_location_id and not await location.get(db, id=obj_in.storage_location_id):
            raise HTTPException(status_code=404, detail="Storage location not found.")
        if obj_in.vendor_id and not await vendor.get(db, id=obj_in.vendor_id):
            raise HTTPException(status_code=404, detail="Vendor not found.")

        return await super().create(db, obj_in=obj_in)


material_batch = CRUDMaterialBatch()


# =============================================================================
# 7. 자재 거래 (MaterialTransaction) CRUD
# =============================================================================
class CRUDMaterialTransaction(
    CRUDBase[
        inv_models.MaterialTransaction,
        inv_schemas.MaterialTransactionCreate,
        inv_schemas.MaterialTransactionUpdate
    ]
):
    def __init__(self):
        super().__init__(model=inv_models.MaterialTransaction)

    async def create(self, db: AsyncSession, *, obj_in: inv_schemas.MaterialTransactionCreate) -> inv_models.MaterialTransaction:
        # [수정] 'wastewater_plant' -> 'facility'
        from app.domains.usr.crud import user
        from app.domains.loc.crud import facility
        from app.domains.fms.crud import equipment, equipment_history
        from app.domains.ven.crud import vendor

        db_material = await material.get(db, id=obj_in.material_id)
        if not db_material:
            raise HTTPException(status_code=404, detail="Material not found.")

        # [수정] 'wastewater_plant' -> 'facility'
        db_plant = await facility.get(db, id=obj_in.facility_id)
        if not db_plant:
            raise HTTPException(status_code=404, detail="Wastewater plant not found.")

        if obj_in.performed_by_user_id and not await user.get(db, id=obj_in.performed_by_user_id):
            raise HTTPException(status_code=404, detail="User not found.")
        if obj_in.related_equipment_id and not await equipment.get(db, id=obj_in.related_equipment_id):
            raise HTTPException(status_code=404, detail="Related equipment not found.")
        if obj_in.related_equipment_history_id and not await equipment_history.get(db, id=obj_in.related_equipment_history_id):
            raise HTTPException(status_code=404, detail="Related equipment history not found.")
        if obj_in.vendor_id and not await vendor.get(db, id=obj_in.vendor_id):
            raise HTTPException(status_code=404, detail="Vendor not found.")
        if obj_in.source_batch_id and not await material_batch.get(db, id=obj_in.source_batch_id):
            raise HTTPException(status_code=404, detail="Source batch not found.")

        if obj_in.transaction_type == "USAGE":
            quantity_to_deduct = Decimal(str(abs(obj_in.quantity_change)))
            batches = await material_batch.get_batches_by_material_and_plant(db, material_id=obj_in.material_id, facility_id=obj_in.facility_id)

            current_stock = sum(Decimal(str(b.quantity)) for b in batches)
            if current_stock < quantity_to_deduct:
                raise HTTPException(status_code=400, detail=f"Not enough stock for material ID {obj_in.material_id}.")

            last_deducted_batch_id = None
            remaining_to_deduct = quantity_to_deduct
            for batch in batches:
                if remaining_to_deduct <= 0:
                    break

                quantity_in_batch = Decimal(str(batch.quantity))
                deduct_from_this_batch = min(remaining_to_deduct, quantity_in_batch)

                batch.quantity = float(quantity_in_batch - deduct_from_this_batch)
                remaining_to_deduct -= deduct_from_this_batch

                db.add(batch)
                last_deducted_batch_id = batch.id

            obj_in.source_batch_id = last_deducted_batch_id
            await db.commit()

        if obj_in.transaction_date is None:
            obj_in.transaction_date = datetime.now(UTC)

        return await super().create(db, obj_in=obj_in)


material_transaction = CRUDMaterialTransaction()
