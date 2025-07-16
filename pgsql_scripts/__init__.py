# pgsql_scripts/__init__.py
"""
Alembic 데이터베이스 마이그레이션 스크립트 패키지입니다.

이 패키지는 Alembic 툴이 데이터베이스 스키마 변경 사항을 관리하고,
버전 제어를 수행하며, 데이터베이스를 새로운 스키마로 업그레이드하거나
이전 스키마로 다운그레이드하는 데 필요한 마이그레이션 스크립트들을 포함합니다.

주요 하위 디렉토리:
- `sql/`: 실제 script code를 backup

주요 파일:
- `functions.py`: pgsql 함수 정의
- `triggers.py`: pgsql trigger 정의
- `views.py`: pgsql view 정의

이 `__init__.py` 파일은 'pgsql-script' 디렉토리를 Python 패키지로 인식하게 하여,
Alembic이 해당 디렉토리 내의 모듈들을 올바르게 로드할 수 있도록 합니다.
대부분의 경우, 이 파일은 비어 있거나 간단한 문서화만 포함합니다.
"""

# Alembic은 일반적으로 이 __init__.py 파일을 통해 특정 Python 로직을
# 실행하지 않습니다. 주로 패키지 인식 목적으로만 존재합니다.

# 패키지 메타데이터 (선택 사항, Alembic 빌드 시스템에서 직접 사용될 일은 거의 없습니다.)
__title__ = "Alembic Pgsql script"
__description__ = "Database migration function-scripts, trigger-scripts, view-scripts managed by Alembic."
__version__ = "0.1.0"  # 마이그레이션 스크립트 패키지의 내부 버전
__all__ = []  # 이 패키지에서 'from migrations import *' 시 내보낼 이름 목록.

import pkgutil
import importlib
import inspect
# from alembic_utils.pg_function import PGFunction
# from alembic_utils.pg_trigger import PGTrigger
# from alembic_utils.pg_view import PGView

# ⭐️ Alembic-utils의 고급 기능을 임포트합니다
from alembic_utils.replaceable_entity import ReplaceableEntity
# ⭐️ PGView, PGFunction, PGTrigger를 직접 임포트할 필요가 없습니다.
#    ReplaceableEntity라는 부모 클래스로 한 번에 확인합니다.

# Alembic과 Pytest에서 공통으로 사용할 객체 리스트
# ⭐️ 이 리스트는 아래의 자동 탐색 로직에 의해 자동으로 채워집니다.
all_db_objects = []

# --- 자동 탐색 로직 ---
# 설명:
# 'pgsql_scripts' 패키지 안에 있는 모든 파이썬 모듈(functions.py, triggers.py 등)을
# 순회하며, Alembic-utils로 정의된 객체(PGFunction, PGTrigger 등)를
# 자동으로 찾아 'all_db_objects' 리스트에 추가합니다.

# 1. 현재 패키지('pgsql_scripts') 내의 모든 모듈을 찾습니다.
for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    # 2. 찾은 모듈을 동적으로 임포트합니다. (예: from . import functions)
    module = importlib.import_module(f".{module_name}", __package__)

    # 3. 임포트된 모듈 안의 모든 멤버(객체, 변수 등)를 확인합니다.
    for name, obj in inspect.getmembers(module):
        # 4. 해당 멤버가 ReplaceableEntity를 상속받는 객체인지 확인합니다.
        #    (PGFunction, PGTrigger 등이 모두 이 클래스를 상속합니다)
        if isinstance(obj, ReplaceableEntity):
            # 5. 맞다면, 최종 리스트에 추가합니다.
            all_db_objects.append(obj)
