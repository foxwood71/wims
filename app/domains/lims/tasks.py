# app/tasks/worksheet_tasks.py
import json
from sqlalchemy.sql import text
from app.core.database import get_async_session_context
# from app.domains.lims.crud import worksheet_data, worksheet_item  # 더 이상 필요하지 않을 수 있습니다.


async def add_new_item_to_worksheet_data(
    ctx, worksheet_id: int, new_code: str
):
    """
    새로운 WorksheetItem이 생성되었을 때, 모든 과거 WorksheetData의
    raw_data JSON에 새로운 키와 null 값을 추가하는 백그라운드 작업
    """
    print(f"백그라운드 작업 시작: {worksheet_id}번 워크시트에 새 항목 '{new_code}' 추가 동기화")

    #  새로운 키와 기본값(null)을 JSON 객체로 만듭니다.
    #  json.dumps를 사용하여 SQL 쿼리 내에서 문자열로 안전하게 전달합니다.
    new_pair = json.dumps({new_code: None})

    #  PostgreSQL의 jsonb 함수를 사용하여 단일 UPDATE 쿼리 실행
    #  1. '분석_내용' 배열의 각 객체(element)를 순회
    #  2. 각 객체에 새로운 키-값 쌍을 추가 (|| 연산자 사용)
    #  3. 변경된 객체들을 다시 JSON 배열로 조합 (jsonb_agg)
    #  4. 최종적으로 raw_data 필드를 업데이트 (jsonb_set)
    query = text("""
        UPDATE lims.worksheet_data
        SET raw_data = jsonb_set(
            raw_data,
            '{분석_내용}',
            (
                SELECT jsonb_agg(element || :new_pair::jsonb)
                FROM jsonb_array_elements(raw_data -> '분석_내용') AS element
            )
        )
        WHERE
            worksheet_id = :worksheet_id
            AND jsonb_typeof(raw_data -> '분석_내용') = 'array';
    """)

    updated_count = 0
    async with get_async_session_context() as db:
        try:
            result = await db.execute(
                query,
                {
                    "worksheet_id": worksheet_id,
                    "new_pair": new_pair,
                },
            )
            await db.commit()
            updated_count = result.rowcount
        except Exception as e:
            await db.rollback()
            print(f"백그라운드 작업 실패: {e}")
            return {"status": "error", "message": str(e)}

    print(f"작업 완료! 총 {updated_count}개의 데이터에 새 항목 키 추가됨.")
    return {"status": "success", "updated_count": updated_count}


async def sync_worksheet_item_code_change(
    ctx, worksheet_id: int, old_code: str, new_code: str
):
    """
    WorksheetItem의 코드가 변경되었을 때, 모든 과거 WorksheetData의
    raw_data JSON 키를 단일 쿼리로 업데이트하는 백그라운드 작업 (성능 개선)
    """
    print(f"백그라운드 작업 시작: {worksheet_id}번 워크시트의 '{old_code}' -> '{new_code}'")

    # -- PostgreSQL의 jsonb 함수를 사용하여 단일 UPDATE 쿼리 실행 --
    # 1. '분석_내용' 배열의 각 JSON 객체를 순회 (jsonb_array_elements)
    # 2. 각 객체에 old_code 키가 있는지 확인 (?)
    # 3. 키가 있다면, old_code를 제거(-)하고 new_code를 추가(||)
    # 4. 변경된 객체들을 다시 JSON 배열로 조합 (jsonb_agg)
    # 5. 최종적으로 raw_data 필드를 업데이트 (jsonb_set)
    query = text("""
        UPDATE lims.worksheet_data
        SET raw_data = jsonb_set(
            raw_data,
            '{분석_내용}',
            (
                SELECT jsonb_agg(
                    CASE
                        WHEN element ? :old_code
                        THEN (element - :old_code) || jsonb_build_object(:new_code, element -> :old_code)
                        ELSE element
                    END
                )
                FROM jsonb_array_elements(raw_data -> '분석_내용') AS element
            )
        )
        WHERE
            worksheet_id = :worksheet_id
            AND jsonb_typeof(raw_data -> '분석_내용') = 'array'
            AND raw_data -> '분석_내용' :: TEXT LIKE :like_pattern;
    """)

    updated_count = 0
    async with get_async_session_context() as db:
        try:
            result = await db.execute(
                query,
                {
                    "old_code": old_code,
                    "new_code": new_code,
                    "worksheet_id": worksheet_id,
                    "like_pattern": f'%"{old_code}"%'  # 변경할 키가 포함된 JSON만 대상으로 필터링
                },
            )
            await db.commit()
            updated_count = result.rowcount  # 영향을 받은 행의 수
        except Exception as e:
            await db.rollback()
            # 실제 운영 환경에서는 로깅(logging)이 필요합니다.
            print(f"백그라운드 작업 실패: {e}")
            return {"status": "error", "message": str(e)}

    print(f"작업 완료! 총 {updated_count}개의 데이터 업데이트됨.")
    return {"status": "success", "updated_count": updated_count}
