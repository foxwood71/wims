# app/tasks/inv_tasks.py

import json
from typing import List
from sqlalchemy.sql import text
from app.core.database import get_async_session_context
from app.domains.inv import models as inv_models


async def sync_material_specs_on_spec_definition_name_change(
    ctx,  # ARQ context
    spec_definition_id: int,
    old_spec_name: str,
    new_spec_name: str,
    category_ids: List[int]  # 관련 카테고리 ID 목록
):
    """
    MaterialSpecDefinition의 이름이 변경되었을 때,
    관련된 MaterialSpec의 specs JSONB 필드의 키를 업데이트하는 백그라운드 작업.
    """
    print(f"백그라운드 작업 시작: MaterialSpecDefinition ID {spec_definition_id} 이름 변경 동기화: '{old_spec_name}' -> '{new_spec_name}'")
    print(f"대상 카테고리 ID: {category_ids}")

    #  PostgreSQL의 jsonb 함수를 사용하여 단일 UPDATE 쿼리 실행
    #  old_spec_name 키를 제거하고, new_spec_name 키로 값을 이동
    query = text("""
        UPDATE inv.materials_specs AS ms
        SET specs = (ms.specs - :old_spec_name) || jsonb_build_object(:new_spec_name, ms.specs -> :old_spec_name)
        FROM inv.materials AS m
        WHERE
            ms.materials_id = m.id
            AND m.material_category_id = ANY(:category_ids)
            AND ms.specs ? :old_spec_name;
    """)

    updated_count = 0
    async with get_async_session_context() as db:
        try:
            result = await db.execute(
                query,
                {
                    "old_spec_name": old_spec_name,
                    "new_spec_name": new_spec_name,
                    "category_ids": category_ids,
                },
            )
            await db.commit()
            updated_count = result.rowcount
        except Exception as e:
            await db.rollback()
            # 실제 환경에서는 로깅 시스템에 에러를 기록
            print(f"백그라운드 자재 스펙 이름 변경 동기화 실패: {e}")
            return {"status": "error", "message": str(e)}

    print(f"작업 완료! 총 {updated_count}개의 MaterialSpec 데이터가 업데이트됨.")
    return {"status": "success", "updated_count": updated_count}


async def sync_material_specs_on_spec_definition_delete(
    ctx,  # ARQ context
    spec_definition_id: int,
    spec_name_to_remove: str,
    category_ids: List[int]  # 관련 카테고리 ID 목록
):
    """
    MaterialSpecDefinition이 삭제되었을 때,
    관련된 MaterialSpec의 specs JSONB 필드에서 해당 키를 제거하는 백그라운드 작업.
    """
    print(f"백그라운드 작업 시작: MaterialSpecDefinition ID {spec_definition_id} 삭제 동기화: '{spec_name_to_remove}' 제거")
    print(f"대상 카테고리 ID: {category_ids}")

    #  PostgreSQL의 jsonb 함수를 사용하여 단일 UPDATE 쿼리 실행
    #  해당 키를 가진 모든 JSONB 객체에서 키를 제거
    query = text("""
        UPDATE inv.materials_specs AS ms
        SET specs = ms.specs - :spec_name_to_remove
        FROM inv.materials AS m
        WHERE
            ms.materials_id = m.id
            AND m.material_category_id = ANY(:category_ids)
            AND ms.specs ? :spec_name_to_remove;
    """)

    updated_count = 0
    async with get_async_session_context() as db:
        try:
            result = await db.execute(
                query,
                {
                    "spec_name_to_remove": spec_name_to_remove,
                    "category_ids": category_ids,
                },
            )
            await db.commit()
            updated_count = result.rowcount
        except Exception as e:
            await db.rollback()
            #  실제 환경에서는 로깅 시스템에 에러를 기록
            print(f"백그라운드 자재 스펙 삭제 동기화 실패: {e}")
            return {"status": "error", "message": str(e)}

    print(f"작업 완료! 총 {updated_count}개의 MaterialSpec 데이터에서 키가 제거됨.")
    return {"status": "success", "updated_count": updated_count}


async def add_spec_to_materials_in_category(
    ctx,  # ARQ context
    material_category_id: int,
    new_spec_name: str
):
    """
    MaterialCategory에 새로운 MaterialSpecDefinition이 연결되었을 때,
    해당 카테고리에 속한 모든 Material의 MaterialSpec에 새로운 스펙 필드를 null 값으로 추가하는 백그라운드 작업.
    """
    print(f"백그라운드 작업 시작: 카테고리 ID {material_category_id}에 새 스펙 '{new_spec_name}' 추가 동기화")

    updated_count = 0
    async with get_async_session_context() as db:
        try:
            #  1. 해당 카테고리에 속한 모든 자재 (Material)를 조회합니다.
            #     MaterialSpec이 없는 자재도 포함하기 위해 LEFT JOIN 또는 서브쿼리 사용
            #     여기서는 Material을 조회하여 MaterialSpec이 없으면 새로 생성하도록 구현
            materials_to_update_stmt = text("""
                SELECT
                    m.id AS material_id,
                    ms.id AS material_spec_id,
                    ms.specs AS current_specs
                FROM inv.materials AS m
                LEFT JOIN inv.materials_specs AS ms ON m.id = ms.materials_id
                WHERE m.material_category_id = :material_category_id;
            """)

            result = await db.execute(
                materials_to_update_stmt,
                {"material_category_id": material_category_id}
            )
            rows = result.fetchall()

            for row in rows:
                material_id = row.material_id
                material_spec_id = row.material_spec_id
                current_specs = row.current_specs if row.current_specs else {}

                if new_spec_name not in current_specs:
                    updated_count += 1
                    if material_spec_id is None:
                        #  MaterialSpec이 없으면 새로 생성 (JSONB 필드 사용)
                        insert_query = text("""
                            INSERT INTO inv.materials_specs (materials_id, specs)
                            VALUES (:material_id, jsonb_build_object(:new_spec_name, NULL));
                        """)
                        await db.execute(insert_query, {"material_id": material_id, "new_spec_name": new_spec_name})
                    else:
                        #  기존 MaterialSpec에 새 필드 추가
                        update_query = text("""
                            UPDATE inv.materials_specs
                            SET specs = specs || jsonb_build_object(:new_spec_name, NULL)
                            WHERE id = :material_spec_id;
                        """)
                        await db.execute(update_query, {"material_spec_id": material_spec_id, "new_spec_name": new_spec_name})

            await db.commit()

        except Exception as e:
            await db.rollback()
            print(f"백그라운드 자재 스펙 추가 동기화 실패: {e}")
            return {"status": "error", "message": str(e)}

    print(f"작업 완료! 총 {updated_count}개의 MaterialSpec 데이터에 새 항목 키 추가됨.")
    return {"status": "success", "updated_count": updated_count}
