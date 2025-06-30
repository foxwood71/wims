# app/domains/loc/crud.py

"""
'loc' 도메인 (위치 정보)과 관련된 CRUD 로직을 담당하는 모듈입니다.
"""

from typing import List, Union, Dict, Any, Optional
import logging

# from sqlalchemy.orm import joinedload # joinedload 임포트 추가
from sqlalchemy.exc import IntegrityError

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import HTTPException, status

# 공통 CRUDBase 및 LOC 도메인의 모델, 스키마 임포트
from app.core.crud_base import CRUDBase
from . import models as loc_models
from . import schemas as loc_schemas
from app.domains.fms.models import Equipment as FmsEquipment


# 로거 인스턴스 생성: 파일의 최상단에 위치하여 모듈 전체에서 사용 가능하도록 합니다.
logger = logging.getLogger(__name__)


# =============================================================================
# 1. 시설 (Facility) CRUD
# =============================================================================
class CRUDFacility(
    CRUDBase[
        loc_models.Facility,
        loc_schemas.FacilityCreate,
        loc_schemas.FacilityUpdate
    ]
):
    def __init__(self):
        super().__init__(model=loc_models.Facility)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[loc_models.Facility]:
        """시설 코드로 조회합니다."""
        statement = select(self.model).where(self.model.code == code)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[loc_models.Facility]:
        """시설 이름으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: loc_schemas.FacilityCreate) -> loc_models.Facility:
        """코드/이름 중복을 확인하고 생성합니다."""
        if obj_in.code and await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=400, detail="Facility with this code already exists.")
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=400, detail="Facility with this name already exists.")
        return await super().create(db, obj_in=obj_in)

    # async def remove(self, db: AsyncSession, *, id: int) -> Optional[loc_models.Facility]:
    #     """ID로 시설을 삭제합니다. 관련된 데이터가 있으면 삭제를 제한합니다."""
    #     db_obj = await self.get(db, id=id)
    #     if db_obj is None:
    #         return None

    #     existing_locations = await db.execute(
    #         select(loc_models.Location).where(loc_models.Location.facility_id == id)  # facility_id -> facility_id
    #     )
    #     if existing_locations.scalars().first():
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Cannot delete facility because there are associated locations."
    #         )

    #     existing_equipments = await db.execute(
    #         select(FmsEquipment).where(FmsEquipment.facility_id == id)  # facility_id -> facility_id
    #     )
    #     if existing_equipments.scalars().first():
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Cannot delete facility because there are associated equipments."
    #         )

    #     try:
    #         await db.delete(db_obj)
    #         await db.commit()
    #         return db_obj
    #     except IntegrityError as e:
    #         await db.rollback()
    #         logger.error(f"IntegrityError caught during facility deletion (ID: {id}): {e}", exc_info=True)
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Cannot delete facility due to existing related data."
    #         )
    #     except Exception as e:
    #         await db.rollback()
    #         logger.error(f"Unexpected error during facility deletion (ID: {id}): {e}", exc_info=True)
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"An unexpected error occurred: {e}"
    #         )
    async def remove(self, db: AsyncSession, *, id: int) -> Optional[loc_models.Facility]:
        """
        시설을 삭제합니다.
        단, 하위에 소속된 장소(Location)나 설비(Equipment)가 있으면 삭제를 거부합니다.
        """
        # 1. 삭제할 시설에 소속된 장소(Location)가 있는지 확인
        location_check_stmt = select(loc_models.Location).where(loc_models.Location.facility_id == id).limit(1)
        if (await db.execute(location_check_stmt)).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this facility as it has associated locations."
            )

        # 2. 삭제할 시설에 소속된 설비(Equipment)가 있는지 확인
        equipment_check_stmt = select(FmsEquipment).where(FmsEquipment.facility_id == id).limit(1)
        if (await db.execute(equipment_check_stmt)).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this facility as it has associated equipment."
            )

        # 3. 하위 데이터가 없으면, 부모 클래스의 기본 삭제 로직을 호출
        # (remove 대신 delete를 사용하고 계시므로 delete로 유지합니다)
        return await super().delete(db, id=id)

    async def update(
        self,
        db: AsyncSession, *, db_obj: loc_models.Facility, obj_in: Union[loc_schemas.FacilityUpdate, Dict[str, Any]]
    ) -> loc_models.Facility:
        """시설 정보를 업데이트합니다."""
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


facility = CRUDFacility()  # 인스턴스명 변경


# =============================================================================
# 2. 위치 유형 (LocationType) CRUD
# =============================================================================
class CRUDLocationType(
    CRUDBase[
        loc_models.LocationType,
        loc_schemas.LocationTypeCreate,
        loc_schemas.LocationTypeUpdate
    ]
):
    def __init__(self):
        super().__init__(model=loc_models.LocationType)

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[loc_models.LocationType]:
        """유형 이름으로 조회합니다."""
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: loc_schemas.LocationTypeCreate) -> loc_models.LocationType:
        """이름 중복을 확인하고 생성합니다."""
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=400, detail="Location type with this name already exists.")
        return await super().create(db, obj_in=obj_in)

    # async def remove(self, db: AsyncSession, *, id: int) -> Optional[loc_models.LocationType]:
    #     """ID로 유형을 삭제합니다. 관련된 Location 데이터가 있으면 삭제를 제한합니다."""
    #     # 명시적으로 관련된 Location이 있는지 확인합니다.
    #     check_query = select(loc_models.Location).where(loc_models.Location.location_type_id == id)
    #     result = await db.execute(select(check_query.exists()))
    #     is_in_use = result.scalar()

    #     if is_in_use:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Cannot delete location type due to existing related data."
    #         )

    #     # 관련된 데이터가 없으면 삭제를 진행합니다.
    #     db_obj = await self.get(db, id=id)
    #     if db_obj:
    #         await db.delete(db_obj)
    #         await db.commit()
    #         return db_obj
    #     return None

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[loc_models.LocationType]:
        """
        장소 유형을 삭제합니다.
        단, 해당 유형을 사용하는 장소(Location)가 있으면 삭제를 거부합니다.
        """
        # 1. 이 유형을 사용하는 장소가 있는지 확인합니다.
        location_check_stmt = select(loc_models.Location).where(loc_models.Location.location_type_id == id).limit(1)
        if (await db.execute(location_check_stmt)).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this location type as it is currently in use by locations."
            )

        # 2. 연결된 장소가 없으면, 부모 클래스의 기본 삭제 로직을 호출
        return await super().delete(db, id=id)

    async def update(  # update 추가
        self,
        db: AsyncSession,
        *,
        db_obj: loc_models.LocationType,
        obj_in: Union[loc_schemas.LocationTypeUpdate, Dict[str, Any]]
    ) -> loc_models.LocationType:
        """유형 정보를 업데이트합니다."""
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


location_type = CRUDLocationType()


# =============================================================================
# 3. 상세 위치 (Location) CRUD
# =============================================================================
class CRUDLocation(
    CRUDBase[
        loc_models.Location,
        loc_schemas.LocationCreate,
        loc_schemas.LocationUpdate
    ]
):
    def __init__(self):
        super().__init__(model=loc_models.Location)

    async def get_by_facility(  # get_by_plant -> get_by_facility
        self, db: AsyncSession, *, facility_id: int, skip: int = 0, limit: int = 100
    ) -> List[loc_models.Location]:
        """특정 시설 ID에 속한 장소 목록을 조회합니다."""
        statement = select(self.model).where(self.model.facility_id == facility_id).offset(skip).limit(limit)  # facility_id -> facility_id
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def get_by_name_and_facility(  # get_by_name_and_plant -> get_by_name_and_facility
        self, db: AsyncSession, *, facility_id: int, name: str, parent_location_id: Optional[int] = None
    ) -> Optional[loc_models.Location]:
        """주어진 시설 ID, 이름, 상위 장소 ID 조합으로 장소를 조회합니다."""
        statement = select(self.model).where(
            self.model.facility_id == facility_id,  # facility_id -> facility_id
            self.model.name == name,
            self.model.parent_location_id == parent_location_id
        )
        result = await db.execute(statement)
        return result.scalars().one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: loc_schemas.LocationCreate) -> loc_models.Location:
        """FK 유효성을 확인하고 생성합니다."""
        if not await facility.get(db, id=obj_in.facility_id):  # wastewater_plant -> facility, facility_id -> facility_id
            raise HTTPException(status_code=400, detail="Facility not found for the given ID")
        if obj_in.location_type_id and not await location_type.get(db, id=obj_in.location_type_id):
            raise HTTPException(status_code=400, detail="Location type not found for the given ID")
        if obj_in.parent_location_id and not await self.get(db, id=obj_in.parent_location_id):
            raise HTTPException(status_code=400, detail="Parent location not found for the given ID")
        return await super().create(db, obj_in=obj_in)

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[loc_models.Location]:
        """ID로 장소를 삭제합니다. 연결된 설비(Equipment)가 있으면 삭제를 제한합니다."""
        equipment_check_query = select(FmsEquipment).where(FmsEquipment.current_location_id == id)
        result = await db.execute(select(equipment_check_query.exists()))
        is_in_use_by_equipment = result.scalar()

        if is_in_use_by_equipment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete location due to existing related data."
            )

        db_obj = await self.get(db, id=id)
        if db_obj:
            try:
                await db.delete(db_obj)
                await db.commit()
                return db_obj
            except IntegrityError as e:
                await db.rollback()
                logger.error(f"IntegrityError during location deletion (ID: {id}): {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete location due to existing related data."
                )
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: loc_models.Location, obj_in: Union[loc_schemas.LocationUpdate, Dict[str, Any]]
    ) -> loc_models.Location:
        """장소 정보를 업데이트합니다."""
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


location = CRUDLocation()
