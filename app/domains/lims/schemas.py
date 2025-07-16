# app/domains/lims/schemas.py

"""
'lims' 도메인 (실험실 정보 관리 시스템 및 QA/QC)의 Pydantic 스키마를 정의하는 모듈입니다.

이 스키마들은 API 요청(Request) 및 응답(Response) 데이터의 유효성을 검사하고,
데이터를 직렬화(Serialization) 및 역직렬화(Deserialization)하는 데 사용됩니다.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, time, UTC  # UTC 임포트 추가
from pydantic import BaseModel, Field as PydanticField  # Pydantic Field와 SQLModel Field 충돌 방지

# from sqlmodel import SQLModel  # SQLModel 클래스 임포트 (BaseModel 기능 포함)


# =============================================================================
# 1. 분석 항목 (Parameter) 스키마
# =============================================================================
class ParameterBase(BaseModel):
    code: str = PydanticField(max_length=5, description="분석 항목 코드")
    analysis_group: Optional[str] = PydanticField(default=None, max_length=50, description="동일 분석 항목 그룹")
    name: str = PydanticField(max_length=255, description="분석 항목명")
    units: Optional[str] = PydanticField(default=None, max_length=255, description="측정 단위")
    method: Optional[str] = PydanticField(default=None, max_length=255, description="분석 방법")
    detection_limit_low: Optional[float] = PydanticField(default=None, description="하한 검출 한계")
    detection_limit_high: Optional[float] = PydanticField(default=None, description="상한 검출 한계")
    quantification_limit: Optional[float] = PydanticField(default=None, description="정량 한계")
    default_value0: Optional[str] = PydanticField(default=None, max_length=255, description="기본값 0")
    default_value1: Optional[str] = PydanticField(default=None, max_length=255, description="기본값 1")
    default_value2: Optional[str] = PydanticField(default=None, max_length=255, description="기본값 2")
    instrument_id: Optional[int] = PydanticField(default=None, description="관련 장비 ID (FK)")
    price: Optional[float] = PydanticField(default=None, description="분석 비용")
    description: Optional[str] = PydanticField(default=None, description="설명")
    sort_order: int = PydanticField(description="정렬 순서")  # 생성 시 필수
    is_active: bool = PydanticField(default=True, description="활성 여부")


class ParameterCreate(ParameterBase):
    pass  # ParameterBase에서 이미 모든 필수 필드가 정의됨


class ParameterUpdate(BaseModel):  # 업데이트는 모두 Optional
    code: Optional[str] = PydanticField(None, max_length=4, description="분석 항목 코드")
    analysis_group: Optional[str] = PydanticField(None, max_length=50, description="동일 분석 항목 그룹")
    name: Optional[str] = PydanticField(None, max_length=255, description="분석 항목명")
    units: Optional[str] = PydanticField(None, max_length=255, description="측정 단위")
    method: Optional[str] = PydanticField(None, max_length=255, description="분석 방법")
    detection_limit_low: Optional[float] = PydanticField(None, description="하한 검출 한계")
    detection_limit_high: Optional[float] = PydanticField(None, description="상한 검출 한계")
    quantification_limit: Optional[float] = PydanticField(None, description="정량 한계")
    default_value0: Optional[str] = PydanticField(None, max_length=255, description="기본값 0")
    default_value1: Optional[str] = PydanticField(None, max_length=255, description="기본값 1")
    default_value2: Optional[str] = PydanticField(None, max_length=255, description="기본값 2")
    instrument_id: Optional[int] = PydanticField(None, description="관련 장비 ID (FK)")
    price: Optional[float] = PydanticField(None, description="분석 비용")
    description: Optional[str] = PydanticField(None, description="설명")
    sort_order: Optional[int] = PydanticField(None, description="정렬 순서")
    is_active: Optional[bool] = PydanticField(None, description="활성 여부")


class ParameterResponse(ParameterBase):
    id: int = PydanticField(description="분석 항목 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 2. 프로젝트 (Project) 스키마
# =============================================================================
class ProjectBase(BaseModel):
    code: str = PydanticField(max_length=4, description="프로젝트 코드")
    name: str = PydanticField(max_length=255, description="프로젝트명")
    start_date: date = PydanticField(description="프로젝트 시작일")
    end_date: date = PydanticField(description="프로젝트 종료일")
    description: Optional[str] = PydanticField(default=None, description="설명")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):  # 업데이트는 모두 Optional
    code: Optional[str] = PydanticField(None, max_length=4, description="프로젝트 코드")
    name: Optional[str] = PydanticField(None, max_length=255, description="프로젝트명")
    start_date: Optional[date] = PydanticField(None, description="프로젝트 시작일")
    end_date: Optional[date] = PydanticField(None, description="프로젝트 종료일")
    description: Optional[str] = PydanticField(None, description="설명")


class ProjectResponse(ProjectBase):
    id: int = PydanticField(description="프로젝트 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 3. 시료 용기 (SampleContainer) 스키마
# =============================================================================
class SampleContainerBase(BaseModel):
    code: int = PydanticField(description="용기 코드")
    name: str = PydanticField(max_length=255, description="용기 명칭")
    capacity_ml: Optional[float] = PydanticField(default=None, description="용기 용량(mL)")
    memo: Optional[str] = PydanticField(default=None, description="메모")


class SampleContainerCreate(SampleContainerBase):
    pass


class SampleContainerUpdate(BaseModel):  # 업데이트는 모두 Optional
    code: Optional[int] = PydanticField(None, description="용기 코드")
    name: Optional[str] = PydanticField(None, max_length=255, description="용기 명칭")
    memo: Optional[str] = PydanticField(None, description="메모")


class SampleContainerResponse(SampleContainerBase):
    id: int = PydanticField(description="용기 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 4. 시료 유형 (SampleType) 스키마
# =============================================================================
class SampleTypeBase(BaseModel):
    code: int = PydanticField(description="시료 유형 코드")
    name: str = PydanticField(max_length=255, description="시료 유형 명칭")
    memo: Optional[str] = PydanticField(default=None, description="메모")


class SampleTypeCreate(SampleTypeBase):
    pass


class SampleTypeUpdate(BaseModel):  # 업데이트는 모두 Optional
    code: Optional[int] = PydanticField(None, description="시료 유형 코드")
    name: Optional[str] = PydanticField(None, max_length=255, description="시료 유형 명칭")
    memo: Optional[str] = PydanticField(None, description="메모")


class SampleTypeResponse(SampleTypeBase):
    id: int = PydanticField(description="시료 유형 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 5. 채수 지점 (SamplingPoint) 스키마
# =============================================================================
class SamplingPointBase(BaseModel):
    code: str = PydanticField(max_length=10, description="채수 지점 코드")
    name: str = PydanticField(max_length=255, description="채수 지점명")
    facility_id: int = PydanticField(description="소속 처리장 ID (FK)")
    memo: Optional[str] = PydanticField(default=None, description="메모")


class SamplingPointCreate(SamplingPointBase):
    pass


class SamplingPointUpdate(BaseModel):  # 업데이트는 모두 Optional
    code: Optional[str] = PydanticField(None, max_length=10, description="채수 지점 코드")
    name: Optional[str] = PydanticField(None, max_length=255, description="채수 지점명")
    facility_id: Optional[int] = PydanticField(None, description="소속 처리장 ID (FK)")
    memo: Optional[str] = PydanticField(None, description="메모")


class SamplingPointResponse(SamplingPointBase):
    id: int = PydanticField(description="채수 지점 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 6. 날씨 조건 (WeatherCondition) 스키마
# =============================================================================
class WeatherConditionBase(BaseModel):
    code: int = PydanticField(description="날씨 코드")
    status: str = PydanticField(max_length=255, description="날씨 상태 (예: 맑음, 비)")
    memo: Optional[str] = PydanticField(default=None, description="메모")


class WeatherConditionCreate(WeatherConditionBase):
    pass


class WeatherConditionUpdate(BaseModel):  # 업데이트는 모두 Optional
    code: Optional[int] = PydanticField(None, description="날씨 코드")
    status: Optional[str] = PydanticField(None, max_length=255, description="날씨 상태")
    memo: Optional[str] = PydanticField(None, description="메모")


class WeatherConditionResponse(WeatherConditionBase):
    id: int = PydanticField(description="날씨 조건 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 7. 시험 의뢰 (TestRequest) 스키마
# =============================================================================
class TestRequestBase(BaseModel):
    # request_code는 DB에서 자동 생성되므로 Create에서는 Optional, Response에서는 필수
    request_code: Optional[str] = PydanticField(default=None, max_length=20, description="시험 의뢰 코드 (자동 생성)")
    request_date: Optional[date] = PydanticField(default=None, description="의뢰 일자 (미입력 시 오늘 날짜)")
    project_id: int = PydanticField(description="관련 프로젝트 ID (FK)")
    department_id: int = PydanticField(description="의뢰 부서 ID (FK)")
    requester_login_id: int = PydanticField(description="의뢰 사용자 ID (FK)")
    title: str = PydanticField(description="의뢰 제목")
    label_printed: bool = PydanticField(default=False, description="라벨 인쇄 여부")
    memo: Optional[str] = PydanticField(default=None, description="메모")
    # submitted_at은 DB에서 자동 생성되므로 Create에서는 Optional, Response에서는 필수
    submitted_at: Optional[datetime] = PydanticField(default_factory=lambda: datetime.now(UTC), description="제출 일시")
    sampling_date: Optional[date] = PydanticField(default=None, description="채수일자")
    sampling_time_from: Optional[time] = PydanticField(default=None, description="채수시각(시)")
    sampling_time_to: Optional[time] = PydanticField(default=None, description="채수시각(종)")
    sampling_weather_id: Optional[int] = PydanticField(default=None, description="날씨 조건 ID (FK)")
    sampler: Optional[str] = PydanticField(default=None, max_length=32, description="채수자")
    water_temp: Optional[float] = PydanticField(default=None, description="수온")
    air_temp: Optional[float] = PydanticField(default=None, description="기온")
    # requested_parameters: Dict[str, Any] = PydanticField(description="요청된 분석 항목 (JSONB)")  [삭제] smaple과 중복


class TestRequestCreate(TestRequestBase):
    # <<< 수정된 부분 시작 >>>
    # API 요청 시에는 requester_login_id가 없어도 되도록 Optional로 재정의합니다.
    # 라우터에서 현재 로그인한 사용자로 자동 할당합니다.
    requester_login_id: Optional[int] = PydanticField(default=None, description="의뢰 사용자 ID (FK)")
    # <<< 수정된 부분 끝 >>>
    # request_code: Optional[str] = None  # 생성 시에는 클라이언트에서 제공하지 않음 [제거] 각각의 sample에서 분석항목 기록


class TestRequestUpdate(BaseModel):  # 업데이트는 모두 Optional
    request_code: Optional[str] = PydanticField(None, max_length=20, description="시험 의뢰 코드")
    request_date: Optional[date] = PydanticField(None, description="의뢰 일자")
    project_id: Optional[int] = PydanticField(None, description="관련 프로젝트 ID (FK)")
    department_id: Optional[int] = PydanticField(None, description="의뢰 부서 ID (FK)")
    requester_login_id: Optional[int] = PydanticField(None, description="의뢰 사용자 ID (FK)")
    title: Optional[str] = PydanticField(None, description="의뢰 제목")
    label_printed: Optional[bool] = PydanticField(None, description="라벨 인쇄 여부")
    memo: Optional[str] = PydanticField(None, description="메모")
    sampling_date: Optional[date] = PydanticField(None, description="채수일자")
    sampling_time_from: Optional[time] = PydanticField(None, description="채수시각(시)")
    sampling_time_to: Optional[time] = PydanticField(None, description="채수시각(종)")
    sampling_weather_id: Optional[int] = PydanticField(None, description="날씨 조건 ID (FK)")
    sampler: Optional[str] = PydanticField(None, max_length=32, description="채수자")
    water_temp: Optional[float] = PydanticField(None, description="수온")
    air_temp: Optional[float] = PydanticField(None, description="기온")
    # requested_parameters: Optional[Dict[str, Any]] = PydanticField(None, description="요청된 분석 항목 (JSONB)")  [삭제] smaple과 중복


class TestRequestResponse(TestRequestBase):
    id: int = PydanticField(description="시험 의뢰 고유 ID")
    # request_code는 DB에서 생성되어 응답에서는 필수 필드임.
    request_code: str = PydanticField(max_length=20, description="시험 의뢰 코드")
    submitted_at: datetime = PydanticField(description="제출 일시")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 8. 원 시료 (Sample) 스키마
# =============================================================================
class SampleBase(BaseModel):
    sample_code: Optional[str] = PydanticField(default=None, max_length=24, description="시료 코드 (자동 생성)")
    request_id: int = PydanticField(description="관련 시험 의뢰 ID (FK)")
    request_sheet_index: Optional[int] = PydanticField(default=None, description="시험 의뢰서 내 시료 순번")
    sampling_point_id: int = PydanticField(description="채수 지점 ID (FK)")
    sampling_date: date = PydanticField(description="채수일자")
    sampling_time: Optional[time] = PydanticField(default=None, description="채수시각")
    # sampling_weather_id: Optional[int] = PydanticField(default=None, description="채수 시 날씨 조건 ID (FK)")  [삭제] test_request와 중복
    sampler: Optional[str] = PydanticField(default=None, max_length=32, description="채수자")
    sample_temp: Optional[float] = PydanticField(default=None, description="시료 온도")
    sample_type_id: int = PydanticField(description="시료 유형 ID (FK)")
    container_id: int = PydanticField(description="시료 용기 ID (FK)")
    parameters_for_analysis: Dict[str, Any] = PydanticField(description="분석할 항목 (JSONB)")
    amount: int = PydanticField(default=1, description="시료 수량 (최소 1)")
    storage_location_id: Optional[int] = PydanticField(default=None, description="보관 위치 ID (FK)")
    analysis_status: str = PydanticField(default='Pending', max_length=20, description="분석 상태")
    request_date: Optional[date] = PydanticField(default=None, description="의뢰 일자")
    collected_date: Optional[date] = PydanticField(default=None, description="수집 일자")  # CRUD에서 default 설정
    analyze_date: Optional[date] = PydanticField(default=None, description="분석 시작 일자")
    complete_date: Optional[date] = PydanticField(default=None, description="분석 완료 일자")
    disposal_date: Optional[date] = PydanticField(default=None, description="폐기 일자")
    storage_period: Optional[int] = PydanticField(default=None, description="보관 기간 (일)")
    collector: Optional[str] = PydanticField(default=None, max_length=255, description="수집자")
    manager: Optional[str] = PydanticField(default=None, max_length=255, description="담당자")
    memo: Optional[str] = PydanticField(default=None, description="메모")
    collector_login_id: Optional[int] = PydanticField(default=None, description="수집자 사용자 ID (FK)")


class SampleCreate(SampleBase):
    sample_code: Optional[str] = None  # 생성 시 자동 생성
    collected_date: Optional[date] = None  # CRUD에서 default 설정
    request_date: Optional[date] = None  # CRUD에서 TestRequest로부터 가져옴


class SampleUpdate(BaseModel):  # 업데이트는 모두 Optional
    sample_code: Optional[str] = PydanticField(None, max_length=24, description="시료 코드")
    request_id: Optional[int] = PydanticField(None, description="관련 시험 의뢰 ID (FK)")
    request_sheet_index: Optional[int] = PydanticField(None, description="시험 의뢰서 내 시료 순번")
    sampling_point_id: Optional[int] = PydanticField(None, description="채수 지점 ID (FK)")
    sampling_date: Optional[date] = PydanticField(None, description="채수일자")
    sampling_time: Optional[time] = PydanticField(None, description="채수시각")
    # sampling_weather_id: Optional[int] = PydanticField(default=None, description="채수 시 날씨 조건 ID (FK)")  [삭제] test_request와 중복
    sampler: Optional[str] = PydanticField(None, max_length=32, description="채수자")
    sample_temp: Optional[float] = PydanticField(None, description="시료 온도")
    sample_type_id: Optional[int] = PydanticField(None, description="시료 유형 ID (FK)")
    container_id: Optional[int] = PydanticField(None, description="시료 용기 ID (FK)")
    parameters_for_analysis: Optional[Dict[str, Any]] = PydanticField(None, description="분석할 항목 (JSONB)")
    amount: Optional[int] = PydanticField(None, description="시료 수량")
    storage_location_id: Optional[int] = PydanticField(None, description="보관 위치 ID (FK)")
    analysis_status: Optional[str] = PydanticField(None, max_length=20, description="분석 상태")
    request_date: Optional[date] = PydanticField(None, description="의뢰 일자")
    collected_date: Optional[date] = PydanticField(None, description="수집 일자")
    analyze_date: Optional[date] = PydanticField(None, description="분석 시작 일자")
    complete_date: Optional[date] = PydanticField(None, description="분석 완료 일자")
    disposal_date: Optional[date] = PydanticField(None, description="폐기 일자")
    storage_period: Optional[int] = PydanticField(None, description="보관 기간 (일)")
    collector: Optional[str] = PydanticField(None, max_length=255, description="수집자")
    manager: Optional[str] = PydanticField(None, max_length=255, description="담당자")
    memo: Optional[str] = PydanticField(None, description="메모")
    collector_login_id: Optional[int] = PydanticField(None, description="수집자 사용자 ID (FK)")


class SampleResponse(SampleBase):
    id: int = PydanticField(description="시료 고유 ID")
    # sample_code는 DB에서 생성되어 필수
    sample_code: str = PydanticField(max_length=24, description="시료 코드")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 9. 분할 시료 (AliquotSample) 스키마
# =============================================================================
class AliquotSampleBase(BaseModel):
    parent_sample_id: int = PydanticField(description="원 시료 ID (FK)")
    aliquot_code: Optional[str] = PydanticField(default=None, max_length=50, description="분할 시료 코드 (자동 생성)")
    parameter_id: int = PydanticField(description="분석 항목 ID (FK)")
    used_volume: Optional[float] = PydanticField(default=None, description="분석에 사용된 시료 용량(mL)")
    analysis_status: str = PydanticField(default='Pending', max_length=20, description="분석 상태")
    analysis_date: Optional[date] = PydanticField(default=None, description="분석일")
    analyst_login_id: Optional[int] = PydanticField(default=None, description="분석자 사용자 ID (FK)")
    result: Optional[float] = PydanticField(default=None, description="분할 시료의 최종 분석 결과")
    unit: Optional[str] = PydanticField(default=None, max_length=50, description="결과 단위")
    qc_data: Optional[Dict[str, Any]] = PydanticField(default=None, description="품질 관리 (QC) 데이터")
    memo: Optional[str] = PydanticField(default=None, description="메모")
    disposal_date: Optional[date] = PydanticField(default=None, description="폐기일 (트리거로 자동 설정)")
    status: str = PydanticField(default='Active', max_length=20, description="분할 시료 상태")


class AliquotSampleCreate(AliquotSampleBase):
    aliquot_code: Optional[str] = None  # 생성 시 자동 생성
    disposal_date: Optional[date] = None  # DB 트리거로 자동 설정


class AliquotSampleUpdate(BaseModel):  # 업데이트는 모두 Optional
    aliquot_code: Optional[str] = PydanticField(None, max_length=50, description="분할 시료 코드")
    parent_sample_id: Optional[int] = PydanticField(None, description="원 시료 ID (FK)")
    parameter_id: Optional[int] = PydanticField(None, description="분석 항목 ID (FK)")
    analysis_status: Optional[str] = PydanticField(None, max_length=20, description="분석 상태")
    analysis_date: Optional[date] = PydanticField(None, description="분석일")
    analyst_login_id: Optional[int] = PydanticField(None, description="분석자 사용자 ID (FK)")
    result: Optional[float] = PydanticField(None, description="분할 시료의 최종 분석 결과")
    unit: Optional[str] = PydanticField(None, max_length=50, description="결과 단위")
    qc_data: Optional[Dict[str, Any]] = PydanticField(None, description="품질 관리 (QC) 데이터")
    memo: Optional[str] = PydanticField(None, description="메모")
    disposal_date: Optional[date] = PydanticField(None, description="폐기일")
    status: Optional[str] = PydanticField(None, max_length=20, description="분할 시료 상태")


class AliquotSampleResponse(AliquotSampleBase):
    id: int = PydanticField(description="분할 시료 고유 ID")
    aliquot_code: str = PydanticField(max_length=50, description="분할 시료 코드")  # Response에서는 필수로
    disposal_date: Optional[date] = PydanticField(default=None, description="폐기일")  # Response에서는 Optional로
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 10. 워크시트 (Worksheet) 스키마
# =============================================================================
class WorksheetBase(BaseModel):
    code: str = PydanticField(max_length=255, description="워크시트 코드")
    name: str = PydanticField(max_length=255, description="워크시트명")
    memo: Optional[str] = PydanticField(default=None, description="메모")
    sort_order: Optional[int] = PydanticField(default=None, description="정렬 순서")
    data_start_row: Optional[int] = PydanticField(default=None, description="개별 데이터 시작 행 번호")
    header_layout: Optional[Dict[str, Any]] = PydanticField(default=None, description="표제부 레이아웃 (JSON)")


class WorksheetCreate(WorksheetBase):
    pass


class WorksheetUpdate(BaseModel):
    code: Optional[str] = PydanticField(None, max_length=255, description="워크시트 코드")
    name: Optional[str] = PydanticField(None, max_length=255, description="워크시트명")
    memo: Optional[str] = PydanticField(None, description="메모")
    sort_order: Optional[int] = PydanticField(None, description="정렬 순서")
    data_start_row: Optional[int] = PydanticField(None, description="개별 데이터 시작 행 번호")
    header_layout: Optional[Dict[str, Any]] = PydanticField(None, description="표제부 레이아웃 (JSON)")


class WorksheetResponse(WorksheetBase):
    id: int = PydanticField(description="워크시트 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 11. 워크시트 항목 (WorksheetItem) 스키마
# =============================================================================
class WorksheetItemBase(BaseModel):
    worksheet_id: int = PydanticField(description="관련 워크시트 ID (FK)")
    item_type: str = PydanticField(default='ROW', max_length=20, description="항목 유형 (HEADER 또는 ROW)")
    code: str = PydanticField(max_length=255, description="항목 코드")
    priority_order: int = PydanticField(description="우선 순서/정렬 순서")
    xls_cell_address: Optional[str] = PydanticField(default=None, max_length=24, description="엑셀 셀 주소")
    name: str = PydanticField(max_length=255, description="항목명")
    label: str = PydanticField(max_length=255, description="항목 라벨")
    type: int = PydanticField(description="데이터 타입 (숫자, 문자열 등)")

    # <<< [수정] 항목의 활성 상태를 관리하는 필드 추가 >>>
    is_active: bool = PydanticField(default=True, description="항목 활성 여부")

    format: Optional[str] = PydanticField(default=None, max_length=255, description="데이터 형식")
    unit: Optional[str] = PydanticField(default=None, max_length=8, description="단위")
    memo: Optional[str] = PydanticField(default=None, description="메모")


class WorksheetItemCreate(WorksheetItemBase):
    pass


class WorksheetItemUpdate(BaseModel):
    worksheet_id: Optional[int] = PydanticField(None, description="관련 워크시트 ID (FK)")
    item_type: Optional[str] = PydanticField(None, max_length=20, description="항목 유형 (HEADER 또는 ROW)")
    code: Optional[str] = PydanticField(None, max_length=255, description="항목 코드")
    priority_order: Optional[int] = PydanticField(None, description="우선 순서/정렬 순서")
    xls_cell_address: Optional[str] = PydanticField(None, max_length=24, description="엑셀 셀 주소")
    name: Optional[str] = PydanticField(None, max_length=255, description="항목명")
    label: Optional[str] = PydanticField(None, max_length=255, description="항목 라벨")
    type: Optional[int] = PydanticField(None, description="데이터 타입")

    # <<< [수정] 항목의 활성 상태를 관리하는 필드 추가 >>>
    is_active: Optional[bool] = PydanticField(None, description="항목 활성 여부")

    format: Optional[str] = PydanticField(None, max_length=255, description="데이터 형식")
    unit: Optional[str] = PydanticField(None, max_length=8, description="단위")
    memo: Optional[str] = PydanticField(None, description="메모")


class WorksheetItemResponse(WorksheetItemBase):
    id: int = PydanticField(description="워크시트 항목 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 12. 워크시트 데이터 (WorksheetData) 스키마
# =============================================================================
class WorksheetDataBase(BaseModel):
    worksheet_id: int = PydanticField(description="관련 워크시트 ID (FK)")
    data_date: date = PydanticField(description="데이터 입력/분석 일자")
    analyst_login_id: Optional[int] = PydanticField(default=None, description="분석자 사용자 ID (FK)")
    verified_by_login_id: Optional[int] = PydanticField(default=None, description="검증자 사용자 ID (FK)")
    verified_at: Optional[datetime] = PydanticField(default=None, description="검증 일시")
    is_verified: bool = PydanticField(default=False, description="검증 완료 여부")
    notes: Optional[str] = PydanticField(default=None, description="비고")
    raw_data: Dict[str, Any] = PydanticField(description="원시 데이터 (JSONB)")


class WorksheetDataCreate(WorksheetDataBase):
    pass


class WorksheetDataUpdate(BaseModel):  # 업데이트는 모두 Optional
    worksheet_id: Optional[int] = PydanticField(None, description="관련 워크시트 ID (FK)")
    data_date: Optional[date] = PydanticField(None, description="데이터 입력/분석 일자")
    analyst_login_id: Optional[int] = PydanticField(None, description="분석자 사용자 ID (FK)")
    verified_by_login_id: Optional[int] = PydanticField(None, description="검증자 사용자 ID (FK)")
    verified_at: Optional[datetime] = PydanticField(None, description="검증 일시")
    is_verified: Optional[bool] = PydanticField(None, description="검증 완료 여부")
    notes: Optional[str] = PydanticField(None, description="비고")
    raw_data: Optional[Dict[str, Any]] = PydanticField(None, description="원시 데이터 (JSONB)")


class WorksheetDataResponse(WorksheetDataBase):
    id: int = PydanticField(description="워크시트 데이터 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 13. 분석 결과 (AnalysisResult) 스키마
# =============================================================================
class AnalysisResultBase(BaseModel):
    aliquot_sample_id: int = PydanticField(description="관련 분할 시료 ID (FK)")
    parameter_id: int = PydanticField(description="관련 분석 항목 ID (FK)")
    worksheet_id: int = PydanticField(description="관련 워크시트 ID (FK)")
    worksheet_data_id: int = PydanticField(description="관련 워크시트 데이터 ID (FK)")
    result_value: Optional[float] = PydanticField(default=None, description="분석 결과 값")
    unit: Optional[str] = PydanticField(default=None, max_length=50, description="결과 단위")
    analysis_date: Optional[date] = PydanticField(default=None, description="분석일")
    analyst_login_id: Optional[int] = PydanticField(default=None, description="분석자 사용자 ID (FK)")
    approved_by_login_id: Optional[int] = PydanticField(default=None, description="승인자 사용자 ID (FK)")
    approved_at: Optional[datetime] = PydanticField(default=None, description="승인 일시")
    is_approved: bool = PydanticField(default=False, description="승인 여부")
    notes: Optional[str] = PydanticField(default=None, description="비고")


class AnalysisResultCreate(AnalysisResultBase):
    pass


class AnalysisResultUpdate(BaseModel):  # 업데이트는 모두 Optional
    aliquot_sample_id: Optional[int] = PydanticField(None, description="관련 분할 시료 ID (FK)")
    parameter_id: Optional[int] = PydanticField(None, description="관련 분석 항목 ID (FK)")
    worksheet_id: Optional[int] = PydanticField(None, description="관련 워크시트 ID (FK)")
    worksheet_data_id: Optional[int] = PydanticField(None, description="관련 워크시트 데이터 ID (FK)")
    result_value: Optional[float] = PydanticField(None, description="분석 결과 값")
    unit: Optional[str] = PydanticField(None, max_length=50, description="결과 단위")
    analysis_date: Optional[date] = PydanticField(None, description="분석일")
    analyst_login_id: Optional[int] = PydanticField(None, description="분석자 사용자 ID (FK)")
    approved_by_login_id: Optional[int] = PydanticField(None, description="승인자 사용자 ID (FK)")
    approved_at: Optional[datetime] = PydanticField(None, description="승인 일시")
    is_approved: Optional[bool] = PydanticField(None, description="승인 여부")
    notes: Optional[str] = PydanticField(None, description="비고")


class AnalysisResultResponse(AnalysisResultBase):
    id: int = PydanticField(description="분석 결과 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 14. 시험 의뢰 템플릿 (TestRequestTemplate) 스키마
# =============================================================================
class TestRequestTemplateBase(BaseModel):
    name: str = PydanticField(max_length=255, description="템플릿명")
    login_id: int = PydanticField(description="생성 사용자 ID (FK)")  # routers에서 current_login_id로 기본값 설정 가능
    serialized_text: Dict[str, Any] = PydanticField(description="템플릿 내용 (JSONB)")


class TestRequestTemplateCreate(TestRequestTemplateBase):
    login_id: Optional[int] = PydanticField(default=None, description="생성 사용자 ID (FK)")  # 라우터에서 current_user.id로 설정될 수 있도록 Optional로 변경


class TestRequestTemplateUpdate(BaseModel):  # 업데이트는 모두 Optional
    name: Optional[str] = PydanticField(None, max_length=255, description="템플릿명")
    login_id: Optional[int] = PydanticField(None, description="생성 사용자 ID (FK)")
    serialized_text: Optional[Dict[str, Any]] = PydanticField(None, description="템플릿 내용 (JSONB)")


class TestRequestTemplateResponse(TestRequestTemplateBase):
    id: int = PydanticField(description="템플릿 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 15. 표준 시료 (StandardSample) 스키마
# =============================================================================
class StandardSampleBase(BaseModel):
    code: str = PydanticField(max_length=50, description="표준 시료 코드")
    name: str = PydanticField(max_length=255, description="표준 시료명")
    parameter_id: int = PydanticField(description="관련 분석 항목 ID (FK)")
    concentration: Optional[float] = PydanticField(default=None, description="농도")
    preparation_date: Optional[date] = PydanticField(default=None, description="제조일")
    expiration_date: Optional[date] = PydanticField(default=None, description="유효 기간")
    lot_number: Optional[str] = PydanticField(default=None, max_length=100, description="로트 번호")
    notes: Optional[str] = PydanticField(default=None, description="비고")


class StandardSampleCreate(StandardSampleBase):
    pass


class StandardSampleUpdate(BaseModel):  # 업데이트는 모두 Optional
    code: Optional[str] = PydanticField(None, max_length=50, description="표준 시료 코드")
    name: Optional[str] = PydanticField(None, max_length=255, description="표준 시료명")
    parameter_id: Optional[int] = PydanticField(None, description="관련 분석 항목 ID (FK)")
    concentration: Optional[float] = PydanticField(None, description="농도")
    preparation_date: Optional[date] = PydanticField(None, description="제조일")
    expiration_date: Optional[date] = PydanticField(None, description="유효 기간")
    lot_number: Optional[str] = PydanticField(None, max_length=100, description="로트 번호")
    notes: Optional[str] = PydanticField(None, description="비고")


class StandardSampleResponse(StandardSampleBase):
    id: int = PydanticField(description="표준 시료 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 16. 교정 기록 (CalibrationRecord) 스키마
# =============================================================================
class CalibrationRecordBase(BaseModel):
    equipment_id: int = PydanticField(description="교정된 장비 ID (FK)")
    parameter_id: int = PydanticField(description="교정된 분석 항목 ID (FK)")
    calibration_date: datetime = PydanticField(description="교정 일시")
    next_calibration_date: Optional[datetime] = PydanticField(default=None, description="다음 교정 예정일")
    calibrated_by_login_id: Optional[int] = PydanticField(default=None, description="교정 수행자 사용자 ID (FK)")
    standard_sample_id: Optional[int] = PydanticField(default=None, description="사용된 표준 시료 ID (FK)")
    calibration_curve_data: Optional[Dict[str, Any]] = PydanticField(default=None, description="교정 곡선 데이터")
    acceptance_criteria_met: Optional[bool] = PydanticField(default=None, description="허용 기준 충족 여부")
    notes: Optional[str] = PydanticField(default=None, description="비고")


class CalibrationRecordCreate(CalibrationRecordBase):
    pass


class CalibrationRecordUpdate(BaseModel):  # 업데이트는 모두 Optional
    equipment_id: Optional[int] = PydanticField(None, description="교정된 장비 ID (FK)")
    parameter_id: Optional[int] = PydanticField(None, description="교정된 분석 항목 ID (FK)")
    calibration_date: Optional[datetime] = PydanticField(None, description="교정 일시")
    next_calibration_date: Optional[datetime] = PydanticField(None, description="다음 교정 예정일")
    calibrated_by_login_id: Optional[int] = PydanticField(None, description="교정 수행자 사용자 ID (FK)")
    standard_sample_id: Optional[int] = PydanticField(None, description="사용된 표준 시료 ID (FK)")
    calibration_curve_data: Optional[Dict[str, Any]] = PydanticField(None, description="교정 곡선 데이터")
    acceptance_criteria_met: Optional[bool] = PydanticField(None, description="허용 기준 충족 여부")
    notes: Optional[str] = PydanticField(None, description="비고")


class CalibrationRecordResponse(CalibrationRecordBase):
    id: int = PydanticField(description="교정 기록 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 17. QC 시료 결과 (QcSampleResult) 스키마
# =============================================================================
class QcSampleResultBase(BaseModel):
    aliquot_sample_id: Optional[int] = PydanticField(default=None, description="관련 분할 시료 ID (FK, NULL 허용)")
    parameter_id: int = PydanticField(description="관련 분석 항목 ID (FK)")
    qc_type: str = PydanticField(max_length=50, description="QC 유형")
    expected_value: Optional[float] = PydanticField(default=None, description="예상 값")
    measured_value: Optional[float] = PydanticField(default=None, description="측정 값")
    recovery: Optional[float] = PydanticField(default=None, description="회수율")
    rpd: Optional[float] = PydanticField(default=None, description="상대 백분율 차이")
    acceptance_criteria: Optional[Dict[str, Any]] = PydanticField(default=None, description="허용 기준")
    passed_qc: Optional[bool] = PydanticField(default=None, description="QC 통과 여부")
    analysis_date: date = PydanticField(description="분석일")
    analyst_login_id: int = PydanticField(description="분석자 사용자 ID (FK)")  # routers에서 current_login_id로 기본값 설정 가능
    notes: Optional[str] = PydanticField(default=None, description="비고")


class QcSampleResultCreate(QcSampleResultBase):
    analyst_login_id: Optional[int] = PydanticField(default=None, description="분석자 사용자 ID (FK)")  # 라우터에서 current_user.id로 설정될 수 있도록 Optional로 변경


class QcSampleResultUpdate(BaseModel):  # 업데이트는 모두 Optional
    aliquot_sample_id: Optional[int] = PydanticField(None, description="관련 분할 시료 ID (FK)")
    parameter_id: Optional[int] = PydanticField(None, description="관련 분석 항목 ID (FK)")
    qc_type: Optional[str] = PydanticField(None, max_length=50, description="QC 유형")
    expected_value: Optional[float] = PydanticField(None, description="예상 값")
    measured_value: Optional[float] = PydanticField(None, description="측정 값")
    recovery: Optional[float] = PydanticField(None, description="회수율")
    rpd: Optional[float] = PydanticField(None, description="상대 백분율 차이")
    acceptance_criteria: Optional[Dict[str, Any]] = PydanticField(None, description="허용 기준")
    passed_qc: Optional[bool] = PydanticField(None, description="QC 통과 여부")
    analysis_date: Optional[date] = PydanticField(None, description="분석일")
    analyst_login_id: Optional[int] = PydanticField(None, description="분석자 사용자 ID (FK)")
    notes: Optional[str] = PydanticField(None, description="비고")


class QcSampleResultResponse(QcSampleResultBase):
    id: int = PydanticField(description="QC 시료 결과 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 18. 사용자 정의 프로젝트/결과 보기 (PrView) 스키마
# =============================================================================
class PrViewBase(BaseModel):
    name: str = PydanticField(max_length=255, description="보기 설정명")
    login_id: int = PydanticField(description="생성 사용자 ID (FK)")  # routers에서 current_login_id로 기본값 설정 가능
    facility_id: int = PydanticField(description="단일 필터용 처리시설 ID (FK)")  # plant_id는 생성 시 필수
    facility_ids: Optional[List[int]] = PydanticField(default=None, description="선택된 처리시설 ID 목록 (JSONB 배열)")  # plant_ids는 Optional
    sampling_point_ids: Optional[List[int]] = PydanticField(default=None, description="선택된 채수 지점 ID 목록 (JSONB 배열)")
    parameter_ids: Optional[List[int]] = PydanticField(default=None, description="선택된 분석 항목 ID 목록 (JSONB 배열)")
    memo: Optional[str] = PydanticField(default=None, description="메모")


class PrViewCreate(PrViewBase):
    login_id: Optional[int] = PydanticField(default=None, description="생성 사용자 ID (FK)")  # 라우터에서 current_user.id로 설정될 수 있도록 Optional로 변경


class PrViewUpdate(BaseModel):  # 업데이트는 모두 Optional
    name: Optional[str] = PydanticField(None, max_length=255, description="보기 설정명")
    login_id: Optional[int] = PydanticField(None, description="생성 사용자 ID (FK)")
    facility_id: Optional[int] = PydanticField(None, description="단일 필터용 처리시설 ID (FK)")
    facility_ids: Optional[List[int]] = PydanticField(None, description="선택된 처리시설 ID 목록")
    sampling_point_ids: Optional[List[int]] = PydanticField(None, description="선택된 채수 지점 ID 목록")
    parameter_ids: Optional[List[int]] = PydanticField(None, description="선택된 분석 항목 ID 목록")
    memo: Optional[str] = PydanticField(None, description="메모")


class PrViewResponse(PrViewBase):
    id: int = PydanticField(description="보기 설정 고유 ID")
    created_at: datetime = PydanticField(description="레코드 생성 일시")
    updated_at: datetime = PydanticField(description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True
