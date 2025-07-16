COMMENT ON FUNCTION lims.generate_sample_code() IS 'LIMS 관련 함수 (plant_id, department_id, user_id 등 FK 참조 변경).';

CREATE OR REPLACE FUNCTION lims.generate_test_request_code() RETURNS trigger
    LANGUAGE plpgsql
    AS $generate_test_request_code$
    DECLARE
        request_date CHAR(8) := to_char(NEW.request_date, 'YYYYMMDD');
        project_c CHAR(4);
        dept_c CHAR(4);
    BEGIN
        SELECT code INTO project_c FROM lims.projects WHERE id = NEW.project_id;
        SELECT code INTO dept_c FROM usr.departments WHERE id = NEW.department_id;

        NEW.request_code := lpad(project_c::text,4,'0') ||
                            lpad(dept_c::text,4,'0') ||
                            request_date ||
                            lpad(NEW.id::text,4,'0');
        RETURN NEW;
    END;
$generate_test_request_code$;
COMMENT ON FUNCTION lims.generate_test_request_code() IS '새 시험 의뢰의 고유 코드를 자동으로 생성합니다.';