import psycopg2
import logging
import json
from datetime import datetime

# 로깅 설정  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 데이터베이스 연결 정보 설정 (각자의 환경에 맞게 수정) ---
GUMC_DB_CONFIG = {
    'host': 'localhost',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'port': '5432',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'database': 'gumc_dbv3',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'user': 'lims',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'password': 'lims1234'  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
}

WIMS_DB_CONFIG = {
    'host': 'localhost',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'port': '5432',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'database': 'wims_dbv1',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'user': 'wims',  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    'password': 'wims1234'  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
}


# -----------------------------------------------------------
def get_db_connection(db_config):
    """데이터베이스 연결을 설정합니다."""  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    conn = None  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        conn = psycopg2.connect(**db_config)
        logging.info(f"데이터베이스에 성공적으로 연결되었습니다: {db_config['database']}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    except Exception as e:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        logging.error(f"데이터베이스 연결 오류: {e}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        raise  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    return conn  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.


def migrate_data(gumc_conn, wims_conn):
    """1단계 데이터를 GUMC에서 WIMS로 이전합니다."""  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    gumc_cur = gumc_conn.cursor()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    wims_cur = wims_conn.cursor()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    # 1. usr.departments (GUMC: users.tbldepartments) 이전
    logging.info("usr.departments 테이블 이전 시작...")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        gumc_cur.execute("SELECT department_id, code, name, note, sort_order, site_list, registered_date FROM users.tbldepartments;")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        departments_data = gumc_cur.fetchall()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

        for row in departments_data:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            department_id, code, name, note, sort_order, site_list_str, registered_date = row  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            # site_list는 JSONB 타입으로 변환 (GUMC는 text)  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            site_list_jsonb = []  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            if site_list_str:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
                try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
                    # site_list_str이 쉼표로 구분된 문자열이라고 가정하고 처리  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
                    # WIMS의 site_list는 JSONB 배열 형태를 기대함 (예: [1, 2, 3])  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
                    site_list_jsonb = [int(s.strip()) for s in site_list_str.split(',') if s.strip().isdigit()]  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
                except ValueError:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
                    logging.warning(f"department_id {department_id}: site_list '{site_list_str}' JSON 변환 실패. 빈 리스트로 처리됩니다.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

            wims_cur.execute(
                """
                INSERT INTO usr.departments (id, code, name, notes, sort_order, site_list, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    code = EXCLUDED.code,
                    name = EXCLUDED.name,
                    notes = EXCLUDED.notes,
                    sort_order = EXCLUDED.sort_order,
                    site_list = EXCLUDED.site_list,
                    updated_at = EXCLUDED.updated_at;
                """,
                (department_id, code, name, note, sort_order, json.dumps(site_list_jsonb), registered_date, registered_date)
            )
        logging.info(f"usr.departments {len(departments_data)}개 레코드 이전 완료.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.commit()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    except Exception as e:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.rollback()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        logging.error(f"usr.departments 이전 중 오류 발생: {e}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        raise  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    # 2. usr.users (GUMC: users.tblusers) 이전
    logging.info("usr.users 테이블 이전 시작...")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        gumc_cur.execute("SELECT user_id, name, password, department_id, roll, code FROM users.tblusers;")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        users_data = gumc_cur.fetchall()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

        for row in users_data:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            user_id, name, password_hash_gumc, department_id, role, code = row  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

            # WIMS의 password_hash는 pgcrypto를 통해 해싱된 형태여야 함.  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            # GUMC의 password가 평문이라면, WIMS에서 '비밀번호 재설정'을 안내해야 함.  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            # 여기서는 임시로 GUMC의 password를 그대로 사용하거나,  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            # pgcrypto의 crypt 함수를 사용해 재해싱하는 것을 고려.  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            # 예시: password_hash_wims = f"crypt('{password_hash_gumc}', gen_salt('bf'))"  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            # 실제 운영에서는 안전한 비밀번호 정책을 따를 것을 권장.  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

            wims_cur.execute(
                """
                INSERT INTO usr.users (id, username, password_hash, email, full_name, department_id, role, code, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    password_hash = EXCLUDED.password_hash,
                    email = EXCLUDED.email,
                    full_name = EXCLUDED.full_name,
                    department_id = EXCLUDED.department_id,
                    role = EXCLUDED.role,
                    code = EXCLUDED.code,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at;
                """,
                (user_id, name, password_hash_gumc, None, name, department_id, role, code, True, datetime.now(), datetime.now())
            )
        logging.info(f"usr.users {len(users_data)}개 레코드 이전 완료.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.commit()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    except Exception as e:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.rollback()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        logging.error(f"usr.users 이전 중 오류 발생: {e}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        raise  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    # 3. loc.wastewater_plants (GUMC: lims.tblsite) 이전
    logging.info("loc.wastewater_plants 테이블 이전 시작...")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        gumc_cur.execute("SELECT site_id, site_code, site_name, site_address, site_manager, site_tel, memo, is_stp FROM lims.tblsite;")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        plants_data = gumc_cur.fetchall()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

        for row in plants_data:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            site_id, site_code, site_name, site_address, site_manager, site_tel, memo, is_stp = row  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            wims_cur.execute(
                """
                INSERT INTO loc.wastewater_plants (id, code, name, address, contact_person, contact_phone, latitude, longitude, description, is_stp, sort_order, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    code = EXCLUDED.code,
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    contact_person = EXCLUDED.contact_person,
                    contact_phone = EXCLUDED.contact_phone,
                    description = EXCLUDED.description,
                    is_stp = EXCLUDED.is_stp,
                    updated_at = EXCLUDED.updated_at;
                """,
                (site_id, site_code, site_name, site_address, site_manager, site_tel, None, None, memo, is_stp, None, datetime.now(), datetime.now())
            )
        logging.info(f"loc.wastewater_plants {len(plants_data)}개 레코드 이전 완료.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.commit()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    except Exception as e:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.rollback()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        logging.error(f"loc.wastewater_plants 이전 중 오류 발생: {e}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        raise  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    # 4. lims.sampling_points (GUMC: lims.tblsmp) 이전
    logging.info("lims.sampling_points 테이블 이전 시작...")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        gumc_cur.execute("SELECT smp_id, smp_code, smp_loc_name, site_id, memo FROM lims.tblsmp;")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        sampling_points_data = gumc_cur.fetchall()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

        for row in sampling_points_data:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            smp_id, smp_code, smp_loc_name, site_id, memo = row  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

            # WIMS의 plant_id는 loc.wastewater_plants의 ID를 참조  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            # GUMC의 site_id는 lims.tblsite의 site_id이므로 직접 매핑  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            wims_cur.execute(
                """
                INSERT INTO lims.sampling_points (id, code, name, plant_id, memo, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    code = EXCLUDED.code,
                    name = EXCLUDED.name,
                    plant_id = EXCLUDED.plant_id,
                    memo = EXCLUDED.memo,
                    updated_at = EXCLUDED.updated_at;
                """,
                (smp_id, smp_code, smp_loc_name, site_id, memo, datetime.now(), datetime.now())
            )
        logging.info(f"lims.sampling_points {len(sampling_points_data)}개 레코드 이전 완료.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.commit()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    except Exception as e:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn.rollback()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        logging.error(f"lims.sampling_points 이전 중 오류 발생: {e}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        raise  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    gumc_cur.close()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    wims_cur.close()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.


def verify_data(wims_conn):
    """이전된 데이터의 개수를 검증합니다."""  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    wims_cur = wims_conn.cursor()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    logging.info("\n--- 데이터 검증 시작 ---")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    tables_to_verify = {
        "usr.departments": "SELECT COUNT(*) FROM usr.departments;",  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        "usr.users": "SELECT COUNT(*) FROM usr.users;",  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        "loc.wastewater_plants": "SELECT COUNT(*) FROM loc.wastewater_plants;",  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        "lims.sampling_points": "SELECT COUNT(*) FROM lims.sampling_points;"  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    }

    for table_name, query in tables_to_verify.items():  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            wims_cur.execute(query)  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            count = wims_cur.fetchone()[0]  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            logging.info(f"테이블 {table_name}의 레코드 수: {count}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

            # 추가적인 샘플 데이터 검증 (선택 사항)  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            wims_cur.execute(f"SELECT * FROM {table_name} ORDER BY id LIMIT 5;")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            sample_data = wims_cur.fetchall()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            logging.info(f"테이블 {table_name}의 샘플 데이터 (상위 5개):")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            for s_row in sample_data:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
                logging.info(f"  {s_row}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

        except Exception as e:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            logging.error(f"테이블 {table_name} 검증 중 오류 발생: {e}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    logging.info("--- 데이터 검증 완료 ---")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    wims_cur.close()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.


def main():
    gumc_conn = None  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    wims_conn = None  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    try:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        logging.info("데이터 이전 프로그램 시작...")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        gumc_conn = get_db_connection(GUMC_DB_CONFIG)  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        wims_conn = get_db_connection(WIMS_DB_CONFIG)  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

        if gumc_conn and wims_conn:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            migrate_data(gumc_conn, wims_conn)  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            verify_data(wims_conn)  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            logging.info("1단계 데이터 이전 및 검증 완료.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        else:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            logging.error("데이터베이스 연결 실패로 인해 이전 작업을 시작할 수 없습니다.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.

    except Exception as e:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        logging.critical(f"프로그램 실행 중 치명적인 오류 발생: {e}")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
    finally:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        if gumc_conn:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            gumc_conn.close()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            logging.info("GUMC DB 연결 해제.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
        if wims_conn:  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            wims_conn.close()  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.
            logging.info("WIMS DB 연결 해제.")  # 2025-06-01: 앞으로 파이썬 인라인 코멘트 # 기호전에 스페이스 2개 넣어줘.


if __name__ == "__main__":
    main()
