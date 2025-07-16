#!/bin/bash

# --- 스크립트 설명 ---
# migrations/versions 폴더를 비우고 재생성하여
# Alembic 마이그레이션 히스토리를 초기화합니다.

# 프로젝트 루트에서 실행되고 있는지 확인
if [ ! -d "migrations" ]; then
    echo "오류: 이 스크립트는 프로젝트 루트 폴더(backend)에서 실행해야 합니다."
    exit 1
fi

echo "Alembic versions 폴더를 초기화합니다..."

# 기존 versions 폴더 삭제
rm -rf migrations/versions

# 폴더 다시 생성
mkdir -p migrations/versions

# 패키지로 인식할 수 있도록 __init__.py 파일 생성
touch migrations/versions/__init__.py

echo "완료: 'migrations/versions' 폴더가 깨끗하게 초기화되었습니다."