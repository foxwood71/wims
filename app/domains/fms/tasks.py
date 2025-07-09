# app/tasks/fms_equipment_tasks.py (수정된 코드)


import logging
from typing import Any, Dict  # , List

# from sqlalchemy.sql import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# from app.core.database import get_async_session_context
from app.domains.fms import models as fms_models

#  로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_spec_key_for_all_equipments(
    ctx: Dict[str, Any], category_id: int, spec_key: str
) -> Dict[str, Any]:
    """
    특정 카테고리에 속한 모든 자재에 대해, 새로운 스펙 키를 추가하거나 업데이트합니다.
    """
    db: AsyncSession = ctx['db']
    logger.info(
        "백그라운드 작업 시작: 설비 카테고리 ID %d에 새 스펙 키 '%s' 추가 동기화",
        category_id, spec_key
    )

    #  1. 카테고리에 속한 모든 설비 ID를 조회합니다.
    equipment_query = select(fms_models.Equipment.id).where(
        fms_models.Equipment.equipment_category_id == category_id
    )
    equipments_result = await db.execute(equipment_query)
    equipment_ids = equipments_result.scalars().all()

    if not equipment_ids:
        logger.info("작업 완료! 스펙을 추가할 설비가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    #  2. 해당 설비들의 기존 스펙 정보를 한 번에 가져옵니다.
    spec_query = select(fms_models.EquipmentSpec).where(
        fms_models.EquipmentSpec.equipment_id.in_(equipment_ids)
    )
    specs_result = await db.execute(spec_query)
    specs_map = {spec.equipment_id: spec for spec in specs_result.scalars().all()}

    update_count = 0
    #  3. 각 설비에 대해 스펙을 업데이트하거나 새로 생성합니다.
    for eq_id in equipment_ids:
        if eq_id in specs_map:
            #  기존 스펙이 있으면, 키만 추가
            spec = specs_map[eq_id]
            if spec_key not in spec.specs:
                new_specs = spec.specs.copy()
                new_specs[spec_key] = None
                spec.specs = new_specs
                db.add(spec)
                update_count += 1
        else:
            #  기존 스펙이 없으면, 새로 생성
            new_spec = fms_models.EquipmentSpec(
                equipment_id=eq_id, specs={spec_key: None}
            )
            db.add(new_spec)
            update_count += 1

    if update_count > 0:
        await db.commit()

    logger.info("작업 완료! 총 %d개의 EquipmentSpec에 새 키 추가됨.", update_count)
    return {"status": "ok", "updated_count": update_count}


async def update_spec_key_for_all_equipments(
    ctx: Dict[str, Any], spec_def_id: int, old_key: str, new_key: str
) -> Dict[str, Any]:
    """
    특정 스펙 정의와 연결된 모든 설비 스펙의 키 이름을 ORM을 사용하여 변경합니다.
    """
    db: AsyncSession = ctx['db']
    logger.info(
        "백그라운드 작업 시작: 설비 스펙 정의 ID %d의 키를 '%s'에서 '%s'(으)로 변경합니다.",
        spec_def_id, old_key, new_key
    )

    # 1. 해당 스펙 정의를 사용하는 모든 카테고리 ID를 찾습니다.
    link_query = select(fms_models.EquipmentCategorySpecDefinition.equipment_category_id).where(
        fms_models.EquipmentCategorySpecDefinition.spec_definition_id == spec_def_id
    )
    links_result = await db.execute(link_query)
    category_ids = links_result.scalars().all()

    if not category_ids:
        logger.info("작업 완료! 해당 스펙을 사용하는 카테고리가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    # 2. 해당 카테고리에 속한 모든 설비 ID를 찾습니다.
    equipment_query = select(fms_models.Equipment.id).where(
        fms_models.Equipment.equipment_category_id.in_(category_ids)
    )
    equipments_result = await db.execute(equipment_query)
    equipment_ids = equipments_result.scalars().all()

    if not equipment_ids:
        logger.info("작업 완료! 해당 스펙을 사용하는 설비가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    # 3. 해당 설비들의 스펙 정보 중, 변경이 필요한 스펙만 가져옵니다.
    spec_query = select(fms_models.EquipmentSpec).where(
        fms_models.EquipmentSpec.equipment_id.in_(equipment_ids)
    )
    specs_result = await db.execute(spec_query)
    specs_to_update = [
        spec for spec in specs_result.scalars().all() if old_key in spec.specs
    ]

    update_count = 0
    # 4. 각 스펙의 키를 파이썬 딕셔너리처럼 변경합니다.
    for spec in specs_to_update:
        new_specs = spec.specs.copy()
        if old_key in new_specs:
            new_specs[new_key] = new_specs.pop(old_key)
            spec.specs = new_specs
            db.add(spec)
            update_count += 1

    if update_count > 0:
        await db.commit()

    logger.info("작업 완료! 총 %d개의 EquipmentSpec 데이터에서 키 이름 변경됨.", update_count)
    return {"status": "ok", "updated_count": update_count}


async def delete_spec_key_from_all_equipments(
    ctx: Dict[str, Any], spec_definition_id: int, spec_key_to_remove: str
) -> Dict[str, Any]:
    """
    특정 스펙 정의가 삭제될 때, 연결된 모든 설비의 스펙에서 해당 키를 ORM 방식으로 제거합니다.
    """
    db: AsyncSession = ctx['db']
    logger.info("백그라운드 작업 시작: 설비 스펙 정의 ID %d 삭제 동기화: '%s' 제거", spec_definition_id, spec_key_to_remove)

    link_query = select(fms_models.EquipmentCategorySpecDefinition.equipment_category_id).where(fms_models.EquipmentCategorySpecDefinition.spec_definition_id == spec_definition_id)
    category_ids = (await db.execute(link_query)).scalars().all()
    if not category_ids:
        logger.info("작업 완료! 해당 스펙을 사용하는 카테고리가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    equipment_query = select(fms_models.Equipment.id).where(fms_models.Equipment.equipment_category_id.in_(category_ids))
    equipment_ids = (await db.execute(equipment_query)).scalars().all()
    if not equipment_ids:
        logger.info("작업 완료! 해당 스펙을 사용하는 설비가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    spec_query = select(fms_models.EquipmentSpec).where(fms_models.EquipmentSpec.equipment_id.in_(equipment_ids))
    specs_to_update = [spec for spec in (await db.execute(spec_query)).scalars().all() if spec_key_to_remove in spec.specs]

    update_count = 0
    for spec in specs_to_update:
        new_specs = spec.specs.copy()
        if spec_key_to_remove in new_specs:
            new_specs.pop(spec_key_to_remove)
            spec.specs = new_specs
            db.add(spec)
            update_count += 1

    if update_count > 0:
        await db.commit()

    logger.info("작업 완료! 총 %d개의 EquipmentSpec에서 키가 제거됨.", update_count)
    return {"status": "ok", "updated_count": update_count}
