# pgslq_scripts/functions.py
from alembic_utils.pg_function import PGFunction

generate_test_request_code_func = PGFunction(
    schema="lims",  # 스키마 이름
    signature="generate_test_request_code()",  # 함수 시그니처
    definition="""
    -- 새 시험 의뢰의 고유 코드를 자동으로 생성합니다.
    RETURNS TRIGGER AS $$
    DECLARE
        request_date_val CHAR(8);
        project_code_val CHAR(4);
        dept_code_val CHAR(4);
        next_id BIGINT;
    BEGIN
        -- 1. 테이블의 기본 키 시퀀스에서 다음 ID 값을 미리 가져옵니다.
        --    (테이블명_id_seq 형식의 시퀀스 이름을 사용합니다.)
        SELECT nextval(pg_get_serial_sequence('lims.test_requests', 'id')) INTO next_id;

        -- 2. 가져온 ID를 NEW.id에 직접 할당합니다.
        NEW.id = next_id;

        -- 3. 나머지 필요한 값들을 조회합니다.
        request_date_val := to_char(NEW.request_date, 'YYYYMMDD');
        SELECT code INTO project_code_val FROM lims.projects WHERE id = NEW.project_id;
        SELECT code INTO dept_code_val FROM usr.departments WHERE id = NEW.department_id;

        -- 4. 이제 안전하게 확보된 NEW.id를 사용하여 request_code를 생성합니다.
        NEW.request_code := COALESCE(project_code_val, 'NA') ||
                            COALESCE(dept_code_val, 'NA') ||
                            request_date_val ||
                            lpad(NEW.id::text, 4, '0');
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
)

generate_sample_code_func = PGFunction(
    schema="lims",  # 스키마 이름
    signature="generate_sample_code()",  # 함수 시그니처
    definition="""
    RETURNS TRIGGER AS $$
    DECLARE
        request_code_val TEXT;
        next_seq INT;
    BEGIN
        -- 연결된 시험분석 요구서의 코드를 가져옵니다.
        SELECT request_code INTO request_code_val
        FROM lims.test_requests
        WHERE id = NEW.request_id;

        IF request_code_val IS NULL THEN
            RAISE EXCEPTION 'Cannot generate sample code: TestRequest.request_code is NULL for request_id %', NEW.request_id;
        END IF;

        -- 해당 요구서에 이미 연결된 시료의 수를 계산합니다.
        SELECT count(*) + 1 INTO next_seq
        FROM lims.samples
        WHERE request_id = NEW.request_id;

        -- request_sheet_index와 sample_code를 설정합니다.
        NEW.request_sheet_index := next_seq;
        NEW.sample_code := request_code_val || '-' || next_seq;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
)
