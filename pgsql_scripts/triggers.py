# pgsql_scripts/triggers.py
from alembic_utils.pg_trigger import PGTrigger
from . import functions as pg_func
# from .functions import  generate_test_request_code_func, generate_sample_code_func

db_schema = pg_func.generate_test_request_code_func.schema
db_func = pg_func.generate_test_request_code_func.signature
trg_before_insert_test_requests = PGTrigger(
    schema="lims",
    signature="before_insert_test_requests",
    on_entity="lims.test_requests",  # 이 트리거가 적용될 테이블
    is_constraint=False,
    definition=f"""
    BEFORE INSERT
    ON lims.test_requests
    FOR EACH ROW
    EXECUTE FUNCTION {db_schema}.{db_func}
    """
)

db_schema = pg_func.generate_sample_code_func.schema
db_func = pg_func.generate_sample_code_func.signature
trg_before_insert_samples = PGTrigger(
    schema="lims",  # 스키마 이름
    signature="before_insert_samples",  # 트리거 이름
    on_entity="lims.samples",  # 트리거를 적용할 테이블
    is_constraint=False,
    definition=f"""
    BEFORE INSERT
    ON lims.samples
    FOR EACH ROW
    EXECUTE FUNCTION {db_schema}.{db_func}
    """
    # {함수.identity}를 사용하면 함수가 변경되어도 자동으로 참조
)
