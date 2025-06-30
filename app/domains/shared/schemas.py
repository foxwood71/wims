# app/domains/shared/schemas.py

"""
'shared' 도메인 (PostgreSQL 'app' 스키마)의 Pydantic 스키마를 정의하는 모듈입니다.

이 모듈은 API 요청(생성, 업데이트) 및 응답(조회)에 사용되는 데이터 유효성 검사 및
직렬화를 위한 Pydantic 모델을 포함합니다.
SQLModel의 기능을 활용하여 데이터베이스 ORM 모델과 Pydantic 모델 간의 일관성을 유지합니다.
"""

from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, HttpUrl  # BaseModel도 명시적으로 임포트
from sqlmodel import SQLModel  # SQLModel 클래스 임포트


# =============================================================================
# 1. app.versions 테이블 스키마
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
# 2. app.image_types 테이블 스키마
# =============================================================================
class ImageTypeBase(SQLModel):
    """
    이미지 유형의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    """
    name: str = Field(..., max_length=100, description="이미지 유형 명칭 (예: 설비 사진, 도면)")
    description: Optional[str] = Field(None, description="이미지 유형에 대한 설명")


class ImageTypeCreate(ImageTypeBase):
    """
    새로운 이미지 유형을 생성하기 위한 Pydantic 모델입니다.
    """
    pass


class ImageTypeUpdate(ImageTypeBase):
    """
    기존 이미지 유형을 업데이트하기 위한 Pydantic 모델입니다.
    """
    name: Optional[str] = Field(None, max_length=100, description="이미지 유형 명칭")


class ImageTypeRead(ImageTypeBase):
    """
    이미지 유형 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="이미지 유형 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 3. app.images 테이블 스키마
# =============================================================================
class ImageBase(SQLModel):
    """
    업로드된 이미지의 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    """
    image_type_id: Optional[int] = Field(None, description="이미지 유형 ID (FK)")
    # file_name과 file_path는 실제 파일 업로드 시에만 필요하거나 백엔드에서 생성되므로
    # ImageCreate에서는 별도로 처리될 수 있습니다. 여기서는 모델의 기본 속성으로 정의.
    file_name: Optional[str] = Field(None, max_length=255, description="저장된 파일 이름")
    file_path: Optional[str] = Field(None, max_length=255, description="서버 내 파일 저장 경로")
    file_size_kb: Optional[int] = Field(None, description="파일 크기 (KB)")
    mime_type: Optional[str] = Field(None, max_length=50, description="파일 MIME 타입")
    description: Optional[str] = Field(None, description="이미지에 대한 설명")
    uploaded_by_user_id: Optional[int] = Field(None, description="이미지를 업로드한 사용자 ID (FK)")
    uploaded_at: Optional[datetime] = Field(None, description="이미지 업로드 일시")
    department_id: Optional[int] = Field(None, description="이미지 소유 부서")


class ImageCreate(ImageBase):
    """
    새로운 이미지를 업로드하고 데이터베이스에 기록하기 위한 Pydantic 모델입니다.
    클라이언트가 직접 파일 이름을 지정하지 않으므로 Optional로 두거나,
    라우터에서 동적으로 생성합니다.
    """
    # file_name, file_path, file_size_kb, mime_type, uploaded_at 등은
    # FastAPI의 UploadFile 객체로부터 백엔드에서 직접 추출/생성되므로
    # 클라이언트가 요청 본문에 포함할 필요가 없습니다.
    # 따라서 ImageCreate 스키마에는 이들을 Optional로 두거나 제외할 수 있습니다.
    # 여기서는 ORM 모델과의 일관성을 위해 Base에서 그대로 상속받고,
    # 라우터에서 필요한 필드만 채워넣는 방식으로 사용합니다.
    file_name: str
    file_path: str
    file_size_kb: int
    mime_type: str
    uploaded_by_user_id: int
    uploaded_at: datetime


class ImageUpdate(ImageBase):
    """
    기존 이미지 정보를 업데이트하기 위한 Pydantic 모델입니다.
    모든 필드는 선택 사항입니다 (부분 업데이트 가능).
    """
    # file_name, file_path 등은 업데이트 시 변경되지 않아야 하므로 제외하거나
    # 모델에서 Field(...)로 default=None을 명시적으로 사용합니다.
    image_type_id: Optional[int] = None
    description: Optional[str] = None
    department_id: Optional[int] = None


class ImageRead(ImageBase):
    """
    업로드된 이미지 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="이미지 고유 ID")
    file_name: Optional[str] = Field(None, max_length=255, description="저장된 파일 이름")
    file_path: Optional[str] = Field(None, max_length=255, description="서버 내 파일 저장 경로")
    file_size_kb: Optional[int] = Field(None, description="파일 크기 (KB)")
    mime_type: Optional[str] = Field(None, max_length=50, description="파일 MIME 타입")
    uploaded_by_user_id: Optional[int] = Field(None, description="이미지를 업로드한 사용자 ID (FK)")
    uploaded_at: Optional[datetime] = Field(None, description="이미지 업로드 일시")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True


# =============================================================================
# 4. app.entity_images 테이블 스키마
# =============================================================================
class EntityImageBase(SQLModel):
    """
    엔티티와 이미지 간의 연결 기본 속성을 정의하는 Pydantic/SQLModel Base 스키마입니다.
    """
    image_id: int = Field(..., description="연결할 이미지 ID (필수)")
    entity_type: str = Field(..., max_length=50, description="연결된 엔티티 유형 (예: EQUIPMENT, MATERIAL, LOCATION)")
    entity_id: int = Field(..., description="연결된 엔티티의 ID")
    is_main_image: bool = Field(False, description="해당 엔티티의 대표 이미지 여부")


class EntityImageCreate(EntityImageBase):
    """
    새로운 엔티티-이미지 연결을 생성하기 위한 Pydantic 모델입니다.
    """
    pass


class EntityImageUpdate(EntityImageBase):
    """
    기존 엔티티-이미지 연결 정보를 업데이트하기 위한 Pydantic 모델입니다.
    """
    image_id: Optional[int] = Field(None, description="연결할 이미지 ID")
    entity_type: Optional[str] = Field(None, max_length=50, description="연결된 엔티티 유형")
    entity_id: Optional[int] = Field(None, description="연결된 엔티티의 ID")
    is_main_image: Optional[bool] = Field(None, description="해당 엔티티의 대표 이미지 여부")


class EntityImageRead(EntityImageBase):
    """
    엔티티-이미지 연결 정보를 클라이언트에 응답하기 위한 Pydantic 모델입니다.
    """
    id: int = Field(..., description="연결 고유 ID")
    created_at: datetime = Field(..., description="레코드 생성 일시")
    updated_at: datetime = Field(..., description="레코드 마지막 업데이트 일시")

    class Config:
        from_attributes = True
