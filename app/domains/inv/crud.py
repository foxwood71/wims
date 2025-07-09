# app/domains/inv/crud.py (전체 파일 내용)

"""
'inv' 도메인의 CRUD(Create, Read, Update, Delete) 작업을 위한 함수들을 정의하는 모듈입니다.
SQLModel과 SQLAlchemy를 사용하여 데이터베이스와 상호작용합니다.
"""

import logging
from typing import Any, Dict, Generic, List, Type, TypeVar, Union
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy.future import select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException

#  코어 및 다른 모듈 임포트
from app.domains.inv import models as inv_models
from app.domains.inv import schemas as inv_schemas
from app.domains.inv import tasks as inv_tasks
# app/domains/inv/crud.py (전체 파일 내용)

#  로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    모든 CRUD 작업을 위한 기본 클래스입니다.
    이 클래스를 상속받아 각 모델에 특화된 CRUD 클래스를 구현합니다.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        """ID로 단일 객체를 조회합니다."""
        result = await db.get(self.model, id)
        return result

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """여러 객체를 조회합니다."""
        materials_result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return materials_result.scalars().all()

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType
    ) -> ModelType:
        """새로운 객체를 생성합니다."""
        db_obj = self.model.model_validate(obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """기존 객체를 업데이트합니다."""
        obj_data = (
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        )

        for field in obj_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_data[field])

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> ModelType | None:
        """ID로 객체를 삭제합니다."""
        obj = await db.get(self.model, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


class MaterialCategoryCRUD(
    CRUDBase[
        inv_models.MaterialCategory,
        inv_schemas.MaterialCategoryCreate,
        inv_schemas.MaterialCategoryUpdate,
    ]
):
    """MaterialCategory 모델에 특화된 CRUD 작업을 처리합니다."""

    async def get_by_code(
        self, db: AsyncSession, *, code: str
    ) -> inv_models.MaterialCategory | None:
        """카테고리 코드로 객체를 조회합니다."""
        query = select(self.model).where(self.model.code == code)
        result = await db.execute(query)
        return result.scalar_one_or_none()


class MaterialSpecDefinitionCRUD(
    CRUDBase[
        inv_models.MaterialSpecDefinition,
        inv_schemas.MaterialSpecDefinitionCreate,
        inv_schemas.MaterialSpecDefinitionUpdate,
    ]
):
    """MaterialSpecDefinition 모델에 특화된 CRUD 작업을 처리합니다."""

    async def get_by_name(
        self, db: AsyncSession, *, name: str
    ) -> inv_models.MaterialSpecDefinition | None:
        """스펙 이름으로 객체를 조회합니다."""
        query = select(self.model).where(self.model.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: inv_models.MaterialSpecDefinition,
        obj_in: Union[inv_schemas.MaterialSpecDefinitionUpdate, Dict[str, Any]],
        arq_redis_pool
    ) -> inv_models.MaterialSpecDefinition:
        """
        스펙 정의를 업데이트합니다.
        스펙 이름(name)이 변경되면, 관련된 모든 자재의 스펙 키도
        백그라운드 작업(또는 동기 작업)으로 업데이트합니다.
        """
        old_name = db_obj.name
        update_data = (
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        )
        new_name = update_data.get("name")

        updated_obj = await super().update(db, db_obj=db_obj, obj_in=update_data)

        if new_name and old_name != new_name:
            old_key = old_name.lower().replace(' ', '_')
            new_key = new_name.lower().replace(' ', '_')

            if arq_redis_pool:
                await arq_redis_pool.enqueue_job(
                    "update_spec_key_for_all_materials",
                    db_obj.id,
                    old_key,
                    new_key,
                )
            else:
                logger.info(
                    "ARQ Redis pool not available, "
                    "performing spec key update synchronously."
                )
                await inv_tasks.update_spec_key_for_all_materials(
                    {"db": db}, db_obj.id, old_key, new_key
                )
        return updated_obj

    async def remove(
        self, db: AsyncSession, *, id: int, arq_redis_pool
    ) -> inv_models.MaterialSpecDefinition | None:
        """
        스펙 정의를 삭제합니다.
        삭제 전에 관련된 모든 자재의 스펙에서 해당 키를
        백그라운드 작업을 통해 삭제합니다.
        """
        spec_def_to_delete = await self.get(db, id)
        if not spec_def_to_delete:
            return None

        spec_key_to_remove = spec_def_to_delete.name

        if arq_redis_pool:
            await arq_redis_pool.enqueue_job(
                "remove_spec_key_from_all_materials",
                spec_def_to_delete.id,
                spec_key_to_remove,
            )
        else:
            logger.warning(
                "ARQ Redis pool not available, "
                "skipping background task for spec key removal."
            )

        return await super().delete(db, id=id)


class MaterialCategorySpecDefinitionCRUD(
    CRUDBase[
        inv_models.MaterialCategorySpecDefinition,
        inv_schemas.MaterialCategorySpecDefinitionCreate,
        inv_schemas.MaterialCategorySpecDefinitionUpdate,
    ]
):
    """MaterialCategory와 MaterialSpecDefinition의 관계 테이블 CRUD를 처리합니다."""

    async def get_by_link(
        self,
        db: AsyncSession,
        *,
        material_category_id: int,
        spec_definition_id: int,
    ) -> inv_models.MaterialCategorySpecDefinition | None:
        """카테고리 ID와 스펙 정의 ID로 연결 객체를 조회합니다."""
        query = select(self.model).where(
            self.model.material_category_id == material_category_id,
            self.model.spec_definition_id == spec_definition_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def generate_spec_key(
        self, spec_def: inv_models.MaterialSpecDefinition
    ) -> str:
        """
        스펙 정의 객체로부터 JSON 키를 생성합니다.
        'name' 필드가 이미 완전한 키라고 가정합니다.
        """
        return spec_def.name.lower().replace(' ', '_')

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: inv_schemas.MaterialCategorySpecDefinitionCreate,
        arq_redis_pool=None,
    ) -> inv_models.MaterialCategorySpecDefinition:
        """
        카테고리에 스펙 정의를 연결합니다.
        연결 후, 해당 카테고리에 속한 모든 자재에 새로운 스펙 키를
        백그라운드 작업(또는 동기 작업)으로 추가합니다.
        """
        link = await self.get_by_link(
            db,
            material_category_id=obj_in.material_category_id,
            spec_definition_id=obj_in.spec_definition_id,
        )
        if link:
            return link

        created_link = await super().create(db, obj_in=obj_in)
        spec_def = await db.get(
            inv_models.MaterialSpecDefinition, obj_in.spec_definition_id
        )
        spec_key = await self.generate_spec_key(spec_def)
        material_category_id = obj_in.material_category_id

        if arq_redis_pool:
            await arq_redis_pool.enqueue_job(
                "add_spec_key_for_all_materials",
                material_category_id,
                spec_key
            )
        else:
            logger.info(
                "ARQ Redis pool not available. "
                "Performing spec key addition synchronously for category %d.",
                material_category_id,
            )
            await inv_tasks.add_spec_key_for_all_materials(
                {"db": db}, material_category_id, spec_key
            )

        return created_link

    async def delete_link(
        self,
        db: AsyncSession,
        *,
        material_category_id: int,
        spec_definition_id: int,
        arq_redis_pool=None,
    ):
        """
        카테고리와 스펙 정의의 연결을 해제합니다.
        연결 해제 후, 관련된 모든 자재의 스펙에서 해당 키를
        백그라운드 작업(또는 동기 작업)으로 삭제합니다.
        """
        link_to_delete = await self.get_by_link(
            db,
            material_category_id=material_category_id,
            spec_definition_id=spec_definition_id,
        )
        if not link_to_delete:
            return None

        spec_def = await db.get(inv_models.MaterialSpecDefinition, spec_definition_id)
        spec_key_to_remove = await self.generate_spec_key(spec_def)

        if arq_redis_pool:
            await arq_redis_pool.enqueue_job(
                "remove_spec_key_from_materials_in_category",
                material_category_id,
                spec_key_to_remove,
            )
        else:
            logger.info(
                "ARQ Redis pool not available. "
                "Performing spec key removal synchronously for category %d.",
                material_category_id,
            )
            await inv_tasks.delete_spec_key_for_all_materials(
                {"db": db}, material_category_id, spec_key_to_remove
            )

        await db.delete(link_to_delete)
        await db.commit()
        return link_to_delete


class MaterialCRUD(
    CRUDBase[
        inv_models.Material, inv_schemas.MaterialCreate, inv_schemas.MaterialUpdate
    ]
):
    """Material 모델에 특화된 CRUD 작업을 처리합니다."""

    async def get_by_code(
        self, db: AsyncSession, *, code: str
    ) -> inv_models.Material | None:
        """자재 코드로 객체를 조회합니다."""
        query = select(self.model).where(self.model.code == code)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, *, obj_in: inv_schemas.MaterialCreate
    ) -> inv_models.Material:
        """
        새로운 자재를 생성합니다.
        생성 시, 자재가 속한 카테고리에 정의된 모든 스펙을 가져와
        해당 자재의 스펙에 null 값으로 자동 추가합니다.
        """
        material = self.model.model_validate(obj_in)
        db.add(material)
        await db.commit()
        await db.refresh(material)

        query = select(inv_models.MaterialSpecDefinition).join(
            inv_models.MaterialCategorySpecDefinition
        ).where(
            inv_models.MaterialCategorySpecDefinition.material_category_id
            == material.material_category_id
        )
        result = await db.execute(query)
        spec_definitions = result.scalars().all()

        initial_specs = {}
        if spec_definitions:
            for spec_def in spec_definitions:
                spec_key = (
                    await material_category_spec_definition.generate_spec_key(
                        spec_def
                    )
                )
                initial_specs[spec_key] = None

        if initial_specs:
            spec_obj = inv_models.MaterialSpec(
                materials_id=material.id, specs=initial_specs
            )
            db.add(spec_obj)
            await db.commit()
            await db.refresh(material)

        return material


class MaterialSpecCRUD(
    CRUDBase[
        inv_models.MaterialSpec,
        inv_schemas.MaterialSpecCreate,
        inv_schemas.MaterialSpecUpdate,
    ]
):
    """MaterialSpec 모델에 특화된 CRUD 작업을 처리합니다."""

    async def _validate_spec_keys(
        self, db: AsyncSession, materials_id: int, specs: Dict[str, Any]
    ):
        """
        입력된 스펙 키들이 해당 자재의 카테고리에 정의되어 있는지 검증합니다.
        """
        material = await db.get(inv_models.Material, materials_id)
        if not material:
            raise HTTPException(status_code=404, detail="Material not found.")

        query = select(inv_models.MaterialSpecDefinition).join(
            inv_models.MaterialCategorySpecDefinition
        ).where(
            inv_models.MaterialCategorySpecDefinition.material_category_id == material.material_category_id
        )
        result = await db.execute(query)
        spec_definitions = result.scalars().all()

        valid_keys = {
            await material_category_spec_definition.generate_spec_key(spec_def)
            for spec_def in spec_definitions
        }

        keys_to_validate = {k for k, v in specs.items() if v is not None}

        if not keys_to_validate.issubset(valid_keys):
            invalid_keys = keys_to_validate - valid_keys
            raise HTTPException(
                status_code=400,
                detail=f"Invalid spec keys provided: {list(invalid_keys)}. "
                       f"Valid keys for this material are: {list(valid_keys)}"
            )

    async def get_specs_for_material(
        self, db: AsyncSession, *, materials_id: int
    ) -> inv_models.MaterialSpec | None:
        """특정 자재의 스펙 객체를 조회합니다."""
        query = select(self.model).where(self.model.materials_id == materials_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, *, obj_in: inv_schemas.MaterialSpecCreate
    ) -> inv_models.MaterialSpec:
        """새로운 자재 스펙을 생성합니다. 생성 전 유효성 검사를 수행합니다."""
        await self._validate_spec_keys(
            db, materials_id=obj_in.materials_id, specs=obj_in.specs
        )
        return await super().create(db, obj_in=obj_in)

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: inv_models.MaterialSpec,
        obj_in: inv_schemas.MaterialSpecUpdate,
    ) -> inv_models.MaterialSpec:
        """
        기존 자재 스펙을 업데이트합니다.
        값이 null인 키는 삭제하고, 나머지는 추가/업데이트합니다.
        """
        await self._validate_spec_keys(
            db, materials_id=db_obj.materials_id, specs=obj_in.specs
        )

        updated_specs = db_obj.specs.copy()

        for key, value in obj_in.specs.items():
            if value is None:
                updated_specs.pop(key, None)
            else:
                updated_specs[key] = value

        db_obj.specs = updated_specs

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class MaterialBatchCRUD(
    CRUDBase[
        inv_models.MaterialBatch,
        inv_schemas.MaterialBatchCreate,
        inv_schemas.MaterialBatchUpdate,
    ]
):
    """MaterialBatch 모델에 특화된 CRUD 작업을 처리합니다."""

    async def get_by_batch_number(
        self, db: AsyncSession, *, batch_number: str
    ) -> inv_models.MaterialBatch | None:
        """배치 번호로 객체를 조회합니다."""
        query = select(self.model).where(self.model.lot_number == batch_number)
        result = await db.execute(query)
        return result.scalar_one_or_none()


class MaterialTransactionCRUD(
    CRUDBase[
        inv_models.MaterialTransaction,
        inv_schemas.MaterialTransactionCreate,
        inv_schemas.MaterialTransactionUpdate,
    ]
):
    """
    MaterialTransaction 모델에 특화된 CRUD 작업을 처리합니다.
    거래 유형에 따라 다른 비즈니스 로직을 수행합니다.
    """

    async def create(
        self, db: AsyncSession, *, obj_in: inv_schemas.MaterialTransactionCreate
    ) -> Union[inv_models.MaterialTransaction, List[inv_models.MaterialTransaction]]:
        """
        새로운 자재 거래를 생성합니다.
        - USAGE: FIFO 로직에 따라 재고를 차감합니다.
        - PURCHASE: 새로운 배치를 생성하고 재고를 추가합니다.
        """
        if obj_in.transaction_type == "USAGE":
            return await self._create_usage_transaction(db, obj_in)
        elif obj_in.transaction_type == "PURCHASE":
            return await self._create_purchase_transaction(db, obj_in)
        else:
            raise NotImplementedError(
                f"Transaction type '{obj_in.transaction_type}' is not implemented."
            )

    async def _create_purchase_transaction(
        self, db: AsyncSession, obj_in: inv_schemas.MaterialTransactionCreate
    ) -> inv_models.MaterialTransaction:
        """구매(입고) 거래를 처리하고 새 배치를 생성합니다."""
        if obj_in.quantity_change <= 0:
            raise HTTPException(status_code=400, detail="Purchase quantity must be positive.")

        new_batch = inv_models.MaterialBatch(
            material_id=obj_in.material_id,
            facility_id=obj_in.facility_id,
            vendor_id=obj_in.vendor_id,
            quantity=Decimal(str(obj_in.quantity_change)),
            unit_cost=Decimal(str(obj_in.unit_price)),
            received_date=obj_in.transaction_date,
        )
        db.add(new_batch)
        await db.flush()
        await db.refresh(new_batch)

        transaction = inv_models.MaterialTransaction.model_validate(
            obj_in, update={'source_batch_id': new_batch.id}
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        return transaction

    async def _create_usage_transaction(
        self, db: AsyncSession, obj_in: inv_schemas.MaterialTransactionCreate
    ) -> List[inv_models.MaterialTransaction]:
        """자재 사용 거래를 FIFO 로직에 따라 처리합니다."""
        if obj_in.quantity_change >= 0:
            raise HTTPException(status_code=400, detail="Usage quantity must be negative.")

        usage_needed = abs(Decimal(str(obj_in.quantity_change)))

        query = (
            select(inv_models.MaterialBatch)
            .where(inv_models.MaterialBatch.material_id == obj_in.material_id)
            .where(inv_models.MaterialBatch.facility_id == obj_in.facility_id)
            .where(inv_models.MaterialBatch.quantity > 0)
            .order_by(inv_models.MaterialBatch.received_date.asc())
        )
        result = await db.execute(query)
        batches = result.scalars().all()

        current_stock = sum(batch.quantity for batch in batches)
        if current_stock < usage_needed:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Required: {usage_needed}, "
                       f"Available: {current_stock}"
            )

        transactions_created = []
        for batch in batches:
            if usage_needed <= 0:
                break

            usage_from_batch = min(batch.quantity, usage_needed)
            batch.quantity -= usage_from_batch

            transaction_data = obj_in.model_dump()
            transaction_data['quantity_change'] = -usage_from_batch
            transaction_data['source_batch_id'] = batch.id

            transaction = inv_models.MaterialTransaction.model_validate(transaction_data)

            db.add(batch)
            db.add(transaction)
            transactions_created.append(transaction)

            usage_needed -= usage_from_batch

        await db.commit()
        for t in transactions_created:
            await db.refresh(t)

        return transactions_created


#  각 CRUD 클래스의 인스턴스 생성
material_category = MaterialCategoryCRUD(inv_models.MaterialCategory)
material_spec_definition = MaterialSpecDefinitionCRUD(
    inv_models.MaterialSpecDefinition
)
material_category_spec_definition = MaterialCategorySpecDefinitionCRUD(
    inv_models.MaterialCategorySpecDefinition
)
material = MaterialCRUD(inv_models.Material)
material_spec = MaterialSpecCRUD(inv_models.MaterialSpec)
material_batch = MaterialBatchCRUD(inv_models.MaterialBatch)
material_transaction = MaterialTransactionCRUD(inv_models.MaterialTransaction)
