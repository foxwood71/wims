# app/domains/usr/routers.py

"""
'usr' 도메인 (사용자 및 부서 관리)과 관련된 API 엔드포인트를 정의하는 모듈입니다.
권한 확인 로직이 올바르게 수정되었습니다.
"""

from typing import List  # , Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

# 애플리케이션 설정 및 의존성 임포트
from app.core.config import settings
from app.core.database import get_session
from app.core import dependencies as deps

# usr 도메인의 CRUD, 모델, 스키마
from . import crud as usr_crud
from . import models as usr_models
from . import schemas as usr_schemas


# 라우터 인스턴스 생성 (prefix는 main.py에서 관리하므로 제거)
router = APIRouter(
    tags=["User & Department Management (사용자 및 부서 관리)"],  # Swagger UI에 표시될 태그
    responses={404: {"description": "Not found"}},  # 이 라우터의 공통 응답 정의
)


# =============================================================================
# 1. 인증 (Authentication) 엔드포인트
# =============================================================================

@router.post("/auth/token", response_model=usr_schemas.Token, summary="Access Token 획득")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session),
):
    user = await usr_crud.user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = deps.create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/auth/me", response_model=usr_schemas.UserRead, summary="현재 사용자 정보 조회")
async def read_users_me(current_user: usr_models.User = Depends(deps.get_current_active_user)):
    return current_user


# =============================================================================
# 2. 부서 (Department) 관리 엔드포인트
# =============================================================================

@router.post("/departments", response_model=usr_schemas.DepartmentRead, status_code=status.HTTP_201_CREATED, summary="새 부서 생성")
async def create_department(
    department: usr_schemas.DepartmentCreate,
    db: AsyncSession = Depends(get_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await usr_crud.department.create(db, obj_in=department)


@router.get("/departments", response_model=List[usr_schemas.DepartmentRead], summary="모든 부서 조회")
async def read_departments(
    db: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
):
    return await usr_crud.department.get_multi(db, skip=skip, limit=limit)


@router.get("/departments/{department_id}", response_model=usr_schemas.DepartmentRead, summary="특정 부서 조회")
async def read_department(
    department_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),  # 모든 활성 사용자가 조회 가능하도록 가정 (필요시 admin_user로 변경)
):
    department = await usr_crud.department.get(db, id=department_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department


@router.put("/departments/{department_id}", response_model=usr_schemas.DepartmentRead, summary="부서 업데이트")
async def update_department(
    department_id: int,
    department_in: usr_schemas.DepartmentUpdate,
    db: AsyncSession = Depends(get_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),  # 관리자 권한 필요
):
    db_department = await usr_crud.department.get(db, id=department_id)
    if not db_department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    db_department = await usr_crud.department.get(db, id=department_id)

    if not db_department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    # 중복 이름/코드 검사 (필요시) - 이 부분은 현재 에러와 직접 관련 없음
    if department_in.code and department_in.code != db_department.code:
        if await usr_crud.department.get_by_code(db, code=department_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department with this code already exists")

    if department_in.name and department_in.name != db_department.name:
        if await usr_crud.department.get_by_name(db, name=department_in.name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department with this name already exists")

    # **여기서 업데이트된 객체를 받습니다.**
    updated_dept = await usr_crud.department.update(db, db_obj=db_department, obj_in=department_in)

    # FastAPI는 `response_model`에 따라 반환된 객체를 자동으로 유효성 검사하고 직렬화합니다.
    # `updated_dept`가 SQLModel 객체이므로, `DepartmentRead` 스키마와 호환되는지 확인합니다.
    # 만약 `DepartmentRead`에 모델에 없는 필드가 있다면 문제가 될 수 있습니다.
    return updated_dept  #


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT, summary="부서 삭제")
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),  # 관리자 권한 필요
):
    department = await usr_crud.department.get(db, id=department_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    await usr_crud.department.remove(db, id=department_id)
    return None


# =============================================================================
# 3. 사용자 (User) 관리 엔드포인트
# =============================================================================
@router.post("/users", response_model=usr_schemas.UserRead, status_code=status.HTTP_201_CREATED, summary="새 사용자 생성")
async def create_user(
    user: usr_schemas.UserCreate,
    db: AsyncSession = Depends(get_session),
    current_admin_user: usr_models.User = Depends(deps.get_current_admin_user),
):
    return await usr_crud.user.create(db, obj_in=user)


@router.get("/users", response_model=List[usr_schemas.UserRead], summary="모든 사용자 조회")
async def read_users(
    db: AsyncSession = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    """
    모든 사용자 목록을 조회합니다.
    - 관리자(role <= 10)는 모든 사용자를 조회할 수 있습니다.
    - 일반 사용자(role > 10)는 자신의 정보만 조회합니다.
    """
    # [수정] is_admin 대신 role 기반으로 권한 확인
    if current_user.role > 10:
        return [current_user]

    users = await usr_crud.user.get_multi(db, skip=skip, limit=limit)
    return users


@router.get("/users/{user_id}", response_model=usr_schemas.UserRead, summary="특정 사용자 조회")
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    """
    ID로 특정 사용자 정보를 조회합니다.
    - 관리자는 모든 사용자 정보를 조회할 수 있습니다.
    - 일반 사용자는 자신의 정보만 조회할 수 있습니다.
    """
    user = await usr_crud.user.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # [수정] is_admin 대신 role 기반으로 권한 확인
    if current_user.role > 10 and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view other user's information."
        )
    return user


@router.put("/users/{user_id}", response_model=usr_schemas.UserRead, summary="사용자 업데이트")
async def update_user(
    user_id: int,
    user_in: usr_schemas.UserUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: usr_models.User = Depends(deps.get_current_active_user),
):
    """
    ID로 사용자 정보를 업데이트합니다.
    - 관리자는 모든 사용자 정보를 업데이트할 수 있습니다.
    - 일반 사용자는 자신의 정보만 업데이트할 수 있습니다.
    """
    db_user = await usr_crud.user.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # [수정] is_admin 대신 role 기반으로 권한 확인
    if current_user.role > 10 and db_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update other user's information."
        )

    # 이메일 중복 검사 로직 추가:
    if user_in.email is not None and user_in.email != db_user.email:
        existing_user_with_email = await usr_crud.user.get_by_email(db, email=user_in.email)
        if existing_user_with_email and existing_user_with_email.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    return await usr_crud.user.update(db, db_obj=db_user, obj_in=user_in)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="사용자 삭제")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_superuser: usr_models.User = Depends(deps.get_current_superuser),
):
    """
    ID로 사용자를 삭제합니다. 최고 관리자(Superuser) 권한이 필요합니다.
    """
    db_user = await usr_crud.user.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if db_user.id == current_superuser.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own superuser account.")

    await usr_crud.user.remove(db, id=user_id)
    return None
