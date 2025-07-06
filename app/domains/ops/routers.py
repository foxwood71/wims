# app/domains/ops/routers.py

"""
'ops' 도메인 (PostgreSQL 'ops' 스키마)의 API 엔드포인트를 정의하는 모듈입니다.

이 라우터는 처리 계열, 일일 처리장 운영 현황, 일일 계열별 운영 현황, 사용자 정의 보기 정보에 대한
CRUD 작업을 위한 HTTP 엔드포인트를 제공합니다.
FastAPI의 APIRouter를 사용하여 엔드포인트를 그룹화하고 관리하며,
의존성 주입을 통해 데이터베이스 세션 및 사용자 인증/권한을 처리합니다.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import date
from uuid import UUID

# 핵심 의존성 (데이터베이스 세션, 사용자 인증 등)
from app.core import dependencies as deps
from app.domains.usr.models import User as UsrUser  # 사용자 모델 (권한 검증용)

# 'ops' 도메인의 CRUD, 모델, 스키마
from app.domains.ops import crud as ops_crud
# from app.domains.ops import models as ops_models
from app.domains.ops import schemas as ops_schemas

# 다른 도메인의 CRUD (FK 유효성 검증용)
from app.domains.loc import crud as loc_crud  # facility_id 확인용
from app.domains.usr import crud as usr_crud  # user_id 확인용


router = APIRouter(
    tags=["Operations Information Management (운영 정보 관리)"],  # Swagger UI에 표시될 태그
    responses={404: {"description": "Not found"}},  # 이 라우터의 공통 응답 정의
)


# =============================================================================
# 1. ops.lines 엔드포인트 (처리 계열 관리)
# =============================================================================
@router.post("/lines", response_model=ops_schemas.LineResponse, status_code=status.HTTP_201_CREATED, summary="새 처리 계열 생성")
async def create_line(
    line_create: ops_schemas.LineCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 생성 가능
):
    """
    새로운 처리 계열을 생성합니다. (관리자 권한 필요)
    - `code`: 계열 코드 (고유, 필수)
    - `name`: 계열명 (필수)
    - `facility_id`: 소속 처리시설 ID (필수)
    """
    db_line = await ops_crud.line.get_by_code(db, code=line_create.code)
    if db_line:
        raise HTTPException(status_code=400, detail="Line with this code already exists.")

    db_line = await ops_crud.line.get_by_name(db, name=line_create.name)
    if db_line:
        raise HTTPException(status_code=400, detail="Line with this name already exists.")

    db_plant = await loc_crud.wastewater_plant.get(db, id=line_create.facility_id)
    if not db_plant:
        raise HTTPException(status_code=400, detail="Plant not found for the given ID.")

    return await ops_crud.line.create(db=db, obj_in=line_create)


@router.get("/lines", response_model=List[ops_schemas.LineResponse], summary="모든 처리 계열 목록 조회")
async def read_lines(
    facility_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 처리 계열 목록을 조회하거나, 특정 처리시설로 필터링하여 조회합니다.
    - `facility_id`: 특정 처리시설 ID로 필터링 (선택 사항)
    """
    if facility_id:
        # 특정 처리장 존재 여부 확인 (선택 사항)
        db_plant = await loc_crud.wastewater_plant.get(db, id=facility_id)
        if not db_plant:
            raise HTTPException(status_code=404, detail="Plant not found for the given facility_id.")
        lines = await ops_crud.line.get_multi(db, facility_id=facility_id, skip=skip, limit=limit)  # `get_by_plant` 대신 `get_multi` 사용
    else:
        lines = await ops_crud.line.get_multi(db, skip=skip, limit=limit)
    return lines


@router.get("/lines/{line_id}", response_model=ops_schemas.LineResponse, summary="특정 처리 계열 정보 조회")
async def read_line(
    line_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 처리 계열 정보를 조회합니다.
    - `line_id`: 조회할 계열의 고유 ID
    """
    db_line = await ops_crud.line.get(db, id=line_id)
    if db_line is None:
        raise HTTPException(status_code=404, detail="Line not found.")
    return db_line


@router.put("/lines/{line_id}", response_model=ops_schemas.LineResponse, summary="처리 계열 정보 업데이트")
async def update_line(
    line_id: int,
    line_update: ops_schemas.LineUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 업데이트 가능
):
    """
    특정 ID의 처리 계열 정보를 업데이트합니다. (관리자 권한 필요)
    """
    db_line = await ops_crud.line.get(db, id=line_id)
    if db_line is None:
        raise HTTPException(status_code=404, detail="Line not found.")

    # 코드 또는 이름 변경 시 중복 확인
    if line_update.code and line_update.code != db_line.code:
        existing_line_by_code = await ops_crud.line.get_by_code(db, code=line_update.code)
        if existing_line_by_code:
            raise HTTPException(status_code=400, detail="Another line with this code already exists.")

    if line_update.name and line_update.name != db_line.name:
        existing_line_by_name = await ops_crud.line.get_by_name(db, name=line_update.name)
        if existing_line_by_name:
            raise HTTPException(status_code=400, detail="Another line with this name already exists.")

    if line_update.facility_id and line_update.facility_id != db_line.facility_id:
        db_plant = await loc_crud.wastewater_plant.get(db, id=line_update.facility_id)
        if not db_plant:
            raise HTTPException(status_code=400, detail="New plant not found for the given ID.")

    return await ops_crud.line.update(db=db, db_obj=db_line, obj_in=line_update)


@router.delete("/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT, summary="처리 계열 삭제")
async def delete_line(
    line_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 삭제 가능
):
    """
    특정 ID의 처리 계열을 삭제합니다. (관리자 권한 필요)
    참고: 이 계열을 참조하는 일일 계열별 운영 현황(`ops.daily_line_operations`)이 있다면
    `ON DELETE RESTRICT` 정책에 따라 삭제가 실패할 수 있습니다.
    - `line_id`: 삭제할 계열의 고유 ID
    """
    db_line = await ops_crud.line.delete(db, id=line_id)
    if db_line is None:
        raise HTTPException(status_code=404, detail="Line not found.")
    return {}


# =============================================================================
# 2. ops.daily_plant_operations 엔드포인트 (일일 처리장 운영 현황 관리)
# =============================================================================
@router.post("/daily_plant_operations", response_model=ops_schemas.DailyPlantOperationResponse, status_code=status.HTTP_201_CREATED, summary="새 일일 처리장 운영 현황 생성")
async def create_daily_plant_operation(
    op_create: ops_schemas.DailyPlantOperationCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 활성 사용자만 생성 가능
):
    """
    새로운 일일 처리장 운영 현황 기록을 생성합니다.
    - `facility_id`: 처리시설 ID (필수)
    - `op_date`: 운영 일자 (필수)
    """
    db_plant = await loc_crud.wastewater_plant.get(db, id=op_create.facility_id)
    if not db_plant:
        raise HTTPException(status_code=400, detail="Plant not found for the given ID.")

    # plant_id와 op_date 조합의 UNIQUE 제약 조건 확인
    db_operation = await ops_crud.daily_plant_operation.get_by_plant_and_date(
        db, facility_id=op_create.facility_id, op_date=op_create.op_date
    )
    if db_operation:
        raise HTTPException(status_code=400, detail="Daily plant operation record already exists for this plant and date.")

    return await ops_crud.daily_plant_operation.create(db=db, obj_in=op_create)


@router.get("/daily_plant_operations", response_model=List[ops_schemas.DailyPlantOperationResponse], summary="모든 일일 처리장 운영 현황 목록 조회")
async def read_daily_plant_operations(
    facility_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 일일 처리장 운영 현황 목록을 조회하거나, 필터링하여 조회합니다.
    - `facility_id`: 특정 처리시설 ID로 필터링 (선택 사항)
    - `start_date`: 조회 시작일 (선택 사항)
    - `end_date`: 조회 종료일 (선택 사항)
    """
    if facility_id:
        db_plant = await loc_crud.wastewater_plant.get(db, id=facility_id)
        if not db_plant:
            raise HTTPException(status_code=404, detail="Plant not found for the given facility_id.")
        operations = await ops_crud.daily_plant_operation.get_by_plant(
            db, facility_id=facility_id, start_date=start_date, end_date=end_date, skip=skip, limit=limit
        )
    else:
        # facility_id 없이 전체 조회 (날짜 필터링만 적용)
        operations = await ops_crud.daily_plant_operation.get_multi(db, skip=skip, limit=limit)  # 여기서 날짜 필터링 추가 필요
    return operations


@router.get("/daily_plant_operations/{op_id}", response_model=ops_schemas.DailyPlantOperationResponse, summary="특정 일일 처리장 운영 현황 정보 조회 (ID 기준)")
async def read_daily_plant_operation(
    op_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 일일 처리장 운영 현황 기록을 조회합니다.
    - `op_id`: 조회할 기록의 고유 ID
    """
    db_operation = await ops_crud.daily_plant_operation.get(db, id=op_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily plant operation record not found.")
    return db_operation


@router.get("/daily_plant_operations/by_global_id/{global_id}", response_model=ops_schemas.DailyPlantOperationResponse, summary="특정 일일 처리장 운영 현황 정보 조회 (Global ID 기준)")
async def read_daily_plant_operation_by_global_id(
    global_id: UUID,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 Global ID (UUID)의 일일 처리장 운영 현황 기록을 조회합니다.
    - `global_id`: 조회할 기록의 Global ID (UUID)
    """
    db_operation = await ops_crud.daily_plant_operation.get_by_global_id(db, global_id=global_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily plant operation record not found.")
    return db_operation


@router.put("/daily_plant_operations/{op_id}", response_model=ops_schemas.DailyPlantOperationResponse, summary="일일 처리장 운영 현황 업데이트")
async def update_daily_plant_operation(
    op_id: int,
    op_update: ops_schemas.DailyPlantOperationUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 업데이트 가능
):
    """
    특정 ID의 일일 처리장 운영 현황 기록을 업데이트합니다. (관리자 권한 필요)
    """
    db_operation = await ops_crud.daily_plant_operation.get(db, id=op_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily plant operation record not found.")

    # plant_id와 op_date는 복합 PK이므로 업데이트 불가 (schema에서도 해당 필드는 Optional이 아님)
    # 하지만 만약 schemas.DailyPlantOperationUpdate에 이 필드들이 Optional로 정의되어 있고
    # 실제로 변경 시도되었다면, 여기서 에러를 발생시켜야 합니다.
    # Pydantic `exclude_unset=True`로 인해 기본적으로 설정되지 않은 필드는 무시됩니다.
    # 만약 plant_id나 op_date를 변경하려 시도했다면, 새로운 레코드를 생성해야 합니다.

    return await ops_crud.daily_plant_operation.update(db=db, db_obj=db_operation, obj_in=op_update)


@router.delete("/daily_plant_operations/{op_id}", status_code=status.HTTP_204_NO_CONTENT, summary="일일 처리장 운영 현황 삭제")
async def delete_daily_plant_operation(
    op_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 삭제 가능
):
    """
    특정 ID의 일일 처리장 운영 현황 기록을 삭제합니다. (관리자 권한 필요)
    참고: 이 기록을 참조하는 일일 계열별 운영 현황(`ops.daily_line_operations`)이 있다면
    `ON DELETE RESTRICT` 정책에 따라 삭제가 실패할 수 있습니다.
    - `op_id`: 삭제할 기록의 고유 ID
    """
    db_operation = await ops_crud.daily_plant_operation.delete(db, id=op_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily plant operation record not found.")
    return {}


# =============================================================================
# 3. ops.daily_line_operations 엔드포인트 (일일 계열별 운영 현황 관리)
# =============================================================================
@router.post("/daily_line_operations", response_model=ops_schemas.DailyLineOperationResponse, status_code=status.HTTP_201_CREATED, summary="새 일일 계열별 운영 현황 생성")
async def create_daily_line_operation(
    op_create: ops_schemas.DailyLineOperationCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 활성 사용자만 생성 가능
):
    """
    새로운 일일 계열별 운영 현황 기록을 생성합니다.
    - `daily_plant_op_id`: 관련 일일 처리장 운영 레코드 ID (필수)
    - `line_id`: 계열 ID (필수)
    - `op_date`: 운영 일자 (필수)
    """
    db_plant_op = await ops_crud.daily_plant_operation.get_by_global_id(db, global_id=op_create.daily_plant_op_id)
    if not db_plant_op:
        raise HTTPException(status_code=400, detail="Daily plant operation record not found for the given ID.")

    db_line = await ops_crud.line.get(db, id=op_create.line_id)
    if not db_line:
        raise HTTPException(status_code=400, detail="Line not found for the given ID.")

    # op_date와 daily_plant_op_id의 날짜가 일치하는지 확인 (선택 사항, 비즈니스 규칙)
    if db_plant_op.op_date != op_create.op_date:
        raise HTTPException(status_code=400, detail="Operation date must match the associated daily plant operation record's date.")

    # line_id와 op_date 조합의 UNIQUE 제약 조건 확인
    db_operation = await ops_crud.daily_line_operation.get_by_line_and_date(
        db, line_id=op_create.line_id, op_date=op_create.op_date
    )
    if db_operation:
        raise HTTPException(status_code=400, detail="Daily line operation record already exists for this line and date.")

    return await ops_crud.daily_line_operation.create(db=db, obj_in=op_create)


@router.get("/daily_line_operations", response_model=List[ops_schemas.DailyLineOperationResponse], summary="모든 일일 계열별 운영 현황 목록 조회")
async def read_daily_line_operations(
    daily_plant_op_id: Optional[UUID] = None,
    line_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 일일 계열별 운영 현황 목록을 조회하거나, 필터링하여 조회합니다.
    - `daily_plant_op_id`: 특정 일일 처리장 운영 레코드의 Global ID로 필터링 (선택 사항)
    - `line_id`: 특정 계열 ID로 필터링 (선택 사항)
    - `start_date`: 조회 시작일 (선택 사항)
    - `end_date`: 조회 종료일 (선택 사항)
    """
    if daily_plant_op_id:
        db_plant_op = await ops_crud.daily_plant_operation.get_by_global_id(db, global_id=daily_plant_op_id)
        if not db_plant_op:
            raise HTTPException(status_code=404, detail="Daily plant operation record not found for the given daily_plant_op_id.")
        operations = await ops_crud.daily_line_operation.get_by_daily_plant_op_id(
            db, daily_plant_op_global_id=daily_plant_op_id, skip=skip, limit=limit
        )
    elif line_id:
        db_line = await ops_crud.line.get(db, id=line_id)
        if not db_line:
            raise HTTPException(status_code=404, detail="Line not found for the given line_id.")
        operations = await ops_crud.daily_line_operation.get_by_line(
            db, line_id=line_id, start_date=start_date, end_date=end_date, skip=skip, limit=limit
        )
    else:
        operations = await ops_crud.daily_line_operation.get_multi(db, skip=skip, limit=limit)
    return operations


@router.get("/daily_line_operations/{op_id}", response_model=ops_schemas.DailyLineOperationResponse, summary="특정 일일 계열별 운영 현황 정보 조회 (ID 기준)")
async def read_daily_line_operation(
    op_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 일일 계열별 운영 현황 기록을 조회합니다.
    - `op_id`: 조회할 기록의 고유 ID
    """
    db_operation = await ops_crud.daily_line_operation.get(db, id=op_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily line operation record not found.")
    return db_operation


@router.get("/daily_line_operations/by_global_id/{global_id}", response_model=ops_schemas.DailyLineOperationResponse, summary="특정 일일 계열별 운영 현황 정보 조회 (Global ID 기준)")
async def read_daily_line_operation_by_global_id(
    global_id: UUID,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 Global ID (UUID)의 일일 계열별 운영 현황 기록을 조회합니다.
    - `global_id`: 조회할 기록의 Global ID (UUID)
    """
    db_operation = await ops_crud.daily_line_operation.get_by_global_id(db, global_id=global_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily line operation record not found.")
    return db_operation


@router.put("/daily_line_operations/{op_id}", response_model=ops_schemas.DailyLineOperationResponse, summary="일일 계열별 운영 현황 업데이트")
async def update_daily_line_operation(
    op_id: int,
    op_update: ops_schemas.DailyLineOperationUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 업데이트 가능
):
    """
    특정 ID의 일일 계열별 운영 현황 기록을 업데이트합니다. (관리자 권한 필요)
    """
    db_operation = await ops_crud.daily_line_operation.get(db, id=op_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily line operation record not found.")

    # 관련 FK 존재 여부 검증 (변경 시)
    if op_update.daily_plant_op_id and op_update.daily_plant_op_id != db_operation.daily_plant_op_id:
        if not await ops_crud.daily_plant_operation.get_by_global_id(db, global_id=op_update.daily_plant_op_id):
            raise HTTPException(status_code=400, detail="New daily plant operation record not found.")

    if op_update.line_id and op_update.line_id != db_operation.line_id:
        if not await ops_crud.line.get(db, id=op_update.line_id):
            raise HTTPException(status_code=400, detail="New line not found.")

    # line_id와 op_date 조합의 UNIQUE 제약 조건 재확인 (변경 시)
    if (op_update.line_id and op_update.line_id != db_operation.line_id) or \
       (op_update.op_date and op_update.op_date != db_operation.op_date):

        target_line_id = op_update.line_id if op_update.line_id else db_operation.line_id
        target_op_date = op_update.op_date if op_update.op_date else db_operation.op_date

        existing_record = await ops_crud.daily_line_operation.get_by_line_and_date(
            db, line_id=target_line_id, op_date=target_op_date
        )
        if existing_record and existing_record.id != op_id:
            raise HTTPException(status_code=400, detail="Daily line operation record already exists for this line and date.")

    return await ops_crud.daily_line_operation.update(db=db, db_obj=db_operation, obj_in=op_update)


@router.delete("/daily_line_operations/{op_id}", status_code=status.HTTP_204_NO_CONTENT, summary="일일 계열별 운영 현황 삭제")
async def delete_daily_line_operation(
    op_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 관리자 이상만 삭제 가능
):
    """
    특정 ID의 일일 계열별 운영 현황 기록을 삭제합니다. (관리자 권한 필요)
    - `op_id`: 삭제할 기록의 고유 ID
    """
    db_operation = await ops_crud.daily_line_operation.delete(db, id=op_id)
    if db_operation is None:
        raise HTTPException(status_code=404, detail="Daily line operation record not found.")
    return {}


# =============================================================================
# 4. ops.views 엔드포인트 (사용자 정의 운영 데이터 보기 관리)
# =============================================================================
@router.post("/views", response_model=ops_schemas.OpsViewResponse, status_code=status.HTTP_201_CREATED, summary="새 사용자 정의 운영 데이터 보기 생성")
async def create_ops_view(
    view_create: ops_schemas.OpsViewCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 활성 사용자만 생성 가능
):
    """
    새로운 사용자 정의 운영 데이터 보기 설정을 생성합니다.
    - `name`: 보기 설정명 (필수)
    - `user_id`: 생성 사용자 ID (필수, 기본값: 현재 로그인 사용자)
    - `facility_ids`: 처리시설 ID 목록 (JSONB 배열, 선택 사항)
    """
    if view_create.user_id is None:  # 사용자 ID가 제공되지 않았다면 현재 로그인 사용자의 ID를 사용
        view_create.user_id = current_user.id
    else:  # 제공되었다면 해당 사용자 존재 여부 확인
        db_user = await usr_crud.user.get(db, id=view_create.user_id)
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found for the given ID.")

    # 동일 사용자 내에서 이름 중복 확인
    db_view = await ops_crud.ops_view.get_by_name_and_user(
        db, name=view_create.name, user_id=view_create.user_id
    )
    if db_view:
        raise HTTPException(status_code=400, detail="User defined view with this name already exists for this user.")

    # facility_ids, line_ids, sampling_point_ids에 포함된 ID들이 실제로 존재하는지 검증 (선택 사항)
    # 예를 들어, plant_ids의 각 ID에 대해 loc_crud.wastewater_plant.get(db, id=facility_id) 호출하여 확인

    return await ops_crud.ops_view.create(db=db, obj_in=view_create)


@router.get("/views", response_model=List[ops_schemas.OpsViewResponse], summary="모든 사용자 정의 운영 데이터 보기 목록 조회")
async def read_ops_views(
    user_id: Optional[int] = None,  # 특정 사용자 보기 필터링
    facility_id: Optional[int] = None,  # 특정 처리장 ID를 포함하는 보기 필터링
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db_session)
):
    """
    모든 사용자 정의 운영 데이터 보기 목록을 조회하거나, 필터링하여 조회합니다.
    - `user_id`: 특정 사용자 ID로 필터링 (선택 사항)
    - `facility_id`: 특정 처리시설 ID를 포함하는 보기만 필터링 (JSONB 배열 내 검색)
    """
    if user_id:
        views = await ops_crud.ops_view.get_views_by_user(db, user_id=user_id, skip=skip, limit=limit)
    elif facility_id:
        views = await ops_crud.ops_view.get_views_by_plant_id(db, facility_id=facility_id, skip=skip, limit=limit)
    else:
        views = await ops_crud.ops_view.get_multi(db, skip=skip, limit=limit)
    return views


@router.get("/views/{view_id}", response_model=ops_schemas.OpsViewResponse, summary="특정 사용자 정의 운영 데이터 보기 정보 조회")
async def read_ops_view(
    view_id: int,
    db: Session = Depends(deps.get_db_session)
):
    """
    특정 ID의 사용자 정의 운영 데이터 보기 설정을 조회합니다.
    - `view_id`: 조회할 보기 설정의 고유 ID
    """
    db_view = await ops_crud.ops_view.get(db, id=view_id)
    if db_view is None:
        raise HTTPException(status_code=404, detail="User defined view not found.")
    return db_view


@router.put("/views/{view_id}", response_model=ops_schemas.OpsViewResponse, summary="사용자 정의 운영 데이터 보기 업데이트")
async def update_ops_view(
    view_id: int,
    view_update: ops_schemas.OpsViewUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 활성 사용자만 업데이트 가능 (또는 관리자)
):
    """
    특정 ID의 사용자 정의 운영 데이터 보기 설정을 업데이트합니다.
    (자신이 생성한 설정이거나 관리자만 업데이트 가능)
    """
    db_view = await ops_crud.ops_view.get(db, id=view_id)
    if db_view is None:
        raise HTTPException(status_code=404, detail="User defined view not found.")

    # 권한 확인: 자신이 생성한 설정이거나 관리자만 수정 가능
    if db_view.user_id != current_user.id and current_user.role < 10:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this view.")

    # 이름 변경 시 중복 확인 (동일 사용자 내에서)
    if view_update.name and view_update.name != db_view.name:
        existing_view_by_name = await ops_crud.ops_view.get_by_name_and_user(
            db, name=view_update.name, user_id=db_view.user_id  # 기존 user_id 기준
        )
        if existing_view_by_name and existing_view_by_name.id != view_id:
            raise HTTPException(status_code=400, detail="Another view with this name already exists for this user.")

    # facility_ids, line_ids, sampling_point_ids에 포함된 ID들이 실제로 존재하는지 검증 (선택 사항)

    return await ops_crud.ops_view.update(db=db, db_obj=db_view, obj_in=view_update)


@router.delete("/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT, summary="사용자 정의 운영 데이터 보기 삭제")
async def delete_ops_view(
    view_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: UsrUser = Depends(deps.get_current_admin_user)  # 활성 사용자만 삭제 가능 (또는 관리자)
):
    """
    특정 ID의 사용자 정의 운영 데이터 보기 설정을 삭제합니다.
    (자신이 생성한 설정이거나 관리자만 삭제 가능)
    - `view_id`: 삭제할 보기 설정의 고유 ID
    """
    db_view = await ops_crud.ops_view.get(db, id=view_id)
    if db_view is None:
        raise HTTPException(status_code=404, detail="User defined view not found.")

    # 권한 확인: 자신이 생성한 설정이거나 관리자만 삭제 가능
    if db_view.user_id != current_user.id and current_user.role < 10:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to delete this view.")

    await ops_crud.ops_view.delete(db, id=view_id)
    return {}


# ====================================================================
# [추가] 범용 파일 업로드 라우터
# ====================================================================
@router.post(
    "/files/",
    response_model=FileRead,
    status_code=201,
    tags=["File Management"]
)
def upload_general_file(
    *,
    session: Session = Depends(get_session),
    upload_file: UploadFile = File(...)
):
    """
    엑셀, PDF 등 범용 파일을 업로드합니다.
    """
    #  파일 저장 위치를 'files' 디렉토리로 지정
    saved_path = save_upload_file_to_static("files", upload_file)

    file_size = upload_file.file.tell()

    db_file = FileModel(
        path=saved_path,
        name=upload_file.filename,
        content_type=upload_file.content_type,
        size=file_size,
    )

    session.add(db_file)
    session.commit()
    session.refresh(db_file)

    return db_file
