# app/tasks/general_tasks.py

from datetime import datetime
from sqlmodel import select
from app.core.database import get_async_session_context


async def health_check_database_task(ctx):
    """
    ARQ 워커에 의해 실행될 주기적인 데이터베이스 헬스 체크 태스크.
    데이터베이스 연결 상태를 확인하고 로그를 남깁니다.
    """
    print(f"[{datetime.now()}] ARQ 태스크: 데이터베이스 헬스 체크 실행!")

    try:
        async with get_async_session_context() as db:
            # 데이터베이스에 간단한 쿼리를 실행하여 연결 상태를 확인합니다.
            result = await db.execute(select(1))
            if result.scalar_one_or_none() == 1:
                print("데이터베이스 헬스 체크: 성공적으로 연결되었습니다.")
                return {"status": "success", "message": "Database connection successful."}
            else:
                # select(1)이 1을 반환하지 않는 경우는 드뭅니다.
                error_msg = "Database health check failed: No result from test query."
                print(f"데이터베이스 헬스 체크: 실패 - {error_msg}")
                return {"status": "failed", "message": error_msg}
    except Exception as e:
        error_msg = f"데이터베이스 연결 오류: {e}"
        print(f"데이터베이스 헬스 체크: 실패 - {error_msg}")
        # 실제 운영 환경에서는 슬랙 알림, 이메일 등 외부 알림 시스템과 연동할 수 있습니다.
        return {"status": "failed", "message": error_msg}
