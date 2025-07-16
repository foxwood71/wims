# app/domains/lims/crud.py

"""
'lims' 도메인의 CRUD 로직을 담당하는 모듈입니다.
올바른 비동기 문법과 순환 참조를 회피하는 임포트 패턴을 사용합니다.
"""

from typing import List, Optional  # , Dict, Any
from datetime import date, datetime, timedelta, UTC

from sqlmodel import select  # , SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import HTTPException, status

# 공통 CRUDBase 임포트
from app.core.crud_base import CRUDBase

# LIMS 도메인의 모델 및 스키마
from . import models as lims_models
from . import schemas as lims_schemas


# =============================================================================
# 1. 분석 항목 (Parameter) CRUD
# =============================================================================
class CRUDParameter(CRUDBase[lims_models.Parameter, lims_schemas.ParameterCreate, lims_schemas.ParameterUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.Parameter)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[lims_models.Parameter]:
        """분석 항목 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    # [신규] 동일 그룹 내 이름 중복을 확인하기 위한 메소드 추가
    async def get_by_name_and_group(self, db: AsyncSession, *, name: str, group: Optional[str]) -> Optional[lims_models.Parameter]:
        """분석 항목명과 그룹명으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name, self.model.analysis_group == group)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.ParameterCreate) -> lims_models.Parameter:
        """코드 중복 및 동일 그룹 내 이름 중복을 확인하고 생성합니다."""
        from app.domains.fms.crud import equipment as fms_equipment_crud

        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parameter with this code already exists.")

        if await self.get_by_name_and_group(db, name=obj_in.name, group=obj_in.analysis_group):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Parameter with name '{obj_in.name}' already exists in group '{obj_in.analysis_group}'.")

        if obj_in.instrument_id:
            if not await fms_equipment_crud.get(db, id=obj_in.instrument_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.Parameter, obj_in: lims_schemas.ParameterUpdate) -> lims_models.Parameter:
        """업데이트 시 코드 중복 및 FK 유효성 검사."""
        # [FK 유효성 검사]
        from app.domains.fms.crud import equipment as fms_equipment_crud

        # 코드 중복 검사
        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parameter with this code already exists.")

        # 동일 그룹 내 이름 중복 검사
        target_name = obj_in.name if obj_in.name is not None else db_obj.name
        target_group = obj_in.analysis_group if obj_in.analysis_group is not None else db_obj.analysis_group

        if (obj_in.name is not None and obj_in.name != db_obj.name) or \
           (obj_in.analysis_group is not None and obj_in.analysis_group != db_obj.analysis_group):
            existing_by_name_group = await self.get_by_name_and_group(db, name=target_name, group=target_group)
            if existing_by_name_group and existing_by_name_group.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Parameter with name '{target_name}' already exists in group '{target_group}'.")

        # FK 유효성 검사
        if obj_in.instrument_id is not None and obj_in.instrument_id != db_obj.instrument_id:
            if not await fms_equipment_crud.get(db, id=obj_in.instrument_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New instrument not found.")
            # None으로 업데이트하는 경우
            if obj_in.instrument_id is None:
                db_obj.instrument_id = None

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


parameter = CRUDParameter()


# =============================================================================
# 2. 프로젝트 (Project) CRUD
# =============================================================================
class CRUDProject(CRUDBase[lims_models.Project, lims_schemas.ProjectCreate, lims_schemas.ProjectUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.Project)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[lims_models.Project]:
        """프로젝트 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.ProjectCreate) -> lims_models.Project:
        """코드 중복을 확인하고 생성합니다."""
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project with this code already exists.")
        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.Project, obj_in: lims_schemas.ProjectUpdate) -> lims_models.Project:
        """업데이트 시 코드 중복 검사."""
        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project with this code already exists.")
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


project = CRUDProject()


# =============================================================================
# 3. 시료 용기 (SampleContainer) CRUD
# =============================================================================
class CRUDSampleContainer(CRUDBase[lims_models.SampleContainer, lims_schemas.SampleContainerCreate, lims_schemas.SampleContainerUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.SampleContainer)

    async def get_by_code(self, db: AsyncSession, *, code: int) -> Optional[lims_models.SampleContainer]:
        """용기 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[lims_models.SampleContainer]:
        """용기명으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.SampleContainerCreate) -> lims_models.SampleContainer:
        """코드 또는 이름 중복을 확인하고 생성합니다."""
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample container with this code already exists.")
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample container with this name already exists.")
        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.SampleContainer, obj_in: lims_schemas.SampleContainerUpdate) -> lims_models.SampleContainer:
        """업데이트 시 코드 또는 이름 중복 검사."""
        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample container with this code already exists.")
        if obj_in.name is not None and obj_in.name != db_obj.name:
            existing_by_name = await self.get_by_name(db, name=obj_in.name)
            if existing_by_name and existing_by_name.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample container with this name already exists.")
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


sample_container = CRUDSampleContainer()


# =============================================================================
# 4. 시료 유형 (SampleType) CRUD
# =============================================================================
class CRUDSampleType(CRUDBase[lims_models.SampleType, lims_schemas.SampleTypeCreate, lims_schemas.SampleTypeUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.SampleType)

    async def get_by_code(self, db: AsyncSession, *, code: int) -> Optional[lims_models.SampleType]:
        """시료 유형 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[lims_models.SampleType]:
        """시료 유형명으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.SampleTypeCreate) -> lims_models.SampleType:
        """코드 또는 이름 중복을 확인하고 생성합니다."""
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample type with this code already exists.")
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample type with this name already exists.")
        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.SampleType, obj_in: lims_schemas.SampleTypeUpdate) -> lims_models.SampleType:
        """업데이트 시 코드 또는 이름 중복 검사."""
        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample type with this code already exists.")
        if obj_in.name is not None and obj_in.name != db_obj.name:
            existing_by_name = await self.get_by_name(db, name=obj_in.name)
            if existing_by_name and existing_by_name.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample type with this name already exists.")
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


sample_type = CRUDSampleType()


# =============================================================================
# 5. 채수 지점 (SamplingPoint) CRUD
# =============================================================================
class CRUDSamplingPoint(CRUDBase[lims_models.SamplingPoint, lims_schemas.SamplingPointCreate, lims_schemas.SamplingPointUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.SamplingPoint)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[lims_models.SamplingPoint]:
        """채수 지점 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_plant_id(self, db: AsyncSession, *, facility_id: int, skip: int = 0, limit: int = 100) -> List[lims_models.SamplingPoint]:
        """특정 처리장의 채수 지점 목록을 조회합니다."""
        statement = select(self.model).where(self.model.facility_id == facility_id).offset(skip).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.SamplingPointCreate) -> lims_models.SamplingPoint:
        """FK 유효성 및 코드 중복을 확인하고 생성합니다."""
        # [FK 유효성 검사]
        # 순환 참조 방지를 위해 함수 내에서 임포트
        from app.domains.loc.crud import facility as loc_facility_crud  # <<< 수정된 부분

        if not await loc_facility_crud.get(db, id=obj_in.facility_id):  # <<< 수정된 부분
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wastewater plant not found.")

        if obj_in.code and await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sampling point with this code already exists.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.SamplingPoint, obj_in: lims_schemas.SamplingPointUpdate) -> lims_models.SamplingPoint:
        """업데이트 시 코드 중복 및 FK 유효성 검사."""
        from app.domains.loc.crud import facility as loc_facility_crud  # <<< 수정된 부분

        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sampling point with this code already exists.")

        if obj_in.facility_id is not None and obj_in.facility_id != db_obj.facility_id:
            if not await loc_facility_crud.get(db, id=obj_in.facility_id):  # <<< 수정된 부분
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New wastewater plant not found.")
            # None으로 업데이트하는 경우
            if obj_in.facility_id is None:
                db_obj.facility_id = None

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


sampling_point = CRUDSamplingPoint()


# =============================================================================
# 6. 날씨 조건 (WeatherCondition) CRUD
# =============================================================================
class CRUDWeatherCondition(CRUDBase[lims_models.WeatherCondition, lims_schemas.WeatherConditionCreate, lims_schemas.WeatherConditionUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.WeatherCondition)

    async def get_by_code(self, db: AsyncSession, *, code: int) -> Optional[lims_models.WeatherCondition]:
        """날씨 조건 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_status(self, db: AsyncSession, *, status_str: str) -> Optional[lims_models.WeatherCondition]:
        """날씨 상태 문자열로 조회합니다."""
        statement = select(self.model).where(self.model.status == status_str)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.WeatherConditionCreate) -> lims_models.WeatherCondition:
        """코드 또는 상태 중복을 확인하고 생성합니다."""
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weather condition with this code already exists.")
        if await self.get_by_status(db, status_str=obj_in.status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weather condition with this status already exists.")
        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.WeatherCondition, obj_in: lims_schemas.WeatherConditionUpdate) -> lims_models.WeatherCondition:
        """업데이트 시 코드 또는 상태 중복 검사."""
        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weather condition with this code already exists.")
        if obj_in.status is not None and obj_in.status != db_obj.status:
            existing_by_status = await self.get_by_status(db, status_str=obj_in.status)
            if existing_by_status and existing_by_status.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weather condition with this status already exists.")
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


weather_condition = CRUDWeatherCondition()


# =============================================================================
# 7. 시험 의뢰 (TestRequest) CRUD
# =============================================================================
class CRUDTestRequest(CRUDBase[lims_models.TestRequest, lims_schemas.TestRequestCreate, lims_schemas.TestRequestUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.TestRequest)

    async def get_by_request_code(self, db: AsyncSession, *, request_code: str) -> Optional[lims_models.TestRequest]:
        """요청 코드로 조회합니다."""
        statement = select(self.model).where(self.model.request_code == request_code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        department_id: Optional[int] = None,  # 부서 ID 필터
        start_date: Optional[date] = None,   # 시작일 필터
        end_date: Optional[date] = None,     # 종료일 필터
        skip: int = 0,
        limit: int = 100
    ) -> List[lims_models.TestRequest]:
        """
        시험 의뢰 다중 조회 (부서 및 의뢰 날짜 검색 기능 포함)
        """
        query = select(self.model)

        # 1. 부서 ID 필터링
        if department_id is not None:
            query = query.where(self.model.department_id == department_id)

        # 2. 시작일 필터링 (TestRequest 모델의 'request_date' 필드 사용)
        if start_date is not None:
            query = query.where(self.model.request_date >= start_date)

        # 3. 종료일 필터링 (TestRequest 모델의 'request_date' 필드 사용)
        if end_date is not None:
            # end_date 당일까지 포함하기 위함
            query = query.where(self.model.request_date < end_date + timedelta(days=1))

        # 정렬 및 페이징
        query = query.order_by(self.model.id.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.TestRequestCreate, current_login_id: int) -> lims_models.TestRequest:
        """
        시험 의뢰를 생성합니다. 이 과정에서 다음을 수행합니다:
        - `request_date`가 없으면 오늘 날짜로 설정합니다.
        - `requester_login_id`가 없으면 현재 사용자로 설정합니다.
        - 관련된 외래 키(FK)들이 유효한지 확인합니다.
        """
        # 1. request_date 기본값 설정 (사용자 제안)
        if obj_in.request_date is None:
            obj_in.request_date = date.today()

        # 2. requester_login_id 기본값 설정 (기존 로직)
        if obj_in.requester_login_id is None:
            obj_in.requester_login_id = current_login_id

        # 3. 의뢰된 분석 항목 유효성 검사 (사용자 제안) [삭제] 각각의 sample에 분석항목을 기록
        #    (주의: requested_parameters의 key가 Parameter의 'code'라고 가정합니다.)
        # if obj_in.requested_parameters:
        #     requested_param_codes = list(obj_in.requested_parameters.keys())
        #     query = select(lims_models.Parameter.code).where(
        #         lims_models.Parameter.code.in_(requested_param_codes)
        #     )
        #     result = await db.execute(query)
        #     valid_param_codes = {code for code, in result.all()}
        #     invalid_codes = set(requested_param_codes) - valid_param_codes
        #     if invalid_codes:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail=f"등록되지 않은 분석 항목 코드가 포함되어 있습니다: {', '.join(invalid_codes)}"
        #         )

        # 4. 필수 및 선택적 FK 존재 여부 확인 (기존 로직)
        #    (순환 참조를 피하기 위해 함수 내에서 임포트)
        from app.domains.usr.crud import user, department

        if not await project.get(db, id=obj_in.project_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if not await department.get(db, id=obj_in.department_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
        if not await user.get(db, id=obj_in.requester_login_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requester user not found.")

        if obj_in.sampling_weather_id:
            if not await weather_condition.get(db, id=obj_in.sampling_weather_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sampling weather condition not found.")

        # 5. 제출 시간(submitted_at) 기본값 설정 (기존 로직)
        if obj_in.submitted_at is None:
            obj_in.submitted_at = datetime.now(UTC)

        # 6. 최종적으로 CRUDBase의 create 메소드 호출하여 객체 생성
        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.TestRequest, obj_in: lims_schemas.TestRequestUpdate) -> lims_models.TestRequest:
        """업데이트 시 FK 유효성 및 코드 중복 검사."""
        from app.domains.usr.crud import user, department

        if obj_in.project_id is not None and obj_in.project_id != db_obj.project_id:
            if not await project.get(db, id=obj_in.project_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        if obj_in.department_id is not None and obj_in.department_id != db_obj.department_id:
            if not await department.get(db, id=obj_in.department_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

        if obj_in.requester_login_id is not None and obj_in.requester_login_id != db_obj.requester_login_id:
            if not await user.get(db, id=obj_in.requester_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requester user not found.")
            # None으로 업데이트하는 경우
            if obj_in.requester_login_id is None:
                db_obj.requester_login_id = None

        if obj_in.sampling_weather_id is not None and obj_in.sampling_weather_id != db_obj.sampling_weather_id:
            if not await weather_condition.get(db, id=obj_in.sampling_weather_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sampling weather condition not found.")
            # None으로 업데이트하는 경우
            if obj_in.sampling_weather_id is None:
                db_obj.sampling_weather_id = None

        # # request_code는 보통 업데이트하지 않지만, schema에 있다면 처리 [삭제] 각각의 sample에 분석항목을 기록
        # if obj_in.request_code is not None and obj_in.request_code != db_obj.request_code:
        #     existing_by_code = await self.get_by_request_code(db, request_code=obj_in.request_code)
        #     if existing_by_code and existing_by_code.id != db_obj.id:
        #         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test request with this code already exists.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


test_request = CRUDTestRequest()


# =============================================================================
# 8. 원 시료 (Sample) CRUD
# =============================================================================
class CRUDSample(CRUDBase[lims_models.Sample, lims_schemas.SampleCreate, lims_schemas.SampleUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.Sample)

    async def get_by_sample_code(self, db: AsyncSession, *, sample_code: str) -> Optional[lims_models.Sample]:
        """시료 코드로 조회합니다."""
        statement = select(self.model).where(self.model.sample_code == sample_code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.SampleCreate) -> lims_models.Sample:
        """
        [수정] FK 유효성을 확인하고 생성합니다.
        DB 트리거로 생성되는 sample_code를 위해, 해당 필드를 제외하고 INSERT합니다.
        """
        # 순환 참조 방지를 위해 함수 내에서 임포트
        from app.domains.loc.crud import location
        from app.domains.usr.crud import user

        # 필수 FK 확인
        if not await test_request.get(db, id=obj_in.request_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test request not found.")
        if not await sampling_point.get(db, id=obj_in.sampling_point_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sampling point not found.")
        if not await sample_type.get(db, id=obj_in.sample_type_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample type not found.")
        if not await sample_container.get(db, id=obj_in.container_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample container not found.")

        # 선택적 FK 확인
        if obj_in.sampling_weather_id:
            if not await weather_condition.get(db, id=obj_in.sampling_weather_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sampling weather condition not found.")
        if obj_in.storage_location_id:
            if not await location.get(db, id=obj_in.storage_location_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage location not found.")
        if obj_in.collector_login_id:
            if not await user.get(db, id=obj_in.collector_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collector user not found.")

        # collected_date 설정 (현재 날짜로)
        if obj_in.collected_date is None:
            obj_in.collected_date = date.today()

        # request_date 설정 (TestRequest에서 가져옴)
        test_req = await test_request.get(db, id=obj_in.request_id)
        if test_req and obj_in.request_date is None:
            obj_in.request_date = test_req.request_date

        # <<< 수정된 로직 시작 >>>
        # .model_dump()를 사용하여 Python 타입을 유지하면서 딕셔너리로 변환하고, 'sample_code'는 제외합니다.
        # 이렇게 하면 date 객체가 문자열로 변환되는 것을 막을 수 있습니다.
        obj_in_data = obj_in.model_dump(exclude={"sample_code"})

        # 수정된 데이터로 DB 모델 객체 생성
        db_obj = self.model(**obj_in_data)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)  # DB에서 최신 상태(트리거로 생성된 값 포함)를 다시 로드

        return db_obj

    async def update(self, db: AsyncSession, *, db_obj: lims_models.Sample, obj_in: lims_schemas.SampleUpdate) -> lims_models.Sample:
        """업데이트 시 FK 유효성 및 코드 중복 검사."""
        from app.domains.loc.crud import location
        from app.domains.usr.crud import user

        if obj_in.request_id is not None and obj_in.request_id != db_obj.request_id:
            if not await test_request.get(db, id=obj_in.request_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test request not found.")
        if obj_in.sampling_point_id is not None and obj_in.sampling_point_id != db_obj.sampling_point_id:
            if not await sampling_point.get(db, id=obj_in.sampling_point_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sampling point not found.")
        if obj_in.sample_type_id is not None and obj_in.sample_type_id != db_obj.sample_type_id:
            if not await sample_type.get(db, id=obj_in.sample_type_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample type not found.")
        if obj_in.container_id is not None and obj_in.container_id != db_obj.container_id:
            if not await sample_container.get(db, id=obj_in.container_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample container not found.")

        if obj_in.sampling_weather_id is not None and obj_in.sampling_weather_id != db_obj.sampling_weather_id:
            if obj_in.sampling_weather_id is not None:
                if not await weather_condition.get(db, id=obj_in.sampling_weather_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sampling weather condition not found.")
            else:  # None으로 업데이트하는 경우
                db_obj.sampling_weather_id = None
        if obj_in.storage_location_id is not None and obj_in.storage_location_id != db_obj.storage_location_id:
            # None으로 업데이트하는 경우도 포함
            if obj_in.storage_location_id is not None:
                if not await location.get(db, id=obj_in.storage_location_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage location not found.")
            else:  # storage_location_id를 None으로 설정
                db_obj.storage_location_id = None
        if obj_in.collector_login_id is not None and obj_in.collector_login_id != db_obj.collector_login_id:
            if obj_in.collector_login_id is not None:
                if not await user.get(db, id=obj_in.collector_login_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collector user not found.")
            else:  # collector_login_id를 None으로 설정
                db_obj.collector_login_id = None

        # sample_code는 보통 업데이트하지 않지만, schema에 있다면 처리
        if obj_in.sample_code is not None and obj_in.sample_code != db_obj.sample_code:
            existing_by_code = await self.get_by_sample_code(db, sample_code=obj_in.sample_code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample with this code already exists.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


sample = CRUDSample()


# =============================================================================
# 9. 분할 시료 (AliquotSample) CRUD
# =============================================================================
class CRUDAliquotSample(CRUDBase[lims_models.AliquotSample, lims_schemas.AliquotSampleCreate, lims_schemas.AliquotSampleUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.AliquotSample)

    async def get_by_aliquot_code(self, db: AsyncSession, *, aliquot_code: str) -> Optional[lims_models.AliquotSample]:
        """분할 시료 코드로 조회합니다."""
        statement = select(self.model).where(self.model.aliquot_code == aliquot_code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.AliquotSampleCreate) -> lims_models.AliquotSample:
        """FK 유효성을 확인하고 생성합니다."""
        # 순환 참조 방지를 위해 함수 내에서 임포트
        from app.domains.usr.crud import user

        # 필수 FK 확인
        if not await sample.get(db, id=obj_in.parent_sample_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent sample not found.")
        if not await parameter.get(db, id=obj_in.parameter_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")

        # 선택적 FK 확인
        if obj_in.analyst_login_id:
            if not await user.get(db, id=obj_in.analyst_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")

        # aliquot_code는 DB 트리거에 의해 생성되므로, 여기서 중복 검사할 필요 없음
        if obj_in.aliquot_code and await self.get_by_aliquot_code(db, aliquot_code=obj_in.aliquot_code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aliquot sample with this code already exists.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.AliquotSample, obj_in: lims_schemas.AliquotSampleUpdate) -> lims_models.AliquotSample:
        """업데이트 시 FK 유효성 및 코드 중복 검사."""
        from app.domains.usr.crud import user

        if obj_in.parent_sample_id is not None and obj_in.parent_sample_id != db_obj.parent_sample_id:
            if not await sample.get(db, id=obj_in.parent_sample_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent sample not found.")
        if obj_in.parameter_id is not None and obj_in.parameter_id != db_obj.parameter_id:
            if not await parameter.get(db, id=obj_in.parameter_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")

        if obj_in.analyst_login_id is not None and obj_in.analyst_login_id != db_obj.analyst_login_id:
            if obj_in.analyst_login_id is not None:
                if not await user.get(db, id=obj_in.analyst_login_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")
            else:
                db_obj.analyst_login_id = None  # None으로 업데이트

        if obj_in.aliquot_code is not None and obj_in.aliquot_code != db_obj.aliquot_code:
            existing_by_code = await self.get_by_aliquot_code(db, aliquot_code=obj_in.aliquot_code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aliquot sample with this code already exists.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


aliquot_sample = CRUDAliquotSample()


# =============================================================================
# 10. 워크시트 (Worksheet) CRUD
# =============================================================================
class CRUDWorksheet(CRUDBase[lims_models.Worksheet, lims_schemas.WorksheetCreate, lims_schemas.WorksheetUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.Worksheet)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[lims_models.Worksheet]:
        """워크시트 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[lims_models.Worksheet]:
        """워크시트 명으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.WorksheetCreate) -> lims_models.Worksheet:
        """코드 또는 이름 중복을 확인하고 생성합니다."""
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worksheet with this code already exists.")
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worksheet with this name already exists.")
        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.Worksheet, obj_in: lims_schemas.WorksheetUpdate) -> lims_models.Worksheet:
        """업데이트 시 코드 또는 이름 중복 검사."""
        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worksheet with this code already exists.")
        if obj_in.name is not None and obj_in.name != db_obj.name:
            existing_by_name = await self.get_by_name(db, name=obj_in.name)
            if existing_by_name and existing_by_name.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worksheet with this name already exists.")
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


worksheet = CRUDWorksheet()


# =============================================================================
# 11. 워크시트 항목 (WorksheetItem) CRUD
# =============================================================================
class CRUDWorksheetItem(CRUDBase[lims_models.WorksheetItem, lims_schemas.WorksheetItemCreate, lims_schemas.WorksheetItemUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.WorksheetItem)

    async def get_by_worksheet_and_code(self, db: AsyncSession, *, worksheet_id: int, code: str) -> Optional[lims_models.WorksheetItem]:
        """워크시트 ID와 항목 코드로 조회합니다."""
        statement = select(self.model).where(
            self.model.worksheet_id == worksheet_id,
            self.model.code == code
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.WorksheetItemCreate) -> lims_models.WorksheetItem:
        """FK 유효성 및 중복을 확인하고 생성합니다."""
        if not await worksheet.get(db, id=obj_in.worksheet_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found.")

        if await self.get_by_worksheet_and_code(db, worksheet_id=obj_in.worksheet_id, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worksheet item with this code already exists for this worksheet.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.WorksheetItem, obj_in: lims_schemas.WorksheetItemUpdate) -> lims_models.WorksheetItem:
        """업데이트 시 FK 유효성 및 중복 검사."""
        if obj_in.worksheet_id is not None and obj_in.worksheet_id != db_obj.worksheet_id:
            if not await worksheet.get(db, id=obj_in.worksheet_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found.")

        if (obj_in.worksheet_id is not None and obj_in.worksheet_id != db_obj.worksheet_id) or \
           (obj_in.code is not None and obj_in.code != db_obj.code):

            target_worksheet_id = obj_in.worksheet_id if obj_in.worksheet_id is not None else db_obj.worksheet_id
            target_code = obj_in.code if obj_in.code is not None else db_obj.code

            existing_item = await self.get_by_worksheet_and_code(db, worksheet_id=target_worksheet_id, code=target_code)
            if existing_item and existing_item.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worksheet item with this code already exists for the specified worksheet.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


worksheet_item = CRUDWorksheetItem()


# =============================================================================
# 12. 워크시트 데이터 (WorksheetData) CRUD
# =============================================================================
class CRUDWorksheetData(CRUDBase[lims_models.WorksheetData, lims_schemas.WorksheetDataCreate, lims_schemas.WorksheetDataUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.WorksheetData)

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.WorksheetDataCreate) -> lims_models.WorksheetData:
        """FK 유효성을 확인하고 생성합니다."""
        from app.domains.usr.crud import user

        if not await worksheet.get(db, id=obj_in.worksheet_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found.")

        if obj_in.analyst_login_id:
            if not await user.get(db, id=obj_in.analyst_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")
        if obj_in.verified_by_login_id:
            if not await user.get(db, id=obj_in.verified_by_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verifier user not found.")

        # raw_data는 JSONB 타입이므로, 유효한 JSON 형식인지 Pydantic 스키마에서 검증됨

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.WorksheetData, obj_in: lims_schemas.WorksheetDataUpdate) -> lims_models.WorksheetData:
        """업데이트 시 FK 유효성 검사."""
        from app.domains.usr.crud import user

        if obj_in.worksheet_id is not None and obj_in.worksheet_id != db_obj.worksheet_id:
            if not await worksheet.get(db, id=obj_in.worksheet_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found.")

        if obj_in.analyst_login_id is not None and obj_in.analyst_login_id != db_obj.analyst_login_id:
            if obj_in.analyst_login_id is not None:
                if not await user.get(db, id=obj_in.analyst_login_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")
            else:
                db_obj.analyst_login_id = None  # None으로 업데이트
        if obj_in.verified_by_login_id is not None and obj_in.verified_by_login_id != db_obj.verified_by_login_id:
            if obj_in.verified_by_login_id is not None:
                if not await user.get(db, id=obj_in.verified_by_login_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verifier user not found.")
            else:
                db_obj.verified_by_login_id = None  # None으로 업데이트

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


worksheet_data = CRUDWorksheetData()


# =============================================================================
# 13. 분석 결과 (AnalysisResult) CRUD
# =============================================================================
class CRUDAnalysisResult(CRUDBase[lims_models.AnalysisResult, lims_schemas.AnalysisResultCreate, lims_schemas.AnalysisResultUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.AnalysisResult)

    async def get_by_unique_constraint(self, db: AsyncSession, *, aliquot_sample_id: int, parameter_id: int, worksheet_data_id: int) -> Optional[lims_models.AnalysisResult]:
        """복합 고유 키 (aliquot_sample_id, parameter_id, worksheet_data_id)로 조회합니다."""
        statement = select(self.model).where(
            self.model.aliquot_sample_id == aliquot_sample_id,
            self.model.parameter_id == parameter_id,
            self.model.worksheet_data_id == worksheet_data_id
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.AnalysisResultCreate) -> lims_models.AnalysisResult:
        """FK 유효성 및 복합 고유 키 중복을 확인하고 생성합니다."""
        from app.domains.usr.crud import user

        # 필수 FK 확인
        if not await aliquot_sample.get(db, id=obj_in.aliquot_sample_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliquot sample not found.")
        if not await parameter.get(db, id=obj_in.parameter_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")
        if not await worksheet.get(db, id=obj_in.worksheet_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found.")
        if not await worksheet_data.get(db, id=obj_in.worksheet_data_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet data not found.")

        # 선택적 FK 확인
        if obj_in.analyst_login_id:
            if not await user.get(db, id=obj_in.analyst_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")
        if obj_in.approved_by_login_id:
            if not await user.get(db, id=obj_in.approved_by_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approver user not found.")

        if await self.get_by_unique_constraint(db,
                                               aliquot_sample_id=obj_in.aliquot_sample_id,
                                               parameter_id=obj_in.parameter_id,
                                               worksheet_data_id=obj_in.worksheet_data_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analysis result with this combination of aliquot, parameter, and worksheet data already exists.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.AnalysisResult, obj_in: lims_schemas.AnalysisResultUpdate) -> lims_models.AnalysisResult:
        """업데이트 시 FK 유효성 및 복합 고유 키 중복 검사."""
        from app.domains.usr.crud import user

        if obj_in.aliquot_sample_id is not None and obj_in.aliquot_sample_id != db_obj.aliquot_sample_id:
            if not await aliquot_sample.get(db, id=obj_in.aliquot_sample_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliquot sample not found.")
        if obj_in.parameter_id is not None and obj_in.parameter_id != db_obj.parameter_id:
            if not await parameter.get(db, id=obj_in.parameter_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")
        if obj_in.worksheet_id is not None and obj_in.worksheet_id != db_obj.worksheet_id:
            if not await worksheet.get(db, id=obj_in.worksheet_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet not found.")
        if obj_in.worksheet_data_id is not None and obj_in.worksheet_data_id != db_obj.worksheet_data_id:
            if not await worksheet_data.get(db, id=obj_in.worksheet_data_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worksheet data not found.")

        if obj_in.analyst_login_id is not None and obj_in.analyst_login_id != db_obj.analyst_login_id:
            if obj_in.analyst_login_id is not None:
                if not await user.get(db, id=obj_in.analyst_login_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")
            else:
                db_obj.analyst_login_id = None
        if obj_in.approved_by_login_id is not None and obj_in.approved_by_login_id != db_obj.approved_by_login_id:
            if obj_in.approved_by_login_id is not None:
                if not await user.get(db, id=obj_in.approved_by_login_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approver user not found.")
            else:
                db_obj.approved_by_login_id = None

        # 복합 고유 키 변경 시 중복 확인
        if (obj_in.aliquot_sample_id is not None and obj_in.aliquot_sample_id != db_obj.aliquot_sample_id) or \
           (obj_in.parameter_id is not None and obj_in.parameter_id != db_obj.parameter_id) or \
           (obj_in.worksheet_data_id is not None and obj_in.worksheet_data_id != db_obj.worksheet_data_id):

            target_aliquot_sample_id = obj_in.aliquot_sample_id if obj_in.aliquot_sample_id is not None else db_obj.aliquot_sample_id
            target_parameter_id = obj_in.parameter_id if obj_in.parameter_id is not None else db_obj.parameter_id
            target_worksheet_data_id = obj_in.worksheet_data_id if obj_in.worksheet_data_id is not None else db_obj.worksheet_data_id

            existing_result = await self.get_by_unique_constraint(db,
                                                                  aliquot_sample_id=target_aliquot_sample_id,
                                                                  parameter_id=target_parameter_id,
                                                                  worksheet_data_id=target_worksheet_data_id)
            if existing_result and existing_result.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analysis result with this combination already exists.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


analysis_result = CRUDAnalysisResult()


# =============================================================================
# 14. 시험 의뢰 템플릿 (TestRequestTemplate) CRUD
# =============================================================================
class CRUDTestRequestTemplate(CRUDBase[lims_models.TestRequestTemplate, lims_schemas.TestRequestTemplateCreate, lims_schemas.TestRequestTemplateUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.TestRequestTemplate)

    async def get_by_name_and_user(self, db: AsyncSession, *, name: str, login_id: int) -> Optional[lims_models.TestRequestTemplate]:
        """템플릿 이름과 사용자 ID로 조회합니다."""
        statement = select(self.model).where(
            self.model.name == name,
            self.model.login_id == login_id
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.TestRequestTemplateCreate, current_login_id: Optional[int] = None) -> lims_models.TestRequestTemplate:
        """FK 유효성 및 이름-사용자 중복을 확인하고 생성합니다."""
        from app.domains.usr.crud import user

        # login_id가 None이면 current_login_id로 설정 (라우터에서 처리 가능)
        if obj_in.login_id is None and current_login_id is not None:
            obj_in.login_id = current_login_id

        if not await user.get(db, id=obj_in.login_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        if await self.get_by_name_and_user(db, name=obj_in.name, login_id=obj_in.login_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test request template with this name already exists for this user.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.TestRequestTemplate, obj_in: lims_schemas.TestRequestTemplateUpdate) -> lims_models.TestRequestTemplate:
        """업데이트 시 FK 유효성 및 이름-사용자 중복 검사."""
        from app.domains.usr.crud import user

        if obj_in.login_id is not None and obj_in.login_id != db_obj.login_id:
            if not await user.get(db, id=obj_in.login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            else:
                db_obj.login_id = obj_in.login_id  # login_id 변경 가능하도록

        if (obj_in.name is not None and obj_in.name != db_obj.name) or \
           (obj_in.login_id is not None and obj_in.login_id != db_obj.login_id):

            target_name = obj_in.name if obj_in.name is not None else db_obj.name
            target_login_id = obj_in.login_id if obj_in.login_id is not None else db_obj.login_id

            existing_template = await self.get_by_name_and_user(db, name=target_name, login_id=target_login_id)
            if existing_template and existing_template.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test request template with this name already exists for the specified user.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


test_request_template = CRUDTestRequestTemplate()


# =============================================================================
# 15. 표준 시료 (StandardSample) CRUD
# =============================================================================
class CRUDStandardSample(CRUDBase[lims_models.StandardSample, lims_schemas.StandardSampleCreate, lims_schemas.StandardSampleUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.StandardSample)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[lims_models.StandardSample]:
        """표준 시료 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.StandardSampleCreate) -> lims_models.StandardSample:
        """FK 유효성 및 코드 중복을 확인하고 생성합니다."""
        if not await parameter.get(db, id=obj_in.parameter_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")

        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Standard sample with this code already exists.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.StandardSample, obj_in: lims_schemas.StandardSampleUpdate) -> lims_models.StandardSample:
        """업데이트 시 FK 유효성 및 코드 중복 검사."""
        if obj_in.parameter_id is not None and obj_in.parameter_id != db_obj.parameter_id:
            if not await parameter.get(db, id=obj_in.parameter_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")

        if obj_in.code is not None and obj_in.code != db_obj.code:
            existing_by_code = await self.get_by_code(db, code=obj_in.code)
            if existing_by_code and existing_by_code.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Standard sample with this code already exists.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


standard_sample = CRUDStandardSample()


# =============================================================================
# 16. 교정 기록 (CalibrationRecord) CRUD
# =============================================================================
class CRUDCalibrationRecord(CRUDBase[lims_models.CalibrationRecord, lims_schemas.CalibrationRecordCreate, lims_schemas.CalibrationRecordUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.CalibrationRecord)

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.CalibrationRecordCreate) -> lims_models.CalibrationRecord:
        """FK 유효성을 확인하고 생성합니다."""
        from app.domains.fms.crud import equipment as fms_equipment_crud
        from app.domains.usr.crud import user

        if not await fms_equipment_crud.get(db, id=obj_in.equipment_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")
        if not await parameter.get(db, id=obj_in.parameter_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")

        if obj_in.calibrated_by_login_id:
            if not await user.get(db, id=obj_in.calibrated_by_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibrated by user not found.")
        if obj_in.standard_sample_id:
            if not await standard_sample.get(db, id=obj_in.standard_sample_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Standard sample not found.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.CalibrationRecord, obj_in: lims_schemas.CalibrationRecordUpdate) -> lims_models.CalibrationRecord:
        """업데이트 시 FK 유효성 검사."""
        from app.domains.fms.crud import equipment as fms_equipment_crud
        from app.domains.usr.crud import user

        if obj_in.equipment_id is not None and obj_in.equipment_id != db_obj.equipment_id:
            if not await fms_equipment_crud.get(db, id=obj_in.equipment_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found.")
        if obj_in.parameter_id is not None and obj_in.parameter_id != db_obj.parameter_id:
            if not await parameter.get(db, id=obj_in.parameter_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")

        if obj_in.calibrated_by_login_id is not None and obj_in.calibrated_by_login_id != db_obj.calibrated_by_login_id:
            if obj_in.calibrated_by_login_id is not None:
                if not await user.get(db, id=obj_in.calibrated_by_login_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibrated by user not found.")
            else:
                db_obj.calibrated_by_login_id = None
        if obj_in.standard_sample_id is not None and obj_in.standard_sample_id != db_obj.standard_sample_id:
            if obj_in.standard_sample_id is not None:
                if not await standard_sample.get(db, id=obj_in.standard_sample_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Standard sample not found.")
            else:
                db_obj.standard_sample_id = None

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


calibration_record = CRUDCalibrationRecord()


# =============================================================================
# 17. QC 시료 결과 (QcSampleResult) CRUD
# =============================================================================
class CRUDQcSampleResult(CRUDBase[lims_models.QcSampleResult, lims_schemas.QcSampleResultCreate, lims_schemas.QcSampleResultUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.QcSampleResult)

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.QcSampleResultCreate) -> lims_models.QcSampleResult:
        """FK 유효성을 확인하고 생성합니다."""
        from app.domains.usr.crud import user

        if obj_in.aliquot_sample_id:
            if not await aliquot_sample.get(db, id=obj_in.aliquot_sample_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliquot sample not found.")
        if not await parameter.get(db, id=obj_in.parameter_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")
        if not await user.get(db, id=obj_in.analyst_login_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.QcSampleResult, obj_in: lims_schemas.QcSampleResultUpdate) -> lims_models.QcSampleResult:
        """업데이트 시 FK 유효성 검사."""
        from app.domains.usr.crud import user

        if obj_in.aliquot_sample_id is not None and obj_in.aliquot_sample_id != db_obj.aliquot_sample_id:
            if obj_in.aliquot_sample_id is not None:
                if not await aliquot_sample.get(db, id=obj_in.aliquot_sample_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliquot sample not found.")
            else:
                db_obj.aliquot_sample_id = None
        if obj_in.parameter_id is not None and obj_in.parameter_id != db_obj.parameter_id:
            if not await parameter.get(db, id=obj_in.parameter_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found.")
        if obj_in.analyst_login_id is not None and obj_in.analyst_login_id != db_obj.analyst_login_id:
            if not await user.get(db, id=obj_in.analyst_login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


qc_sample_result = CRUDQcSampleResult()


# =============================================================================
# 18. 사용자 정의 프로젝트/결과 보기 (PrView) CRUD
# =============================================================================
class CRUDPrView(CRUDBase[lims_models.PrView, lims_schemas.PrViewCreate, lims_schemas.PrViewUpdate]):
    def __init__(self):
        super().__init__(model=lims_models.PrView)

    async def get_by_name_and_user(self, db: AsyncSession, *, name: str, login_id: int) -> Optional[lims_models.PrView]:
        """보기 이름과 사용자 ID로 조회합니다."""
        statement = select(self.model).where(
            self.model.name == name,
            self.model.login_id == login_id
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: lims_schemas.PrViewCreate, current_login_id: Optional[int] = None) -> lims_models.PrView:
        """FK 유효성 및 이름-사용자 중복을 확인하고 생성합니다. (N+1 문제 해결)"""
        from app.domains.usr.crud import user
        from app.domains.loc.crud import facility as loc_facility_crud
        from app.domains.lims.crud import sampling_point, parameter

        if obj_in.login_id is None and current_login_id is not None:
            obj_in.login_id = current_login_id

        # --- 필수 FK 확인 ---
        if not await user.get(db, id=obj_in.login_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        if not await loc_facility_crud.get(db, id=obj_in.facility_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found for primary facility_id.")

        # --- 목록(List) 형태의 FK 유효성 검사 (단일 쿼리 사용) ---
        async def validate_ids(id_list: List[int], crud_obj: CRUDBase, model_name: str):
            if not id_list:
                return
            statement = select(crud_obj.model.id).where(crud_obj.model.id.in_(id_list))
            result = await db.execute(statement)
            found_ids = {row[0] for row in result.all()}
            missing_ids = set(id_list) - found_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model_name} with IDs {list(missing_ids)} not found."
                )

        await validate_ids(obj_in.facility_ids, loc_facility_crud, "Facility")
        await validate_ids(obj_in.sampling_point_ids, sampling_point, "Sampling point")
        await validate_ids(obj_in.parameter_ids, parameter, "Parameter")
        # --- 유효성 검사 로직 종료 ---

        if await self.get_by_name_and_user(db, name=obj_in.name, login_id=obj_in.login_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PR view with this name already exists for this user.")

        return await super().create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, db_obj: lims_models.PrView, obj_in: lims_schemas.PrViewUpdate) -> lims_models.PrView:
        """업데이트 시 FK 유효성 및 이름-사용자 중복 검사."""
        from app.domains.usr.crud import user
        from app.domains.loc.crud import wastewater_plant as loc_plant_crud

        if obj_in.login_id is not None and obj_in.login_id != db_obj.login_id:
            if not await user.get(db, id=obj_in.login_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            else:
                db_obj.login_id = obj_in.login_id  # login_id 변경 가능하도록

        if obj_in.facility_id is not None and obj_in.facility_id != db_obj.facility_id:
            if not await loc_plant_crud.get(db, id=obj_in.facility_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wastewater plant not found for primary facility_id.")
            else:
                db_obj.facility_id = obj_in.facility_id  # facility_id 변경 가능하도록

        # JSONB 배열 필드 내부의 ID 유효성 검사 (선택적)
        if obj_in.facility_ids:  # None이 아닌 경우에만 검사 수행
            for p_id in obj_in.facility_ids:
                if not await loc_plant_crud.get(db, id=p_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Wastewater plant with ID {p_id} not found in facility_ids.")
        # None으로 명시적으로 업데이트 시
        elif obj_in.facility_ids is not None and len(obj_in.facility_ids) == 0:
            obj_in.facility_ids = None  # 빈 리스트가 아닌 None으로 저장되도록

        if obj_in.sampling_point_ids:
            for sp_id in obj_in.sampling_point_ids:
                if not await sampling_point.get(db, id=sp_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sampling point with ID {sp_id} not found in sampling_point_ids.")
        elif obj_in.sampling_point_ids is not None and len(obj_in.sampling_point_ids) == 0:
            obj_in.sampling_point_ids = None

        if obj_in.parameter_ids:
            for p_id in obj_in.parameter_ids:
                if not await parameter.get(db, id=p_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parameter with ID {p_id} not found in parameter_ids.")
        elif obj_in.parameter_ids is not None and len(obj_in.parameter_ids) == 0:
            obj_in.parameter_ids = None

        if (obj_in.name is not None and obj_in.name != db_obj.name) or \
           (obj_in.login_id is not None and obj_in.login_id != db_obj.login_id):

            target_name = obj_in.name if obj_in.name is not None else db_obj.name
            target_login_id = obj_in.login_id if obj_in.login_id is not None else db_obj.login_id

            existing_view = await self.get_by_name_and_user(db, name=target_name, login_id=target_login_id)
            if existing_view and existing_view.id != db_obj.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PR view with this name already exists for the specified user.")

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


pr_view = CRUDPrView()
