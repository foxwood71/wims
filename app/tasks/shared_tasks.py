# app/tasks/cleanup_tasks.py

# import os
# import sys
# import asyncio
from pathlib import Path

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession  # AsyncSession 임포트
from app.core.database import get_async_session_context  # 비동기 세션 컨텍스트 임포트

# 애플리케이션의 모델을 가져옵니다.
from app.domains.shared.models import Image, EntityImage

# 경로 문제가 발생하지 않도록 sys.path에 프로젝트 루트를 추가합니다.
# 이 코드는 원래 독립적인 Python 스크립트(scripts/cleanup_unused_images.py)가 애플리케이션의 다른 모듈
# (예: app.core.config, app.domains.shared.models)을 올바르게 임포트할 수 있도록
# Python 모듈 검색 경로(sys.path)에 프로젝트의 루트 디렉터리를 추가하기 위해 사용
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 스크립트 실행을 위한 비동기 엔진 생성
# ARQ 태스크는 FastAPI 애플리케이션이 시작될 때 미리 설정된 ARQ Redis 커넥션 풀을 통해 작업을 큐에 넣고,
# 태스크 내부에서는 app.core.database.get_async_session_context() 함수를 사용하여 데이터베이스 세션을 가져옵니다.
# 이 get_async_session_context() 함수는 이미 app.core.database 모듈에 정의된 전역 engine 인스턴스를 활용하므로,
# ARQ 태스크 내에서 다시 엔진을 생성할 필요가 없습니다.
# engine = create_async_engine(settings.DATABASE_URL.get_secret_value(), echo=False)


async def cleanup_unused_images_task(ctx):
    """
    ARQ 워커에 의해 실행될 사용되지 않는 이미지를 찾아 파일과 DB 레코드를 삭제하는 태스크 함수.
    """
    print("--- ARQ 태스크: 사용되지 않는 이미지 정리 작업 시작 ---")

    deleted_count = 0

    async with get_async_session_context() as session:  # ARQ 컨텍스트에서 DB 세션 사용
        # 1. 현재 사용 중인 모든 이미지 ID 조회
        in_use_stmt = select(EntityImage.image_id).distinct()
        in_use_result = await session.execute(in_use_stmt)
        in_use_image_ids = set(in_use_result.scalars().all())
        print(f"현재 사용 중인 이미지 ID 개수: {len(in_use_image_ids)}개")

        # 2. 전체 이미지 목록 조회
        all_images_stmt = select(Image)
        all_images_result = await session.execute(all_images_stmt)
        all_images = all_images_result.scalars().all()
        print(f"전체 이미지 개수: {len(all_images)}개")

        # 3. 사용되지 않는 이미지 필터링
        unused_images = [img for img in all_images if img.id not in in_use_image_ids]

        if not unused_images:
            print("삭제할 이미지가 없습니다.")
            return {"status": "success", "message": "삭제할 이미지가 없습니다.", "deleted_count": 0}

        print(f"삭제 대상 이미지 {len(unused_images)}개를 찾았습니다.")

        # 4. 사용되지 않는 이미지 삭제 실행
        for image_to_delete in unused_images:
            try:
                # 4-1. 실제 파일 삭제
                file_path = Path(image_to_delete.file_path)
                if file_path.exists():
                    file_path.unlink()
                    print(f"파일 삭제 성공: {file_path}")
                else:
                    print(f"파일 없음 (DB 레코드만 삭제): {file_path}")

                # 4-2. 데이터베이스 레코드 삭제
                await session.delete(image_to_delete)
                deleted_count += 1

            except Exception as e:
                print(f"오류 발생 (이미지 ID: {image_to_delete.id}, 파일: {image_to_delete.file_path}): {e}")
                # 개별 이미지 삭제 실패 시 롤백하지 않고 다음 이미지로 진행
                # (전체 트랜잭션 롤백은 전체 작업 실패 시에만 고려)

        await session.commit()  # 모든 삭제 작업이 성공적으로 진행되면 커밋

    print(f"--- 총 {deleted_count}개의 사용되지 않는 이미지 정리 완료 ---")
    return {"status": "success", "message": "이미지 정리 완료", "deleted_count": deleted_count}
