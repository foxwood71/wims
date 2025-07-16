# app/domains/ops/crud.py

"""
'ops' 도메인 (운영 데이터 관리)과 관련된 CRUD 로직을 담당하는 모듈입니다.
"""

from typing import List, Optional
from datetime import date
from uuid import UUID
from fastapi import HTTPException, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast, Text

# 공통 CRUDBase 및 OPS 도메인의 모델, 스키마 임포트
from app.core.crud_base import CRUDBase
from . import models as ops_models
from . import schemas as ops_schemas


# =============================================================================
# 1. 계열 (Line) CRUD
# =============================================================================
class CRUDLine(
    CRUDBase[
        ops_models.Line,
        ops_schemas.LineCreate,
        ops_schemas.LineUpdate
    ]
):
    def __init__(self):
        super().__init__(model=ops_models.Line)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[ops_models.Line]:
        """계열 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[ops_models.Line]:
        """계열 명으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)  # `self.model.name == name`으로 변경
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: ops_schemas.LineCreate) -> ops_models.Line:
        """FK 유효성 및 코드 중복을 확인하고 생성합니다."""
        # 순환 참조 방지를 위해 함수 내에서 임포트
        from app.domains.loc.crud import wastewater_plant

        if not await wastewater_plant.get(db, id=obj_in.facility_id):
            raise HTTPException(status_code=404, detail="Wastewater plant not found.")
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=400, detail="Line with this code already exists.")

        return await super().create(db, obj_in=obj_in)


line = CRUDLine()


# =============================================================================
# 2. 처리장 일일 운영 (DailyPlantOperation) CRUD
# =============================================================================
class CRUDDailyPlantOperation(
    CRUDBase[
        ops_models.DailyPlantOperation,
        ops_schemas.DailyPlantOperationCreate,
        ops_schemas.DailyPlantOperationUpdate
    ]
):
    def __init__(self):
        super().__init__(model=ops_models.DailyPlantOperation)

    async def get_by_plant_and_date(
        self, db: AsyncSession, *, facility_id: int, op_date: date
    ) -> Optional[ops_models.DailyPlantOperation]:
        """처리장 ID와 운영일자로 조회합니다."""
        statement = select(self.model).where(
            self.model.facility_id == facility_id,
            self.model.op_date == op_date
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_global_id(self, db: AsyncSession, *, global_id: UUID) -> Optional[ops_models.DailyPlantOperation]:
        """Global ID (UUID)를 기준으로 단일 레코드를 조회합니다."""
        statement = select(self.model).where(self.model.global_id == global_id)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_plant(
        self,
        db: AsyncSession,
        *,
        facility_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ops_models.DailyPlantOperation]:
        """특정 처리장 ID와 날짜 범위로 일일 처리장 운영 현황 목록을 조회합니다."""
        query = select(self.model).where(self.model.facility_id == facility_id)
        if start_date:
            query = query.where(self.model.op_date >= start_date)
        if end_date:
            query = query.where(self.model.op_date <= end_date)
        query = query.offset(skip).limit(limit).order_by(self.model.op_date.desc())  # 최신 데이터 우선
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: ops_schemas.DailyPlantOperationCreate) -> ops_models.DailyPlantOperation:
        """FK 유효성 및 복합 유니크(facility_id, op_date) 중복을 확인하고 생성합니다."""
        from app.domains.loc.crud import wastewater_plant

        if not await wastewater_plant.get(db, id=obj_in.facility_id):
            raise HTTPException(status_code=404, detail="Wastewater plant not found.")
        if await self.get_by_plant_and_date(db, facility_id=obj_in.facility_id, op_date=obj_in.op_date):
            raise HTTPException(status_code=400, detail="Daily plant operation data for this plant and date already exists.")

        return await super().create(db, obj_in=obj_in)


daily_plant_operation = CRUDDailyPlantOperation()


# =============================================================================
# 3. 계열별 일일 운영 (DailyLineOperation) CRUD
# =============================================================================
class CRUDDailyLineOperation(
    CRUDBase[
        ops_models.DailyLineOperation,
        ops_schemas.DailyLineOperationCreate,
        ops_schemas.DailyLineOperationUpdate
    ]
):
    def __init__(self):
        super().__init__(model=ops_models.DailyLineOperation)

    async def get_by_line_and_date(
            self, db: AsyncSession, *, line_id: int, op_date: date
    ) -> Optional[ops_models.DailyLineOperation]:
        """계열 ID와 운영일자로 조회합니다."""
        statement = select(self.model).where(
            self.model.line_id == line_id,
            self.model.op_date == op_date
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_line(
        self,
        db: AsyncSession,
        *,
        line_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ops_models.DailyLineOperation]:
        """특정 계열 ID와 날짜 범위로 일일 계열별 운영 현황 목록을 조회합니다."""
        query = select(self.model).where(self.model.line_id == line_id)
        if start_date:
            query = query.where(self.model.op_date >= start_date)
        if end_date:
            query = query.where(self.model.op_date <= end_date)
        query = query.offset(skip).limit(limit).order_by(self.model.op_date.desc())  # 보통 최신 데이터 먼저
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_daily_plant_op_id(
        self,
        db: AsyncSession,
        *,
        daily_plant_op_global_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ops_models.DailyLineOperation]:
        """특정 일일 처리장 운영 레코드의 Global ID로 일일 계열별 운영 현황 목록을 조회합니다."""
        query = select(self.model).where(self.model.daily_plant_op_id == daily_plant_op_global_id)
        query = query.offset(skip).limit(limit).order_by(self.model.op_date.desc())
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: ops_schemas.DailyLineOperationCreate) -> ops_models.DailyLineOperation:
        """FK 유효성 및 복합 유니크(line_id, op_date) 중복을 확인하고 생성합니다."""
        # daily_plant_op_id (UUID)로 부모 레코드를 조회해야 함
        # db.get()은 PK로 조회하므로, global_id로 조회하는 전용 메서드를 사용해야 합니다.
        parent_op = await daily_plant_operation.get_by_global_id(db, global_id=obj_in.daily_plant_op_id)
        if not parent_op:
            raise HTTPException(status_code=404, detail="Daily plant operation not found for the given global_id.")

        # op_date 일치 여부 확인
        if parent_op.op_date != obj_in.op_date:
            raise HTTPException(status_code=400, detail="Date mismatch between line operation and plant operation.")

        if not await line.get(db, id=obj_in.line_id):
            raise HTTPException(status_code=404, detail="Line not found.")
        if await self.get_by_line_and_date(db, line_id=obj_in.line_id, op_date=obj_in.op_date):
            raise HTTPException(status_code=400, detail="Daily line operation data for this line and date already exists.")

        return await super().create(db, obj_in=obj_in)


daily_line_operation = CRUDDailyLineOperation()


# =============================================================================
# 4. 사용자 정의 뷰 (OpsView) CRUD
# =============================================================================
class CRUDOpsView(
    CRUDBase[
        ops_models.OpsView,
        ops_schemas.OpsViewCreate,
        ops_schemas.OpsViewUpdate
    ]
):
    def __init__(self):
        super().__init__(model=ops_models.OpsView)

    async def get_by_name_and_user(
        self, db: AsyncSession, *, name: str, login_id: int
    ) -> Optional[ops_models.OpsView]:
        """이름과 사용자 ID로 뷰를 조회합니다."""
        statement = select(self.model).where(
            self.model.name == name,
            self.model.login_id == login_id
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_views_by_user(
        self, db: AsyncSession, *, login_id: int, skip: int = 0, limit: int = 100
    ) -> List[ops_models.OpsView]:
        """특정 사용자 ID로 뷰 목록을 조회합니다."""
        query = select(self.model).where(self.model.login_id == login_id)
        query = query.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_views_by_plant_id(
        self, db: AsyncSession, *, facility_id: int, skip: int = 0, limit: int = 100
    ) -> List[ops_models.OpsView]:
        """JSONB 배열 `facility_ids`에 특정 plant_id를 포함하는 뷰 목록을 조회합니다."""
        # JSONB 배열 내 특정 요소 검색을 위한 PostgreSQL `@>` (contains) 연산자 사용
        # 오른쪽에 전달하는 값이 JSONB 타입이어야 하므로, cast를 사용하여 명시적으로 JSONB로 변환합니다.
        # `f'[{facility_id}]'` 문자열을 JSONB 타입으로 캐스팅합니다.
        # func.jsonb_build_array를 사용하여 정확한 JSONB 배열을 생성하고 `@>` 연산자에 전달합니다.
        query = select(self.model).where(
            self.model.facility_ids.op('@>')(func.jsonb_build_array(facility_id))  #
        )

        # 또는, 더 일반적인 `JSONB` 검색을 위해 `cast`를 사용하여 텍스트로 변환 후 `contains` 사용
        # query = select(self.model).where(
        #     cast(self.model.facility_ids, Text).contains(f'"{facility_id}"')
        # )
        # 하지만 `op('@>')`가 JSONB 배열 검색에 더 적합합니다.
        query = query.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: ops_schemas.OpsViewCreate) -> ops_models.OpsView:
        """FK 유효성을 확인하고 생성합니다."""
        from app.domains.usr.crud import user
        from app.domains.loc.crud import wastewater_plant

        if not await user.get(db, id=obj_in.login_id):
            raise HTTPException(status_code=404, detail="User not found.")

        # obj_in.plant_id에 대한 유효성 검사 (init.sql에 따라 필수)
        if not await wastewater_plant.get(db, id=obj_in.facility_id):
            raise HTTPException(status_code=404, detail="Wastewater plant not found for the primary facility_id.")

        # obj_in.facility_ids (JSONB 배열)에 포함된 ID들에 대한 유효성 검사 (선택 사항)
        if obj_in.facility_ids:
            for p_id in obj_in.facility_ids:
                if not await wastewater_plant.get(db, id=p_id):
                    raise HTTPException(status_code=404, detail=f"Wastewater plant with ID {p_id} not found in facility_ids.")

        return await super().create(db, obj_in=obj_in)


ops_view = CRUDOpsView()
