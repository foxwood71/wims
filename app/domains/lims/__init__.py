# app/domains/lims/__init__.py

"""
FastAPI 애플리케이션의 'lims' 도메인 패키지입니다.

이 패키지는 PostgreSQL의 'lims' 스키마에 해당하는 데이터 모델과
관련된 비즈니스 로직 및 API 엔드포인트를 포함합니다.

'lims' 도메인은 실험실 정보 관리 시스템(LIMS) 및 품질 보증/품질 관리(QA/QC)를 위한
핵심 데이터를 관리하는 역할을 합니다. 여기에는 분석 항목(Parameter), 프로젝트(Project),
시료 용기(SampleContainer), 시료 유형(SampleType), 채수 지점(SamplingPoint),
날씨 조건(WeatherCondition), 시험 의뢰(TestRequest), 원 시료(Sample),
분할 시료(AliquotSample), 워크시트(Worksheet), 워크시트 항목(WorksheetItem),
워크시트 데이터(WorksheetData), 분석 결과(AnalysisResult), 시험 의뢰 템플릿(TestRequestTemplate),
사용자 정의 보기(PrView)와 같은 데이터가 포함됩니다.
또한, 표준 시료(StandardSample), 교정 기록(CalibrationRecord),
QC 시료 결과(QCSampleResult)와 같은 QA/QC 관련 데이터도 관리합니다.

주요 서브모듈:
- `models.py`: 'lims' 스키마의 테이블에 매핑되는 SQLModel 정의.
- `schemas.py`: 'lims' 스키마 데이터에 대한 Pydantic 모델 (요청 및 응답 유효성 검사).
- `crud.py`: 'lims' 스키마 테이블에 대한 비동기 CRUD (Create, Read, Update, Delete) 로직.
- `routers.py`: 'lims' 스키마 데이터에 접근하기 위한 FastAPI API 엔드포인트 정의.
- (선택 사항) `functions.py`: 데이터베이스 함수(예: 시료 코드 생성)에 대한 파이썬 래퍼.

이 `__init__.py` 파일은 'lims' 패키지를 Python 패키지로 인식하게 하며,
패키지의 목적을 문서화합니다.
"""


# from . import models, schemas, router, crud  # noqa: F401
# 패키지 메타데이터 (선택 사항)
__title__ = "WIMS LIMS & QA/QC Domain"
__description__ = "Manages laboratory information and quality control data."
__version__ = "0.1.0"  # lims 도메인 패키지의 버전
__all__ = []  # 'from app.domains.lims import *' 시 내보낼 이름 목록. 일반적으로 비워둡니다.

# (선택 사항) 이 패키지에서 다른 패키지로 공통 모델이나 스키마를 노출할 수 있습니다.
# 예를 들어, Parameter 모델이 다른 도메인에서 자주 참조된다면 여기서 노출할 수 있습니다.
# from .models import Parameter, Sample, AliquotSample, TestRequest, Project
# from .schemas import SampleResponse, AliquotSampleResponse, TestRequestResponse

# 하지만, 일반적으로 명시적인 임포트 (예: from app.domains.lims.models import Sample)가 권장됩니다.
