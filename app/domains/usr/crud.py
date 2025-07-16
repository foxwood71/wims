# app/domains/usr/crud.py

"""
'usr' 도메인의 CRUD 작업을 담당하는 모듈입니다.
비동기 문법을 올바르게 사용하여 데이터베이스 쿼리를 실행합니다.
"""

from typing import Optional  # , Type, List, Any
from sqlmodel import select  # , SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

# 공통 CRUDBase 및 usr 도메인의 구성요소 임포트
from app.core.crud_base import CRUDBase
from . import models as usr_models
from . import schemas as usr_schemas
from app.core.security import get_password_hash, verify_password


# =============================================================================
# 1. usr.departments 테이블 CRUD
# =============================================================================
class CRUDDepartment(CRUDBase[usr_models.Department, usr_schemas.DepartmentCreate, usr_schemas.DepartmentUpdate]):
    def __init__(self):
        super().__init__(model=usr_models.Department)

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[usr_models.Department]:
        # statement = select(self.model).where(self.model.name == name)
        # result = await db.execute(statement)
        # return result.scalars().one_or_none()
        # 중복된 select 구문 대신, 부모의 범용 메서드를 호출
        return await self.get_by_attribute(db, attribute="name", value=name)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[usr_models.Department]:
        # statement = select(self.model).where(self.model.code == code)
        # result = await db.execute(statement)
        # return result.scalars().one_or_none()
        # 중복된 select 구문 대신, 부모의 범용 메서드를 호출
        return await self.get_by_attribute(db, attribute="code", value=code)

    async def create(self, db: AsyncSession, *, obj_in: usr_schemas.DepartmentCreate) -> usr_models.Department:
        if await self.get_by_code(db, code=obj_in.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department with this code already exists")
        if await self.get_by_name(db, name=obj_in.name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department with this name already exists")
        return await super().create(db, obj_in=obj_in)

    async def remove(self, db: AsyncSession, *, id: int) -> usr_models.Department:
        """
        부서를 삭제합니다. 관련된 사용자가 있다면 삭제를 거부합니다.
        """
        department_to_delete = await self.get(db, id=id)
        if not department_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,  # Flake8: E501
                                detail="Department not found")

        # 해당 부서에 연결된 사용자가 있는지 확인
        # relationship을 로드하기 위해 refresh_and_load_relationships 사용
        # if department_to_delete.users: # 이렇게 직접 접근하면 users 컬렉션이 로드되지 않을 수 있음
        # ORM 관계를 통해 사용자 수를 직접 쿼리
        user_count_statement = select(usr_models.User).where(usr_models.User.department_id == id)  # Flake8: E501
        users_in_department = await db.execute(user_count_statement)
        users = users_in_department.scalars().all()

        if users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,  # 또는 status.HTTP_409_CONFLICT  # Flake8: E501
                detail="Cannot delete department: associated users exist. "  # Flake8: E501
                       "Please reassign or delete associated users first."
            )

        return await super().delete(db, id=id)


department = CRUDDepartment()


# =============================================================================
# 2. usr.users 테이블 CRUD
# =============================================================================
class CRUDUser(CRUDBase[usr_models.User, usr_schemas.UserCreate, usr_schemas.UserUpdate]):
    def __init__(self):
        super().__init__(model=usr_models.User)

    async def get_by_login_id(self, db: AsyncSession, *, login_id: str) -> Optional[usr_models.User]:
        """사용자명으로 사용자를 조회합니다."""
        # statement = select(self.model).where(self.model.login_id == username)
        # result = await db.execute(statement)
        # return result.scalars().one_or_none()
        return await self.get_by_attribute(db, attribute="login_id", value=login_id)

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[usr_models.User]:
        """이메일로 사용자를 조회합니다."""
        # statement = select(self.model).where(self.model.email == email)
        # result = await db.execute(statement)
        # return result.scalars().one_or_none()
        return await self.get_by_attribute(db, attribute="email", value=email)

    async def create(self, db: AsyncSession, *, obj_in: usr_schemas.UserCreate) -> usr_models.User:
        """새로운 사용자를 생성하며 비밀번호를 해싱하고 중복을 검사합니다."""
        if await self.get_by_login_id(db, login_id=obj_in.login_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        if obj_in.email and await self.get_by_email(db, email=obj_in.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        hashed_password = get_password_hash(obj_in.password)
        user_data = obj_in.model_dump(exclude={"password"})
        db_user = usr_models.User(**user_data, password_hash=hashed_password)

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def authenticate(self, db: AsyncSession, *, login_id: str, password: str) -> Optional[usr_models.User]:
        """사용자명과 비밀번호를 사용하여 사용자를 인증합니다."""
        user = await self.get_by_login_id(db, login_id=login_id)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def remove(self, db: AsyncSession, *, id: int) -> usr_models.User:
        """
        사용자를 삭제합니다. 최고 관리자 계정은 삭제를 허용하지 않습니다.
        """
        user_to_delete = await self.get(db, id=id)
        if not user_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # [수정] 최고 관리자 계정 (role=1) 대신 Enum을 사용합니다.
        if user_to_delete.role == usr_models.UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a admin account directly."
            )

        return await super().delete(db, id=id)  # CRUDBase의 실제 삭제 로직 호출

    async def update(self, db: AsyncSession, *, db_obj: usr_models.User, obj_in: usr_schemas.UserUpdate) -> usr_models.User:
        """
        사용자 정보를 업데이트합니다. 최고 관리자 계정의 역할 변경 및 비활성화를 방지합니다.
        """
        # [수정] 최고 관리자 계정 (role=1) 대신 Enum을 사용합니다.
        if db_obj.role == usr_models.UserRole.ADMIN:
            if obj_in.role is not None and obj_in.role != usr_models.UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change the role of a admin account."
                )
            if obj_in.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate a admin account."
                )
        # 다른 역할의 사용자가 최고 관리자(role=1)로 변경되는 것을 방지
        # (이 로직은 router에서 권한 검증에 의해 대부분 커버되지만, CRUD단에서도 한 번 더 방어 가능)
        elif db_obj.role != usr_models.UserRole.ADMIN and obj_in.role == usr_models.UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,  # 또는 400, 하지만 권한 문제에 더 가까움
                detail="Only a admin can create or promote to another admin."
            )

        return await super().update(db, db_obj=db_obj, obj_in=obj_in)


user = CRUDUser()
