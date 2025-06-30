# app/services/cross_domain_service.py

"""
여러 도메인에 걸쳐 복잡한 비즈니스 로직을 처리하는 서비스 모듈입니다.

이 서비스는 주로 다른 도메인의 CRUD(Create, Read, Update, Delete) 작업을 조합하거나,
비즈니스 규칙을 적용하여 데이터를 조정하는 역할을 수행합니다.
직접적으로 데이터베이스 세션에 접근하여 쿼리를 수행할 수도 있지만,
가급적 각 도메인의 `crud` 모듈을 활용하여 데이터베이스 상호작용을 추상화하는 것이 좋습니다.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException, status

# 의존성 주입을 위해 필요한 경우 (예: get_session)
from app.core.dependencies import get_db_session_dependency

# 관련 도메인의 모델, 스키마, CRUD 모듈을 임포트합니다.
# 이제 'app.domains' 하위 경로를 사용합니다.
from app.domains.lims import models as lims_models
from app.domains.lims import crud as lims_crud
from app.domains.inv import models as inv_models
from app.domains.inv import crud as inv_crud
from app.domains.usr import models as usr_models # 사용자 정보가 필요할 수 있으므로 임포트

class CrossDomainService:
    """
    여러 도메인에 걸친 비즈니스 로직을 처리하는 서비스 클래스입니다.
    """

    def __init__(self, db: Session):
        """
        서비스 인스턴스 초기화. FastAPI의 Depends를 통해 데이터베이스 세션을 주입받습니다.
        Args:
            db (Session): 데이터베이스 세션.
        """
        self.db = db
        # 각 도메인의 CRUD 인스턴스를 서비스 내에서 사용할 수 있도록 초기화합니다.
        self.lims_crud = lims_crud
        self.inv_crud = inv_crud

    async def process_sample_analysis_completion(
        self, aliquot_sample_id: int, analyst_user_id: int, reagent_material_id: Optional[int] = None, quantity_used: Optional[float] = None
    ) -> lims_models.AliquotSample:
        """
        분할 시료의 분석 완료를 처리하고, 필요한 경우 사용된 시약을 재고에서 차감합니다.

        Args:
            aliquot_sample_id (int): 분석이 완료된 분할 시료의 ID.
            analyst_user_id (int): 분석을 완료한 사용자의 ID.
            reagent_material_id (Optional[int]): 사용된 시약(자재)의 ID.
            quantity_used (Optional[float]): 사용된 시약의 수량.

        Returns:
            lims_models.AliquotSample: 업데이트된 분할 시료 객체.

        Raises:
            HTTPException: 시료 또는 자재를 찾을 수 없거나 재고가 부족할 경우.
        """
        # 1. 분할 시료의 상태를 'Completed'로 업데이트
        # 먼저 해당 분할 시료를 조회합니다.
        aliquot_sample = await self.lims_crud.aliquot_sample.get_aliquot_sample(self.db, aliquot_sample_id)
        if not aliquot_sample:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliquot sample not found")

        # 분석 상태 및 분석자 업데이트 (부분 업데이트 스키마를 사용하는 것이 더 좋습니다)
        # 여기서는 편의상 모델 직접 수정 예시
        aliquot_sample.analysis_status = "Completed"
        aliquot_sample.analysis_date = datetime.now().date()
        aliquot_sample.analyst_user_id = analyst_user_id

        # SQLModel 업데이트 로직 (CRUD를 통해)
        updated_aliquot_sample = await self.lims_crud.aliquot_sample.update_aliquot_sample(
            self.db,
            aliquot_sample_id,
            lims_models.AliquotSampleUpdate(
                analysis_status="Completed",
                analysis_date=datetime.now().date(),
                analyst_user_id=analyst_user_id
            )
        )
        if not updated_aliquot_sample:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update aliquot sample status.")


        print(f"DEBUG: 분할 시료 {aliquot_sample_id}의 분석 상태가 'Completed'로 업데이트되었습니다.")

        # 2. 사용된 시약(자재)이 있다면 재고에서 차감 (Inventory 도메인과 연동)
        if reagent_material_id and quantity_used and quantity_used > 0:
            print(f"DEBUG: 시약(자재) ID {reagent_material_id}, 사용량 {quantity_used} 차감 시도.")

            # 해당 자재를 조회
            reagent_material = await self.inv_crud.material.get_material(self.db, reagent_material_id)
            if not reagent_material:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reagent material with ID {reagent_material_id} not found.")

            # FIFO 방식으로 재고 차감 (inv.material_transactions의 트리거를 활용하거나, 여기서 직접 구현)
            # 여기서는 직접 `inv.material_transactions`를 생성하여 차감 로직을 발동시킵니다.
            # `inv.deduct_material_fifo()` 함수가 트리거로 연결되어 있거나,
            # `inv_crud.material_transaction`에 FIFO 로직이 구현되어 있어야 합니다.
            # 여기서는 간단히 트랜잭션만 생성하는 예시를 보여줍니다.
            plant_id_for_transaction = 1 # 예시: 트랜잭션이 발생하는 처리장 ID. 실제로는 aliquot_sample.plant_id 등을 사용
            user_who_performed = await self.lims_crud.user.get_user(self.db, analyst_user_id) # CRUD에서 사용자 조회
            if not user_who_performed:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst user not found for transaction logging.")


            try:
                await self.inv_crud.material_transaction.create_material_transaction(
                    self.db,
                    inv_models.MaterialTransactionCreate(
                        material_id=reagent_material_id,
                        plant_id=plant_id_for_transaction, # 실제 환경에 맞게 조정 필요
                        transaction_type="USAGE",
                        quantity_change=-quantity_used, # 사용이므로 음수
                        transaction_date=datetime.now(timezone.utc),
                        performed_by_user_id=analyst_user_id,
                        notes=f"LIMS analysis completion for aliquot_sample_id: {aliquot_sample_id}"
                    )
                )
                print(f"DEBUG: 자재 {reagent_material.name} (ID: {reagent_material_id}) {quantity_used} {reagent_material.unit_of_measure} 재고 차감 기록 완료.")
            except Exception as e:
                # 재고 부족 등의 오류 처리 (트리거에서 발생할 수 있음)
                print(f"ERROR: 재고 차감 중 오류 발생: {e}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to deduct material from stock: {e}")

        # 3. 원 시료의 분석 상태 업데이트 (LIMS 도메인 내부 트리거 또는 여기서 직접 호출)
        # 이 로직은 lims.update_parent_sample_analysis_status() 트리거에 의해 자동으로 처리될 수 있습니다.
        # 만약 트리거 대신 서비스에서 명시적으로 제어하고자 한다면 여기에 추가 로직을 구현합니다.
        # await self.lims_crud.sample.update_parent_status_based_on_aliquots(self.db, aliquot_sample.parent_sample_id)
        print(f"DEBUG: 원 시료 상태 업데이트는 LIMS 도메인의 트리거에 의해 처리됩니다.")


        # 4. 추가 비즈니스 로직 (예: 알림, 보고서 트리거 등)
        # - 분석 완료 알림 이메일/SMS 발송 (notification_service 사용)
        # - QA/QC 데이터 일관성 검증 로직 호출
        # - 보고서 생성 서비스에 이벤트 전달

        return updated_aliquot_sample

# 이 서비스를 FastAPI 라우터에서 의존성 주입으로 사용할 수 있도록 함수를 정의합니다.
# 이렇게 하면 각 요청마다 서비스 인스턴스가 생성됩니다.
def get_cross_domain_service(
    db: Session = Depends(get_db_session_dependency)
) -> CrossDomainService:
    """
    FastAPI 의존성 주입을 통해 CrossDomainService 인스턴스를 제공합니다.
    """
    return CrossDomainService(db)

# -- 사용 예시 (라우터에서) --
# from fastapi import APIRouter, Depends
# from app.core.dependencies import get_current_active_user
# from app.domains.usr.models import User
# from app.domains.lims import schemas as lims_schemas
#
# router = APIRouter()
#
# @router.post("/lims/aliquot_samples/{aliquot_id}/complete_analysis", response_model=lims_schemas.AliquotSampleResponse)
# async def complete_analysis_and_deduct_material(
#     aliquot_id: int,
#     reagent_material_id: Optional[int] = None,
#     quantity_used: Optional[float] = None,
#     current_user: User = Depends(get_current_active_user),
#     cross_service: CrossDomainService = Depends(get_cross_domain_service) # 서비스 의존성 주입
# ):
#     """
#     분할 시료 분석을 완료하고, 사용된 시약을 재고에서 차감합니다.
#     """
#     updated_aliquot = await cross_service.process_sample_analysis_completion(
#         aliquot_sample_id=aliquot_id,
#         analyst_user_id=current_user.id,
#         reagent_material_id=reagent_material_id,
#         quantity_used=quantity_used
#     )
#     return updated_aliquot