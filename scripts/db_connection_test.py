import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# .env 파일의 DATABASE_URL과 완전히 동일한 문자열을 사용합니다.
DATABASE_URL = "postgresql+asyncpg://wims:wims1234@localhost:5432/wims_dbv1"

async def test_db_connection():
    print("--- 데이터베이스 연결 테스트를 시작합니다... ---")
    print(f"연결 대상: {DATABASE_URL}")

    engine = create_async_engine(DATABASE_URL, echo=True)
    
    try:
        async with engine.begin() as conn:
            print("\n>>> 데이터베이스에 성공적으로 연결되었습니다.")
            
            # 1. 테스트용 테이블이 있다면 먼저 삭제합니다.
            print("\n>>> 기존 테스트 테이블(my_direct_test) 삭제 시도...")
            await conn.execute(text("DROP TABLE IF EXISTS public.my_direct_test;"))
            print(">>> 삭제 완료 (또는 테이블이 원래 없었음).")

            # 2. 새로운 테스트 테이블을 생성합니다.
            print("\n>>> 새로운 테스트 테이블(my_direct_test) 생성 시도...")
            await conn.execute(
                text("CREATE TABLE public.my_direct_test (id serial primary key, message text);")
            )
            print(">>> 테이블 생성 SQL 실행 완료.")

            # 3. 생성된 테이블에 데이터를 삽입합니다.
            print("\n>>> 데이터 삽입 시도...")
            await conn.execute(
                text("INSERT INTO public.my_direct_test (message) VALUES ('Connection successful!');")
            )
            print(">>> 데이터 삽입 SQL 실행 완료.")
            
            print("\n>>> 모든 작업이 성공적으로 실행되었으며, 최종 커밋을 시도합니다.")

        # async with engine.begin() 블록이 성공적으로 끝나면 자동으로 COMMIT 됩니다.
        
        print("\n--- ✅ 테스트 성공! ---")
        print("이제 DB 클라이언트로 'wims_dbv1' 데이터베이스의 'public' 스키마에")
        print("'my_direct_test' 테이블과 데이터가 생성되었는지 확인해주세요.")

    except Exception as e:
        print("\n--- ❌ 테스트 실패! ---")
        print(f"오류가 발생했습니다: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_db_connection())