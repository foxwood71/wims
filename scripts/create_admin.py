# flake8: noqa
# utility/create_admin.py

import asyncio
import typer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database import engine
from app.domains.usr import crud as usr_crud
from app.domains.usr import schemas as usr_schemas
# UserRole Enum을 임포트합니다.
from app.domains.usr.models import UserRole

cli = typer.Typer()


async def create_admin_user(
    db: AsyncSession,
    user_in: usr_schemas.UserCreate
) -> None:
    """
    데이터베이스에 관리자 사용자를 생성하는 비동기 함수
    """
    db_user_by_email = await usr_crud.user.get_by_email(db, email=user_in.email)
    if db_user_by_email:
        print(f"오류: 이미 존재하는 이메일입니다: {user_in.email}")
        return

    db_user_by_username = await usr_crud.user.get_by_username(db, username=user_in.username)
    if db_user_by_username:
        print(f"오류: 이미 존재하는 사용자명입니다: {user_in.username}")
        return

    # 이제 생성(create) 한번으로 모든 작업이 끝납니다.
    await usr_crud.user.create(db, obj_in=user_in)
    print(f"관리자 계정이 성공적으로 생성되었습니다: {user_in.email} ({user_in.username})")


@cli.command()
def main(
    email: str = typer.Option(
        ..., '--email', '-e',
        prompt="관리자 이메일을 입력하세요",
        help="생성할 관리자 계정의 이메일 주소입니다."
    ),
    username: str = typer.Option(
        ..., '--username', '-u',
        prompt="관리자 사용자명(ID)을 입력하세요",
        help="로그인 시 사용할 사용자명(ID)입니다."
    ),
    password: str = typer.Option(
        ..., '--password', '-p',
        prompt="관리자 비밀번호를 입력하세요",
        hide_input=True,
        confirmation_prompt=True,
        help="생성할 관리자 계정의 비밀번호입니다. (최소 8자 이상)"
    ),
    full_name: str = typer.Option(
        "Admin", '--name', '-n',
        prompt="관리자 이름을 입력하세요",
        help="관리자의 이름입니다."
    ),
):
    """
    WIMS 애플리케이션을 위한 새로운 관리자(Admin/Superuser)를 생성합니다.
    """
    if len(password) < 8:
        print("오류: 비밀번호는 최소 8자 이상이어야 합니다.")
        raise typer.Abort()

    print("관리자 계정 생성을 시작합니다...")

    # UserCreate 스키마를 만들 때 role을 직접 ADMIN으로 지정합니다.
    # 만약 역할 이름이 ADMIN이 아니라면 (예: SUPERUSER), 그에 맞게 수정해주세요.
    user_data = usr_schemas.UserCreate(
        email=email,
        username=username,
        password=password,
        full_name=full_name,
        role=UserRole.ADMIN  # ADMIN 역할로 지정
    )

    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def run_creation():
        async with AsyncSessionLocal() as db:
            await create_admin_user(db=db, user_in=user_data)

    asyncio.run(run_creation())


if __name__ == "__main__":
    cli()