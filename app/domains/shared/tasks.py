# app/tasks/cleanup_tasks.py

from pathlib import Path

from sqlmodel import select

from app.core.database import get_async_session_context  # 비동기 세션 컨텍스트 임포트
from app.core.config import settings

from . import models as shared_models


async def cleanup_unused_resources_task(ctx):
    """
    [수정] ARQ 워커에 의해 실행될 사용되지 않는 리소스(파일, 이미지 등)를 찾아
    파일과 DB 레코드를 삭제하는 태스크 함수.
    """
    print("--- ARQ 태스크: 사용되지 않는 리소스 정리 작업 시작 ---")

    deleted_count = 0

    async with get_async_session_context() as session:
        # 1. 현재 `entity_resources` 테이블에서 사용 중인 모든 리소스 ID를 조회합니다.
        # 참고: 더 완벽한 구현을 위해서는 CompanyInfo.logo_id, ReportForm.template_file_id 등
        # 다른 테이블에서 직접 참조되는 리소스 ID도 함께 조회해야 합니다.
        in_use_stmt = select(shared_models.EntityResource.resource_id).distinct()
        in_use_result = await session.execute(in_use_stmt)
        in_use_resource_ids = set(in_use_result.scalars().all())

        # 2. 전체 리소스 목록을 조회합니다.
        all_resources_stmt = select(shared_models.Resource)
        all_resources_result = await session.execute(all_resources_stmt)

        # 3. 사용되지 않는 리소스를 필터링합니다.
        unused_resources = [res for res in all_resources_result if res.id not in in_use_resource_ids]

        if not unused_resources:
            print("삭제할 리소스가 없습니다.")
            return {"status": "success", "message": "삭제할 리소스가 없습니다.", "deleted_count": 0}

        print(f"삭제 대상 리소스 {len(unused_resources)}개를 찾았습니다.")

        # 4. 사용되지 않는 리소스를 삭제합니다.
        for resource_to_delete in unused_resources:
            try:
                # 4-1. 실제 파일 삭제
                # Resource.path는 상대 경로이므로 설정의 UPLOAD_DIR와 조합해야 합니다.
                file_path = Path(settings.UPLOAD_DIR) / resource_to_delete.path
                if file_path.exists():
                    file_path.unlink()
                    print(f"파일 삭제 성공: {file_path}")
                else:
                    print(f"ERROR - get_async_session_context: 리소스 파일 없음 (DB 레코드만 삭제): {file_path}")

                # 4-2. 데이터베이스 레코드 삭제
                await session.delete(resource_to_delete)
                deleted_count += 1

            except Exception as e:
                # 로그 메시지를 새로운 모델 기준으로 변경
                print(f"ERROR - get_async_session_context: 리소스 파일 삭제 실패  (리소스 ID: {resource_to_delete.id}, 파일 경로: {resource_to_delete.path}): {e}")

        await session.commit()

    print(f"---  get_async_session_context: 총 {deleted_count}개의 사용되지 않는 리소스 정리 완료 ---")
    return {"status": "success", "message": "리소스 정리 완료", "deleted_count": deleted_count}
