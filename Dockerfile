# ==============================================================================
# 1. 빌드 스테이지 (build-env): 애플리케이션 의존성을 설치하고 컴파일합니다.
# ==============================================================================
# Python 공식 이미지 중 3.12.9 버전의 slim-bookworm (Debian Bookworm 기반의 최소 이미지) 사용
# slim 버전은 더 작은 이미지 크기를 위해 개발 도구 등이 최소화되어 있습니다.
FROM python:3.12.9-slim-bookworm AS build-env

# 라벨 (메타데이터): 이미지에 대한 정보 제공
LABEL maintainer="Your Name <your.email@example.com>"
LABEL version="1.0.0"
LABEL description="Docker image for WIMS FastAPI application"

# 필요한 시스템 의존성 설치
# asyncpg 및 psycopg2-binary와 같은 라이브러리는 C 확장을 컴파일해야 할 수 있으므로
# build-base, gcc, libpq-dev(PostgreSQL 개발 라이브러리)를 포함합니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    # 추가적으로 필요한 시스템 라이브러리가 있다면 여기에 추가 (예: ImageMagick 등)
    # imagemagick \
    # libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정 (컨테이너 내부에서 애플리케이션 코드가 위치할 경로)
WORKDIR /app

# Python 환경 설정
# PYTHONDONTWRITEBYTECODE: .pyc 파일 생성을 방지하여 이미지 크기 감소
# PYTHONUNBUFFERED: Python 출력을 버퍼링하지 않고 즉시 콘솔로 출력 (로그 확인 용이)
# PIP_NO_CACHE_DIR: pip 캐시 디렉토리를 사용하지 않아 이미지 크기 감소
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv # 가상 환경 경로 설정

# 가상 환경 생성 (시스템 전체가 아닌 격리된 환경에 의존성 설치)
RUN python -m venv $VIRTUAL_ENV
# 생성된 가상 환경 활성화 (이후 RUN 명령은 이 가상 환경 내에서 실행됨)
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# requirements.txt 파일을 컨테이너로 복사
# 캐싱을 활용하여, requirements.txt가 변경되지 않으면 pip install 단계를 스킵하여 빌드 속도 향상
COPY requirements.txt .

# Python 의존성 설치
# --no-deps: 이미 base 이미지에 포함된 의존성 중복 설치 방지
# --no-cache-dir: pip 캐시 디렉토리 생성 방지 (이미 위에 ENV로 설정했지만 명시적으로 한번 더)
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ==============================================================================
# 2. 최종 실행 스테이지 (production): 실제 애플리케이션을 실행합니다.
# ==============================================================================
# 다시 slim-bookworm 이미지를 사용하지만, 시스템 개발 도구는 포함하지 않아 최종 이미지 크기 최소화
FROM python:3.12.9-slim-bookworm AS production

# 컨테이너 사용자 설정 (루트 권한이 아닌 특정 사용자로 실행하여 보안 강화)
# 유저와 그룹 생성 (예: appuser)
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# 필요한 런타임 시스템 의존성 설치 (PostgreSQL 클라이언트 라이브러리 등)
# libpq5: PostgreSQL 연결을 위한 핵심 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    # 추가적인 런타임 의존성이 있다면 여기에 추가 (예: 이미지 처리 라이브러리)
    # libmagickwand-dev \
    && rm -rf /var/lib/apt/lists/*

# 빌드 스테이지에서 설치된 가상 환경을 최종 이미지로 복사
# 가상 환경만 복사하므로, 불필요한 빌드 도구는 포함되지 않습니다.
COPY --from=build-env /opt/venv /opt/venv

# 가상 환경 활성화
ENV PATH="/opt/venv/bin:$PATH"

# 작업 디렉토리 설정
WORKDIR /app

# 애플리케이션 코드 복사
# .dockerignore 파일을 사용하여 불필요한 파일(예: .git, .env, .venv)은 복사되지 않도록 합니다.
COPY app/ ./app/

# .env 파일은 프로덕션 환경에서 볼륨 마운트나 Secrets로 관리하는 것이 더 좋지만
# 개발/테스트 편의를 위해 여기에 포함시킬 수 있습니다.
# 보안을 위해 컨테이너 외부에서 주입하는 것을 권장합니다.
COPY .env ./.env 

# 포트 노출 (FastAPI가 수신할 포트)
EXPOSE 8000

# 컨테이너를 실행할 기본 사용자 설정
# 이 사용자는 루트 권한이 없으므로 보안 위험이 줄어듭니다.
USER appuser

# 애플리케이션 시작 명령어 (Uvicorn)
# uvicorn app.main:app : app/main.py 파일 내의 FastAPI 인스턴스 'app'을 실행합니다.
# --host 0.0.0.0 : 모든 네트워크 인터페이스에서 연결을 수신합니다.
# --port 8000 : 8000번 포트에서 수신합니다.
# --workers 4 : Uvicorn 워커 수 설정 (CPU 코어 수의 1-2배로 설정 권장)
# --log-level info : 로그 레벨 설정 (info, debug, warning, error, critical)
# Note: --reload 옵션은 개발 환경에서만 사용하고 프로덕션에서는 제거해야 합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]