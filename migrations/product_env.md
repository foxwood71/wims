**Alembic 사용을 위한 추가 설정 및 유의 사항:**

1.  **`app/main.py` 수정**: `app/db/session.py`의 `create_db_and_tables()` 함수 호출을 프로덕션 환경에서는 제거하거나, 개발 시에만 사용하도록 조건부로 만드세요. Alembic을 사용하면 테이블 생성은 마이그레이션이 담당합니다.

    ```python
    # wims_backend/app/main.py (예시)
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    from app.db.session import create_db_and_tables # 임포트

    # @asynccontextmanager
    # async def lifespan(app: FastAPI):
    #     print("Starting up...")
    #     # 개발 환경에서만 테이블 자동 생성
    #     if settings.DEBUG_MODE: # settings.py에 DEBUG_MODE=True 추가
    #         create_db_and_tables()
    #     yield
    #     print("Shutting down...")

    # app = FastAPI(lifespan=lifespan, title="WIMS Backend API")
    # ...
    ```

2.  **`SQLModel` 타입 임포트**: `script.py.mako` 파일에 `import sqlmodel`과 같은 SQLModel 관련 임포트가 포함되어 있는지 확인해야 합니다. 이는 `alembic revision --autogenerate`가 SQLModel의 특수 타입(`Field`의 `sa_column`, `UUID` 등)을 올바르게 감지하는 데 필요할 수 있습니다. 위 템플릿에는 이미 포함했습니다.

3.  **첫 마이그레이션 생성**:
    - `wims_backend` 디렉토리로 이동합니다.
    - `alembic revision --autogenerate -m "Create initial tables"` 명령을 실행합니다.
    - `migrations/versions` 디렉토리에 새로운 Python 파일이 생성될 것입니다. 이 파일에 모든 테이블 생성 SQL이 포함됩니다. 내용을 확인하고 필요한 경우 수동으로 수정합니다.
4.  **데이터베이스에 적용**:
    - `alembic upgrade head` 명령을 실행하여 스키마를 데이터베이스에 적용합니다.

이제 `wims_backend` 프로젝트는 Alembic을 통한 데이터베이스 마이그레이션 기능을 갖추게 됩니다.
