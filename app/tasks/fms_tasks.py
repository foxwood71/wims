# app/tasks/fms_equipment_tasks.py (수정된 코드)

from sqlalchemy.sql import text


async def sync_equipment_specs_on_spec_definition_name_change(
    ctx,  # ARQ context
    spec_definition_id: int,
    old_spec_name: str,
    new_spec_name: str
):
    """
    EquipmentSpecDefinition의 이름이 변경되었을 때,
    관련된 모든 EquipmentSpec의 specs JSONB 필드의 키를 업데이트하는 백그라운드 작업.
    """
    # get_async_session_context를 함수 내부에서 임포트합니다.
    from app.core.database import get_async_session_context  # 순환 임포트 때문에 함수 내부에서 정의

    print(f"백그라운드 작업 시작: EquipmentSpecDefinition ID {spec_definition_id}의 이름 변경 동기화: '{old_spec_name}' -> '{new_spec_name}'")

    # PostgreSQL의 jsonb 함수를 사용하여 단일 UPDATE 쿼리 실행
    # old_spec_name 키를 제거하고, new_spec_name 키로 값을 이동
    # f-string 접두사 제거 및 플레이스홀더 사용
    query = text("""
        UPDATE fms.equipment_specs
        SET specs = (specs - :old_spec_name) || jsonb_build_object(:new_spec_name, specs -> :old_spec_name)
        WHERE specs ? :old_spec_name;
    """)

    updated_count = 0
    async with get_async_session_context() as db:
        # 이 스펙 정의를 사용하는 모든 EquipmentSpec 데이터를 조회
        try:
            result = await db.execute(
                query,
                {
                    "old_spec_name": old_spec_name,
                    "new_spec_name": new_spec_name,
                },
            )
            await db.commit()
            updated_count = result.rowcount
        except Exception as e:
            await db.rollback()
            print(f"백그라운드 스펙 이름 변경 동기화 실패: {e}")
            return {"status": "error", "message": str(e)}

    print(f"작업 완료! 총 {updated_count}개의 EquipmentSpec 데이터가 업데이트됨.")
    return {"status": "success", "updated_count": updated_count}


async def sync_equipment_specs_on_spec_definition_delete(
    ctx,  # ARQ context
    spec_definition_id: int,
    spec_name_to_remove: str
):
    """
    EquipmentSpecDefinition이 삭제되었을 때,
    관련된 모든 EquipmentSpec의 specs JSONB 필드에서 해당 키를 제거하는 백그라운드 작업.
    """
    from app.core.database import get_async_session_context  # 순환 임포트 때문에 함수 내부에서 정의

    print(f"백그라운드 작업 시작: EquipmentSpecDefinition ID {spec_definition_id} 삭제 동기화: '{spec_name_to_remove}' 제거")

    # PostgreSQL의 jsonb 함수를 사용하여 단일 UPDATE 쿼리 실행
    # 해당 키를 가진 모든 JSONB 객체에서 키를 제거
    # f-string 접두사 제거 및 플레이스홀더 사용
    query = text("""
        UPDATE fms.equipment_specs
        SET specs = specs - :spec_name_to_remove
        WHERE specs ? :spec_name_to_remove;
    """)

    updated_count = 0
    async with get_async_session_context() as db:
        try:
            result = await db.execute(
                query,
                {
                    "spec_name_to_remove": spec_name_to_remove,
                },
            )
            await db.commit()
            updated_count = result.rowcount
        except Exception as e:
            await db.rollback()
            print(f"백그라운드 스펙 삭제 동기화 실패: {e}")
            return {"status": "error", "message": str(e)}

    print(f"작업 완료! 총 {updated_count}개의 EquipmentSpec 데이터에서 키가 제거됨.")
    return {"status": "success", "updated_count": updated_count}
