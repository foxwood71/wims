import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from arq.connections import create_pool, RedisSettings

from sqlmodel import Session, select
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 핵심 설정 및 데이터베이스 모듈 임포트 (경로 변경 반영)
from app.core.config import settings  # noqa: F401
from app.core.database import engine, get_session

# 각 도메인의 라우터들을 임포트합니다.
# 모든 도메인이 'app/domains' 하위 폴더에 있으므로, 경로를 정확히 지정합니다.
from app import API_PREFIX

# 태스크 모듈 임포트
from app.core import tasks as core_tasks
from app.domains.shared import tasks as shared_tasks
from app.domains.inv import tasks as inv_tasks
from app.domains.fms import tasks as fms_tasks
from app.domains.lims import tasks as lims_tasks

# 기타 라우터 임포트 (기존 코드 유지)
from app.domains.shared.routers import router as shared_router
from app.domains.usr.routers import router as usr_router
from app.domains.loc.routers import router as loc_router
from app.domains.ven.routers import router as ven_router
from app.domains.fms.routers import router as fms_router
from app.domains.inv.routers import router as inv_router
from app.domains.lims.routers import router as lims_router
from app.domains.ops.routers import router as ops_router
from app.domains.corp.routers import router as corp_router
from app.domains.rpt.routers import router as rpt_router

# ARQ 워커가 실행할 태스크 함수 목록
worker_functions = [
    core_tasks.health_check_database_task,
    shared_tasks.cleanup_unused_resources_task,
    inv_tasks.add_spec_key_for_all_materials,
    inv_tasks.update_spec_key_for_all_materials,
    inv_tasks.delete_spec_key_for_all_materials,
    fms_tasks.add_spec_key_for_all_equipments,
    fms_tasks.update_spec_key_for_all_equipments,
    fms_tasks.delete_spec_key_from_all_equipments,
    lims_tasks.sync_worksheet_item_code_change,
    lims_tasks.add_new_item_to_worksheet_data,
]


# ARQ 워커 설정 클래스
class ArqWorkerSettings:
    # 운영 환경에서는 환경 변수 등을 사용하여 설정하는 것이 좋습니다.
    redis_settings = RedisSettings(host="localhost", port=6379)
    functions = worker_functions
    jobs = [
        {
            'name': 'daily_db_health_check',
            'function': 'app.core.tasks.health_check_database_task',
            'cron': '0 0 * * *',
            'timeout': 300,
            'keep_result': 600,
        },
        {
            'name': 'daily_unused_image_cleanup',  # 작업의 고유 이름
            'function': 'app.domains.shared.tasks.cleanup_unused_images_task',  # 실행할 태스크 함수의 전체 경로
            'cron': '0 1 * * *',  # 매일 새벽 1시(01:00)에 실행 (분 시 일 월 요일)
            'timeout': 1800,  # 30분 (필요에 따라 조절)
            'keep_result': 3600,  # 1시간 동안 결과 유지
        },
    ]


# -- 애플리케이션 수명 주기 이벤트 핸들러 --
# FastAPI 0.95.0부터 lifespan 이벤트 핸들러가 권장됩니다.
# 애플리케이션 시작 및 종료 시 실행될 비동기 작업을 정의합니다.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI 애플리케이션의 수명 주기 이벤트(데이터베이스, ARQ Redis)를 함께 처리합니다.
    """
    print("FastAPI 애플리케이션 시작 중...")
    try:
        # --- 시작 시 실행할 로직 ---
        # 1. 데이터베이스 초기화 확인
        print("데이터베이스 초기화/마이그레이션 확인 완료. (Alembic 사용 권장)")

        # 2. ARQ Redis 커넥션 풀 생성 및 app.state에 할당
        print("ARQ Redis 커넥션 풀을 생성합니다...")
        app.state.redis = await create_pool(ArqWorkerSettings.redis_settings)
        print("ARQ Redis 커넥션 풀 생성 완료.")

    except Exception as e:
        print(f"애플리케이션 시작 중 오류 발생: {e}")
        raise

    yield  # 애플리케이션 실행

    print("FastAPI 애플리케이션 종료 중...")
    try:
        # --- 종료 시 실행할 로직 ---
        # 1. ARQ Redis 연결 풀 종료
        if app.state.redis:
            await app.state.redis.close()
            print("ARQ Redis 연결 풀 종료 완료.")

        # 2. 데이터베이스 연결 풀 종료
        await engine.dispose()
        print("데이터베이스 연결 풀 종료 완료.")

    except Exception as e:
        print(f"애플리케이션 종료 중 오류 발생: {e}")


# -- FastAPI 애플리케이션 인스턴스 생성 --
# 애플리케이션의 메타데이터 및 수명 주기 핸들러를 설정합니다.
app = FastAPI(
    title="WIMS API",
    description="Wastewater Information Management System (WIMS) API for managing wastewater treatment plant operations, LIMS, FMS, Inventory, and User data.",
    version="0.1.0",
    docs_url="/docs",       # Swagger UI (Interactive API documentation)
    redoc_url="/redoc",     # ReDoc (Alternative API documentation)
    lifespan=lifespan       # 위에서 정의한 수명 주기 이벤트 핸들러를 등록합니다.
)

# 정적 파일 마운트 (예: 파비콘, CSS, JS 등)
# 'app/static' 폴더가 있다면 해당 경로를 사용합니다.
# BASE_DIR을 사용하여 프로젝트 루트를 기준으로 경로를 지정하는 것이 좋습니다.
# 예를 들어, backend 폴더가 프로젝트 루트라면:
# import os
# BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # main.py가 backend/app에 있다면
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # main.py가 backend에 있다면

# 현재 main.py의 위치가 backend/app/main.py라면, static 폴더는 backend/static에 있다고 가정합니다.
# 따라서 StaticFiles 경로를 적절히 조정해야 합니다.

# 예시: static 폴더가 backend/static 에 있고, main.py가 backend/app 에 있는 경우
# import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")

# 만약 파비콘만 서비스하고 싶다면, 파비콘을 직접 리턴하는 엔드포인트를 만들 수도 있습니다.
# from fastapi.responses import FileResponse
# @app.get("/favicon.ico", include_in_schema=False)
# async def get_favicon():
#     return FileResponse("path/to/your/favicon.ico")


# -- CORS (Cross-Origin Resource Sharing) 미들웨어 설정 --
# 웹 브라우저에서 다른 도메인의 프론트엔드 애플리케이션이 백엔드 API에 접근할 수 있도록 허용합니다.
# 보안을 위해 'allow_origins'는 실제 프론트엔드 도메인으로 제한해야 합니다.
# 개발 환경에서는 모든 출처를 허용할 수 있지만, 프로덕션에서는 매우 위험합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용: 모든 출처 허용. 프로덕션에서는 예: ["http://localhost:3000", "https://your-frontend-domain.com"]
    allow_credentials=True,  # 쿠키, 인증 헤더 등을 포함한 요청 허용
    allow_methods=["*"],  # 모든 HTTP 메서드 (GET, POST, PUT, DELETE 등) 허용
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)

# -- 도메인 라우터 포함 --
# 각 비즈니스 도메인(스키마)에 해당하는 APIRouter 인스턴스들을 메인 애플리케이션에 포함시킵니다.
# 이렇게 함으로써 각 도메인에서 정의된 API 엔드포인트들이 FastAPI 애플리케이션에 등록되어
# 클라이언트 요청을 처리할 수 있게 됩니다.
app.include_router(shared_router, prefix=f"{API_PREFIX}/shared", tags=["Shared (시스템 공용정보 관리)"])
app.include_router(usr_router, prefix=f"{API_PREFIX}/usr", tags=["User & Department Management (사용자 및 부서 관리)"])
app.include_router(loc_router, prefix=f"{API_PREFIX}/loc", tags=["Location Management (위치 관리)"])
app.include_router(ven_router, prefix=f"{API_PREFIX}/ven", tags=["vendor management (공급업체 관리)"])
app.include_router(fms_router, prefix=f"{API_PREFIX}/fms", tags=["Facility Management (설비 관리)"])
app.include_router(inv_router, prefix=f"{API_PREFIX}/inv", tags=["Inventory Management (자재 관리)"])
app.include_router(lims_router, prefix=f"{API_PREFIX}/lims", tags=["Laboratory Information Management (실험실 정보 관리)"])
app.include_router(ops_router, prefix=f"{API_PREFIX}/ops", tags=["Operations Information Management (운영 정보 관리)"])
app.include_router(corp_router, prefix=f"{API_PREFIX}/corp", tags=["Corporation Information Management (회사 정보 관리)"])
app.include_router(rpt_router, prefix=f"{API_PREFIX}/rpt", tags=["Report Management (보고서 관리)"])


# -- 루트 엔드포인트 --
# 애플리케이션의 기본 경로('/')에 대한 간단한 GET 요청 응답을 정의합니다.
@app.get("/", summary="API Root", response_description="Welcome message and documentation link.")
async def read_root():
    """
    WIMS API의 루트 엔드포인트입니다.
    API의 시작점을 알리고 문서 링크를 제공합니다.
    """
    return {"message": "Welcome to WIMS API. Visit /docs for interactive API documentation."}


# -- 헬스 체크 엔드포인트 --
# 애플리케이션과 데이터베이스의 연결 상태를 확인하는 엔드포인트입니다.
# 배포 환경에서 서비스의 정상 작동 여부를 모니터링하는 데 유용합니다.
@app.get("/health-check", summary="Health Check", response_description="Status of the application and database connection.")
async def health_check(session: Session = Depends(get_session)):
    """
    애플리케이션의 헬스 체크 엔드포인트입니다.
    데이터베이스 연결을 테스트하여 서비스의 정상 작동 여부를 확인합니다.
    """
    try:
        # 데이터베이스에 간단한 쿼리를 실행하여 연결 상태를 확인합니다.
        # select(1)은 가장 가볍고 안전한 방법 중 하나입니다.
        result = await session.exec(select(1))
        if result.first():
            return {"status": "ok", "database_connection": "successful"}
        else:
            # select(1)이 결과를 반환하지 않는 경우는 드뭅니다.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database health check failed: No result from test query"
            )
    except Exception as e:
        # 데이터베이스 연결 중 예외가 발생하면 500 에러를 반환합니다.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error during health check: {e}"
        )


# -- Uvicorn 서버 직접 실행 (개발용) --
# 이 부분은 Docker나 셸 스크립트(start_app.sh)를 통해 Uvicorn을 실행할 경우 주석 처리됩니다.
# 개발 환경에서 스크립트 없이 바로 이 파일을 실행할 때 유용합니다.
# if __name__ == "__main__":
#     import uvicorn
#     # reload=True는 코드 변경 시 서버를 자동으로 재시작합니다.
#     # 프로덕션에서는 절대 사용하지 마세요.
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
