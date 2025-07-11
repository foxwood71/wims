"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel  #  SQLModel을 지원하기 위해 이 줄을 추가합니다.
${imports if imports else ""}

#  revision identifiers, used by Alembic.
revision = '${up_revision}'
down_revision = ${down_revision | repr,n}
branch_labels = ${branch_labels | repr,n}
depends_on = ${depends_on | repr,n}


def upgrade() -> None:
    #  ### commands auto generated by Alembic - please adjust! ###
    #  필요한 모든 스키마를 여기에 정의합니다.
    schemas = ['fms', 'inv', 'lims', 'loc', 'ops', 'shared', 'usr', 'ven']
    for schema in schemas:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    ${upgrades if upgrades else "pass"}
    #  ### end Alembic commands ###


def downgrade() -> None:
    #  ### commands auto generated by Alembic - please adjust! ###
    ${downgrades if downgrades else "pass"}
    #  ### end Alembic commands ###
