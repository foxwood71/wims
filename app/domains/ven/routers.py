# app/domains/ven/routers.py

"""
'ven' 도메인 (공급업체 관리)과 관련된 API 엔드포인트를 정의하는 모듈입니다.
"""

from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

# 공통 의존성 및 ven 도메인의 구성요소 임포트
# 핵심 의존성 (데이터베이스 세션, 사용자 인증 등)
from app.core import dependencies as deps

from app.domains.usr.models import User

from . import crud as ven_crud
from . import schemas as ven_schemas
from . import models as ven_models

# APIRouter 인스턴스 생성
router = APIRouter(
    tags=["vendor management (공급업체 관리)"],  # Swagger UI에 표시될 태그
    responses={404: {"description": "Not found"}},  # 이 라우터의 공통 응답 정의
)


# =============================================================================
# 1. 공급업체 카테고리 (VendorCategory) API
# =============================================================================


@router.post(
    "/vendor_categories",
    response_model=ven_schemas.VendorCategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="새 공급업체 카테고리 생성",
)
async def create_vendor_category(
    category_in: ven_schemas.VendorCategoryCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 필요 시 관리자 권한 추가
):
    """
    새로운 공급업체 카테고리를 생성합니다.
    - **name**: 카테고리 이름 (필수, 고유)
    - **description**: 설명 (선택)
    """
    #  카테고리 이름 중복 확인  #
    db_category = await ven_crud.vendor_category.get_vendor_category_by_name(
        db, name=category_in.name
    )
    if db_category:
        raise HTTPException(
            status_code=400, detail="Vendor category with this name already exists"
        )
    return await ven_crud.vendor_category.create(db, obj_in=category_in)


@router.get(
    "/vendor_categories",
    response_model=List[ven_schemas.VendorCategoryRead],
    summary="모든 공급업체 카테고리 조회",
)
async def read_vendor_categories(
    db: AsyncSession = Depends(deps.get_db_session), skip: int = 0, limit: int = 100
):
    """
    모든 공급업체 카테고리 목록을 조회합니다.
    """
    # 1. 올바른 CRUD 메서드 호출: ven_crud.vendor_category 사용
    categories = await ven_crud.vendor_category.get_multi(db, skip=skip, limit=limit)
    #  return categories
    # 2. 올바른 스키마로 변환: VendorCategoryRead.model_validate 사용
    #  return [ven_schemas.VendorCategoryRead.model_validate(cat) for cat in categories]
    return [ven_schemas.VendorCategoryRead.model_validate(cat.model_dump()) for cat in categories]


@router.get(  # 이 데코레이터가 추가되어야 합니다.
    "/vendor_categories/{category_id}",
    response_model=ven_schemas.VendorCategoryRead,
    summary="특정 공급업체 카테고리 정보 조회",
)
async def read_vendor_category(
    category_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    """
    특정 ID의 공급업체 카테고리 정보를 조회합니다.
    """
    db_category = await ven_crud.vendor_category.get(db, id=category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Not found")
    return db_category


@router.put(
    "/vendor_categories/{category_id}",
    response_model=ven_schemas.VendorCategoryRead,
    summary="공급업체 카테고리 정보 수정",
)
async def update_vendor_category(
    category_id: int,
    category_in: ven_schemas.VendorCategoryUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),
):
    """
    ID로 특정 공급업체 카테고리의 정보를 수정합니다.
    """
    db_category = await ven_crud.vendor_category.get(db, id=category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Vendor category not found")
    return await ven_crud.vendor_category.update(
        db, db_obj=db_category, obj_in=category_in
    )


@router.delete(
    "/vendor_categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="공급업체 카테고리 삭제",
)
async def delete_vendor_category(
    category_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),
):
    """
    ID로 특정 공급업체 카테고리를 삭제합니다.
    이때, 해당 카테고리에 연결된 벤더들은 '분류없음' 카테고리로 자동 변경됩니다.
    """
    db_category = await ven_crud.vendor_category.get(db, id=category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Vendor category not found")

    # 1. '분류없음' 기본 카테고리 조회 또는 생성 (실제 앱에서는 미리 생성된 ID를 사용)
    #    여기서는 예시를 위해 이름으로 조회한다고 가정. 실제는 설정 파일의 ID를 사용
    default_category = await ven_crud.vendor_category.get_vendor_category_by_name(
        db, name="분류없음"
    )
    if not default_category:
        # '분류없음' 카테고리가 없으면 생성 (앱 초기화 시 1회만 수행하는 것이 좋음)
        default_category = await ven_crud.vendor_category.create(
            db,
            obj_in=ven_schemas.VendorCategoryCreate(
                name="분류없음", description="카테고리가 없는 벤더들을 위한 기본 분류"
            ),
        )
        print(f"DEBUG: Created default '분류없음' category with ID: {default_category.id}")

    # 2. 삭제될 카테고리에 연결된 모든 벤더를 조회
    #    (이 메서드는 ven_crud.vendor_category 에 추가되어야 함, 현재 crud.py 에는 없음)
    #    예시: await ven_crud.vendor_category.get_vendors_linked_to_category(db, category_id=category_id)
    #    현재는 VendorVendorCategory CRUD를 통해 벤더 ID 목록을 가져와야 합니다.
    linked_vendor_links = await ven_crud.vendor_vendor_category.get_links_by_category(
        db, category_id=category_id
    )  # CRUD에 get_links_by_category 추가 필요

    # 3. 연결된 각 벤더를 '분류없음' 카테고리로 재연결
    for link in linked_vendor_links:
        try:
            # 새로운 연결 생성 (이미 연결되어 있다면 400 에러 발생하므로 try-except 필요)
            await ven_crud.vendor_vendor_category.create(
                db,
                obj_in=ven_schemas.VendorVendorCategoryCreate(
                    vendor_id=link.vendor_id,
                    vendor_category_id=default_category.id,
                ),
            )
            print(f"DEBUG: Vendor {link.vendor_id} re-linked to '분류없음' category.")
        except HTTPException as e:  # 중복 연결 에러 처리 (만약 이미 기본에 연결되어 있었다면)
            if e.detail == "Vendor is already linked to this category.":
                print(
                    f"DEBUG: Vendor {link.vendor_id} was already linked to '분류없음'. Skipping."
                )
            else:
                raise  # 다른 예외는 다시 발생

    # 4. 원래 카테고리 삭제 (ON DELETE CASCADE에 의해 연결 테이블 레코드도 삭제됨)
    await ven_crud.vendor_category.delete(db, id=category_id)

    return None


# =============================================================================
# 2. 공급업체 (Vendor) API
# =============================================================================


@router.post(
    "/vendors",
    response_model=ven_schemas.VendorRead,
    status_code=status.HTTP_201_CREATED,
    summary="새 공급업체 생성",
)
async def create_vendor(
    vendor_in: ven_schemas.VendorCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),
):
    """
    새로운 공급업체를 생성합니다.
    - **name**: 공급업체 이름 (필수, 고유)
    - **business_number**: 사업자 등록 번호 (선택, 고유)
    """
    # [추가] 공급업체 이름 중복 확인
    db_vendor_by_name = await ven_crud.vendor.get_vendor_by_name(
        db, name=vendor_in.name
    )
    if db_vendor_by_name:
        raise HTTPException(
            status_code=400, detail="Vendor with this name already exists"
        )

    # [추가] 사업자 등록 번호 중복 확인 (사업자 번호가 입력된 경우에만)
    if vendor_in.business_number:
        db_vendor_by_bn = await ven_crud.vendor.get_vendor_by_business_number(
            db, business_number=vendor_in.business_number
        )
        if db_vendor_by_bn:
            raise HTTPException(
                status_code=400,
                detail="Vendor with this business number already exists",
            )

    return await ven_crud.vendor.create(db, obj_in=vendor_in)


@router.get(
    "/vendors",
    response_model=List[ven_schemas.VendorRead],
    summary="모든 공급업체 조회",
)
async def read_vendors(db: AsyncSession = Depends(deps.get_db_session), skip: int = 0, limit: int = 100):
    """
    모든 공급업체 목록을 조회합니다.
    """
    # 올바른 CRUD 메서드 호출: ven_crud.vendor 사용
    vendors = await ven_crud.vendor.get_multi(db, skip=skip, limit=limit)
    return vendors
    # 올바른 스키마로 변환: VendorRead.model_validate 사용
    #  return [ven_schemas.VendorRead.model_validate(v) for v in vendors]
    #  return [ven_schemas.VendorRead.model_validate(v.model_dump()) for v in vendors]


@router.get(
    "/vendors/{vendor_id}",
    response_model=ven_schemas.VendorReadWithDetails,
    summary="특정 공급업체 상세 조회",
)
async def read_vendor(vendor_id: int, db: AsyncSession = Depends(deps.get_db_session)):
    """
    ID로 특정 공급업체의 상세 정보(담당자 포함)를 조회합니다.
    """
    # eager loading을 위해 selectinload 사용
    statement = select(ven_models.Vendor).where(ven_models.Vendor.id == vendor_id)
    # .options()를 사용하여 관계를 미리 로드 (eager loading)
    # contacts 관계를 로드하여 MissingGreenlet 에러 방지
    statement = statement.options(selectinload(ven_models.Vendor.contacts))

    result = await db.execute(statement)
    db_vendor = result.scalars().first()

    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # db_vendor 객체에 contacts가 이미 로드되어 있으므로, 직접 반환 가능.
    # FastAPI/Pydantic이 이를 VendorReadWithDetails 스키마에 맞춰 직렬화합니다.
    return db_vendor


@router.put(
    "/vendors/{vendor_id}",
    response_model=ven_schemas.VendorRead,
    summary="공급업체 정보 수정",
)
async def update_vendor(
    vendor_id: int,
    vendor_in: ven_schemas.VendorUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 권한 추가
):
    """
    ID로 특정 공급업체의 정보를 수정합니다.
    """
    db_vendor = await ven_crud.vendor.get(db, id=vendor_id)
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return await ven_crud.vendor.update(db, db_obj=db_vendor, obj_in=vendor_in)


@router.delete(
    "/vendors/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="공급업체 삭제",
)
async def delete_vendor(
    vendor_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 권한 추가
):
    """
    ID로 특정 공급업체를 삭제합니다.
    """
    db_vendor = await ven_crud.vendor.get(db, id=vendor_id)
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await ven_crud.vendor.delete(db, id=vendor_id)
    return None


# =============================================================================
# 3. 공급업체 담당자 (VendorContact) API
# =============================================================================


@router.post(
    "/vendor_contacts",
    response_model=ven_schemas.VendorContactRead,
    status_code=status.HTTP_201_CREATED,
    summary="새 공급업체 담당자 생성",
)
async def create_vendor_contact(
    contact_in: ven_schemas.VendorContactCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 권한 추가
):
    """
    새로운 공급업체 담당자 정보를 생성합니다.
    """
    # FK 유효성 검사 추가 (vendor_id)
    db_vendor = await ven_crud.vendor.get(db, id=contact_in.vendor_id)
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")  # 여기서 404를 반환함
    return await ven_crud.vendor_contact.create(db, obj_in=contact_in)


@router.get(
    "/vendors/{vendor_id}/contacts",
    response_model=List[ven_schemas.VendorContactRead],
    summary="특정 공급업체의 모든 담당자 조회",
)
async def read_contacts_for_vendor(
    vendor_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    """
    특정 공급업체에 속한 모든 담당자 목록을 조회합니다.
    """
    db_vendor = await ven_crud.vendor.get(db, id=vendor_id)
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    #  return await ven_crud.vendor_contact.get_by_vendor(db, vendor_id=vendor_id)
    contacts = await ven_crud.vendor_contact.get_contacts_by_vendor(
        db, vendor_id=vendor_id
    )
    return contacts
    #  return [ven_schemas.VendorContactRead.model_validate(c.model_dump()) for c in contacts]


@router.get(
    "/vendor_contacts/{contact_id}",
    response_model=ven_schemas.VendorContactRead,
    summary="특정 공급업체 담당자 조회",
)
async def read_vendor_contact(
    contact_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    """
    ID를 기준으로 특정 공급업체 담당자를 조회합니다.
    """
    db_contact = await ven_crud.vendor_contact.get(db, id=contact_id)
    if not db_contact:
        raise HTTPException(status_code=404, detail="Not found")
    return db_contact


@router.put(
    "/vendor_contacts/{contact_id}",  # <-- 이 부분은 기존에 없던 엔드포인트이므로 추가되어야 합니다.
    response_model=ven_schemas.VendorContactRead,
    summary="공급업체 담당자 정보 수정",
)
async def update_vendor_contact(
    contact_id: int,
    contact_in: ven_schemas.VendorContactUpdate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 권한 추가
):
    """
    ID로 특정 공급업체 담당자의 정보를 수정합니다.
    """
    db_contact = await ven_crud.vendor_contact.get(db, id=contact_id)
    if not db_contact:
        raise HTTPException(status_code=404, detail="Vendor contact not found")
    return await ven_crud.vendor_contact.update(
        db, db_obj=db_contact, obj_in=contact_in
    )


@router.delete(
    "/vendor_contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="공급업체 담당자 삭제",
)
async def delete_vendor_contact(
    contact_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 관리자 권한 추가
):
    """
    ID로 특정 공급업체 담당자를 삭제합니다.
    """
    db_contact = await ven_crud.vendor_contact.get(db, id=contact_id)
    if not db_contact:
        raise HTTPException(status_code=404, detail="Vendor contact not found")
    await ven_crud.vendor_contact.delete(db, id=contact_id)
    return None


# =============================================================================
# 4. 공급업체-카테고리 연결 (VendorVendorCategory) API 추가
# =============================================================================


@router.post(
    "/vendor_vendor_categories",
    response_model=ven_schemas.VendorVendorCategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="공급업체와 카테고리 연결",
)
async def create_vendor_vendor_category(
    link_in: ven_schemas.VendorVendorCategoryCreate,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 관리자 권한 필요
):
    """
    특정 공급업체에 카테고리를 연결합니다.
    - **vendor_id**: 공급업체 ID (필수)
    - **vendor_category_id**: 공급업체 카테고리 ID (필수)
    """
    #  이미 존재하는 연결인지 확인  #
    existing_link = await ven_crud.vendor_vendor_category.get_link(
        db, vendor_id=link_in.vendor_id, category_id=link_in.vendor_category_id
    )
    if existing_link:
        raise HTTPException(
            status_code=400, detail="Vendor is already linked to this category."
        )

    #  유효한 vendor_id와 vendor_category_id인지 확인  #
    vendor_obj = await ven_crud.vendor.get(db, id=link_in.vendor_id)
    category_obj = await ven_crud.vendor_category.get(db, id=link_in.vendor_category_id)

    if not vendor_obj:
        raise HTTPException(status_code=404, detail="Vendor not found.")
    if not category_obj:
        raise HTTPException(status_code=404, detail="Vendor category not found.")

    return await ven_crud.vendor_vendor_category.create(db, obj_in=link_in)


@router.get(
    "/vendors/{vendor_id}/categories",
    response_model=List[ven_schemas.VendorCategoryRead],
    summary="특정 공급업체에 연결된 모든 카테고리 조회",
)
async def read_vendor_categories_for_vendor(
    vendor_id: int, db: AsyncSession = Depends(deps.get_db_session)
):
    """
    특정 공급업체에 연결된 모든 카테고리 목록을 조회합니다.
    """
    db_vendor = await ven_crud.vendor.get(db, id=vendor_id)
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    categories = await ven_crud.vendor_vendor_category.get_categories_for_vendor(
        db, vendor_id=vendor_id
    )
    return categories
    #  return [ven_schemas.VendorCategoryRead.model_validate(c) for c in categories]
    # return [ven_schemas.VendorCategoryRead.model_validate(c.model_dump()) for c in categories]


@router.delete(
    "/vendor_vendor_categories",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="공급업체와 카테고리 연결 해제",
)
async def delete_vendor_vendor_category(
    vendor_id: int,
    vendor_category_id: int,
    db: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_admin_user),  # 관리자 권한 필요
):
    """
    특정 공급업체와 카테고리 간의 연결을 해제합니다.
    """
    db_link = await ven_crud.vendor_vendor_category.get_link(db, vendor_id, vendor_category_id)
    if not db_link:
        raise HTTPException(status_code=404, detail="Vendor-category link not found.")
    await ven_crud.vendor_vendor_category.delete_link(db, vendor_id, vendor_category_id)
    return None
