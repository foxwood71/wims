# app/domains/shared/schemas.py

"""
'shared' 도메인 (PostgreSQL 'app' 스키마)의 Pydantic 스키마를 정의하는 모듈입니다.

이 모듈은 API 요청(생성, 업데이트) 및 응답(조회)에 사용되는 데이터 유효성 검사 및
직렬화를 위한 Pydantic 모델을 포함합니다.
SQLModel의 기능을 활용하여 데이터베이스 ORM 모델과 Pydantic 모델 간의 일관성을 유지합니다.
"""
from typing import Optional  # , List
from datetime import datetime, date
from pydantic import BaseModel, Field, computed_field  # noqa:F401 BaseModel도 명시적으로 임포트
from sqlmodel import SQLModel  # SQLModel 클래스 임포트

from .models import ResourceType
from app.domains.usr.schemas import UserRead


# =============================================================================
# 1. shared.versions 테이블 스키마
# =============================================================================
class VersionBase(SQLModel):
    """
    애플리케이션 버전의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    생성 및 업데이트 스키마의 기반이 됩니다.
    """
    version: Optional[str] = Field(None, max_length=50, description="애플리케이션 버전 번호")
    publish_date: Optional[date] = Field(None, description="버전 배포일")
    notes: Optional[str] = Field(None, description="버전에 대한 설명 또는 변경 사항")


class VersionCreate(VersionBase):
    """
    새로운 애플리케이션 버전을 생성하기 위한 Pydantic 모델입니다.
    모든 필드를 Optional로 두어 유연성을 높이거나, 필수 필드를 지정할 수 있습니다.
    """
    # 생성 시 필드를 필수로 만들 경우 Optional 제거
    version: str = Field(..., max_length=50, description="애플리케이션 버전 번호 (필수)")
    publish_date: date = Field(..., description="버전 배포일 (필수)")


class VersionUpdate(VersionBase):
    """
    기존 애플리케이션 버전을 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    pass  # VersionBase의 모든 필드가 Optional이므로 추가 정의 필요 없음


class VersionRead(VersionBase):
    """
    애플리케이션 버전 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    데이터베이스에서 자동으로 생성되는 ID 및 타임스탬프 필드를 포함합니다.
    """
    id: int = Field(..., description="버전 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        # ORM 모드 설정: ORM 모델에서 Pydantic 모델로 변환할 때
        # 속성 이름(예: `db_obj.id`)으로 접근할 수 있도록 허용합니다.
        from_attributes = True


# =============================================================================
# 2. shared.ResourceCategory 테이블 스키마
# =============================================================================
class ResourceCategoryBase(SQLModel):
    """
    리소스 유형의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    """
    name: str = Field(..., max_length=100, description="리소스 유형 명칭 (예: 설비 사진, 도면)")
    description: Optional[str] = Field(None, description="리소스 유형에 대한 설명")


class ResourceCategoryCreate(ResourceCategoryBase):
    """
    새로운 리소스 유형을 생성하기 위한 Pydantic 모델입니다.
    """
    pass


class ResourceCategoryUpdate(ResourceCategoryBase):
    """
    기존 리소스 유형을 업데이트하기 위한 Pydantic 모델입니다.
    """
    name: Optional[str] = Field(None, max_length=100, description="리소스 유형 명칭")


class ResourceCategoryRead(ResourceCategoryBase):
    """
    리소스 유형 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="리소스 유형 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 3. shared.Resource 테이블 스키마
# =============================================================================
class ResourceBase(SQLModel):
    """
    업로드된 리소스의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    """
    type: ResourceType = Field(..., description="리소스 유형 (IMAGE, FILE 등)")
    category_id: int = Field(..., description="리소스 유형 ID (FK)")
    name: Optional[str] = Field(None, max_length=255, description="리소스 명칭")
    size_kb: Optional[int] = Field(None, description="리소스 크기 (KB)")
    content_type: Optional[str] = Field(None, max_length=255, description="리소스 MIME 타입")
    path: Optional[str] = Field(None, max_length=255, description="서버 상대 경로 (고유 리소스명)")
    description: Optional[str] = Field(None, description="리소스 설명")
    uploader_id: Optional[int] = Field(None, description="리소스를 업로드한 사용자 ID (FK)")
    uploaded_at: Optional[datetime] = Field(None, description="리소스 업로드 일시")
    department_id: Optional[int] = Field(None, description="리소스 소유 부서")


class ResourceCreate(ResourceBase):
    """
    새로운 리소스를 업로드하고 데이터베이스에 기록하기 위한 Pydantic 모델입니다.
    클라이언트가 직접 파일 이름을 지정하지 않으므로 Optional로 두거나,
    라우터에서 동적으로 생성합니다.
    """
    type: ResourceType
    category_id: int
    name: str
    path: str
    size_kb: int
    content_type: str
    uploader_id: int
    department_id: int
    uploaded_at: datetime
    pass


# [수정] ResourceBase 상속을 제거하고, 독립적인 SQLModel로 변경합니다.
class ResourceUpdate(SQLModel):
    """
    기존 리소스 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항이어야 합니다 (부분 업데이트).
    """
    category_id: Optional[int] = None
    description: Optional[str] = None
    department_id: Optional[int] = None


class ResourceRead(ResourceBase):
    """
    업로드된 리소스 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="리소스 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    @computed_field
    @property
    def url(self) -> str:
        """파일 ID를 이용해 다운로드 URL을 동적으로 생성합니다."""
        return f"/api/v1/shared/resources/{self.id}"

    class Config:
        from_attributes = True

    # 관계된 객체의 상세 정보도 함께 보여주기 위해 추가
    category: Optional[ResourceCategoryRead] = None
    uploader: Optional[UserRead] = None  # UserRead 스키마 필요


# =============================================================================
# 4. shared.entity_resource 테이블 스키마
# =============================================================================
class EntityResourceBase(SQLModel):
    """
    엔티티와 리소스 간의 연결 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    """
    resource_id: int = Field(..., description="연결할 리소스 ID (필수)")
    entity_type: str = Field(..., max_length=50, description="연결된 엔티티 유형 (예: EQUIPMENT, MATERIAL, LOCATION)")
    entity_id: int = Field(..., description="연결된 엔티티의 ID")
    is_main: bool = Field(False, description="해당 엔티티의 대표 리소스 여부")


class EntityResourceCreate(EntityResourceBase):
    """
    새로운 엔티티-리소스 연결을 생성하기 위한 Pydantic 모델입니다.
    """
    pass


class EntityResourceUpdate(EntityResourceBase):
    """
    기존 엔티티-리소스 연결 정보를 업데이트하기 위한 Pydantic 모델입니다.
    엔티티-리소스 연결 업데이트용 스키마 (is_main만 변경)
    """
    is_main: bool


class EntityResourceRead(EntityResourceBase):
    """
    엔티티-리소스 연결 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="연결 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    # 연결된 리소스의 상세 정보를 함께 반환
    resource: ResourceRead

    class Config:
        from_attributes = True


# =============================================================================
# 4. 파일 업로드 응답 전용 스키마
# =============================================================================
class ResourceUploadResponse(BaseModel):
    """
    파일/이미지 업로드 성공 시 클라이언트에 반환되는 정보입니다.
    테스트 코드 및 프론트엔드의 요구사항에 맞춤.
    """
    id: int = Field(..., description="저장된 리소스의 고유 ID")
    url: str = Field(..., description="리소스에 접근(다운로드)할 수 있는 URL")
    message: str = Field(default="Resource uploaded successfully.", description="성공 메시지")
