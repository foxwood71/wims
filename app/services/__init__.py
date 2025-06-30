# app/services/__init__.py

"""
FastAPI 애플리케이션의 서비스 계층 패키지입니다.

이 패키지는 애플리케이션의 핵심 비즈니스 로직, 특히 여러 도메인(스키마)에 걸쳐
상호 작용하는 복잡한 작업이나 외부 시스템과의 통합을 처리하는 모듈을 포함합니다.

CRUD (Create, Read, Update, Delete) 작업은 각 도메인의 `crud.py` 파일에서
직접 데이터베이스와 상호 작용하는 반면, `services` 계층은 이러한 CRUD 작업을
조합하거나, 추가적인 비즈니스 규칙을 적용하거나, 여러 도메인 데이터를
복합적으로 처리하는 상위 수준의 로직을 담당합니다.

예시 서비스:
- `cross_domain_service.py`: 서로 다른 도메인(예: LIMS와 Inventory) 간의
  복잡한 비즈니스 흐름을 조정하는 서비스.
- `notification_service.py`: 특정 이벤트 발생 시 사용자에게 알림을 보내는 서비스.
- `report_generation_service.py`: 여러 도메인의 데이터를 취합하여 복잡한 보고서를 생성하는 서비스.

이 `__init__.py` 파일은 `services` 패키지를 Python 패키지로 인식하게 하며,
선택적으로 패키지의 주요 서비스들을 직접 임포트하여 노출할 수 있습니다.
"""

# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS Services"
__description__ = "Business logic and cross-domain services for WIMS FastAPI application."
__version__ = "0.1.0" # services 패키지의 버전
__all__ = [] # 'from app.services import *' 시 내보낼 이름 목록. 일반적으로 비워둡니다.

# (선택 사항) 서비스 모듈들을 패키지 레벨에서 직접 노출
# 이렇게 하면 'from app.services import cross_domain_service'와 같이 바로 임포트할 수 있습니다.
# from . import cross_domain_service
# from . import notification_service # 예시
# from . import report_generation_service # 예시

# 또는 특정 서비스 클래스나 함수만 노출할 수도 있습니다.
# from .cross_domain_service import CrossDomainService