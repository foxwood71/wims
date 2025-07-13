# app/domains/models/__init__.py

"""
이 파일은 모든 도메인의 SQLModel 모델들을 한 곳에서 중앙 관리하여,
다른 모듈에서 쉽게 임포트할 수 있도록 하는 역할을 합니다.
SQLModel.metadata가 모든 테이블을 인식하도록 보장합니다.
"""

# usr (User, Department)
from app.domains.usr.models import User, UserRole, Department

# shared (Version, Resource, ResourceCategory, EntityResource)
from app.domains.shared.models import Version, Resource, ResourceCategory, EntityResource

# loc (facility, Location, LocationType)
from app.domains.loc.models import Facility, Location, LocationType

# ven (Vendor, VendorCategory, VendorContact, VendorVendorCategory)
from app.domains.ven.models import Vendor, VendorCategory, VendorContact, VendorVendorCategory

# fms (Equipment, EquipmentCategory, EquipmentSpecDefinition, EquipmentHistory, EquipmentSpec)
from app.domains.fms.models import Equipment, EquipmentCategory, EquipmentSpecDefinition, EquipmentHistory, EquipmentSpec

# inv (Material, MaterialCategory, MaterialBatch, MaterialTransaction, MaterialSpec, etc.)
from app.domains.inv.models import (
    Material, MaterialCategory, MaterialBatch, MaterialTransaction,
    MaterialSpec, MaterialSpecDefinition, MaterialCategorySpecDefinition
)

# lims (모든 LIMS 관련 모델)
from app.domains.lims.models import (
    Parameter, Project, SampleContainer, SampleType, SamplingPoint,
    WeatherCondition, TestRequest, Sample, AliquotSample, Worksheet,
    WorksheetItem, WorksheetData, AnalysisResult, TestRequestTemplate,
    PrView, StandardSample, CalibrationRecord, QcSampleResult
)

# ops (Line, DailyPlantOperation, DailyLineOperation, OpsView)
from app.domains.ops.models import (
    Line, DailyPlantOperation, DailyLineOperation, OpsView
)

# corp (CompanyInfo)
from app.domains.corp.models import CompanyInfo

# rpt (ReportForm)
from app.domains.rpt.models import ReportForm


#  `from app.domains.models import *` 구문으로 임포트될 모델 목록 정의
__all__ = [
    #  usr
    "User", "UserRole", "Department",
    # shared
    "Version", "Resource", "ResourceCategory", "EntityResource",
    # loc
    "Facility", "Location", "LocationType",
    # ven
    "Vendor", "VendorCategory", "VendorContact", "VendorVendorCategory",
    # fms
    "Equipment", "EquipmentCategory", "EquipmentSpecDefinition", "EquipmentHistory", "EquipmentSpec",
    # inv
    "Material", "MaterialCategory", "MaterialBatch", "MaterialTransaction", "MaterialSpec",
    "MaterialSpecDefinition", "MaterialCategorySpecDefinition",
    # lims
    "Parameter", "Project", "SampleContainer", "SampleType", "SamplingPoint", "WeatherCondition",
    "TestRequest", "Sample", "AliquotSample", "Worksheet", "WorksheetItem", "WorksheetData",
    "AnalysisResult", "TestRequestTemplate", "PrView", "StandardSample", "CalibrationRecord",
    "QcSampleResult",
    # ops
    "Line", "DailyPlantOperation", "DailyLineOperation", "OpsView",
    # corp
    "CompanyInfo",
    # rpt
    "ReportForm",
]

# =============================================================================
# 순환 참조 해결 (Circular Reference Resolution)
# =============================================================================
# 모든 모델 클래스가 메모리에 로드된 후, Pydantic/SQLModel이
# 문자열로 된 타입 힌트(예: "Resource")를 실제 클래스로 변환하도록 강제합니다.
# 이 과정은 양방향 관계(back_populates)로 인한 순환 참조 문제를 해결합니다.

# User.model_rebuild()
# Department.model_rebuild()
# Resource.model_rebuild()
# ResourceCategory.model_rebuild()
# EntityResource.model_rebuild()
# CompanyInfo.model_rebuild()
# ReportForm.model_rebuild()
