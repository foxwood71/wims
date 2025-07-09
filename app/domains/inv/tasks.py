# app/tasks/inv_tasks.py

import logging
from typing import Any, Dict  # , List

# from sqlalchemy.sql import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# from app.core.database import get_async_session_context
from app.domains.inv import models as inv_models

#  로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# async def change_spec_key_from_materials_in_category(
#     ctx,  # ARQ context
#     spec_definition_id: int,
#     old_spec_name: str,
#     new_spec_name: str,
#     category_ids: List[int]  # 관련 카테고리 ID 목록
# ):
#     """
#     MaterialSpecDefinition의 이름이 변경되었을 때,
#     관련된 MaterialSpec의 specs JSONB 필드의 키를 업데이트하는 백그라운드 작업.
#     """
#     print(f"백그라운드 작업 시작: MaterialSpecDefinition ID {spec_definition_id} 이름 변경 동기화: '{old_spec_name}' -> '{new_spec_name}'")
#     print(f"대상 카테고리 ID: {category_ids}")

#     #  PostgreSQL의 jsonb 함수를 사용하여 단일 UPDATE 쿼리 실행
#     #  old_spec_name 키를 제거하고, new_spec_name 키로 값을 이동
#     query = text("""
#         UPDATE inv.materials_specs AS ms
#         SET specs = (ms.specs - :old_spec_name) || jsonb_build_object(:new_spec_name, ms.specs -> :old_spec_name)
#         FROM inv.materials AS m
#         WHERE
#             ms.materials_id = m.id
#             AND m.material_category_id = ANY(:category_ids)
#             AND ms.specs ? :old_spec_name;
#     """)

#     updated_count = 0
#     async with get_async_session_context() as db:
#         try:
#             result = await db.execute(
#                 query,
#                 {
#                     "old_spec_name": old_spec_name,
#                     "new_spec_name": new_spec_name,
#                     "category_ids": category_ids,
#                 },
#             )
#             await db.commit()
#             updated_count = result.rowcount
#         except Exception as e:
#             await db.rollback()
#             # 실제 환경에서는 로깅 시스템에 에러를 기록
#             print(f"백그라운드 자재 스펙 이름 변경 동기화 실패: {e}")
#             return {"status": "error", "message": str(e)}

#     print(f"작업 완료! 총 {updated_count}개의 MaterialSpec 데이터가 업데이트됨.")
#     return {"status": "success", "updated_count": updated_count}

async def add_spec_key_for_all_materials(
    ctx: Dict[str, Any], category_id: int, spec_key: str
) -> Dict[str, Any]:
    """
    특정 카테고리에 속한 모든 자재에 대해, 새로운 스펙 키를 추가하거나 업데이트합니다.
    """
    db: AsyncSession = ctx['db']
    print(
        f"백그라운드 작업 시작: 카테고리 ID {category_id}에 "
        f"새 스펙 '{spec_key}' 추가 동기화"
    )

    #  1. 카테고리에 속한 모든 자재를 조회합니다.
    material_query = select(inv_models.Material).where(
        inv_models.Material.material_category_id == category_id
    )
    material_rs = await db.execute(material_query)
    materials = material_rs.scalars().all()

    if not materials:
        print("작업 완료! 스펙을 추가할 자재가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    material_ids = [m.id for m in materials]

    #  2. 해당 자재들의 기존 스펙 정보를 한 번에 가져옵니다.
    spec_query = select(inv_models.MaterialSpec).where(
        inv_models.MaterialSpec.materials_id.in_(material_ids)
    )
    #  자재 ID를 키로 하는 딕셔너리로 만들어 쉽게 접근합니다.
    specs_rs = await db.execute(spec_query)
    specs_map = {spec.materials_id: spec for spec in specs_rs.scalars().all()}

    update_count = 0
    #  3. 각 자재에 대해 스펙을 업데이트하거나 새로 생성합니다.
    for material_id in material_ids:
        if material_id in specs_map:
            #  기존 스펙이 있으면, specs JSON에 키만 추가합니다.
            spec = specs_map[material_id]
            if spec_key not in spec.specs:
                new_specs = spec.specs.copy()
                new_specs[spec_key] = None
                spec.specs = new_specs  # SQLAlchemy가 변경을 감지하도록 재할당
                db.add(spec)
                update_count += 1
        else:
            #  기존 스펙이 없으면, 새로 생성합니다.
            new_spec = inv_models.MaterialSpec(
                materials_id=material_id,
                specs={spec_key: None}
            )
            db.add(new_spec)
            update_count += 1

    await db.commit()
    print(f"작업 완료! 총 {update_count}개의 MaterialSpec 데이터에 새 항목 키 추가됨.")
    return {"status": "ok", "updated_count": update_count}


async def update_spec_key_for_all_materials(
    ctx: Dict[str, Any], spec_def_id: int, old_key: str, new_key: str
) -> Dict[str, Any]:
    """
    특정 스펙 정의(spec_def_id)와 연결된 모든 자재 스펙의 키 이름을 변경합니다.
    (예: 'viscosity' -> 'viscosity_new')
    """
    db: AsyncSession = ctx['db']
    print(
        f"백그라운드 작업 시작: 스펙 정의 ID {spec_def_id}의 키를 "
        f"'{old_key}'에서 '{new_key}'(으)로 변경합니다."
    )

    # 1. 해당 스펙 정의를 사용하는 모든 카테고리 ID를 찾습니다.
    link_query = select(inv_models.MaterialCategorySpecDefinition.material_category_id).where(
        inv_models.MaterialCategorySpecDefinition.spec_definition_id == spec_def_id
    )
    links_result = await db.execute(link_query)
    category_ids = links_result.scalars().all()

    if not category_ids:
        print("작업 완료! 해당 스펙을 사용하는 카테고리가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    # 2. 해당 카테고리에 속한 모든 자재 ID를 찾습니다.
    material_query = select(inv_models.Material.id).where(
        inv_models.Material.material_category_id.in_(category_ids)
    )
    materials_result = await db.execute(material_query)
    material_ids = materials_result.scalars().all()

    if not material_ids:
        print("작업 완료! 해당 스펙을 사용하는 자재가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    # 3. 해당 자재들의 스펙 정보 중, 변경이 필요한 스펙만 가져옵니다.
    spec_query = select(inv_models.MaterialSpec).where(
        inv_models.MaterialSpec.materials_id.in_(material_ids)
    )
    specs_result = await db.execute(spec_query)
    specs_to_update = [
        spec for spec in specs_result.scalars().all() if old_key in spec.specs
    ]

    update_count = 0
    # 4. 각 스펙의 키를 변경합니다.
    for spec in specs_to_update:
        new_specs = spec.specs.copy()
        new_specs[new_key] = new_specs.pop(old_key)  # 키 이름 변경
        spec.specs = new_specs  # 변경 감지를 위해 재할당
        db.add(spec)
        update_count += 1

    if update_count > 0:
        await db.commit()

    print(f"작업 완료! 총 {update_count}개의 MaterialSpec 데이터에서 키 이름 변경됨.")
    return {"status": "ok", "updated_count": update_count}


async def delete_spec_key_for_all_materials(
    ctx: Dict[str, Any],  # ARQ context
    category_id: int,  # 관련 카테고리 ID
    spec_key_to_remove: str,
):
    """
    MaterialSpecDefinition이 삭제되었을 때,
    관련된 MaterialSpec의 specs JSONB 필드에서 해당 키를 제거하는 백그라운드 작업.
    """
    db: AsyncSession = ctx['db']
    print(
        f"백그라운드 작업 시작: 카테고리 ID {category_id}에서 "
        f"스펙 키 '{spec_key_to_remove}' 제거 동기화"
    )

    # 1. 카테고리에 속한 모든 자재를 조회합니다.
    material_query = select(inv_models.Material).where(
        inv_models.Material.material_category_id == category_id
    )
    materials_result = await db.execute(material_query)
    materials = materials_result.scalars().all()
    if not materials:
        print("작업 완료! 스펙을 제거할 자재가 없습니다.")
        return {"status": "ok", "updated_count": 0}

    material_ids = [m.id for m in materials]

    # 2. 해당 자재들의 기존 스펙 정보를 한 번에 가져옵니다.
    spec_query = select(inv_models.MaterialSpec).where(
        inv_models.MaterialSpec.materials_id.in_(material_ids)
    )
    specs_result = await db.execute(spec_query)
    specs_to_update = specs_result.scalars().all()

    update_count = 0
    # 3. 각 자재 스펙에서 해당 키를 제거합니다.
    for spec in specs_to_update:
        if spec_key_to_remove in spec.specs:
            new_specs = spec.specs.copy()
            new_specs.pop(spec_key_to_remove, None)
            spec.specs = new_specs  # 변경 감지를 위해 재할당
            db.add(spec)
            update_count += 1

    if update_count > 0:
        await db.commit()

    print(f"작업 완료! 총 {update_count}개의 MaterialSpec 데이터에서 항목 키 제거됨.")
    return {"status": "ok", "updated_count": update_count}
